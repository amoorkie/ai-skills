from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.architecture_designer import (
    ArchitectureDesignerInput,
    design_architecture,
    enrich_input_from_repo_analysis,
    run,
)
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput, analyze_repository


def test_architecture_designer_creates_spec(tmp_path: Path) -> None:
    result = run(
        ArchitectureDesignerInput(
            product_name="Ops Portal",
            product_goal="Provide incident and workload visibility for operations teams.",
            primary_users=["Ops manager"],
        ),
        output_dir=tmp_path / "generated",
        output_name="ops-portal-arch",
    )
    text = result.output_path.read_text(encoding="utf-8")
    assert "## Observed Signals" in text
    assert "## Inferred Decisions" in text
    assert "## Decision Log" in text
    assert "## Tradeoffs" in text
    assert "## Alternatives Considered" in text
    assert "## ADR Summary" in text
    assert "## Component Architecture" in text
    assert "## API Surface (Initial)" in text
    assert "## Risks and Mitigations" in text
    assert "## Phased Decisions" in text
    assert "## Risk-to-Decision Linkage" in text
    assert "## ADR Priority Matrix" in text
    assert result.metadata["heuristic_mode"] is True
    assert result.metadata["confidence"] in {"low", "medium", "high"}


def test_architecture_designer_includes_custom_constraints(tmp_path: Path) -> None:
    result = run(
        ArchitectureDesignerInput(
            product_name="Finance Portal",
            product_goal="Provide reliable financial operations workflows.",
            constraints=["Deploy in one region", "Use managed PostgreSQL"],
        ),
        output_dir=tmp_path / "generated",
        output_name="finance-portal-arch",
    )
    text = result.output_path.read_text(encoding="utf-8")
    assert "- Deploy in one region" in text
    assert "- Use managed PostgreSQL" in text


def test_architecture_designer_derives_entities_and_endpoints_from_requirements() -> None:
    spec = design_architecture(
        ArchitectureDesignerInput(
            product_name="Approval Hub",
            product_goal="Help teams approve vendor invoices and audit policy decisions.",
            functional_requirements=[
                "Support approval workflows for invoices",
                "Track audit history for policy decisions",
                "Integrate with ERP systems",
            ],
            constraints=["Single region"],
        )
    )

    assert any("Invoice" in entity for entity in spec.data_entities)
    assert any("/invoices" in endpoint for endpoint in spec.api_endpoints)
    assert any("Workflow Orchestrator" == component for component in spec.components)
    assert any("Integration Adapter Layer" == component for component in spec.components)
    assert spec.confidence in {"medium", "high"}
    assert spec.observed_signals
    assert spec.inferred_decisions
    assert spec.decision_log
    assert spec.tradeoffs
    assert spec.alternatives_considered
    assert spec.adr_records
    assert spec.phased_decisions
    assert spec.risk_decision_links
    assert spec.decision_priorities
    assert spec.adr_priority_matrix
    assert spec.assumed_defaults


def test_architecture_designer_changes_output_for_different_domains() -> None:
    finance = design_architecture(
        ArchitectureDesignerInput(
            product_name="Finance Portal",
            product_goal="Manage invoices, approvals, and audit history for finance teams.",
            functional_requirements=["Approve invoices", "Export audit reports"],
        )
    )
    support = design_architecture(
        ArchitectureDesignerInput(
            product_name="Support Console",
            product_goal="Help support teams triage tickets and monitor SLA risk.",
            functional_requirements=["Track ticket queues", "Monitor SLA breaches"],
        )
    )

    assert finance.data_entities != support.data_entities
    assert finance.api_endpoints != support.api_endpoints


def test_architecture_designer_can_ingest_repo_context(sample_repo: Path) -> None:
    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo))
    data = enrich_input_from_repo_analysis(
        ArchitectureDesignerInput(
            product_name="Ops Portal",
            product_goal="Provide operational visibility for tooling teams.",
        ),
        analysis,
    )

    spec = design_architecture(data)

    assert data.repo_context_signals
    assert any("Repository context carried into architecture planning" in item for item in spec.observed_signals)
