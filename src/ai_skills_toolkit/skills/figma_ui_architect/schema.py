"""Pydantic schemas for figma_ui_architect."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FigmaUiArchitectInput(BaseModel):
    product_name: str = Field(min_length=2, max_length=120)
    product_goal: str = Field(min_length=10, max_length=600)
    users: list[str] = Field(default_factory=list)
    jtbds: list[str] = Field(default_factory=list, description="Jobs to be done.")
    constraints: list[str] = Field(default_factory=list)
    preferred_platform: str = Field(default="Web", min_length=2, max_length=30)
    design_tone: str = Field(default="Professional, clear, data-forward", min_length=3, max_length=120)

