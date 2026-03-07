"""Pydantic schemas for repo_analyzer."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class RepoAnalyzerInput(BaseModel):
    repo_path: Path = Field(default=Path("."), description="Path to a local repository.")
    include_hidden: bool = False
    max_files: int = Field(default=5000, ge=10, le=200000)
    largest_file_count: int = Field(default=12, ge=1, le=200)

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, value: Path) -> Path:
        resolved = value.resolve()
        if not resolved.exists():
            raise ValueError(f"Path does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")
        return resolved


class FileStat(BaseModel):
    path: str
    extension: str
    size_bytes: int


class RepoAnalysis(BaseModel):
    repo_path: str
    has_git_dir: bool
    total_files: int
    total_dirs: int
    total_size_bytes: int
    language_breakdown: dict[str, int]
    key_files: list[str]
    largest_files: list[FileStat]
    notes: list[str]

