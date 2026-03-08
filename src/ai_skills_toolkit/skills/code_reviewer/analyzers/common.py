"""Shared helpers for code-review analyzers."""

from __future__ import annotations

from ai_skills_toolkit.skills.code_reviewer.schema import ReviewFinding


def make_finding(
    *,
    rule_id: str,
    severity: str,
    category: str,
    scope: str,
    path: str,
    line: int,
    title: str,
    detail: str,
    recommendation: str,
    confidence: float,
    impact: str = "medium",
    likelihood: str = "medium",
    blast_radius: str = "module",
    fix_complexity: str = "medium",
    affected_paths: list[str] | None = None,
    tests_to_add: list[str] | None = None,
    open_questions: list[str] | None = None,
    inferred: bool = False,
    evidence: list[str] | None = None,
) -> ReviewFinding:
    return ReviewFinding(
        rule_id=rule_id,
        severity=severity,
        category=category,
        scope=scope,
        path=path,
        line=line,
        title=title,
        detail=detail,
        recommendation=recommendation,
        confidence=confidence,
        impact=impact,
        likelihood=likelihood,
        blast_radius=blast_radius,
        fix_complexity=fix_complexity,
        affected_paths=list(affected_paths or [path]),
        tests_to_add=list(tests_to_add or []),
        open_questions=list(open_questions or []),
        inferred=inferred,
        evidence=list(evidence or [f"Observed at `{path}:{line}`."]),
    )


def line_number_for_pattern(content: str, pattern: str) -> int:
    index = content.find(pattern)
    if index < 0:
        return 1
    return content.count("\n", 0, index) + 1
