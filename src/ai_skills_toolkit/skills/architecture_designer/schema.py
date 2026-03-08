"""Pydantic schemas for architecture_designer."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ArchitectureDesignerInput(BaseModel):
    product_name: str = Field(min_length=2, max_length=120)
    product_goal: str = Field(min_length=10, max_length=600)
    primary_users: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    repo_context_signals: list[str] = Field(default_factory=list)


class ArchitectureSpec(BaseModel):
    product_name: str
    summary: str
    observed_signals: list[str]
    inferred_decisions: list[str]
    decision_log: list[str]
    tradeoffs: list[str]
    alternatives_considered: list[str]
    adr_records: list[str]
    phased_decisions: list[str]
    risk_decision_links: list[str]
    decision_priorities: list[str]
    adr_priority_matrix: list[str]
    assumed_defaults: list[str]
    components: list[str]
    api_endpoints: list[str]
    data_entities: list[str]
    risks: list[str]
    open_questions: list[str]
    confidence: Literal["low", "medium", "high"]
