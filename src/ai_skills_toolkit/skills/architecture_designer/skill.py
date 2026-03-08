"""Implementation for architecture_designer."""

from __future__ import annotations

from pathlib import Path
import re

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.architecture_designer.schema import ArchitectureDesignerInput, ArchitectureSpec

STOPWORDS = {
    "about",
    "across",
    "admin",
    "allow",
    "and",
    "build",
    "clear",
    "data",
    "deliver",
    "efficient",
    "for",
    "from",
    "help",
    "into",
    "manage",
    "monitor",
    "more",
    "operations",
    "portal",
    "product",
    "provide",
    "reliable",
    "support",
    "system",
    "teams",
    "their",
    "tool",
    "users",
    "using",
    "with",
    "workflow",
    "workflows",
}


def _normalize_tokens(*values: str) -> list[str]:
    tokens: list[str] = []
    for value in values:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", value.lower()):
            if token not in STOPWORDS:
                tokens.append(token)
    return tokens


def _title_term(token: str) -> str:
    return token.replace("_", " ").replace("-", " ").title()


def _normalize_domain_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 4:
        return token[:-1]
    return token


def _pluralize(term: str) -> str:
    slug = term.lower().replace(" ", "-")
    if slug.endswith("s"):
        return slug
    if slug.endswith("y") and len(slug) > 1 and slug[-2] not in "aeiou":
        return f"{slug[:-1]}ies"
    return f"{slug}s"


def _derive_domain_terms(data: ArchitectureDesignerInput) -> list[str]:
    preferred: list[str] = []
    for entry in [data.product_goal, *data.functional_requirements]:
        for token in _normalize_tokens(entry):
            token = _normalize_domain_token(token)
            if token not in preferred:
                preferred.append(token)
    return preferred[:6]


def _derive_components(data: ArchitectureDesignerInput, domain_terms: list[str]) -> list[str]:
    text = " ".join(
        [data.product_goal, *data.functional_requirements, *data.non_functional_requirements, *data.constraints]
    ).lower()
    components = [
        "API Gateway / BFF",
        "Application Service Layer",
    ]
    if domain_terms:
        components.extend([f"{_title_term(term)} Domain Service" for term in domain_terms[:2]])
    else:
        components.append("Core Domain Module")
    if any(word in text for word in ("approval", "workflow", "queue", "orchestrat", "job")):
        components.append("Workflow Orchestrator")
    if any(word in text for word in ("sync", "integration", "integrate", "webhook", "erp", "third-party", "third party")):
        components.append("Integration Adapter Layer")
    if any(word in text for word in ("notify", "email", "slack", "alert", "message")):
        components.append("Notification Service")
    components.append("Persistence Layer")
    if any(word in text for word in ("async", "batch", "import", "export", "schedule", "report")):
        components.append("Background Worker / Scheduler")
    components.append("Observability Stack (logs, metrics, traces)")
    deduped: list[str] = []
    for component in components:
        if component not in deduped:
            deduped.append(component)
    return deduped


def _derive_entities(data: ArchitectureDesignerInput, domain_terms: list[str]) -> list[str]:
    entities = ["User"]
    if data.primary_users:
        entities.append("Workspace")
    for term in domain_terms[:4]:
        titled = _title_term(term)
        if titled not in entities:
            entities.append(titled)
    text = " ".join([data.product_goal, *data.functional_requirements]).lower()
    if any(word in text for word in ("audit", "compliance", "trace")):
        entities.append("Audit Log")
    if any(word in text for word in ("job", "queue", "schedule", "batch")):
        entities.append("Job")
    if any(word in text for word in ("rule", "policy", "approval")):
        entities.append("Policy")
    return entities[:6]


