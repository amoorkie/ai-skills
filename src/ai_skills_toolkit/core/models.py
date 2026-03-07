"""Shared pydantic models for skill execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SkillRunResult(BaseModel):
    skill_name: str
    output_path: Path
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)

