"""Implementation for doc_writer."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.doc_writer.schema import DocWriterInput
from ai_skills_toolkit.skills.repo_analyzer.schema import RepoAnalysis, RepoAnalyzerInput
from ai_skills_toolkit.skills.repo_analyzer.skill import analyze_repository


def _collect_top_level_entries(repo_path: Path, max_entries: int) -> list[str]:
    entries = sorted(
        (entry for entry in repo_path.iterdir() if not entry.name.startswith(".")),
        key=lambda p: (not p.is_dir(), p.name.lower()),
    )
    rendered: list[str] = []
    for entry in entries[:max_entries]:
        entry_type = "dir" if entry.is_dir() else "file"
        rendered.append(f"- `{entry.name}` ({entry_type})")
    if len(entries) > max_entries:
        rendered.append(f"- ... ({len(entries) - max_entries} more entries)")
    return rendered


def _audience_mode(audience: str) -> str:
    audience_lower = audience.lower()
    if "ai" in audience_lower or "agent" in audience_lower:
        return "ai_agents"
    if "platform" in audience_lower or "infra" in audience_lower or "ops" in audience_lower:
        return "platform"
    return "engineers"


def _executive_summary(analysis: RepoAnalysis, audience: str) -> str:
    mode = _audience_mode(audience)
    if mode == "ai_agents":
        return (
            f"This repository appears to be a `{analysis.project_kind}` with {analysis.total_files} analyzed files. "
            "Use the runtime signals, key files, and top-level structure below as the shortest path for planning and tool use."
        )
    if mode == "platform":
        return (
            f"This repository appears to be a `{analysis.project_kind}`. Focus first on entrypoints, packaging/tooling signals, "
            "test coverage signals, and deployment-related files before changing runtime or release workflows."
        )
    return (
        f"This repository appears to be a `{analysis.project_kind}` with clear language and tooling signals. "
        "Use this document as a starting point for onboarding, code navigation, and planning follow-up documentation."
    )


def _audience_guidance(analysis: RepoAnalysis, audience: str) -> list[str]:
    mode = _audience_mode(audience)
    if mode == "ai_agents":
        guidance = [
            "Start from key files and likely entrypoints before scanning the full tree.",
            "Use project kind and tooling signals to choose the right skill or execution path.",
            "Treat notes and missing signals as uncertainty markers, not as hard facts.",
        ]
    elif mode == "platform":
        guidance = [
            "Validate packaging, CI, test entrypoints, and deployment markers before changing runtime paths.",
            "Check whether the test suite and install commands align with the current manifests.",
            "Review environment, secrets, and rollback assumptions in deployment-related files.",
        ]
    else:
        guidance = [
            "Start with likely entrypoints and key files to understand the main execution paths.",
            "Use language and tooling signals to map where build, test, and release behavior lives.",
            "Prefer documenting assumptions and unresolved gaps while exploring the codebase.",
        ]
    if analysis.test_file_count == 0:
        guidance.append("No dedicated test files were detected, so verify quality gates manually before assuming coverage.")
    return guidance


def _setup_checklist(analysis: RepoAnalysis) -> list[str]:
    checklist: list[str] = []
    if any("Python packaging manifest" in signal for signal in analysis.tooling_signals):
        checklist.append("Install Python dependencies from `pyproject.toml` or `requirements.txt`.")
    if any("Node package manifest" in signal for signal in analysis.tooling_signals):
        checklist.append("Install Node dependencies from `package.json` and its lockfile if present.")
    if any("Docker container build" in signal for signal in analysis.tooling_signals):
        checklist.append("Verify container build assumptions before relying on local runtime parity.")
    if analysis.test_file_count > 0:
        checklist.append("Run the detected test suite before making behavioral changes.")
    else:
        checklist.append("Establish a smoke-test path because no dedicated test suite was detected.")
    checklist.append("Capture runtime entrypoints and project-specific assumptions before implementation work.")
    return checklist


def _suggested_next_docs(analysis: RepoAnalysis, audience: str) -> list[str]:
    suggestions: list[str] = []
    mode = _audience_mode(audience)
    if analysis.project_kind in {"python_cli", "python_service"}:
        suggestions.append("Runtime entrypoints and command/reference guide")
    if analysis.project_kind in {"frontend_app", "multi_language_toolkit"}:
        suggestions.append("Build pipeline and frontend environment guide")
    if any("Docker container build" in signal for signal in analysis.tooling_signals):
        suggestions.append("Deployment and container operations runbook")
    if analysis.test_file_count > 0:
        suggestions.append("Quality and test strategy")
    else:
        suggestions.append("Testing gaps and validation strategy")
    if mode == "ai_agents":
        suggestions.append("Agent operating notes and repository navigation map")
    else:
        suggestions.append("Domain model and glossary")
    suggestions.append("API contract reference")
    deduped: list[str] = []
    for item in suggestions:
        if item not in deduped:
            deduped.append(item)
    return deduped


def generate_document(data: DocWriterInput, analysis: RepoAnalysis | None = None) -> str:
    """Generate repository documentation based on live local repository analysis."""
    analysis = analysis or analyze_repository(RepoAnalyzerInput(repo_path=data.repo_path))
    lines: list[str] = []
    lines.append(f"# {data.title}")
    lines.append("")
    lines.append(f"**Audience:** {data.audience}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(_executive_summary(analysis, data.audience))
    lines.append("")
    lines.append("## Repository Snapshot")
    lines.append("")
    lines.append(f"- **Path:** `{analysis.repo_path}`")
    lines.append(f"- **Project kind:** `{analysis.project_kind}`")
    lines.append(f"- **Files analyzed:** {analysis.total_files}")
    lines.append(f"- **Directories discovered:** {analysis.total_dirs}")
    lines.append(f"- **Test files discovered:** {analysis.test_file_count}")
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
    lines.append("## Runtime Signals")
    lines.append("")
    if analysis.entrypoints:
        lines.append("- Likely entrypoints:")
        lines.extend([f"  - `{entrypoint}`" for entrypoint in analysis.entrypoints])
    else:
        lines.append("- Likely entrypoints: none detected")
    if analysis.tooling_signals:
        lines.append("- Tooling signals:")
        lines.extend([f"  - {signal}" for signal in analysis.tooling_signals])
    else:
        lines.append("- Tooling signals: none detected")
    lines.append("")
    lines.append("## Audience Guidance")
    lines.append("")
    lines.extend([f"- {item}" for item in _audience_guidance(analysis, data.audience)])
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
        lines.extend([f"- {item}" for item in _setup_checklist(analysis)])
        lines.append("")
    lines.append("## Suggested Next Documentation")
    lines.append("")
    lines.extend([f"- {item}" for item in _suggested_next_docs(analysis, data.audience)])
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
    analysis = analyze_repository(RepoAnalyzerInput(repo_path=data.repo_path))
    markdown = generate_document(data, analysis=analysis)
    output_path = build_output_path(output_dir, "doc_writer", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="doc_writer",
        output_path=output_path,
        summary="Documentation generated from repository analysis.",
        metadata=build_run_metadata(
            artifact_type="repository_documentation",
            subject=str(data.repo_path.resolve()),
            subject_type="repository",
            warning_count=len(analysis.notes),
            extra={
                "repo_path": str(data.repo_path.resolve()),
                "project_kind": analysis.project_kind,
                "file_count": analysis.total_files,
                "directory_count": analysis.total_dirs,
                "test_file_count": analysis.test_file_count,
                "audience": data.audience,
                "include_setup_checklist": data.include_setup_checklist,
            },
        ),
    )
