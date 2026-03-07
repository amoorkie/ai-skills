"""Implementation for figma_ui_architect."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.skills.figma_ui_architect.schema import FigmaUiArchitectInput


def _default_users() -> list[str]:
    return ["Admin user", "Operator", "Manager"]


def _default_jtbds() -> list[str]:
    return [
        "When monitoring operations, I want a high-signal dashboard so I can detect issues quickly.",
        "When reviewing item details, I want clear state history so I can decide the next action confidently.",
        "When managing configuration, I want safe defaults and guardrails so I do not break production workflows.",
    ]


def generate_ui_spec(data: FigmaUiArchitectInput) -> str:
    """Generate a Figma-ready UI planning spec for product/design handoff."""
    users = data.users or _default_users()
    jtbds = data.jtbds or _default_jtbds()

    lines: list[str] = []
    lines.append(f"# Figma UI Architecture Spec: {data.product_name}")
    lines.append("")
    lines.append("## Product Goal")
    lines.append("")
    lines.append(data.product_goal.strip())
    lines.append("")
    lines.append("## Users")
    lines.append("")
    lines.extend([f"- {user}" for user in users])
    lines.append("")
    lines.append("## JTBD")
    lines.append("")
    lines.extend([f"- {jtbd}" for jtbd in jtbds])
    lines.append("")
    lines.append("## Flows")
    lines.append("")
    lines.append("1. Sign in -> land on dashboard -> inspect KPIs -> drill into exceptions.")
    lines.append("2. Open entity detail -> review timeline + metadata -> apply action -> confirm status transition.")
    lines.append("3. Navigate to admin settings -> update rules/roles -> validate impact preview -> publish changes.")
    lines.append("")
    lines.append("## Screens")
    lines.append("")
    lines.append("- Dashboard Overview (mini app + KPI panels + alert feed)")
    lines.append("- Entity List (search, filter, bulk actions)")
    lines.append("- Entity Detail (timeline, attributes, action rail)")
    lines.append("- Admin Settings (roles, automation rules, environment toggles)")
    lines.append("- Audit Log (event stream + export controls)")
    lines.append("")
    lines.append("## Frame Naming")
    lines.append("")
    lines.append("- `01_Dashboard/Overview_Default`")
    lines.append("- `02_Entities/List_Filtered`")
    lines.append("- `03_Entities/Detail_Expanded`")
    lines.append("- `04_Admin/Settings_Roles`")
    lines.append("- `05_Audit/Log_WithResults`")
    lines.append("")
    lines.append("## Components")
    lines.append("")
    lines.append("- App shell (sidebar + topbar + environment switcher)")
    lines.append("- KPI cards (normal, warning, critical)")
    lines.append("- Data table with sticky header, column controls, pagination")
    lines.append("- Global filters (date range, owner, status, tag)")
    lines.append("- Detail panel blocks (summary, timeline, related items, actions)")
    lines.append("- Form primitives (text input, select, segmented control, multi-select)")
    lines.append("- Feedback UI (toast, inline validation, empty states, loading skeleton)")
    lines.append("")
    lines.append("## States")
    lines.append("")
    lines.append("- Loading, empty, success, partial failure, and permission-denied states for each major screen")
    lines.append("- Table row states: default, hovered, selected, disabled")
    lines.append("- Action button states: default, pending, success, error")
    lines.append("- Form states: pristine, dirty, invalid, submitted")
    lines.append("")
    lines.append("## Handoff Notes")
    lines.append("")
    lines.append(f"- Platform target: {data.preferred_platform}")
    lines.append(f"- Visual tone: {data.design_tone}")
    if data.constraints:
        lines.extend([f"- Constraint: {constraint}" for constraint in data.constraints])
    lines.append("- Define responsive behavior for desktop-first admin workflows and a compact tablet layout.")
    lines.append("- Align spacing/typography tokens with existing design system before final polish.")
    lines.append("- Attach interaction notes to all flows with branching conditions.")
    lines.append("")
    lines.append("## Open Questions")
    lines.append("")
    lines.append("- Which metrics are mission-critical on first-load dashboard view?")
    lines.append("- What approval rules are required for destructive admin actions?")
    lines.append("- Which integrations should influence entity state in real time?")
    lines.append("- What accessibility bar is required (e.g., WCAG 2.1 AA)?")
    lines.append("")
    return "\n".join(lines)


def run(
    data: FigmaUiArchitectInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "figma-ui-architecture-spec",
    overwrite: bool = False,
) -> SkillRunResult:
    """Execute figma_ui_architect and save markdown output."""
    markdown = generate_ui_spec(data)
    output_path = build_output_path(output_dir, "figma_ui_architect", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="figma_ui_architect",
        output_path=output_path,
        summary=f"Figma-ready UI architecture spec created for {data.product_name}.",
        metadata={"product_name": data.product_name, "platform": data.preferred_platform},
    )
