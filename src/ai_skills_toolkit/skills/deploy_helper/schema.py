"""Pydantic schemas for deploy_helper."""

from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ai_skills_toolkit.core.validators import validate_repo_dir

Platform = Literal["auto", "generic", "docker", "render", "vercel", "cloudflare"]
PreferredPlatform = Literal["generic", "docker", "render", "vercel", "cloudflare"]


class DeployHelperInput(BaseModel):
    """Input contract for deployment planning."""

    repo_path: Path = Field(default=Path("."), description="Path to local repository.")
    platform: Platform = "auto"
    environment: str = Field(default="production", min_length=2, max_length=40)
    app_name: str = Field(default="app", min_length=2, max_length=120)
    required_env_vars: list[str] = Field(default_factory=list)
    prefer_platform: PreferredPlatform | None = None
    service_path: str | None = Field(default=None, min_length=1, max_length=240)

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, value: Path) -> Path:
        return validate_repo_dir(value)

    @field_validator("service_path")
    @classmethod
    def validate_service_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.replace("\\", "/").strip().strip("/")
        if not normalized:
            raise ValueError("service_path must not be empty")
        candidate = PurePosixPath(normalized)
        if candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts):
            raise ValueError("service_path must point to a repository subdirectory")
        return normalized


class DeployPlan(BaseModel):
    """Structured deployment plan result."""

    repository: str
    platform: str
    detected_files: list[str]
    candidate_platforms: list[str] = Field(default_factory=list)
    manifest_signals: list[str] = Field(default_factory=list)
    checklist: list[str]
    commands: list[str]
    env_vars: list[str]
    notes: list[str] = Field(default_factory=list)
