"""Implementation for code_reviewer."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.core.repo_scan import DEFAULT_EXCLUDED_DIRS, iter_repo_files
from ai_skills_toolkit.skills.code_reviewer.analyzers import extract_ast_findings, extract_semantic_findings
from ai_skills_toolkit.skills.code_reviewer.ranking import (
    build_risk_clusters,
    cluster_findings,
    severity_counts,
    sort_findings,
    top_risk_areas,
)
from ai_skills_toolkit.skills.code_reviewer.render import render_markdown
from ai_skills_toolkit.skills.code_reviewer.schema import CodeReviewReport, CodeReviewerInput

EXCLUDED_DIRS = DEFAULT_EXCLUDED_DIRS | {"tests"}


def _iter_source_files(repo_path: Path, include_tests: bool) -> list[Path]:
    excluded_dirs = DEFAULT_EXCLUDED_DIRS if include_tests else EXCLUDED_DIRS
    files, _ = iter_repo_files(
        repo_path,
        include_hidden=False,
        excluded_dirs=excluded_dirs,
        file_filter=lambda path: path.suffix == ".py",
    )
    return files


def _changed_python_rel_paths(repo_path: Path, base_ref: str | None) -> tuple[set[str] | None, list[str]]:
    assumptions: list[str] = []
    try:
        if base_ref:
            diff = subprocess.run(
                ["git", "diff", "--name-only", f"{base_ref}...HEAD", "--", "*.py"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if diff.returncode != 0:
                assumptions.append(f"Could not resolve git diff from `{base_ref}`; falling back to full repository review.")
                return None, assumptions
            changed = {line.strip().replace("\\", "/") for line in diff.stdout.splitlines() if line.strip()}
            return changed, assumptions

        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if status.returncode != 0:
            assumptions.append("Git status was unavailable; falling back to full repository review.")
            return None, assumptions
        changed: set[str] = set()
        for line in status.stdout.splitlines():
            if len(line) < 4:
                continue
            path_text = line[3:].strip()
            if " -> " in path_text:
                path_text = path_text.split(" -> ", maxsplit=1)[1].strip()
            if path_text.endswith(".py"):
                changed.add(path_text.replace("\\", "/"))
        return changed, assumptions
    except OSError:
        assumptions.append("Git executable was unavailable; falling back to full repository review.")
        return None, assumptions


def _module_name_for_rel(rel_path: str) -> str:
    module = rel_path.removesuffix(".py").replace("/", ".")
    if module.endswith(".__init__"):
        module = module[: -len(".__init__")]
    return module


def _resolve_import_targets(module_name: str, level: int, imported_module: str | None) -> list[str]:
    parts = module_name.split(".") if module_name else []
    package_parts = parts[:-1]
    if level > 0:
        anchor_parts = package_parts[: max(0, len(package_parts) - (level - 1))]
        if imported_module:
            return [".".join(anchor_parts + imported_module.split("."))]
        return [".".join(anchor_parts)] if anchor_parts else []
    if imported_module:
        return [imported_module]
    return []


def _imported_module_names(rel_path: str, content: str) -> set[str]:
    try:
        tree = ast.parse(content, filename=rel_path)
    except SyntaxError:
        return set()

    current_module = _module_name_for_rel(rel_path)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imported.update(
                target
                for target in _resolve_import_targets(current_module, node.level, node.module)
                if target
            )
    return imported


def _build_import_graph(repo: Path, files: list[Path]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    module_index = { _module_name_for_rel(file_path.relative_to(repo).as_posix()): file_path.relative_to(repo).as_posix() for file_path in files }
    outgoing: dict[str, set[str]] = {}
    incoming: dict[str, set[str]] = {}

    for file_path in files:
        rel = file_path.relative_to(repo).as_posix()
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        targets: set[str] = set()
        for imported_module in _imported_module_names(rel, content):
            candidate = imported_module
            while candidate:
                mapped = module_index.get(candidate)
                if mapped:
                    targets.add(mapped)
                    break
                if "." not in candidate:
                    break
                candidate = candidate.rsplit(".", maxsplit=1)[0]
        outgoing[rel] = targets
        for target in targets:
            incoming.setdefault(target, set()).add(rel)
    return outgoing, incoming


def _expand_with_import_graph(
    repo: Path,
    files: list[Path],
    selected_rel_paths: set[str],
    hops: int,
) -> set[str]:
    if hops <= 0 or not selected_rel_paths:
        return selected_rel_paths
    outgoing, incoming = _build_import_graph(repo, files)
    expanded = set(selected_rel_paths)
    frontier = set(selected_rel_paths)
    for _ in range(hops):
        next_frontier: set[str] = set()
        for rel in frontier:
            next_frontier.update(outgoing.get(rel, set()))
            next_frontier.update(incoming.get(rel, set()))
        next_frontier -= expanded
        if not next_frontier:
            break
        expanded.update(next_frontier)
        frontier = next_frontier
    return expanded


def _resolve_review_files(repo: Path, data: CodeReviewerInput) -> tuple[list[Path], list[str], bool]:
    all_files = _iter_source_files(repo, include_tests=data.include_tests)
    assumptions: list[str] = []
    if not data.changed_only:
        return all_files, assumptions, False

    changed_rel_paths, diff_assumptions = _changed_python_rel_paths(repo, data.base_ref)
    assumptions.extend(diff_assumptions)
    if changed_rel_paths is None:
        return all_files, assumptions, False

    changed_parent_dirs = {str(Path(rel_path).parent).replace("\\", "/") for rel_path in changed_rel_paths}
    selected_rel_paths = {
        file_path.relative_to(repo).as_posix()
        for file_path in all_files
        if file_path.relative_to(repo).as_posix() in changed_rel_paths
        or file_path.relative_to(repo).parent.as_posix() in changed_parent_dirs
    }
    expanded_rel_paths = _expand_with_import_graph(repo, all_files, selected_rel_paths, data.diff_context_hops)
    selected = [file_path for file_path in all_files if file_path.relative_to(repo).as_posix() in expanded_rel_paths]
    if not selected:
        assumptions.append("Diff-aware review found no changed Python files, so no source files were analyzed.")
    else:
        assumptions.append(
            f"Diff-aware review expanded changed files to sibling and import-linked Python modules within {data.diff_context_hops} hop(s)."
        )
    return selected, assumptions, True


def review_repository(data: CodeReviewerInput) -> CodeReviewReport:
    """Run heuristic review over local repository source files."""
    repo = data.repo_path.resolve()
    findings = []
    source_texts: dict[str, str] = {}
    selected_files, assumptions, diff_active = _resolve_review_files(repo, data)

    for file_path in selected_files:
        rel = file_path.relative_to(repo).as_posix()
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        source_texts[rel] = content
        findings.extend(extract_ast_findings(rel, content))

    findings.extend(extract_semantic_findings(source_texts))
    findings = cluster_findings(findings)
    if not data.include_low_severity:
        findings = [finding for finding in findings if finding.severity != "low"]
    findings = sort_findings(findings)[: data.max_findings]
    counts = severity_counts(findings)

    summary = (
        "No findings detected by heuristic review."
        if not findings
        else (
            f"Detected {len(findings)} findings "
            f"({counts['high']} high, {counts['medium']} medium, {counts['low']} low). "
            "Prioritize high-severity items first."
        )
    )

    return CodeReviewReport(
        repository=str(repo),
        findings=findings,
        top_risk_clusters=build_risk_clusters(findings),
        coverage={
            "ast_rules": True,
            "semantic_rules": True,
            "tests_included": data.include_tests,
            "hidden_files_included": False,
            "diff_aware": diff_active,
            "import_graph_context": diff_active and data.diff_context_hops > 0,
        },
        assumptions=[
            "Review is heuristic and based on the current workspace snapshot.",
            "Semantic findings are inferred from code structure and may require manual confirmation.",
            *assumptions,
        ],
        review_mode="ast+token+semantic+diff+graph" if diff_active else "ast+token+semantic",
        summary=summary,
    )


def run(
    data: CodeReviewerInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "code-review-report",
    overwrite: bool = False,
) -> SkillRunResult:
    """Execute code_reviewer and persist markdown findings report."""
    report = review_repository(data)
    markdown = render_markdown(report)
    output_path = build_output_path(output_dir, "code_reviewer", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="code_reviewer",
        output_path=output_path,
        summary=report.summary,
        metadata=build_run_metadata(
            artifact_type="code_review_report",
            subject=report.repository,
            subject_type="repository",
            warning_count=len(report.findings),
            extra={
                "repository": report.repository,
                "finding_count": len(report.findings),
                "high_severity_count": counts["high"] if (counts := severity_counts(report.findings)) else 0,
                "medium_severity_count": counts["medium"] if counts else 0,
                "low_severity_count": counts["low"] if counts else 0,
                "rule_count": len({finding.rule_id for finding in report.findings}),
                "top_risk_areas": top_risk_areas(report.findings),
                "review_coverage_mode": report.review_mode,
                "category_count": len({finding.category for finding in report.findings}),
                "cluster_count": len(report.top_risk_clusters),
            },
        ),
    )
