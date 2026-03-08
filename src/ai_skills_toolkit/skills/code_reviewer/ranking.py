"""Ranking and clustering for code-review findings."""

from __future__ import annotations

from ai_skills_toolkit.skills.code_reviewer.schema import ReviewFinding, RiskCluster

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
SEVERITY_WEIGHT = {"high": 5, "medium": 3, "low": 1}


def cluster_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    grouped: dict[tuple[str, str], ReviewFinding] = {}
    for finding in findings:
        key = (finding.rule_id, finding.path)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = finding.model_copy(deep=True)
            continue
        grouped[key] = existing.model_copy(
            update={
                "line": min(existing.line, finding.line),
                "confidence": max(existing.confidence, finding.confidence),
                "occurrence_count": existing.occurrence_count + finding.occurrence_count,
                "evidence": list(dict.fromkeys(existing.evidence + finding.evidence)),
                "tests_to_add": list(dict.fromkeys(existing.tests_to_add + finding.tests_to_add)),
                "open_questions": list(dict.fromkeys(existing.open_questions + finding.open_questions)),
                "affected_paths": list(dict.fromkeys(existing.affected_paths + finding.affected_paths)),
            }
        )
    return list(grouped.values())


def severity_counts(findings: list[ReviewFinding]) -> dict[str, int]:
    return {
        "high": sum(1 for finding in findings if finding.severity == "high"),
        "medium": sum(1 for finding in findings if finding.severity == "medium"),
        "low": sum(1 for finding in findings if finding.severity == "low"),
    }


def top_risk_areas(findings: list[ReviewFinding]) -> list[str]:
    scores: dict[str, int] = {}
    for finding in findings:
        for path in finding.affected_paths:
            scores[path] = scores.get(path, 0) + SEVERITY_WEIGHT[finding.severity] + (finding.occurrence_count - 1)
    return [path for path, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:5]]


def sort_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    return sorted(findings, key=lambda item: (SEVERITY_RANK[item.severity], item.path, item.line))


def build_risk_clusters(findings: list[ReviewFinding]) -> list[RiskCluster]:
    groups: dict[str, list[ReviewFinding]] = {}
    for finding in findings:
        if finding.rule_id in {
            "deploy.service-path-command-scope-mismatch",
            "validation.path-traversal-parent-segments",
            "deploy.manifest-selection-ambiguity",
        }:
            key = "scoped-deploy-integrity"
        elif finding.rule_id == "repo.hidden-ci-signal-mismatch":
            key = "operational-signal-integrity"
        elif finding.rule_id in {"python.bare-except", "python.broad-except-exception"}:
            key = "error-boundary-handling"
        else:
            key = f"{finding.category}:{finding.path}"
        groups.setdefault(key, []).append(finding)

    clusters: list[RiskCluster] = []
    for cluster_id, grouped in groups.items():
        sorted_group = sort_findings(grouped)
        primary = sorted_group[0]
        affected_paths = list(dict.fromkeys(path for finding in sorted_group for path in finding.affected_paths))
        rule_ids = list(dict.fromkeys(finding.rule_id for finding in sorted_group))
        clusters.append(
            RiskCluster(
                cluster_id=cluster_id,
                title=_cluster_title(cluster_id, primary),
                severity=primary.severity,
                category=primary.category,
                summary=_cluster_summary(cluster_id, sorted_group),
                affected_paths=affected_paths,
                finding_rule_ids=rule_ids,
                recommendation=primary.recommendation,
            )
        )
    return sorted(clusters, key=lambda item: (SEVERITY_RANK[item.severity], item.title))


def _cluster_title(cluster_id: str, primary: ReviewFinding) -> str:
    mapping = {
        "scoped-deploy-integrity": "Scoped deploy support is unsafe",
        "operational-signal-integrity": "Operational signals are incomplete by default",
        "error-boundary-handling": "Error boundaries hide useful failure information",
    }
    return mapping.get(cluster_id, primary.title)


def _cluster_summary(cluster_id: str, findings: list[ReviewFinding]) -> str:
    if cluster_id == "scoped-deploy-integrity":
        return "Scoped deployment support has both validation and command-generation gaps, so monorepo deploys can escape or target the wrong service."
    if cluster_id == "operational-signal-integrity":
        return "Repository operational metadata is incomplete in normal runs, which can mislead documentation and deployment planning."
    if cluster_id == "error-boundary-handling":
        return "Failure handling catches too broadly, which reduces diagnosability and can hide real regressions."
    return findings[0].detail
