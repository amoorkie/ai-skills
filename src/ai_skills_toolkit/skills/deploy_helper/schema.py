"""Pydantic schemas for deploy_helper."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Platform = Literal["auto", "generic", "docker", "render", "vercel", "cloudflare"]


class DeployHelperInput(BaseModel):
    """Input contract for deployment planning."""

    repo_path: Path = Field(default=Path("."), description="Path to local repository.")
    platform: Platform = "auto"
    environment: str = Field(default="production", min_length=2, max_length=40)
    app_name: str = Field(default="app", min_length=2, max_length=120)
    required_env_vars: list[str] = Field(default_factory=list)

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, value: Path) -> Path:
        resolved = value.resolve()
        if not resolved.exists():
            raise ValueError(f"Path does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")
        return resolved


class DeployPlan(BaseModel):
    """Structured deployment plan result."""

    repository: str
    platform: str
    detected_files: list[str]
    checklist: list[str]
    commands: list[str]
    env_vars: list[str]
    notes: list[str] = Field(default_factory=list)

