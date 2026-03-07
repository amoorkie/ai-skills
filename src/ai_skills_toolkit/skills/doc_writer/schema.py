"""Pydantic schemas for doc_writer."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class DocWriterInput(BaseModel):
    repo_path: Path = Field(default=Path("."), description="Path to local repository.")
    title: str = Field(default="Project Documentation", min_length=3, max_length=120)
    audience: str = Field(default="Engineers and AI agents", min_length=3, max_length=120)
    include_setup_checklist: bool = True
    max_top_level_entries: int = Field(default=30, ge=5, le=200)

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, value: Path) -> Path:
        resolved = value.resolve()
        if not resolved.exists():
            raise ValueError(f"Path does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")
        return resolved

