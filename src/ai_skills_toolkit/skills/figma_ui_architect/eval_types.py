"""Shared types for figma UI architect evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_skills_toolkit.skills.figma_ui_architect.schema import FigmaUiArchitectInput


@dataclass(frozen=True)
class EvaluationCase:
    """Single evaluation scenario with expected UI planning outputs."""

    name: str
    input_data: FigmaUiArchitectInput
    expected_fragments: set[str] = field(default_factory=set)
    forbidden_fragments: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class EvaluationCaseResult:
    """Per-case evaluation output."""

    name: str
    missing_fragments: set[str]
    forbidden_fragments_found: set[str]
    recall: float
    passed: bool


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    case_results: list[EvaluationCaseResult]
    overall_recall: float
    pass_rate: float
