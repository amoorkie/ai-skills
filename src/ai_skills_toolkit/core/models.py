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


def build_run_metadata(
    *,
    artifact_type: str,
    subject: str,
    subject_type: str,
    output_format: str = "markdown",
    warning_count: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable metadata envelope for skill outputs."""
    metadata: dict[str, Any] = {
        "artifact_type": artifact_type,
        "subject": subject,
        "subject_type": subject_type,
        "output_format": output_format,
    }
    if warning_count is not None:
        metadata["warning_count"] = warning_count
    if extra:
        metadata.update(extra)
    return metadata
