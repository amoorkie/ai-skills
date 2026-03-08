"""Shared types for repo analyzer evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCase:
    """Single evaluation scenario with expected repository signals."""

    name: str
    repo_path: Path
    include_hidden: bool = False
    expected_project_kind: str | None = None
    expected_entrypoints: set[str] = field(default_factory=set)
    expected_tooling_signals: set[str] = field(default_factory=set)
    forbidden_largest_paths: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class EvaluationCaseResult:
    """Per-case evaluation output."""

    name: str
    project_kind_correct: bool
    missing_entrypoints: set[str]
    missing_tooling_signals: set[str]
    forbidden_largest_hits: set[str]
    signal_recall: float
    noise_rate: float
    passed: bool


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    case_results: list[EvaluationCaseResult]
    overall_project_kind_accuracy: float
    overall_signal_recall: float
    average_noise_rate: float
    pass_rate: float
