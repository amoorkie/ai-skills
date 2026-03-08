"""Shared types for test generator evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCase:
    """Single evaluation scenario with expected target ranking and planning hints."""

    name: str
    repo_path: Path
    expected_target_paths: set[str] = field(default_factory=set)
    expected_top_path: str | None = None
    expected_test_types_by_target: dict[str, set[str]] = field(default_factory=dict)
    forbidden_target_paths: set[str] = field(default_factory=set)
    input_overrides: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationCaseResult:
    """Per-case evaluation output."""

    name: str
    found_target_paths: list[str]
    top_path: str | None
    missing_target_paths: set[str]
    missing_test_types_by_target: dict[str, set[str]]
    forbidden_target_hits: set[str]
    target_recall: float
    top_path_correct: bool
    test_type_recall: float
    noise_rate: float
    passed: bool


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    case_results: list[EvaluationCaseResult]
    overall_target_recall: float
    overall_top_path_accuracy: float
    overall_test_type_recall: float
    average_noise_rate: float
    pass_rate: float
