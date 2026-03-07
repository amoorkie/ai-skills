from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.figma_ui_architect import FigmaUiArchitectInput, generate_ui_spec, run


REQUIRED_HEADINGS = [
    "## Product Goal",
    "## Users",
    "## JTBD",
    "## Flows",
    "## Screens",
    "## Frame Naming",
    "## Components",
    "## States",
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
