"""Shared types for doc writer evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCase:
    """Single evaluation scenario with expected documentation sections and signals."""

    name: str
    repo_path: Path
    title: str = "Project Documentation"
    audience: str = "Engineers and AI agents"
    include_setup_checklist: bool = True
    expected_fragments: set[str] = field(default_factory=set)
    forbidden_fragments: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class EvaluationCaseResult:
    """Per-case evaluation output."""

    name: str
    missing_fragments: set[str]
    forbidden_fragments_found: set[str]
    fragment_recall: float
    noise_rate: float
    passed: bool


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    case_results: list[EvaluationCaseResult]
    overall_fragment_recall: float
    average_noise_rate: float
    pass_rate: float
