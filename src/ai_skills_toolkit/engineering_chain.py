"""Cross-skill orchestration for repository engineering workflows."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.code_reviewer import CodeReviewerInput, run as run_code_reviewer
from ai_skills_toolkit.skills.doc_writer import DocWriterInput, run as run_doc_writer
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput, analyze_repository, run as run_repo_analyzer
from ai_skills_toolkit.skills.test_generator import TestGeneratorInput, run as run_test_generator


class EngineeringChainInput(BaseModel):
    repo_path: Path = Field(default=Path("."), description="Repository path used for the engineering workflow.")
    review_changed_only: bool = False
    review_base_ref: str | None = Field(default=None, max_length=120)
    review_diff_context_hops: int = Field(default=1, ge=0, le=3)
    include_review_tests: bool = False
    review_max_findings: int = Field(default=80, ge=1, le=1000)
    test_focus_paths: list[str] = Field(default_factory=list)
    test_max_targets: int = Field(default=20, ge=1, le=200)
    doc_title: str = Field(default="Engineering Workflow Documentation", min_length=3, max_length=120)
    doc_audience: str = Field(default="Engineers and AI agents", min_length=3, max_length=120)


def render_engineering_chain_markdown(
    *,
    repo_result: SkillRunResult,
    review_result: SkillRunResult,
    test_result: SkillRunResult,
    doc_result: SkillRunResult,
    repo_project_kind: str,
    review_warning_count: int,
    top_target_paths: list[str],
) -> str:
    """Render a summary artifact for the chained engineering workflow."""
    lines: list[str] = []
    lines.append("# Engineering Chain Report")
    lines.append("")
    lines.append(f"- **Repository analysis artifact:** `{repo_result.output_path}`")
    lines.append(f"- **Code review artifact:** `{review_result.output_path}`")
    lines.append(f"- **Test plan artifact:** `{test_result.output_path}`")
    lines.append(f"- **Documentation artifact:** `{doc_result.output_path}`")
    lines.append(f"- **Repository kind:** `{repo_project_kind}`")
    lines.append(f"- **Review findings count:** `{review_warning_count}`")
    if top_target_paths:
        lines.append(f"- **Top test targets:** `{', '.join(top_target_paths[:3])}`")
    lines.append("")
    lines.append("## Pipeline")
    lines.append("")
    lines.append("- `repo_analyzer` established repository topology, runtime, and hotspot context.")
    lines.append("- `code_reviewer` identified prioritized implementation risks for the current workspace.")
    lines.append("- `test_generator` converted source-risk signals into a targeted test plan.")
    lines.append("- `doc_writer` produced repository documentation for onboarding and execution context.")
    lines.append("")
    lines.append("## Follow-up")
    lines.append("")
    lines.append("- Fix high-priority review findings before broadening test coverage work.")
    lines.append("- Turn the highest-ranked test targets into executable tests, not just planning notes.")
    lines.append("- Keep documentation aligned with the reviewed runtime and deployment reality.")
    lines.append("")
    return "\n".join(lines)


def run_engineering_chain(
    data: EngineeringChainInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "engineering-chain",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run repo analysis -> code review -> test generation -> documentation as one linked workflow."""
    repo_input = RepoAnalyzerInput(repo_path=data.repo_path)
    repo_result = run_repo_analyzer(
        repo_input,
        output_dir=output_dir,
        output_name=f"{output_name}-repo-analysis",
        overwrite=overwrite,
    )
    repo_analysis = analyze_repository(repo_input)

    review_result = run_code_reviewer(
        CodeReviewerInput(
            repo_path=data.repo_path,
            include_tests=data.include_review_tests,
            max_findings=data.review_max_findings,
            changed_only=data.review_changed_only,
            base_ref=data.review_base_ref,
            diff_context_hops=data.review_diff_context_hops,
        ),
        output_dir=output_dir,
        output_name=f"{output_name}-code-review",
        overwrite=overwrite,
    )

    test_result = run_test_generator(
        TestGeneratorInput(
            repo_path=data.repo_path,
            focus_paths=data.test_focus_paths,
            max_targets=data.test_max_targets,
        ),
        output_dir=output_dir,
        output_name=f"{output_name}-test-plan",
        overwrite=overwrite,
    )

    doc_result = run_doc_writer(
        DocWriterInput(
            repo_path=data.repo_path,
            title=data.doc_title,
            audience=data.doc_audience,
        ),
        output_dir=output_dir,
        output_name=f"{output_name}-documentation",
        overwrite=overwrite,
    )

    markdown = render_engineering_chain_markdown(
        repo_result=repo_result,
        review_result=review_result,
        test_result=test_result,
        doc_result=doc_result,
        repo_project_kind=repo_analysis.project_kind,
        review_warning_count=int(review_result.metadata.get("warning_count", 0)),
        top_target_paths=list(test_result.metadata.get("top_target_paths", [])),
    )
    output_path = build_output_path(output_dir, "engineering_chain", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)

    return SkillRunResult(
        skill_name="engineering_chain",
        output_path=output_path,
        summary="Engineering chain completed: repository, review, test-plan, and documentation artifacts created.",
        metadata=build_run_metadata(
            artifact_type="engineering_chain_report",
            subject=str(data.repo_path),
            subject_type="repository",
            warning_count=int(review_result.metadata.get("warning_count", 0)),
            extra={
                "repo_artifact": str(repo_result.output_path),
                "review_artifact": str(review_result.output_path),
                "test_artifact": str(test_result.output_path),
                "doc_artifact": str(doc_result.output_path),
                "repo_project_kind": repo_analysis.project_kind,
                "top_target_paths": list(test_result.metadata.get("top_target_paths", [])),
            },
        ),
    )
