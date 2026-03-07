"""Implementation for test_generator."""

from __future__ import annotations

from pathlib import Path
import re

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.skills.test_generator.schema import TestGenerationResult, TestGeneratorInput, TestTarget

EXCLUDED_DIRS = {"tests", ".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}
FUNC_RE = re.compile(r"^\s*def\s+([a-zA-Z_]\w*)\s*\(", flags=re.MULTILINE)
CLASS_RE = re.compile(r"^\s*class\s+([a-zA-Z_]\w*)\s*[\(:]", flags=re.MULTILINE)


def _iter_python_files(repo_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_path.rglob("*.py"):
        rel_parts = set(path.relative_to(repo_path).parts)
        if rel_parts.intersection(EXCLUDED_DIRS):
            continue
        files.append(path)
    return sorted(files)


def _priority(path: Path, focus_paths: list[str]) -> int:
    if not focus_paths:
        return 1
    rel = path.as_posix()
    for index, focus in enumerate(focus_paths):
        normalized_focus = focus.replace("\\", "/")
        if normalized_focus and normalized_focus in rel:
            return 100 - index
    return 0


def _risk_notes(content: str) -> list[str]:
    notes: list[str] = []
    if "except:" in content:
        notes.append("Contains bare except blocks.")
    if "TODO" in content or "FIXME" in content:
        notes.append("Contains TODO/FIXME markers.")
    if "pass" in content:
        notes.append("Contains pass statements; behavior may be incomplete.")
    return notes


def generate_test_plan(data: TestGeneratorInput) -> TestGenerationResult:
    """Inspect repository Python source and prepare actionable pytest test plan."""
    repo = data.repo_path.resolve()
    files = _iter_python_files(repo)
    ranked = sorted(files, key=lambda p: (_priority(p.relative_to(repo), data.focus_paths), -p.stat().st_size), reverse=True)

    targets: list[TestTarget] = []
    notes: list[str] = []

    for file_path in ranked:
        if len(targets) >= data.max_targets:
            notes.append(f"Target list capped at {data.max_targets}.")
            break
        rel = file_path.relative_to(repo).as_posix()
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        functions = sorted(set(FUNC_RE.findall(content)))
        classes = sorted(set(CLASS_RE.findall(content)))
        if not functions and not classes:
            continue
        targets.append(
            TestTarget(
                path=rel,
                functions=functions[:15],
                classes=classes[:10],
                risk_notes=_risk_notes(content),
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
            lines.append("")

    lines.append("## Suggested Test Cases")
    lines.append("")
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
        metadata={"target_count": len(result.targets), "repository": result.repository},
    )
