"""Shared types for architecture designer evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_skills_toolkit.skills.architecture_designer.schema import ArchitectureDesignerInput


@dataclass(frozen=True)
class EvaluationCase:
    """Single evaluation scenario with expected architectural outputs."""

    name: str
    input_data: ArchitectureDesignerInput
    expected_components: set[str] = field(default_factory=set)
    expected_entities: set[str] = field(default_factory=set)
    expected_endpoints: set[str] = field(default_factory=set)
    expected_risks: set[str] = field(default_factory=set)
    expected_questions: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class EvaluationCaseResult:
    """Per-case evaluation output."""

    name: str
    missing_components: set[str]
    missing_entities: set[str]
    missing_endpoints: set[str]
    missing_risk_fragments: set[str]
    missing_question_fragments: set[str]
    recall: float
    passed: bool


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    case_results: list[EvaluationCaseResult]
    overall_recall: float
    pass_rate: float
