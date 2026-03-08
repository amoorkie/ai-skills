"""Built-in evaluation corpus for figma_ui_architect."""

from __future__ import annotations

from ai_skills_toolkit.skills.figma_ui_architect.eval_types import EvaluationCase
from ai_skills_toolkit.skills.figma_ui_architect.schema import FigmaUiArchitectInput


def build_builtin_eval_cases() -> list[EvaluationCase]:
    """Create the built-in evaluation corpus."""
    return [
        EvaluationCase(
            name="access-approval-workspace",
            input_data=FigmaUiArchitectInput(
                product_name="Access Control",
                product_goal="Help security teams approve access requests and review audit history.",
                jtbds=[
                    "When reviewing access requests, I want to approve or reject them quickly.",
                    "When investigating incidents, I want audit history so I can explain account changes.",
                ],
                constraints=["WCAG 2.1 AA", "Desktop-first"],
            ),
            expected_fragments={
                "- Approvals and Access",
                "- Detail Workspace",
                "approve or reject them quickly",
                "What approval rules and escalation paths are required",
                "Accessible focus, keyboard-navigation, and contrast-review states",
            },
        ),
        EvaluationCase(
            name="support-queue-workflow",
            input_data=FigmaUiArchitectInput(
                product_name="Support Desk",
                product_goal="Help support leads monitor SLA breaches and triage ticket queues.",
                jtbds=["When triaging queues, I want filters and bulk actions so I can respond faster."],
            ),
            expected_fragments={
                "- Queue / List View",
                "Searchable data table with filters and bulk actions",
                "List row states: default, hovered, selected, bulk-selected, disabled",
            },
            forbidden_fragments={"- Settings and Rules"},
        ),
        EvaluationCase(
            name="automation-settings-workflow",
            input_data=FigmaUiArchitectInput(
                product_name="Automation Admin",
                product_goal="Help admins configure automation rules and integrations safely.",
                jtbds=[
                    "When configuring automation, I want clear settings and previews so I can avoid production mistakes."
                ],
                constraints=["Responsive web"],
            ),
            expected_fragments={
                "- Settings and Rules",
                "- Integrations",
                "Form primitives for rules, roles, and environment controls",
                "Form states: pristine, dirty, invalid, submitted",
            },
        ),
    ]
