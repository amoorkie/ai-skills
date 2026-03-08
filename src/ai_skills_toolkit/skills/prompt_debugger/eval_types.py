"""Shared types for prompt debugger evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvaluationCase:
    """Single evaluation scenario with expected diagnosis and variant fragments."""

    name: str
    prompt: str
    goal: str | None = None
    context: str | None = None
    target_model: str | None = None
    expected_issue_titles: set[str] = field(default_factory=set)
    forbidden_issue_titles: set[str] = field(default_factory=set)
    expected_variant_fragments: set[str] = field(default_factory=set)
    expected_language: str | None = None
    expected_task_type: str | None = None


@dataclass(frozen=True)
class EvaluationCaseResult:
    """Per-case evaluation output."""

    name: str
    language_correct: bool
    task_type_correct: bool
    missing_issue_titles: set[str]
    forbidden_issue_hits: set[str]
    missing_variant_fragments: set[str]
    recall: float
    noise_rate: float
    passed: bool


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    case_results: list[EvaluationCaseResult]
    overall_language_accuracy: float
    overall_task_accuracy: float
    overall_recall: float
    average_noise_rate: float
    pass_rate: float