def _derive_api_endpoints(data: ArchitectureDesignerInput, entities: list[str]) -> list[str]:
    endpoints = ["GET /api/v1/health"]
    text = " ".join([data.product_goal, *data.functional_requirements]).lower()
    if any(word in text for word in ("auth", "session", "login", "access")):
        endpoints.insert(0, "POST /api/v1/auth/session")
    domain_entities = [entity for entity in entities if entity not in {"User", "Workspace"}]
    for entity in domain_entities[:3]:
        slug = _pluralize(entity)
        endpoints.append(f"GET /api/v1/{slug}")
        endpoints.append(f"POST /api/v1/{slug}")
    if domain_entities:
        primary_slug = _pluralize(domain_entities[0])
        endpoints.append(f"PATCH /api/v1/{primary_slug}" + "/{id}")
    if any(word in text for word in ("audit", "history", "timeline")):
        endpoints.append("GET /api/v1/audit-logs")
    if any(word in text for word in ("report", "metric", "dashboard")):
        endpoints.append("GET /api/v1/metrics/summary")
    return endpoints[:10]


def _derive_risks(data: ArchitectureDesignerInput, domain_terms: list[str]) -> list[str]:
    text = " ".join(
        [data.product_goal, *data.functional_requirements, *data.non_functional_requirements, *data.constraints]
    ).lower()
    risks: list[str] = []
    if not data.functional_requirements:
        risks.append("Core domain workflows are not yet explicit, so component and API boundaries may drift.")
    if any(word in text for word in ("real-time", "realtime", "stream", "webhook")):
        risks.append("Event ordering and delivery guarantees may be unclear for near-real-time flows.")
    if any(word in text for word in ("audit", "finance", "compliance", "policy")):
        risks.append("Compliance-sensitive data will need explicit retention, access, and audit controls.")
    if any(word in text for word in ("import", "export", "integration", "integrate", "sync", "erp")):
        risks.append("External integrations can dominate failure modes without retry and idempotency design.")
    if any(word in text for word in ("latency", "scale", "throughput", "sla", "slo")):
        risks.append("Performance targets may be missed unless workload shape is validated early.")
    if not risks:
        focus = _title_term(domain_terms[0]) if domain_terms else "domain"
        risks.append(f"{focus} workflows may expand faster than shared platform boundaries are defined.")
    risks.append("Operational complexity increases if observability and ownership are deferred.")
    return risks[:4]


def _derive_open_questions(data: ArchitectureDesignerInput, entities: list[str]) -> list[str]:
    questions: list[str] = []
    if not data.non_functional_requirements:
        questions.append("What availability, latency, and recovery targets are required for phase 1?")
    if not data.constraints:
        questions.append("Which deployment, data residency, or tooling constraints are fixed up front?")
    focus_entity = next((entity for entity in entities if entity not in {"User", "Workspace"}), "core records")
    questions.append(f"What are the allowed lifecycle states and ownership rules for {focus_entity.lower()}?")
    if any("Integration" in requirement or "integration" in requirement.lower() for requirement in data.functional_requirements):
        questions.append("Which external systems are system-of-record versus downstream consumers?")
    else:
        questions.append("Which integrations are mandatory in phase 1 versus safe to defer?")
    return questions[:4]


def _derive_observed_signals(data: ArchitectureDesignerInput, domain_terms: list[str]) -> list[str]:
    signals: list[str] = [f"Primary goal: {data.product_goal.strip()}"]
    if data.functional_requirements:
        signals.append(
            "Explicit functional requirements mention "
            + ", ".join(item.strip().rstrip(".") for item in data.functional_requirements[:3])
            + "."
        )
    if data.non_functional_requirements:
        signals.append(
            "Explicit non-functional requirements mention "
            + ", ".join(item.strip().rstrip(".") for item in data.non_functional_requirements[:3])
            + "."
        )
    if data.constraints:
        signals.append("Explicit constraints: " + ", ".join(item.strip() for item in data.constraints[:3]) + ".")
    if domain_terms:
        signals.append(
            "Dominant domain terms inferred from input: "
            + ", ".join(_title_term(term) for term in domain_terms[:4])
            + "."
        )
    if data.repo_context_signals:
        signals.append("Repository context carried into architecture planning: " + "; ".join(data.repo_context_signals[:3]))
    return signals[:5]


