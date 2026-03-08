"""Implementation for test_generator."""

from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path
import re
import tokenize

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.core.repo_scan import DEFAULT_EXCLUDED_DIRS, iter_repo_files
from ai_skills_toolkit.skills.test_generator.schema import TestGenerationResult, TestGeneratorInput, TestTarget

EXCLUDED_DIRS = DEFAULT_EXCLUDED_DIRS | {"tests"}
FUNC_RE = re.compile(r"^\s*def\s+([a-zA-Z_]\w*)\s*\(", flags=re.MULTILINE)
CLASS_RE = re.compile(r"^\s*class\s+([a-zA-Z_]\w*)\s*[\(:]", flags=re.MULTILINE)
TODO_RE = re.compile(r"\b(?:TODO|FIXME)\b")
ENTRYPOINT_NAMES = {"cli.py", "__main__.py", "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py"}
NETWORK_MODULES = {"requests", "httpx", "aiohttp", "urllib", "socket"}
FILESYSTEM_CALLS = {
    "open",
    "Path.read_text",
    "Path.write_text",
    "Path.read_bytes",
    "Path.write_bytes",
    "os.remove",
    "os.unlink",
    "os.rename",
}
SUBPROCESS_CALLS = {"subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_output"}


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        parts: list[str] = [node.func.attr]
        current = node.func.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
    return None


def _iter_python_files(repo_path: Path) -> list[Path]:
    files, _ = iter_repo_files(
        repo_path,
        include_hidden=False,
        excluded_dirs=EXCLUDED_DIRS,
        file_filter=lambda path: path.suffix == ".py",
    )
    return files


def _priority(path: Path, focus_paths: list[str]) -> int:
    if not focus_paths:
        return 1
    rel = path.as_posix()
    for index, focus in enumerate(focus_paths):
        normalized_focus = focus.replace("\\", "/")
        if normalized_focus and normalized_focus in rel:
            return 100 - index
    return 0


def _parse_tree(content: str, filename: str) -> ast.AST | None:
    try:
        return ast.parse(content, filename=filename)
    except SyntaxError:
        return None


