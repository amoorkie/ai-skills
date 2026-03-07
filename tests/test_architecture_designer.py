from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.architecture_designer import ArchitectureDesignerInput, run


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
    assert "## Component Architecture" in text
    assert "## API Surface (Initial)" in text
    assert "## Risks and Mitigations" in text


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