def _derive_inferred_decisions(data: ArchitectureDesignerInput, components: list[str], entities: list[str]) -> list[str]:
    decisions = [
        "Use a layered modular architecture to separate API, domain logic, and persistence concerns."
    ]
    if "Workflow Orchestrator" in components:
        decisions.append("Introduce a workflow orchestration layer because the input describes approvals or queue-driven flows.")
    if "Integration Adapter Layer" in components:
        decisions.append("Isolate third-party integrations behind adapters so retries, mapping, and failures stay contained.")
    if "Background Worker / Scheduler" in components:
        decisions.append("Move async or scheduled work into background workers to keep interactive paths responsive.")
    if any(entity == "Audit Log" for entity in entities):
        decisions.append("Treat audit history as a first-class domain concern rather than an afterthought in observability only.")
    decisions.append("Keep observability in the base architecture so operational ownership is defined from the first release.")
    return decisions[:5]


def _derive_assumed_defaults(data: ArchitectureDesignerInput) -> list[str]:
    defaults = list(data.assumptions[:4])
    if not data.assumptions:
        defaults.extend(
            [
                "Single region deployment for phase 1.",
                "PostgreSQL-compatible relational storage.",
            ]
        )
    if not data.non_functional_requirements:
        defaults.append("Availability, latency, and recovery targets still need product confirmation.")
    if data.repo_context_signals:
        defaults.append("Repository-derived context was treated as operational evidence and should be validated against the intended production target.")
    return defaults[:5]


def _estimate_confidence(data: ArchitectureDesignerInput) -> str:
    evidence_points = 0
    if data.functional_requirements:
        evidence_points += 1
    if data.non_functional_requirements:
        evidence_points += 1
    if data.constraints:
        evidence_points += 1
    if data.primary_users:
        evidence_points += 1
    if evidence_points >= 3:
        return "high"
    if evidence_points >= 2:
        return "medium"
    return "low"


def _derive_decision_log(data: ArchitectureDesignerInput, components: list[str], entities: list[str]) -> list[str]:
    decisions = [
        "Decision: keep API, domain, and persistence separated to reduce coupling and make service boundaries explicit."
    ]
    if "Workflow Orchestrator" in components:
        decisions.append("Decision: centralize multi-step workflow state in an orchestrator instead of scattering it across controllers.")
    if "Integration Adapter Layer" in components:
        decisions.append("Decision: isolate external integrations behind adapters so contract mapping and retries remain replaceable.")
    if "Background Worker / Scheduler" in components:
        decisions.append("Decision: move async or scheduled work off the request path to protect latency-sensitive APIs.")
    if any(entity == "Audit Log" for entity in entities):
        decisions.append("Decision: model audit history explicitly because traceability appears to be product-facing, not only operational.")
    return decisions[:5]


def _derive_tradeoffs(data: ArchitectureDesignerInput, components: list[str]) -> list[str]:
    tradeoffs = [
        "Tradeoff: layered architecture improves clarity and ownership, but adds indirection compared with a faster monolith-first implementation."
    ]
    if "Workflow Orchestrator" in components:
        tradeoffs.append("Tradeoff: an orchestrator improves visibility of approvals/queues, but increases operational and state-management complexity.")
    if "Integration Adapter Layer" in components:
        tradeoffs.append("Tradeoff: adapters reduce vendor lock-in and failure spread, but add translation code and more contracts to maintain.")
    if "Background Worker / Scheduler" in components:
        tradeoffs.append("Tradeoff: background execution helps responsiveness, but introduces eventual consistency and retry/idempotency requirements.")
    if not data.constraints:
        tradeoffs.append("Tradeoff: without fixed constraints, the spec stays flexible, but some choices may be over-designed for the real rollout environment.")
    return tradeoffs[:5]


def _derive_alternatives_considered(data: ArchitectureDesignerInput, components: list[str]) -> list[str]:
    alternatives = [
        "Alternative considered: start with a single deployable monolith. Rejected for now because the input already implies multiple architectural concerns that benefit from explicit boundaries."
    ]
    if "Workflow Orchestrator" in components:
        alternatives.append("Alternative considered: embed workflow state transitions directly in API handlers. Rejected because approvals/queues usually need clearer state ownership and replayability.")
    if "Integration Adapter Layer" in components:
        alternatives.append("Alternative considered: call third-party systems directly from domain services. Rejected because it couples domain logic to vendor-specific contracts and failure modes.")
    if "Background Worker / Scheduler" in components:
        alternatives.append("Alternative considered: execute exports/jobs inline in request handlers. Rejected because long-running work would harm responsiveness and retry control.")
    return alternatives[:5]


