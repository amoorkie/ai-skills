"""Markdown rendering for code-review reports."""

from __future__ import annotations

from ai_skills_toolkit.skills.code_reviewer.ranking import severity_counts
from ai_skills_toolkit.skills.code_reviewer.schema import CodeReviewReport


def render_markdown(report: CodeReviewReport) -> str:
    severity = severity_counts(report.findings)
    categories = sorted({finding.category for finding in report.findings})
    lines: list[str] = []
    lines.append("# Code Review Report")
    lines.append("")
    lines.append(f"- **Repository:** `{report.repository}`")
    lines.append(f"- **Summary:** {report.summary}")
    lines.append(f"- **Review mode:** `{report.review_mode}`")
    lines.append("")
    lines.append("## Risk Overview")
    lines.append("")
    lines.append(f"- High severity: {severity['high']}")
    lines.append(f"- Medium severity: {severity['medium']}")
    lines.append(f"- Low severity: {severity['low']}")
    if report.top_risk_clusters:
        lines.append("- Top risk clusters:")
        lines.extend([f"  - `{cluster.title}` ({cluster.severity})" for cluster in report.top_risk_clusters[:5]])
    if categories:
        lines.append(f"- Categories present: {', '.join(f'`{category}`' for category in categories)}")
    lines.append("")
    lines.append("## Top Risk Clusters")
    lines.append("")
    if report.top_risk_clusters:
        for index, cluster in enumerate(report.top_risk_clusters, start=1):
            lines.append(f"{index}. **[{cluster.severity.upper()}] {cluster.title}**")
            lines.append(f"   - Category: `{cluster.category}`")
            lines.append(f"   - Summary: {cluster.summary}")
            lines.append(f"   - Affected paths: {', '.join(f'`{path}`' for path in cluster.affected_paths)}")
            lines.append(f"   - Rules: {', '.join(f'`{rule}`' for rule in cluster.finding_rule_ids)}")
            lines.append(f"   - Recommended fix: {cluster.recommendation}")
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not report.findings:
        lines.append("- None.")
    else:
        for index, finding in enumerate(report.findings, start=1):
            lines.append(f"{index}. **[{finding.severity.upper()}] {finding.title}** at `{finding.path}:{finding.line}`")
            lines.append(f"   - Rule: `{finding.rule_id}`")
            lines.append(f"   - Category: `{finding.category}`")
            lines.append(f"   - Scope: `{finding.scope}`")
            lines.append(f"   - Impact: `{finding.impact}`")
            lines.append(f"   - Likelihood: `{finding.likelihood}`")
            lines.append(f"   - Blast radius: `{finding.blast_radius}`")
            lines.append(f"   - Fix complexity: `{finding.fix_complexity}`")
            lines.append(f"   - Confidence: {finding.confidence:.2f}")
            if finding.inferred:
                lines.append("   - Evidence mode: inferred from multiple code signals")
            if finding.occurrence_count > 1:
                lines.append(f"   - Occurrences clustered: {finding.occurrence_count}")
            lines.append(f"   - Why it matters: {finding.detail}")
            lines.append(f"   - Recommended fix: {finding.recommendation}")
            if finding.tests_to_add:
                lines.append("   - Tests to add:")
                lines.extend([f"     - {item}" for item in finding.tests_to_add[:3]])
            if finding.evidence:
                lines.append("   - Evidence:")
                lines.extend([f"     - {item}" for item in finding.evidence[:4]])
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    if report.coverage:
        for key, value in sorted(report.coverage.items()):
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("## Assumptions")
    lines.append("")
    if report.assumptions:
        lines.extend([f"- {item}" for item in report.assumptions])
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("## Recommended Next Actions")
    lines.append("")
    lines.append("- Fix high-severity findings first.")
    lines.append("- Start with the highest-risk clusters instead of isolated low-context edits.")
    lines.append("- Add targeted regression tests for each confirmed risky code path.")
    lines.append("- Re-run review after patching to verify cleanup and severity reduction.")
    lines.append("")
    return "\n".join(lines)
