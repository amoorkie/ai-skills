"""Implementation for architecture_designer."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.skills.architecture_designer.schema import ArchitectureDesignerInput, ArchitectureSpec


def design_architecture(data: ArchitectureDesignerInput) -> ArchitectureSpec:
    """Build a baseline architecture specification model from input requirements."""
    components = [
        "API Gateway / BFF",
        "Application Service Layer",
        "Domain Module(s)",
        "Persistence Layer",
        "Background Worker / Scheduler",
        "Observability Stack (logs, metrics, traces)",
    ]
    api_endpoints = [
        "POST /api/v1/auth/session",
        "GET /api/v1/health",
        "GET /api/v1/resources",
        "POST /api/v1/resources",
        "PATCH /api/v1/resources/{id}",
    ]
    data_entities = [
        "User",
        "Workspace",
        "Resource",
        "AuditLog",
        "Job",
    ]
    risks = [
        "Scope creep due to unclear functional priorities",
        "Operational complexity if observability is delayed",
        "Data quality drift without validation and ownership rules",
    ]
    open_questions = [
        "What throughput and latency targets are contractual?",
        "Which integrations are mandatory in phase 1 vs phase 2?",
        "What retention policy is required for audit and analytics data?",
    ]
    summary = (
        f"{data.product_name} should use a layered modular architecture with explicit boundaries between "
        "API, domain logic, and persistence. Prioritize clear contracts, observability from day one, and "
        "incremental delivery with measurable service-level objectives."
    )
    return ArchitectureSpec(
        product_name=data.product_name,
        summary=summary,
        components=components,
        api_endpoints=api_endpoints,
        data_entities=data_entities,
        risks=risks,
        open_questions=open_questions,
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
    if data.assumptions:
        lines.extend([f"- {item}" for item in data.assumptions])
    else:
        lines.append("- Single region deployment for phase 1.")
        lines.append("- PostgreSQL-compatible relational storage.")
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
    lines.append("- Stateless API services behind a load balancer")
    lines.append("- Managed relational database")
    lines.append("- Queue + worker for async workloads")
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
        metadata={"product_name": data.product_name},
    )
