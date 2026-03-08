"""Figma UI architect skill."""

from ai_skills_toolkit.skills.architecture_designer.schema import ArchitectureSpec
from ai_skills_toolkit.skills.figma_ui_architect.schema import FigmaUiArchitectInput
from ai_skills_toolkit.skills.figma_ui_architect.eval import run_builtin_evaluation
from ai_skills_toolkit.skills.figma_ui_architect.skill import generate_ui_spec, run
from ai_skills_toolkit.skills.repo_analyzer.schema import RepoAnalysis


def enrich_input_from_context(
    data: FigmaUiArchitectInput,
    *,
    architecture_spec: ArchitectureSpec | None = None,
    repo_analysis: RepoAnalysis | None = None,
) -> FigmaUiArchitectInput:
    """Inject architecture and repository context into a Figma UI planning request."""
    repo_context = list(data.repo_context_signals)
    architecture_context = list(data.architecture_context)

    if repo_analysis is not None:
        repo_context.extend(
            [
                f"Repository kind: {repo_analysis.project_kind}",
                *repo_analysis.runtime_surface[:2],
                *repo_analysis.service_map[:1],
            ]
        )
    if architecture_spec is not None:
        architecture_context.extend(
            [
                *architecture_spec.inferred_decisions[:2],
                *architecture_spec.decision_priorities[:2],
                *architecture_spec.tradeoffs[:1],
            ]
        )

    return data.model_copy(
        update={
            "repo_context_signals": [item for item in repo_context if item][:4],
            "architecture_context": [item for item in architecture_context if item][:6],
        }
    )


__all__ = [
    "FigmaUiArchitectInput",
    "generate_ui_spec",
    "run",
    "run_builtin_evaluation",
    "enrich_input_from_context",
]
