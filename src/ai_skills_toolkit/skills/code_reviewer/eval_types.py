"""Shared types for code reviewer evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCase:
    """Single evaluation scenario with expected reviewer output."""

    name: str
    repo_path: Path
    expected_rule_ids: set[str] = field(default_factory=set)
    expected_cluster_ids: set[str] = field(default_factory=set)
    forbidden_rule_ids: set[str] = field(default_factory=set)
    input_overrides: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationCaseResult:
    """Per-case evaluation output."""

    name: str
    found_rule_ids: set[str]
    found_cluster_ids: set[str]
    missing_rule_ids: set[str]
    missing_cluster_ids: set[str]
    forbidden_rule_hits: set[str]
    extra_rule_ids: set[str]
    rule_recall: float
    cluster_recall: float
    noise_rate: float
    passed: bool


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    case_results: list[EvaluationCaseResult]
    overall_rule_recall: float
    overall_cluster_recall: float
    average_noise_rate: float
    pass_rate: float