def _derive_adr_records(components: list[str], entities: list[str]) -> list[str]:
    records = [
        "ADR-001: Use layered boundaries between API, domain, and persistence to keep contracts explicit."
    ]
    if "Workflow Orchestrator" in components:
        records.append("ADR-002: Introduce a workflow orchestrator for multi-step state transitions and approvals.")
    if "Integration Adapter Layer" in components:
        records.append("ADR-003: Route external-system calls through adapters to isolate vendor contracts and retries.")
    if "Background Worker / Scheduler" in components:
        records.append("ADR-004: Handle long-running or scheduled work asynchronously via workers.")
    if any(entity == "Audit Log" for entity in entities):
        records.append("ADR-005: Preserve audit history as a first-class domain concern.")
    return records[:5]


def _derive_phased_decisions(components: list[str]) -> list[str]:
    phases = [
        "Phase A decision: establish API/auth/observability foundations before optimizing domain breadth."
    ]
    if "Workflow Orchestrator" in components:
        phases.append("Phase B decision: add workflow orchestration when core approval/queue transitions are stable enough to formalize.")
    if "Integration Adapter Layer" in components:
        phases.append("Phase B decision: integrate external systems only after the internal domain contract is clear.")
    if "Background Worker / Scheduler" in components:
        phases.append("Phase C decision: scale background execution and retry policy once workload shape is measured.")
    phases.append("Phase C decision: harden SLOs, security controls, and ownership runbooks after the primary workflows are proven.")
    return phases[:5]


def _derive_risk_decision_links(risks: list[str], decision_log: list[str], tradeoffs: list[str]) -> list[str]:
    links: list[str] = []
    for risk in risks:
        if "External integrations" in risk:
            links.append("Risk linkage: integration failure modes are mitigated by the adapter-layer decision and its retry/idempotency tradeoff.")
        elif "Compliance-sensitive data" in risk:
            links.append("Risk linkage: compliance exposure is addressed by explicit audit/history decisions plus tighter operational controls.")
        elif "Performance targets" in risk:
            links.append("Risk linkage: performance uncertainty is offset by phased decisions that defer scaling mechanics until workload shape is measured.")
        elif "Operational complexity" in risk:
            links.append("Risk linkage: operational complexity is accepted explicitly in exchange for observability and phased hardening decisions.")
    if not links and decision_log:
        links.append("Risk linkage: key architectural decisions are intended to reduce ambiguity around service boundaries and future scaling.")
    return links[:5]


def _derive_decision_priorities(
    data: ArchitectureDesignerInput,
    components: list[str],
    risks: list[str],
) -> list[str]:
    priorities = [
        "Decide now: API/domain/persistence boundaries and ownership model before implementation spreads across modules."
    ]
    if "Integration Adapter Layer" in components:
        priorities.append("Decide now: integration system-of-record boundaries and retry/idempotency contract.")
    if any("Compliance-sensitive data" in risk for risk in risks):
        priorities.append("Decide now: audit, retention, and access-control baseline for regulated data paths.")
    if "Background Worker / Scheduler" in components:
        priorities.append("Decide later: worker topology, queue depth limits, and retry backoff after real workload shape is measured.")
    if not data.non_functional_requirements:
        priorities.append("Decide later: formal latency/availability targets once phase-1 scope and traffic assumptions are confirmed.")
    return priorities[:6]


def _derive_adr_priority_matrix(adr_records: list[str], decision_priorities: list[str]) -> list[str]:
    matrix: list[str] = []
    now_bias = any(item.startswith("Decide now:") for item in decision_priorities)
    later_bias = any(item.startswith("Decide later:") for item in decision_priorities)

    for index, record in enumerate(adr_records):
        lowered = record.lower()
        if "layered boundaries" in lowered or "audit history" in lowered:
            cadence = "Must decide now"
            rationale = "foundational contract and compliance choices affect every downstream module."
        elif "orchestrator" in lowered or "adapters" in lowered:
            cadence = "Decide next"
            rationale = "workflow and integration boundaries should settle before scaling feature delivery."
        else:
            cadence = "Can decide later" if later_bias else "Decide next"
            rationale = "operational shape depends on workload evidence after initial release slices."
        if index == 0 and now_bias:
            cadence = "Must decide now"
        matrix.append(f"{record} -> {cadence}: {rationale}")
    return matrix[:6]


