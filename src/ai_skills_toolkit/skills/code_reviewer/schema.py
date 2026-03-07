"""Pydantic schemas for code_reviewer."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["high", "medium", "low"]


class CodeReviewerInput(BaseModel):
    """Input for static heuristic code review."""

    repo_path: Path = Field(default=Path("."), description="Path to local repository.")
    include_tests: bool = False
    max_findings: int = Field(default=80, ge=1, le=1000)
    include_low_severity: bool = True

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, value: Path) -> Path:
        resolved = value.resolve()
        if not resolved.exists():
            raise ValueError(f"Path does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")
        return resolved


class ReviewFinding(BaseModel):
    """Single code-review finding."""

    severity: Severity
    path: str
    line: int
    title: str
    detail: str


class CodeReviewReport(BaseModel):
    """Aggregated review report."""

    repository: str
    findings: list[ReviewFinding]
    summary: str

