"""Implementation for doc_writer."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.skills.doc_writer.schema import DocWriterInput
from ai_skills_toolkit.skills.repo_analyzer.schema import RepoAnalyzerInput
from ai_skills_toolkit.skills.repo_analyzer.skill import analyze_repository


def _collect_top_level_entries(repo_path: Path, max_entries: int) -> list[str]:
    entries = sorted(repo_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    rendered: list[str] = []
    for entry in entries[:max_entries]:
        entry_type = "dir" if entry.is_dir() else "file"
        rendered.append(f"- `{entry.name}` ({entry_type})")
    if len(entries) > max_entries:
        rendered.append(f"- ... ({len(entries) - max_entries} more entries)")
    return rendered


def generate_document(data: DocWriterInput) -> str:
    """Generate repository documentation based on live local repository analysis."""
    analysis = analyze_repository(RepoAnalyzerInput(repo_path=data.repo_path))
    lines: list[str] = []
    lines.append(f"# {data.title}")
    lines.append("")
    lines.append(f"**Audience:** {data.audience}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        "This document was generated from local repository inspection and is intended as a practical "
        "starting point for onboarding, planning, and AI-assisted development."
    )
    lines.append("")
    lines.append("## Repository Snapshot")
    lines.append("")
    lines.append(f"- **Path:** `{analysis.repo_path}`")
    lines.append(f"- **Files analyzed:** {analysis.total_files}")
    lines.append(f"- **Directories discovered:** {analysis.total_dirs}")
    lines.append(f"- **Total size analyzed:** {analysis.total_size_bytes} bytes")
    lines.append("")
    lines.append("## Top-Level Structure")
    lines.append("")
    lines.extend(_collect_top_level_entries(data.repo_path, data.max_top_level_entries))
    lines.append("")
    lines.append("## Technology Signals")
    lines.append("")
    if analysis.language_breakdown:
        for language, count in analysis.language_breakdown.items():
            lines.append(f"- {language}: {count} files")
    else:
        lines.append("- No language signals detected.")
    lines.append("")
    lines.append("## Key Files")
    lines.append("")
    if analysis.key_files:
        for key_file in analysis.key_files:
            lines.append(f"- `{key_file}`")
    else:
        lines.append("- No common key files were detected.")
    lines.append("")
    lines.append("## Engineering Notes")
    lines.append("")
    if analysis.notes:
        lines.extend([f"- {note}" for note in analysis.notes])
    else:
        lines.append("- Repository scan completed without warnings.")
    lines.append("")
    if data.include_setup_checklist:
        lines.append("## Setup Checklist")
        lines.append("")
        lines.append("- Verify runtime/toolchain versions.")
        lines.append("- Install dependencies from lock files or project manifests.")
        lines.append("- Run baseline tests and linters.")
        lines.append("- Capture local architecture notes and unresolved assumptions.")
        lines.append("")
    lines.append("## Suggested Next Documentation")
    lines.append("")
    lines.append("- API contract reference")
    lines.append("- Domain model and glossary")
    lines.append("- Deployment and operations runbook")
    lines.append("- Quality and test strategy")
    lines.append("")
    return "\n".join(lines)


def run(
    data: DocWriterInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "repository-documentation",
    overwrite: bool = False,
) -> SkillRunResult:
    """Execute doc_writer and save markdown documentation."""
    markdown = generate_document(data)
    output_path = build_output_path(output_dir, "doc_writer", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="doc_writer",
        output_path=output_path,
        summary="Documentation generated from repository analysis.",
        metadata={"repo_path": str(data.repo_path.resolve())},
    )