def design_architecture(data: ArchitectureDesignerInput) -> ArchitectureSpec:
    """Build a baseline architecture specification model from input requirements."""
    domain_terms = _derive_domain_terms(data)
    components = _derive_components(data, domain_terms)
    data_entities = _derive_entities(data, domain_terms)
    api_endpoints = _derive_api_endpoints(data, data_entities)
    risks = _derive_risks(data, domain_terms)
    open_questions = _derive_open_questions(data, data_entities)
    observed_signals = _derive_observed_signals(data, domain_terms)
    inferred_decisions = _derive_inferred_decisions(data, components, data_entities)
    decision_log = _derive_decision_log(data, components, data_entities)
    tradeoffs = _derive_tradeoffs(data, components)
    alternatives_considered = _derive_alternatives_considered(data, components)
    adr_records = _derive_adr_records(components, data_entities)
    phased_decisions = _derive_phased_decisions(components)
    risk_decision_links = _derive_risk_decision_links(risks, decision_log, tradeoffs)
    decision_priorities = _derive_decision_priorities(data, components, risks)
    adr_priority_matrix = _derive_adr_priority_matrix(adr_records, decision_priorities)
    assumed_defaults = _derive_assumed_defaults(data)
    confidence = _estimate_confidence(data)
    priority_line = (
        f"Primary architectural focus areas are {', '.join(_title_term(term) for term in domain_terms[:3])}."
        if domain_terms
        else "Primary architectural focus areas should be clarified before locking the service boundaries."
    )
    constraints_line = (
        f"Design around these constraints: {', '.join(data.constraints[:3])}."
        if data.constraints
        else "Keep deployment and data constraints explicit before finalizing the runtime topology."
    )
    summary = (
        f"{data.product_name} should use a layered modular architecture with explicit boundaries between "
        "API, domain logic, and persistence. "
        f"{priority_line} {constraints_line} Prioritize clear contracts, observability from day one, "
        "and incremental delivery with measurable service-level objectives."
    )
    return ArchitectureSpec(
        product_name=data.product_name,
        summary=summary,
        observed_signals=observed_signals,
        inferred_decisions=inferred_decisions,
        decision_log=decision_log,
        tradeoffs=tradeoffs,
        alternatives_considered=alternatives_considered,
        adr_records=adr_records,
        phased_decisions=phased_decisions,
        risk_decision_links=risk_decision_links,
        decision_priorities=decision_priorities,
        adr_priority_matrix=adr_priority_matrix,
        assumed_defaults=assumed_defaults,
        components=components,
        api_endpoints=api_endpoints,
        data_entities=data_entities,
        risks=risks,
        open_questions=open_questions,
        confidence=confidence,
    )