def _collect_symbols(content: str, filename: str) -> tuple[list[str], list[str], ast.AST | None]:
    tree = _parse_tree(content, filename)
    if tree is None:
        functions = sorted(set(FUNC_RE.findall(content)))
        classes = sorted(set(CLASS_RE.findall(content)))
        return functions, classes, None

    functions = sorted(
        {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    )
    classes = sorted({node.name for node in tree.body if isinstance(node, ast.ClassDef)})
    return functions, classes, tree


def _risk_notes(content: str, tree: ast.AST | None) -> list[str]:
    notes: list[str] = []
    if tree is not None and any(isinstance(node, ast.ExceptHandler) and node.type is None for node in ast.walk(tree)):
        notes.append("Contains bare except blocks.")
    try:
        if any(
            token.type == tokenize.COMMENT and TODO_RE.search(token.string)
            for token in tokenize.generate_tokens(StringIO(content).readline)
        ):
            notes.append("Contains TODO/FIXME markers.")
    except tokenize.TokenError:
        pass
    if tree is not None and any(isinstance(node, ast.Pass) for node in ast.walk(tree)):
        notes.append("Contains pass statements; behavior may be incomplete.")
    return notes


def _module_signals(path: Path, tree: ast.AST | None, functions: list[str], classes: list[str]) -> dict[str, int | bool]:
    signal_defaults: dict[str, int | bool] = {
        "public_functions": len([name for name in functions if not name.startswith("_")]),
        "public_classes": len([name for name in classes if not name.startswith("_")]),
        "complexity_nodes": 0,
        "except_handlers": 0,
        "raise_count": 0,
        "async_functions": 0,
        "network_calls": 0,
        "filesystem_calls": 0,
        "subprocess_calls": 0,
        "entrypoint": path.name in ENTRYPOINT_NAMES,
        "schema_like": False,
    }
    if tree is None:
        return signal_defaults

    complexity_node_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)
    signal_defaults["complexity_nodes"] = sum(isinstance(node, complexity_node_types) for node in ast.walk(tree))
    signal_defaults["except_handlers"] = sum(isinstance(node, ast.ExceptHandler) for node in ast.walk(tree))
    signal_defaults["raise_count"] = sum(isinstance(node, ast.Raise) for node in ast.walk(tree))
    signal_defaults["async_functions"] = sum(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(tree))

    call_names = [
        call_name
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for call_name in [_call_name(node)]
        if call_name
    ]
    signal_defaults["network_calls"] = sum(
        any(call_name == module or call_name.startswith(f"{module}.") for module in NETWORK_MODULES)
        for call_name in call_names
    )
    signal_defaults["filesystem_calls"] = sum(call_name in FILESYSTEM_CALLS for call_name in call_names)
    signal_defaults["subprocess_calls"] = sum(call_name in SUBPROCESS_CALLS for call_name in call_names)

    top_level_defs = [node for node in getattr(tree, "body", []) if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
    only_classes = bool(top_level_defs) and all(isinstance(node, ast.ClassDef) for node in top_level_defs)
    has_pass_only_class = False
    if only_classes:
        has_pass_only_class = all(
            all(isinstance(child, (ast.Pass, ast.Expr, ast.AnnAssign, ast.Assign)) for child in class_node.body)
            for class_node in top_level_defs
            if isinstance(class_node, ast.ClassDef)
        )
    signal_defaults["schema_like"] = only_classes and has_pass_only_class and not signal_defaults["complexity_nodes"]
    return signal_defaults


def _target_type(path: Path, signals: dict[str, int | bool]) -> str:
    if bool(signals["entrypoint"]):
        return "entrypoint"
    if bool(signals["schema_like"]):
        return "schema"
    if int(signals["network_calls"]) or int(signals["filesystem_calls"]) or int(signals["subprocess_calls"]):
        return "integration-heavy"
    if int(signals["public_classes"]) and int(signals["complexity_nodes"]):
        return "stateful-service"
    if int(signals["complexity_nodes"]) or int(signals["raise_count"]) or int(signals["except_handlers"]):
        return "behavioral-module"
    return "utility-module"


def _priority_breakdown(
    path: Path,
    focus_paths: list[str],
    functions: list[str],
    classes: list[str],
    tree: ast.AST | None,
) -> tuple[int, list[str], str, list[str], list[str]]:
    signals = _module_signals(path, tree, functions, classes)
    reasons: list[str] = []
    test_ideas: list[str] = []
    suggested_test_types: list[str] = []

    focus_score = _priority(path, focus_paths)
    if focus_score > 1:
        for focus in focus_paths:
            normalized_focus = focus.replace("\\", "/")
            if normalized_focus and normalized_focus in path.as_posix():
                reasons.append(f"Matches focus path `{normalized_focus}`.")
                break

    public_api_score = int(signals["public_functions"]) * 6 + int(signals["public_classes"]) * 7
    if public_api_score:
        reasons.append(
            f"Exposes {int(signals['public_functions'])} public functions and {int(signals['public_classes'])} public classes."
        )
        suggested_test_types.append("contract")
        test_ideas.append("Cover the public API surface with stable input/output contract tests.")

    complexity_score = int(signals["complexity_nodes"]) * 3 + int(signals["except_handlers"]) * 4 + int(signals["raise_count"]) * 2
    if complexity_score:
        reasons.append("Contains branching, exception handling, or validation logic.")
        suggested_test_types.append("branching")
        test_ideas.append("Exercise success paths, branching behavior, and failure-mode handling for core control flow.")

    integration_score = int(signals["network_calls"]) * 8 + int(signals["filesystem_calls"]) * 6 + int(signals["subprocess_calls"]) * 9
    if integration_score:
        integration_parts: list[str] = []
        if int(signals["network_calls"]):
            integration_parts.append("network calls")
            test_ideas.append("Mock outbound network calls and assert timeout, retry, or error-surface behavior.")
            suggested_test_types.append("integration-boundary")
        if int(signals["filesystem_calls"]):
            integration_parts.append("filesystem writes/reads")
            test_ideas.append("Use tmp_path-based tests for file creation, mutation, and missing-file scenarios.")
            suggested_test_types.append("filesystem")
        if int(signals["subprocess_calls"]):
            integration_parts.append("subprocess execution")
            test_ideas.append("Patch subprocess invocations and verify command arguments plus non-zero exit handling.")
            suggested_test_types.append("subprocess")
        reasons.append(f"Touches {', '.join(integration_parts)}.")

    async_score = int(signals["async_functions"]) * 5
    if async_score:
        reasons.append("Defines async behavior that benefits from explicit event-loop coverage.")
        suggested_test_types.append("async")
        test_ideas.append("Add async pytest coverage for awaited success and exception paths.")

    entrypoint_score = 15 if bool(signals["entrypoint"]) else 0
    if entrypoint_score:
        reasons.append("Looks like an entrypoint module with user-facing orchestration behavior.")
        suggested_test_types.append("cli")
        test_ideas.append("Verify end-to-end entrypoint behavior, argument handling, and exit/error boundaries.")

    size_score = min(path.stat().st_size // 200, 20)
    if size_score >= 8:
        reasons.append("Large enough to justify targeted regression coverage.")

    schema_penalty = -12 if bool(signals["schema_like"]) else 0
    if schema_penalty:
        reasons.append("Mostly schema-like declarations; lower test priority than behavior-heavy modules.")
        test_ideas.append("Keep schema checks narrow: construction, defaults, and validation boundaries.")
        suggested_test_types.append("validation")

    target_type = _target_type(path, signals)
    score = focus_score + public_api_score + complexity_score + integration_score + async_score + entrypoint_score + size_score + schema_penalty
    deduped_test_ideas = list(dict.fromkeys(test_ideas))
    deduped_test_types = list(dict.fromkeys(suggested_test_types))
    return score, reasons, target_type, deduped_test_ideas[:5], deduped_test_types[:4]


def generate_test_plan(data: TestGeneratorInput) -> TestGenerationResult:
    """Inspect repository Python source and prepare actionable pytest test plan."""
    repo = data.repo_path.resolve()
    files = _iter_python_files(repo)
    analyzed_targets: list[tuple[int, int, str, str, list[str], list[str], list[str], list[str], list[str], list[str]]] = []

    notes: list[str] = []
    for file_path in files:
        rel = file_path.relative_to(repo).as_posix()
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        functions, classes, tree = _collect_symbols(content, rel)
        if not functions and not classes:
            continue
        priority_score, priority_reasons, target_type, test_ideas, suggested_test_types = _priority_breakdown(
            file_path,
            data.focus_paths,
            functions,
            classes,
            tree,
        )
        analyzed_targets.append(
            (
                priority_score,
                file_path.stat().st_size,
                rel,
                target_type,
                functions[:15],
                classes[:10],
                priority_reasons[:4],
                _risk_notes(content, tree),
                test_ideas,
                suggested_test_types,
            )
        )

    ranked = sorted(analyzed_targets, key=lambda item: (item[0], item[1], item[2]), reverse=True)

    targets: list[TestTarget] = []
    for score, _, rel, target_type, functions, classes, priority_reasons, risk_notes, test_ideas, suggested_test_types in ranked:
        if len(targets) >= data.max_targets:
            notes.append(f"Target list capped at {data.max_targets}.")
            break
        targets.append(
            TestTarget(
                path=rel,
                target_type=target_type,
                functions=functions,
                classes=classes,
                priority_score=score,
                priority_reasons=priority_reasons,
                risk_notes=risk_notes,
                test_ideas=test_ideas,
                suggested_test_types=suggested_test_types,
            )
        )

    if not targets:
        notes.append("No Python targets discovered outside excluded directories.")

    return TestGenerationResult(
        repository=str(repo),
        framework=data.test_framework,
        targets=targets,
        notes=notes,
    )


def render_markdown(result: TestGenerationResult, include_edge_cases: bool) -> str:
    """Render test planning results into markdown."""
    lines: list[str] = []
    lines.append("# Test Generation Plan")
    lines.append("")
    lines.append(f"- **Repository:** `{result.repository}`")
    lines.append(f"- **Framework:** `{result.framework}`")
    lines.append(f"- **Targets selected:** {len(result.targets)}")
    lines.append("")
    lines.append("## Target Matrix")
    lines.append("")
    if not result.targets:
        lines.append("- No targets found.")
    else:
        for target in result.targets:
            lines.append(f"### `{target.path}`")
            lines.append("")
            lines.append(f"- Target type: `{target.target_type}`")
            lines.append(f"- Priority score: `{target.priority_score}`")
            if target.priority_reasons:
                lines.append("- Why this is high priority:")
                lines.extend([f"  - {reason}" for reason in target.priority_reasons])
            lines.append("- Functions:")
            if target.functions:
                lines.extend([f"  - `{name}`" for name in target.functions])
            else:
                lines.append("  - none")
            lines.append("- Classes:")
            if target.classes:
                lines.extend([f"  - `{name}`" for name in target.classes])
            else:
                lines.append("  - none")
            if target.risk_notes:
                lines.append("- Risk notes:")
                lines.extend([f"  - {note}" for note in target.risk_notes])
            if target.suggested_test_types:
                lines.append("- Suggested test types:")
                lines.extend([f"  - `{name}`" for name in target.suggested_test_types])
            if target.test_ideas:
                lines.append("- Concrete test ideas:")
                lines.extend([f"  - {idea}" for idea in target.test_ideas])
            lines.append("")

    lines.append("## Suggested Test Cases")
    lines.append("")
    if result.targets:
        lines.append("- Start with the highest-priority modules and convert their concrete test ideas into pytest cases.")
        lines.append("- Cover public APIs first, then branch/error handling, then boundary integrations.")
    else:
        lines.append("- Happy path coverage for each public function/class.")
    if include_edge_cases:
        lines.append("- Edge cases: empty input, invalid input, boundary values, and error handling.")
    lines.append("- Regression tests for previously fixed defects.")
    lines.append("- Contract tests for stable I/O behavior.")
    lines.append("")
    lines.append("## Pytest Starter Template")
    lines.append("")
    lines.append("```python")
    lines.append("import pytest")
    lines.append("")
    lines.append("def test_example_happy_path():")
    lines.append("    assert True")
    lines.append("")
    lines.append("def test_example_invalid_input():")
    lines.append("    with pytest.raises(ValueError):")
    lines.append("        raise ValueError('sample')")
    lines.append("```")
    lines.append("")
    if result.notes:
        lines.append("## Notes")
        lines.append("")
        lines.extend([f"- {note}" for note in result.notes])
        lines.append("")
    return "\n".join(lines)


def run(
    data: TestGeneratorInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "test-generation-plan",
    overwrite: bool = False,
) -> SkillRunResult:
    """Execute test_generator and persist markdown output."""
    result = generate_test_plan(data)
    markdown = render_markdown(result, include_edge_cases=data.include_edge_cases)
    output_path = build_output_path(output_dir, "test_generator", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="test_generator",
        output_path=output_path,
        summary=f"Test plan generated with {len(result.targets)} targets.",
        metadata=build_run_metadata(
            artifact_type="test_plan",
            subject=result.repository,
            subject_type="repository",
            warning_count=len(result.notes),
            extra={
                "repository": result.repository,
                "framework": result.framework,
                "target_count": len(result.targets),
                "top_target_paths": [target.path for target in result.targets[:5]],
            },
        ),
    )
