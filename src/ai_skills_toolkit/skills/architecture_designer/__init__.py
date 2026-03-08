"""Architecture designer skill."""

from ai_skills_toolkit.skills.architecture_designer.schema import ArchitectureDesignerInput
from ai_skills_toolkit.skills.architecture_designer.eval import run_builtin_evaluation
from ai_skills_toolkit.skills.architecture_designer.skill import design_architecture, run
from ai_skills_toolkit.skills.repo_analyzer.schema import RepoAnalysis


def enrich_input_from_repo_analysis(data: ArchitectureDesignerInput, analysis: RepoAnalysis) -> ArchitectureDesignerInput:
    """Inject high-value repository context into an architecture-design request."""
    repo_context_signals = [
        f"Repository kind: {analysis.project_kind}",
        *analysis.runtime_surface[:2],
        *analysis.service_map[:2],
        *analysis.boundary_hotspots[:1],
    ]
    merged = [item for item in repo_context_signals if item]
    return data.model_copy(update={"repo_context_signals": merged[:5]})


__all__ = [
    "ArchitectureDesignerInput",
    "design_architecture",
    "run",
    "run_builtin_evaluation",
    "enrich_input_from_repo_analysis",
]
