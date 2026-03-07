"""Implementation for code_reviewer."""

from __future__ import annotations

from pathlib import Path
import re

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.skills.code_reviewer.schema import CodeReviewReport, CodeReviewerInput, ReviewFinding

EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}


def _iter_source_files(repo_path: Path, include_tests: bool) -> list[Path]:
    files: list[Path] = []
    for path in repo_path.rglob("*.py"):
        rel_parts = set(path.relative_to(repo_path).parts)
        if rel_parts.intersection(EXCLUDED_DIRS):
            continue
        if not include_tests and "tests" in rel_parts:
            continue
        files.append(path)
    return sorted(files)


def _extract_findings(rel_path: str, content: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    lines = content.splitlines()
    is_test_file = rel_path.startswith("tests/") or "/tests/" in rel_path
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("except:"):
            findings.append(
                ReviewFinding(
                    severity="high",
                    path=rel_path,
                    line=idx,
                    title="Bare except",
                    detail="Catches all exceptions and can hide defects. Catch explicit exception types.",
                )
            )
        if "eval(" in stripped:
            findings.append(
                ReviewFinding(
                    severity="high",
                    path=rel_path,
                    line=idx,
                    title="Use of eval",
                    detail="`eval` can execute arbitrary code and introduces security risks.",
                )
            )
        if re.search(r"\bprint\s*\(", stripped):
            findings.append(
                ReviewFinding(
                    severity="low",
                    path=rel_path,
                    line=idx,
                    title="Debug print statement",
                    detail="Use structured logging instead of print for production observability.",
                )
            )
        if "TODO" in stripped or "FIXME" in stripped:
            findings.append(
                ReviewFinding(
                    severity="medium",
                    path=rel_path,
                    line=idx,
                    title="Unresolved TODO/FIXME",
                    detail="Track unfinished work via issue tracker and remove stale markers.",
                )
            )
        if "assert " in stripped and "pytest" not in rel_path and not is_test_file:
            findings.append(
                ReviewFinding(
                    severity="low",
                    path=rel_path,
                    line=idx,
                    title="Runtime assert in non-test module",
                    detail="Assertions can be disabled with optimizations. Prefer explicit exceptions for validation.",
                )
            )
    return findings


def review_repository(data: CodeReviewerInput) -> CodeReviewReport:
    """Run heuristic review over local repository source files."""
    repo = data.repo_path.resolve()
    findings: list[ReviewFinding] = []
    for file_path in _iter_source_files(repo, include_tests=data.include_tests):
        rel = file_path.relative_to(repo).as_posix()
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        findings.extend(_extract_findings(rel, content))

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    findings = sorted(findings, key=lambda f: (severity_rank[f.severity], f.path, f.line))
    if not data.include_low_severity:
        findings = [f for f in findings if f.severity != "low"]
    findings = findings[: data.max_findings]

    summary = (
        "No findings detected by heuristic review."
        if not findings
        else f"Detected {len(findings)} findings. Prioritize high-severity items first."
    )
    return CodeReviewReport(repository=str(repo), findings=findings, summary=summary)


def render_markdown(report: CodeReviewReport) -> str:
    """Render code-review findings into markdown report."""
    lines: list[str] = []
    lines.append("# Code Review Report")
    lines.append("")
    lines.append(f"- **Repository:** `{report.repository}`")
    lines.append(f"- **Summary:** {report.summary}")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not report.findings:
        lines.append("- None.")
    else:
        for index, finding in enumerate(report.findings, start=1):
            lines.append(
                f"{index}. **[{finding.severity.upper()}] {finding.title}** "
                f"at `{finding.path}:{finding.line}`"
            )
            lines.append(f"   - {finding.detail}")
    lines.append("")
    lines.append("## Recommended Next Actions")
    lines.append("")
    lines.append("- Fix high-severity findings first.")
    lines.append("- Add regression tests for each confirmed bug.")
    lines.append("- Re-run review after patching to verify cleanup.")
    lines.append("")
    return "\n".join(lines)


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
        metadata={"finding_count": len(report.findings), "repository": report.repository},
    )
