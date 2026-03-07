"""Pydantic schemas for architecture_designer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArchitectureDesignerInput(BaseModel):
    product_name: str = Field(min_length=2, max_length=120)
    product_goal: str = Field(min_length=10, max_length=600)
    primary_users: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class ArchitectureSpec(BaseModel):
    product_name: str
    summary: str
    components: list[str]
    api_endpoints: list[str]
    data_entities: list[str]
    risks: list[str]
    open_questions: list[str]

