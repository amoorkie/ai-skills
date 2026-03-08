"""Pydantic schemas for test_generator."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ai_skills_toolkit.core.validators import validate_repo_dir


class TestGeneratorInput(BaseModel):
    """Input contract for generating a repository test plan."""

    repo_path: Path = Field(default=Path("."), description="Path to local repository.")
    focus_paths: list[str] = Field(default_factory=list, description="Optional relative paths to prioritize.")
    test_framework: Literal["pytest"] = "pytest"
    include_edge_cases: bool = True
    max_targets: int = Field(default=20, ge=1, le=200)

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, value: Path) -> Path:
        return validate_repo_dir(value)


class TestTarget(BaseModel):
    """Discovered code unit that should receive tests."""

    path: str
    target_type: str = "module"
    functions: list[str] = Field(default_factory=list)
    classes: list[str] = Field(default_factory=list)
    priority_score: int = 0
    priority_reasons: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    test_ideas: list[str] = Field(default_factory=list)
    suggested_test_types: list[str] = Field(default_factory=list)


class TestGenerationResult(BaseModel):
    """Structured planning result produced by test_generator."""

    repository: str
    framework: str
    targets: list[TestTarget]
    notes: list[str] = Field(default_factory=list)
