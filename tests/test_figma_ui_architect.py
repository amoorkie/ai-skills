from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.architecture_designer import ArchitectureDesignerInput, design_architecture
from ai_skills_toolkit.skills.figma_ui_architect import (
    FigmaUiArchitectInput,
    enrich_input_from_context,
    generate_ui_spec,
    run,
)
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput, analyze_repository


REQUIRED_HEADINGS = [
    "## Product Goal",
    "## Observed Signals",
    "## Inferred Decisions",
    "## Decision Log",
    "## Tradeoffs",
    "## Alternatives Considered",
    "## Users",
    "## JTBD",
    "## Assumptions",
    "## Flows",
    "## Screens",
    "## Navigation Model",
    "## Flow-to-Screen Matrix",
    "## Frame Naming",
    "## Components",
    "## Screen-to-Component Mapping",
    "## Component Ownership Matrix",
    "## Component Contract Matrix",
    "## States",
    "## State Coverage Matrix",
    "## Breakpoint Matrix",
    "## Handoff Notes",
    "## Open Questions",
]


def test_figma_ui_architect_contains_required_sections() -> None:
    spec = generate_ui_spec(
        FigmaUiArchitectInput(
            product_name="Admin Tool",
            product_goal="Help teams manage access, tasks, and audit trails efficiently.",
        )
    )
    for heading in REQUIRED_HEADINGS:
        assert heading in spec


def test_figma_ui_architect_writes_output(tmp_path: Path) -> None:
    result = run(
        FigmaUiArchitectInput(
            product_name="Mini Dashboard",
            product_goal="Help support managers monitor SLA breaches and prioritize response.",
        ),
        output_dir=tmp_path / "generated",
        output_name="mini-dashboard-spec",
    )
    assert result.output_path.exists()
    assert result.metadata["heuristic_mode"] is True
    assert result.metadata["confidence"] in {"low", "medium", "high"}


def test_figma_ui_architect_renders_constraints_flatly() -> None:
    spec = generate_ui_spec(
        FigmaUiArchitectInput(
            product_name="Admin Tool",
            product_goal="Help operators manage queue triage.",
            constraints=["Desktop-first", "WCAG 2.1 AA"],
        )
    )
    assert "- Constraint: Desktop-first" in spec
    assert "- Constraint: WCAG 2.1 AA" in spec


def test_figma_ui_architect_derives_screens_from_jtbds_and_constraints() -> None:
    spec = generate_ui_spec(
        FigmaUiArchitectInput(
            product_name="Access Control",
            product_goal="Help security teams approve access requests and review audit history.",
            jtbds=[
                "When reviewing access requests, I want to approve or reject them quickly.",
                "When investigating incidents, I want audit history so I can explain account changes.",
            ],
            constraints=["WCAG 2.1 AA", "Desktop-first"],
        )
    )

    assert "- Approvals and Access" in spec
    assert "- Detail Workspace" in spec
    assert "approve or reject them quickly" in spec
    assert "What approval rules and escalation paths are required" in spec


def test_figma_ui_architect_changes_screen_plan_for_different_products() -> None:
    support_spec = generate_ui_spec(
        FigmaUiArchitectInput(
            product_name="Support Desk",
            product_goal="Help support leads monitor SLA breaches and triage ticket queues.",
            jtbds=["When triaging queues, I want filters and bulk actions so I can respond faster."],
        )
    )
    settings_spec = generate_ui_spec(
        FigmaUiArchitectInput(
            product_name="Automation Admin",
            product_goal="Help admins configure automation rules and integrations safely.",
            jtbds=["When configuring automation, I want clear settings and previews so I can avoid production mistakes."],
        )
    )

    assert "- Queue / List View" in support_spec
    assert "- Settings and Rules" not in support_spec
    assert "- Settings and Rules" in settings_spec
    assert "Tradeoff:" in support_spec
    assert "Decision:" in settings_spec
    assert "Alternative considered:" in settings_spec
    assert "Navigation Model" in support_spec
    assert "Flow-to-Screen Matrix" in support_spec
    assert "State Coverage Matrix" in settings_spec
    assert "Component Ownership Matrix" in settings_spec
    assert "Component Contract Matrix" in settings_spec
    assert "Breakpoint Matrix" in support_spec


def test_figma_ui_architect_marks_default_assumptions_when_inputs_are_sparse() -> None:
    spec = generate_ui_spec(
        FigmaUiArchitectInput(
            product_name="Minimal Tool",
            product_goal="Help operators review records.",
        )
    )

    assert "Default user personas were inserted" in spec
    assert "Default JTBDs were inserted" in spec


def test_figma_ui_architect_can_ingest_architecture_and_repo_context(sample_repo: Path) -> None:
    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo))
    architecture_spec = design_architecture(
        ArchitectureDesignerInput(
            product_name="Ops Console",
            product_goal="Help operators review workflows and integrations safely.",
            functional_requirements=["Support approval workflows", "Integrate with third-party systems"],
        )
    )
    enriched = enrich_input_from_context(
        FigmaUiArchitectInput(
            product_name="Ops Console",
            product_goal="Help operators review workflows and integrations safely.",
        ),
        architecture_spec=architecture_spec,
        repo_analysis=analysis,
    )

    spec = generate_ui_spec(enriched)

    assert enriched.repo_context_signals
    assert enriched.architecture_context
    assert "## Upstream Architecture Context" in spec
    assert "Architecture context:" in spec
