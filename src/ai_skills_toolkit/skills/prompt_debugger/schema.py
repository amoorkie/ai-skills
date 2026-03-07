"""Pydantic schemas for prompt_debugger."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PromptDebuggerInput(BaseModel):
    prompt: str = Field(min_length=10, max_length=30000)
    goal: str | None = Field(default=None, max_length=300)
    context: str | None = Field(default=None, max_length=1000)
    target_model: str | None = Field(default=None, max_length=120)


class PromptIssue(BaseModel):
    severity: Literal["high", "medium", "low"]
    title: str
    rationale: str


class PromptVariant(BaseModel):
    name: str
    why: str
    prompt: str


class PromptDebuggerOutput(BaseModel):
    diagnosis: list[PromptIssue]
    improved_variants: list[PromptVariant]

