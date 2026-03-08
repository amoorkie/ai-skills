"""Pydantic schemas for code_reviewer."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ai_skills_toolkit.core.validators import validate_repo_dir

Severity = Literal["high", "medium", "low"]
FindingCategory = Literal["security", "correctness", "operability", "maintainability"]
FindingScope = Literal["single-file", "cross-file", "contract", "runtime"]
Impact = Literal["high", "medium", "low"]
Likelihood = Literal["high", "medium", "low"]
BlastRadius = Literal["local", "module", "cross-skill", "repository-wide"]
FixComplexity = Literal["small", "medium", "large"]


class CodeReviewerInput(BaseModel):
    """Input for static heuristic code review."""

    repo_path: Path = Field(default=Path("."), description="Path to local repository.")
    include_tests: bool = False
    max_findings: int = Field(default=80, ge=1, le=1000)
    include_low_severity: bool = True
    changed_only: bool = False
    base_ref: str | None = Field(default=None, max_length=120)
    diff_context_hops: int = Field(default=1, ge=0, le=3)

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, value: Path) -> Path:
        return validate_repo_dir(value)


class ReviewFinding(BaseModel):
    """Single code-review finding."""

    rule_id: str
    severity: Severity
    category: FindingCategory
    scope: FindingScope
    path: str
    line: int
    title: str
    detail: str
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    impact: Impact = "medium"
    likelihood: Likelihood = "medium"
    blast_radius: BlastRadius = "module"
    fix_complexity: FixComplexity = "medium"
    affected_paths: list[str] = Field(default_factory=list)
    tests_to_add: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    inferred: bool = False
    evidence: list[str] = Field(default_factory=list)
    occurrence_count: int = Field(default=1, ge=1)


class RiskCluster(BaseModel):
    """Aggregated cluster of related findings."""

    cluster_id: str
    title: str
    severity: Severity
    category: FindingCategory
    summary: str
    affected_paths: list[str]
    finding_rule_ids: list[str]
    recommendation: str


class CodeReviewReport(BaseModel):
    """Aggregated review report."""

    repository: str
    findings: list[ReviewFinding]
    top_risk_clusters: list[RiskCluster] = Field(default_factory=list)
    coverage: dict[str, bool] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    review_mode: str = "ast+token+semantic"
    summary: str
