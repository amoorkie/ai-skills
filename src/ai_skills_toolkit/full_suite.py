"""Top-level orchestration for readiness and workflow chain reports."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.design_chain import DesignChainInput, run_design_chain
from ai_skills_toolkit.engineering_chain import EngineeringChainInput, run_engineering_chain
from ai_skills_toolkit.readiness import run_all_evaluations


class FullSuiteInput(BaseModel):
    repo_path: Path = Field(default=Path("."), description="Repository path used for all workflow stages.")
    product_name: str = Field(min_length=2, max_length=120)
    product_goal: str = Field(min_length=10, max_length=600)
    users: list[str] = Field(default_factory=list)
    jtbds: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    preferred_platform: str = Field(default="Web", min_length=2, max_length=30)
    design_tone: str = Field(default="Professional, clear, data-forward", min_length=3, max_length=120)
    review_changed_only: bool = False
    review_base_ref: str | None = Field(default=None, max_length=120)
    review_diff_context_hops: int = Field(default=1, ge=0, le=3)
    include_review_tests: bool = False
    review_max_findings: int = Field(default=80, ge=1, le=1000)
    test_focus_paths: list[str] = Field(default_factory=list)
    test_max_targets: int = Field(default=20, ge=1, le=200)
    doc_title: str = Field(default="Engineering Workflow Documentation", min_length=3, max_length=120)
    doc_audience: str = Field(default="Engineers and AI agents", min_length=3, max_length=120)


def render_full_suite_markdown(
    *,
    readiness_result: SkillRunResult,
    design_result: SkillRunResult,
    engineering_result: SkillRunResult,
) -> str:
    """Render a summary artifact for the full workflow suite."""
    lines: list[str] = []
    lines.append("# Full Workflow Suite Report")
    lines.append("")
    lines.append(f"- **Readiness report:** `{readiness_result.output_path}`")
    lines.append(f"- **Design workflow report:** `{design_result.output_path}`")
    lines.append(f"- **Engineering workflow report:** `{engineering_result.output_path}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- {readiness_result.summary}")
    lines.append(f"- {design_result.summary}")
    lines.append(f"- {engineering_result.summary}")
    lines.append("")
    lines.append("## Included Workflows")
    lines.append("")
    lines.append("- `benchmark-all`: validates built-in skill readiness across the toolkit.")
    lines.append("- `design-chain`: links repository analysis, architecture design, and UI handoff artifacts.")
    lines.append("- `engineering-chain`: links repository analysis, code review, test planning, and documentation artifacts.")
    lines.append("")
    lines.append("## Follow-up")
    lines.append("")
    lines.append("- Treat readiness failures as release blockers before trusting workflow artifacts.")
    lines.append("- Review design and engineering outputs together so architectural assumptions and implementation risks stay aligned.")
    lines.append("- Use the generated reports as a release packet for manual review, not as a substitute for product or engineering approval.")
    lines.append("")
    return "\n".join(lines)


def run_full_suite(
    data: FullSuiteInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "full-suite",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run readiness plus both linked workflow chains and persist a summary report."""
    readiness_result = run_all_evaluations(
        output_dir=output_dir,
        output_name=f"{output_name}-readiness",
        overwrite=overwrite,
    )
    design_result = run_design_chain(
        DesignChainInput(
            repo_path=data.repo_path,
            product_name=data.product_name,
            product_goal=data.product_goal,
            users=data.users,
            jtbds=data.jtbds,
            functional_requirements=data.functional_requirements,
            non_functional_requirements=data.non_functional_requirements,
            constraints=data.constraints,
            assumptions=data.assumptions,
            preferred_platform=data.preferred_platform,
            design_tone=data.design_tone,
        ),
        output_dir=output_dir,
        output_name=f"{output_name}-design",
        overwrite=overwrite,
    )
    engineering_result = run_engineering_chain(
        EngineeringChainInput(
            repo_path=data.repo_path,
            review_changed_only=data.review_changed_only,
            review_base_ref=data.review_base_ref,
            review_diff_context_hops=data.review_diff_context_hops,
            include_review_tests=data.include_review_tests,
            review_max_findings=data.review_max_findings,
            test_focus_paths=data.test_focus_paths,
            test_max_targets=data.test_max_targets,
            doc_title=data.doc_title,
            doc_audience=data.doc_audience,
        ),
        output_dir=output_dir,
        output_name=f"{output_name}-engineering",
        overwrite=overwrite,
    )

    markdown = render_full_suite_markdown(
        readiness_result=readiness_result,
        design_result=design_result,
        engineering_result=engineering_result,
    )
    output_path = build_output_path(output_dir, "full_suite", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)

    warning_count = int(readiness_result.metadata.get("warning_count", 0))
    return SkillRunResult(
        skill_name="full_suite",
        output_path=output_path,
        summary="Full workflow suite completed: readiness, design chain, and engineering chain artifacts created.",
        metadata=build_run_metadata(
            artifact_type="full_suite_report",
            subject=str(data.repo_path),
            subject_type="repository",
            warning_count=warning_count,
            extra={
                "readiness_artifact": str(readiness_result.output_path),
                "design_artifact": str(design_result.output_path),
                "engineering_artifact": str(engineering_result.output_path),
            },
        ),
    )
