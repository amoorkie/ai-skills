"""Shared types for deploy helper evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCase:
    """Single evaluation scenario with expected deploy-plan properties."""

    name: str
    repo_path: Path
    input_overrides: dict[str, object] = field(default_factory=dict)
    expected_platform: str | None = None
    expected_detected_files: set[str] = field(default_factory=set)
    expected_commands: set[str] = field(default_factory=set)
    expected_notes: set[str] = field(default_factory=set)
    expected_manifest_signals: set[str] = field(default_factory=set)
    forbidden_commands: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class EvaluationCaseResult:
    """Per-case evaluation output."""

    name: str
    platform_correct: bool
    missing_detected_files: set[str]
    missing_commands: set[str]
    missing_notes: set[str]
    missing_manifest_signals: set[str]
    forbidden_command_hits: set[str]
    recall: float
    noise_rate: float
    passed: bool


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    case_results: list[EvaluationCaseResult]
    overall_platform_accuracy: float
    overall_recall: float
    average_noise_rate: float
    pass_rate: float
