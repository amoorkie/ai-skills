"""Cross-skill orchestration for repository-aware product design artifacts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.architecture_designer import (
    ArchitectureDesignerInput,
    design_architecture,
    enrich_input_from_repo_analysis,
    run as run_architecture_designer,
)
from ai_skills_toolkit.skills.figma_ui_architect import (
    FigmaUiArchitectInput,
    enrich_input_from_context,
    run as run_figma_ui_architect,
)
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput, analyze_repository, run as run_repo_analyzer


class DesignChainInput(BaseModel):
    repo_path: Path = Field(default=Path("."), description="Repository path used for upstream context.")
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


def render_design_chain_markdown(
    *,
    repo_result: SkillRunResult,
    architecture_result: SkillRunResult,
    figma_result: SkillRunResult,
    repo_project_kind: str,
    architecture_confidence: str,
    figma_confidence: str,
) -> str:
    """Render a summary artifact for the chained design workflow."""
    lines: list[str] = []
    lines.append("# Design Chain Report")
    lines.append("")
    lines.append(f"- **Repository analysis artifact:** `{repo_result.output_path}`")
    lines.append(f"- **Architecture spec artifact:** `{architecture_result.output_path}`")
    lines.append(f"- **Figma UI architecture artifact:** `{figma_result.output_path}`")
    lines.append(f"- **Repository kind:** `{repo_project_kind}`")
    lines.append(f"- **Architecture confidence:** `{architecture_confidence}`")
    lines.append(f"- **UI handoff confidence:** `{figma_confidence}`")
    lines.append("")
    lines.append("## Pipeline")
    lines.append("")
    lines.append("- `repo_analyzer` established runtime, service, and hotspot context.")
    lines.append("- `architecture_designer` consumed repository context and produced product/architecture decisions.")
    lines.append("- `figma_ui_architect` consumed both repository and architecture context to produce a UI handoff plan.")
    lines.append("")
    lines.append("## Follow-up")
    lines.append("")
    lines.append("- Validate repository-derived assumptions against real deployment/runtime constraints.")
    lines.append("- Review architecture decision priorities before committing UI flows and component contracts.")
    lines.append("- Use the generated UI handoff as the source for design-to-code implementation, not as a substitute for product sign-off.")
    lines.append("")
    return "\n".join(lines)


def run_design_chain(
    data: DesignChainInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "design-chain",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run repo analysis -> architecture design -> figma UI planning as one linked workflow."""
    repo_input = RepoAnalyzerInput(repo_path=data.repo_path)
    repo_result = run_repo_analyzer(
        repo_input,
        output_dir=output_dir,
        output_name=f"{output_name}-repo-analysis",
        overwrite=overwrite,
    )
    repo_analysis = analyze_repository(repo_input)

    architecture_input = ArchitectureDesignerInput(
        product_name=data.product_name,
        product_goal=data.product_goal,
        primary_users=data.users,
        functional_requirements=data.functional_requirements or data.jtbds,
        non_functional_requirements=data.non_functional_requirements,
        constraints=data.constraints,
        assumptions=data.assumptions,
    )
    architecture_input = enrich_input_from_repo_analysis(architecture_input, repo_analysis)
    architecture_result = run_architecture_designer(
        architecture_input,
        output_dir=output_dir,
        output_name=f"{output_name}-architecture",
        overwrite=overwrite,
    )
    architecture_spec = design_architecture(architecture_input)

    figma_input = FigmaUiArchitectInput(
        product_name=data.product_name,
        product_goal=data.product_goal,
        users=data.users,
        jtbds=data.jtbds or data.functional_requirements,
        constraints=data.constraints,
        preferred_platform=data.preferred_platform,
        design_tone=data.design_tone,
    )
    figma_input = enrich_input_from_context(
        figma_input,
        architecture_spec=architecture_spec,
        repo_analysis=repo_analysis,
    )
    figma_result = run_figma_ui_architect(
        figma_input,
        output_dir=output_dir,
        output_name=f"{output_name}-figma-ui",
        overwrite=overwrite,
    )

    markdown = render_design_chain_markdown(
        repo_result=repo_result,
        architecture_result=architecture_result,
        figma_result=figma_result,
        repo_project_kind=repo_analysis.project_kind,
        architecture_confidence=architecture_result.metadata.get("confidence", "unknown"),
        figma_confidence=figma_result.metadata.get("confidence", "unknown"),
    )
    output_path = build_output_path(output_dir, "design_chain", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)

    return SkillRunResult(
        skill_name="design_chain",
        output_path=output_path,
        summary="Design chain completed: repository, architecture, and UI artifacts created.",
        metadata=build_run_metadata(
            artifact_type="design_chain_report",
            subject=data.product_name,
            subject_type="product",
            warning_count=0,
            extra={
                "repo_artifact": str(repo_result.output_path),
                "architecture_artifact": str(architecture_result.output_path),
                "figma_artifact": str(figma_result.output_path),
                "repo_project_kind": repo_analysis.project_kind,
                "architecture_confidence": architecture_result.metadata.get("confidence", "unknown"),
                "figma_confidence": figma_result.metadata.get("confidence", "unknown"),
            },
        ),
    )