def render_markdown(data: ArchitectureDesignerInput, spec: ArchitectureSpec) -> str:
    """Render architecture specification model into markdown."""
    lines: list[str] = []
    lines.append(f"# Architecture Spec: {spec.product_name}")
    lines.append("")
    lines.append("## Product Goal")
    lines.append("")
    lines.append(data.product_goal.strip())
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(spec.summary)
    lines.append("")
    lines.append("## Observed Signals")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.observed_signals])
    lines.append("")
    lines.append("## Inferred Decisions")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.inferred_decisions])
    lines.append("")
    lines.append("## Decision Log")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.decision_log])
    lines.append("")
    lines.append("## Tradeoffs")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.tradeoffs])
    lines.append("")
    lines.append("## Alternatives Considered")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.alternatives_considered])
    lines.append("")
    lines.append("## ADR Summary")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.adr_records])
    lines.append("")
    lines.append("## Users")
    lines.append("")
    if data.primary_users:
        lines.extend([f"- {user}" for user in data.primary_users])
    else:
        lines.append("- TBD")
    lines.append("")
    lines.append("## Functional Requirements")
    lines.append("")
    if data.functional_requirements:
        lines.extend([f"- {item}" for item in data.functional_requirements])
    else:
        lines.append("- Capture MVP requirements before implementation.")
    lines.append("")
    lines.append("## Non-Functional Requirements")
    lines.append("")
    if data.non_functional_requirements:
        lines.extend([f"- {item}" for item in data.non_functional_requirements])
    else:
        lines.append("- Availability target (e.g., 99.9%)")
        lines.append("- Security baseline (authN/authZ, audit logs)")
        lines.append("- Observability baseline (metrics, logs, tracing)")
    lines.append("")
    lines.append("## Constraints")
    lines.append("")
    if data.constraints:
        lines.extend([f"- {item}" for item in data.constraints])
    else:
        lines.append("- TBD constraints")
    lines.append("")
    lines.append("## Assumptions")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.assumed_defaults])
    lines.append("")
    lines.append("## Component Architecture")
    lines.append("")
    lines.extend([f"- {component}" for component in spec.components])
    lines.append("")
    lines.append("## Data Model (Core Entities)")
    lines.append("")
    lines.extend([f"- {entity}" for entity in spec.data_entities])
    lines.append("")
    lines.append("## API Surface (Initial)")
    lines.append("")
    lines.extend([f"- `{endpoint}`" for endpoint in spec.api_endpoints])
    lines.append("")
    lines.append("## Deployment Topology")
    lines.append("")
    lines.append("- Stateless API services behind a load balancer or edge gateway")
    lines.append("- Managed relational database for transactional state")
    if any("Background Worker / Scheduler" == component for component in spec.components):
        lines.append("- Queue + worker for async workloads")
    if any("Integration Adapter Layer" == component for component in spec.components):
        lines.append("- Integration boundary isolated behind adapters and retryable jobs")
    lines.append("- Centralized telemetry and alerting")
    lines.append("")
    lines.append("## Security and Compliance")
    lines.append("")
    lines.append("- Enforce RBAC with least-privilege defaults")
    lines.append("- Encrypt data in transit and at rest")
    lines.append("- Track privileged actions in immutable audit logs")
    lines.append("")
    lines.append("## Risks and Mitigations")
    lines.append("")
    lines.extend([f"- {risk}" for risk in spec.risks])
    lines.append("")
    lines.append("## Delivery Plan")
    lines.append("")
    lines.append("- Phase A: Foundations (repo, CI, observability, auth skeleton)")
    lines.append("- Phase B: Core domain workflows + API contracts")
    lines.append("- Phase C: Hardening (security, performance, SLO tuning)")
    lines.append("")
    lines.append("## Phased Decisions")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.phased_decisions])
    lines.append("")
    lines.append("## Risk-to-Decision Linkage")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.risk_decision_links])
    lines.append("")
    lines.append("## Decision Priority")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.decision_priorities])
    lines.append("")
    lines.append("## ADR Priority Matrix")
    lines.append("")
    lines.extend([f"- {item}" for item in spec.adr_priority_matrix])
    lines.append("")
    lines.append("## Open Questions")
    lines.append("")
    lines.extend([f"- {question}" for question in spec.open_questions])
    lines.append("")
    return "\n".join(lines)


def run(
    data: ArchitectureDesignerInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "architecture-spec",
    overwrite: bool = False,
) -> SkillRunResult:
    """Execute architecture_designer and save architecture markdown."""
    spec = design_architecture(data)
    markdown = render_markdown(data, spec)
    output_path = build_output_path(output_dir, "architecture_designer", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="architecture_designer",
        output_path=output_path,
        summary=f"Architecture spec created for {data.product_name}.",
        metadata=build_run_metadata(
            artifact_type="architecture_spec",
            subject=data.product_name,
            subject_type="product",
            warning_count=len(spec.open_questions),
            extra={
                "product_name": data.product_name,
                "component_count": len(spec.components),
                "entity_count": len(spec.data_entities),
                "endpoint_count": len(spec.api_endpoints),
                "open_question_count": len(spec.open_questions),
                "heuristic_mode": True,
                "confidence": spec.confidence,
            },
        ),
    )
