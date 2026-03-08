"""Pydantic schemas for repo_analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ai_skills_toolkit.core.validators import validate_repo_dir


class RepoAnalyzerInput(BaseModel):
    repo_path: Path = Field(default=Path("."), description="Path to a local repository.")
    include_hidden: bool = False
    max_files: int = Field(default=5000, ge=10, le=200000)
    largest_file_count: int = Field(default=12, ge=1, le=200)

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, value: Path) -> Path:
        return validate_repo_dir(value)


class FileStat(BaseModel):
    path: str
    extension: str
    size_bytes: int


class RepoAnalysis(BaseModel):
    repo_path: str
    has_git_dir: bool
    project_kind: str
    confidence: Literal["low", "medium", "high"]
    total_files: int
    total_dirs: int
    test_file_count: int
    total_size_bytes: int
    language_breakdown: dict[str, int]
    key_files: list[str]
    entrypoints: list[str]
    tooling_signals: list[str]
    manifest_summary: list[str]
    dependency_surface: list[str]
    runtime_surface: list[str]
    service_map: list[str]
    boundary_hotspots: list[str]
    internal_module_graph: list[str]
    hotspot_ranking: list[str]
    observed_signals: list[str]
    inferred_characteristics: list[str]
    assumed_defaults: list[str]
    largest_files: list[FileStat]
    notes: list[str]
