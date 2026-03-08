"""Implementation for figma_ui_architect."""

from __future__ import annotations

from pathlib import Path
import re

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.figma_ui_architect.schema import FigmaUiArchitectInput


def _default_users() -> list[str]:
    return ["Admin user", "Operator", "Manager"]


def _default_jtbds() -> list[str]:
    return [
        "When monitoring operations, I want a high-signal dashboard so I can detect issues quickly.",
        "When reviewing item details, I want clear state history so I can decide the next action confidently.",
        "When managing configuration, I want safe defaults and guardrails so I do not break production workflows.",
    ]


def _screen_slug(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")


def _derive_flows(data: FigmaUiArchitectInput) -> list[str]:
    flows: list[str] = []
    for index, jtbd in enumerate(data.jtbds[:3], start=1):
        cleaned = jtbd.strip().rstrip(".")
        if cleaned.lower().startswith("when "):
            cleaned = cleaned[5:]
        cleaned = re.sub(r"\s+", " ", cleaned)
        flows.append(f"{index}. {cleaned[0].upper() + cleaned[1:]} -> surface relevant data -> complete the next action safely.")

    if flows:
        return flows

    return [
        "1. Sign in -> land on dashboard -> inspect KPIs -> drill into exceptions.",
        "2. Open entity detail -> review timeline + metadata -> apply action -> confirm status transition.",
        "3. Navigate to admin settings -> update rules/roles -> validate impact preview -> publish changes.",
    ]


def _derive_screens(data: FigmaUiArchitectInput) -> list[str]:
    text = " ".join([data.product_goal, *data.jtbds, *data.constraints, *data.architecture_context]).lower()
    screens: list[str] = []
    if any(word in text for word in ("dashboard", "monitor", "metric", "sla", "kpi")):
        screens.append("Dashboard Overview")
    if any(word in text for word in ("queue", "triage", "list", "search", "backlog")):
        screens.append("Queue / List View")
    if any(word in text for word in ("detail", "history", "audit", "timeline", "review")):
        screens.append("Detail Workspace")
    if any(word in text for word in ("approve", "approval", "access", "role", "permission")):
        screens.append("Approvals and Access")
    if any(word in text for word in ("setting", "config", "rule", "automation")):
        screens.append("Settings and Rules")
    if any(word in text for word in ("report", "export", "analytics")):
        screens.append("Reports and Exports")
    if any(word in text for word in ("integration", "sync", "webhook")):
        screens.append("Integrations")
    if not screens:
        screens = ["Dashboard Overview", "Work Queue", "Detail Workspace", "Settings and Rules"]
    deduped: list[str] = []
    for screen in screens:
        if screen not in deduped:
            deduped.append(screen)
    return deduped[:6]


def _derive_components(data: FigmaUiArchitectInput, screens: list[str]) -> list[str]:
    text = " ".join([data.product_goal, *data.jtbds, *data.constraints, *data.architecture_context]).lower()
    components = ["App shell with navigation and context switcher"]
    if any("Dashboard" in screen for screen in screens):
        components.append("KPI cards and trend panels")
    if any("Queue" in screen or "List" in screen for screen in screens):
        components.append("Searchable data table with filters and bulk actions")
    if any("Detail" in screen for screen in screens):
        components.append("Detail panels for summary, timeline, and related records")
    if any("Approvals" in screen for screen in screens):
        components.append("Approval cards with diff preview and decision actions")
    if any("Settings" in screen for screen in screens):
        components.append("Form primitives for rules, roles, and environment controls")
    if any(word in text for word in ("audit", "history", "timeline")):
        components.append("Audit/event stream with actor and timestamp metadata")
    if any(word in text for word in ("mobile", "tablet", "responsive")):
        components.append("Responsive navigation pattern for compact layouts")
    components.append("Feedback UI for loading, validation, and empty states")
    return components[:7]


def _derive_states(data: FigmaUiArchitectInput) -> list[str]:
    text = " ".join([data.preferred_platform, *data.constraints, *data.jtbds, *data.architecture_context]).lower()
    states = [
        "Loading, empty, success, partial failure, and permission-denied states for each major screen",
    ]
    if any(word in text for word in ("queue", "table", "list")):
        states.append("List row states: default, hovered, selected, bulk-selected, disabled")
    if any(word in text for word in ("approval", "action", "submit")):
        states.append("Primary action states: default, pending approval, success, error")
    if any(word in text for word in ("form", "setting", "config", "rule")):
        states.append("Form states: pristine, dirty, invalid, submitted")
    if any(word in text for word in ("realtime", "real-time", "monitor", "dashboard")):
        states.append("Live-update states: fresh, stale, reconnecting")
    if any(word in text for word in ("wcag", "accessibility")):
        states.append("Accessible focus, keyboard-navigation, and contrast-review states")
    return states[:5]


def _derive_open_questions(data: FigmaUiArchitectInput, screens: list[str]) -> list[str]:
    text = " ".join([data.product_goal, *data.jtbds, *data.constraints, *data.architecture_context]).lower()
    questions: list[str] = []
    if any("Dashboard" in screen for screen in screens):
        questions.append("Which metrics are mission-critical on first-load dashboard view?")
    if any("Approvals" in screen for screen in screens):
        questions.append("What approval rules and escalation paths are required for destructive actions?")
    if any(word in text for word in ("integration", "sync", "webhook")):
        questions.append("Which external systems should influence screen state in real time?")
    if any(word in text for word in ("wcag", "accessibility")):
        questions.append("What accessibility acceptance bar is required for release sign-off?")
    if not questions:
        questions.append("What is the most important first-run workflow to optimize for new users?")
        questions.append("Which data points must remain visible without extra clicks?")
    return questions[:4]


def _derive_observed_signals(data: FigmaUiArchitectInput, users: list[str], jtbds: list[str]) -> list[str]:
    signals = [f"Product goal: {data.product_goal.strip()}"]
    signals.append(f"Explicit users/personas: {', '.join(users[:3])}.")
    signals.append(f"Explicit JTBD count: {len(jtbds)}.")
    if data.constraints:
        signals.append("Explicit constraints: " + ", ".join(data.constraints[:3]) + ".")
    if data.repo_context_signals:
        signals.append("Repository context: " + "; ".join(data.repo_context_signals[:2]))
    if data.architecture_context:
        signals.append("Architecture context: " + "; ".join(data.architecture_context[:2]))
    signals.append(f"Preferred platform: {data.preferred_platform}.")
    return signals[:5]


def _derive_inferred_decisions(
    data: FigmaUiArchitectInput,
    screens: list[str],
    components: list[str],
    states: list[str],
) -> list[str]:
    decisions = ["Organize the handoff around flows first, then screens, then reusable component patterns."]
    if any("Queue" in screen or "List" in screen for screen in screens):
        decisions.append("Prioritize dense table/list interactions because the input implies triage or queue management.")
    if any("Settings" in screen for screen in screens):
        decisions.append("Treat configuration as a guarded workflow with previews, validation states, and safe defaults.")
    if any("Approvals" in screen for screen in screens):
        decisions.append("Surface approval decisions with context and diff-style review to reduce destructive mistakes.")
    if any("Audit" in component or "event stream" in component.lower() for component in components):
        decisions.append("Expose history and actor metadata inline because auditability appears central to decision-making.")
    if any("loading" in state.lower() or "permission-denied" in state.lower() for state in states):
        decisions.append("Model system states explicitly so the Figma handoff covers operational and permission edge cases.")
    if any("workflow orchestrator" in item.lower() for item in data.architecture_context):
        decisions.append("Reflect orchestration-heavy behavior in the UI by making state transitions and step context visible to operators.")
    if any("integration" in item.lower() for item in data.architecture_context):
        decisions.append("Keep integration health and sync state visible because architecture decisions imply external-system dependencies.")
    return decisions[:5]


def _derive_assumptions(data: FigmaUiArchitectInput, used_default_users: bool, used_default_jtbds: bool) -> list[str]:
    assumptions: list[str] = []
    if used_default_users:
        assumptions.append("Default user personas were inserted because no explicit users were provided.")
    if used_default_jtbds:
        assumptions.append("Default JTBDs were inserted because no explicit jobs-to-be-done were provided.")
    if not data.constraints:
        assumptions.append("Responsive behavior and accessibility scope still need product confirmation.")
    if not any("mobile" in constraint.lower() for constraint in data.constraints):
        assumptions.append("Desktop-first admin workflows are treated as primary unless mobile constraints are explicit.")
    if data.architecture_context:
        assumptions.append("Architecture-derived constraints were treated as design inputs and should be validated with engineering owners.")
    return assumptions[:5]


def _estimate_confidence(data: FigmaUiArchitectInput) -> str:
    evidence_points = 0
    if data.users:
        evidence_points += 1
    if data.jtbds:
        evidence_points += 1
    if data.constraints:
        evidence_points += 1
    if data.preferred_platform:
        evidence_points += 1
    if evidence_points >= 3:
        return "high"
    if evidence_points >= 2:
        return "medium"
    return "low"


def _derive_decision_log(data: FigmaUiArchitectInput, screens: list[str], components: list[str]) -> list[str]:
    decisions = [
        "Decision: structure the Figma handoff around end-to-end flows first so screen intent stays tied to user work."
    ]
    if any("Queue" in screen or "List" in screen for screen in screens):
        decisions.append("Decision: prioritize queue/list surfaces because triage workflows depend on scanability and bulk actions.")
    if any("Settings" in screen for screen in screens):
        decisions.append("Decision: separate settings from operational workspaces to reduce accidental configuration changes.")
    if any("Approvals" in screen for screen in screens):
        decisions.append("Decision: make approval actions contextual so reviewers see history and consequences before acting.")
    if any("Feedback UI" in component for component in components):
        decisions.append("Decision: define feedback and empty states as reusable patterns rather than one-off screen notes.")
    return decisions[:5]


def _derive_tradeoffs(data: FigmaUiArchitectInput, screens: list[str], constraints: list[str]) -> list[str]:
    tradeoffs = [
        "Tradeoff: high-signal operational layouts improve speed for expert users, but can feel dense for first-time users."
    ]
    if any("Approvals" in screen for screen in screens):
        tradeoffs.append("Tradeoff: adding context-heavy approval screens improves safety, but increases visual complexity and handoff scope.")
    if any("Settings" in screen for screen in screens):
        tradeoffs.append("Tradeoff: strong guardrails in settings reduce mistakes, but can slow down expert admins performing bulk changes.")
    if any("mobile" in constraint.lower() for constraint in constraints):
        tradeoffs.append("Tradeoff: mobile-first interaction patterns improve portability, but constrain information density for admin workflows.")
    else:
        tradeoffs.append("Tradeoff: desktop-first density improves throughput, but requires explicit compact-layout decisions for tablet/mobile states.")
    return tradeoffs[:5]


def _derive_alternatives_considered(screens: list[str], constraints: list[str]) -> list[str]:
    alternatives = [
        "Alternative considered: flat screen inventory without explicit flow grouping. Rejected because handoff quality is stronger when screens remain attached to user journeys."
    ]
    if any("Queue" in screen or "List" in screen for screen in screens):
        alternatives.append("Alternative considered: card-heavy triage UI. Rejected because queue/list workflows usually need denser scanning and bulk action affordances.")
    if any("Settings" in screen for screen in screens):
        alternatives.append("Alternative considered: embed settings inline across operational screens. Rejected to reduce accidental configuration changes and ownership confusion.")
    if any("Approvals" in screen for screen in screens):
        alternatives.append("Alternative considered: put approval actions directly in list rows. Rejected because high-risk actions need more context and review state.")
    if any("mobile" in constraint.lower() for constraint in constraints):
        alternatives.append("Alternative considered: desktop-only density. Rejected because the input explicitly calls for mobile constraints.")
    return alternatives[:5]


def _derive_navigation_model(screens: list[str]) -> list[str]:
    navigation = ["Primary navigation: Overview -> operational workspaces -> settings/integrations."]
    if any("Dashboard" in screen for screen in screens):
        navigation.append("Landing route: Dashboard Overview for high-signal status and drill-down entry.")
    if any("Queue" in screen or "List" in screen for screen in screens):
        navigation.append("Operational route: Queue / List View as the main action-taking workspace.")
    if any("Detail" in screen for screen in screens):
        navigation.append("Deep-link route: Detail Workspace reachable from lists, alerts, and approval contexts.")
    if any("Settings" in screen for screen in screens):
        navigation.append("Admin route: Settings and Rules isolated from day-to-day operations.")
    return navigation[:5]


def _derive_component_mapping(screens: list[str], components: list[str]) -> list[str]:
    mapping: list[str] = []
    for screen in screens:
        linked = [component for component in components if (
            ("Dashboard" in screen and "KPI" in component)
            or (("Queue" in screen or "List" in screen) and "table" in component.lower())
            or ("Detail" in screen and "Detail panels" in component)
            or ("Approvals" in screen and "Approval cards" in component)
            or ("Settings" in screen and "Form primitives" in component)
            or ("Integrations" in screen and "Form primitives" in component)
        )]
        if not linked:
            linked = components[:2]
        mapping.append(f"{screen}: {', '.join(linked[:3])}")
    return mapping[:6]


def _derive_flow_screen_matrix(flows: list[str], screens: list[str]) -> list[str]:
    matrix: list[str] = []
    for flow in flows[:3]:
        if "dashboard" in flow.lower():
            linked = [screen for screen in screens if "Dashboard" in screen or "Detail" in screen]
        elif any(keyword in flow.lower() for keyword in ("triag", "queue", "bulk", "list")):
            linked = [screen for screen in screens if "Queue" in screen or "Detail" in screen]
        elif any(keyword in flow.lower() for keyword in ("config", "setting", "rule")):
            linked = [screen for screen in screens if "Settings" in screen or "Integrations" in screen]
        elif any(keyword in flow.lower() for keyword in ("approve", "access")):
            linked = [screen for screen in screens if "Approvals" in screen or "Detail" in screen]
        else:
            linked = screens[:2]
        matrix.append(f"{flow.split('->', maxsplit=1)[0].strip()}: {', '.join(linked[:3])}")
    return matrix[:4]


def _derive_state_coverage_matrix(screens: list[str], states: list[str]) -> list[str]:
    matrix: list[str] = []
    for screen in screens[:5]:
        linked_states = [state for state in states if (
            ("Queue" in screen and "List row states" in state)
            or ("Approvals" in screen and "Primary action states" in state)
            or ("Settings" in screen and "Form states" in state)
            or ("Dashboard" in screen and "Live-update states" in state)
        )]
        shared_states = [state for state in states if "Loading, empty, success" in state]
        combined = linked_states + shared_states
        if not combined:
            combined = states[:2]
        matrix.append(f"{screen}: {', '.join(combined[:3])}")
    return matrix[:5]


def _derive_component_ownership_matrix(screens: list[str], components: list[str]) -> list[str]:
    ownership: list[str] = []
    for component in components[:6]:
        if "KPI" in component:
            owner = "Dashboard Overview"
        elif "table" in component.lower():
            owner = "Queue / List View"
        elif "Detail panels" in component:
            owner = "Detail Workspace"
        elif "Approval cards" in component:
            owner = "Approvals and Access"
        elif "Form primitives" in component:
            owner = "Settings and Rules"
        else:
            owner = screens[0] if screens else "Primary shell"
        ownership.append(f"{component}: primary owner `{owner}`")
    return ownership[:6]


def _derive_breakpoint_matrix(screens: list[str], constraints: list[str]) -> list[str]:
    matrix: list[str] = []
    mobile_explicit = any("mobile" in constraint.lower() for constraint in constraints)
    tablet_explicit = any("tablet" in constraint.lower() or "responsive" in constraint.lower() for constraint in constraints)
    for screen in screens[:5]:
        if mobile_explicit:
            behavior = "mobile condensed layout + desktop expanded layout"
        elif tablet_explicit:
            behavior = "desktop primary layout + tablet compact variant"
        else:
            behavior = "desktop primary layout; compact behavior still needs confirmation"
        matrix.append(f"{screen}: {behavior}")
    return matrix[:5]


def _derive_component_contract_matrix(components: list[str], states: list[str]) -> list[str]:
    contracts: list[str] = []
    for component in components[:6]:
        lowered = component.lower()
        if "navigation" in lowered:
            contracts.append(
                f"{component}: props=`activeSection`, `contextLabel`, `notificationCount`; state=`collapsed`, `expanded`, `current selection`"
            )
        elif "kpi" in lowered:
            contracts.append(
                f"{component}: props=`label`, `value`, `trend`, `statusTone`; state=`loading`, `fresh`, `stale`"
            )
        elif "table" in lowered:
            contracts.append(
                f"{component}: props=`columns`, `rows`, `filters`, `bulkActions`; state=`default`, `selected`, `bulk-selected`, `empty`"
            )
        elif "detail panels" in lowered:
            contracts.append(
                f"{component}: props=`recordSummary`, `timelineItems`, `relatedRecords`; state=`loading`, `resolved`, `permission-denied`"
            )
        elif "approval cards" in lowered:
            contracts.append(
                f"{component}: props=`requestSummary`, `diffPreview`, `approverActions`; state=`pending`, `approved`, `rejected`, `error`"
            )
        elif "form primitives" in lowered:
            contracts.append(
                f"{component}: props=`fieldSchema`, `defaultValues`, `validationHints`; state=`pristine`, `dirty`, `invalid`, `submitted`"
            )
        else:
            contracts.append(
                f"{component}: props=`content`, `statusTone`, `actions`; state=`default`, `loading`, `empty`, `error`"
            )
    if not contracts and states:
        contracts.append(f"Shared contract fallback: props=`content`, `actions`; state=`{states[0]}`")
    return contracts[:6]


def generate_ui_spec(data: FigmaUiArchitectInput) -> str:
    """Generate a Figma-ready UI planning spec for product/design handoff."""
    used_default_users = not data.users
    used_default_jtbds = not data.jtbds
    users = data.users or _default_users()
    jtbds = data.jtbds or _default_jtbds()
    working_data = data.model_copy(update={"jtbds": jtbds})
    flows = _derive_flows(working_data)
    screens = _derive_screens(working_data)
    components = _derive_components(working_data, screens)
    states = _derive_states(working_data)
    open_questions = _derive_open_questions(working_data, screens)
    observed_signals = _derive_observed_signals(data, users, jtbds)
    inferred_decisions = _derive_inferred_decisions(data, screens, components, states)
    assumptions = _derive_assumptions(data, used_default_users, used_default_jtbds)
    decision_log = _derive_decision_log(data, screens, components)
    tradeoffs = _derive_tradeoffs(data, screens, data.constraints)
    alternatives_considered = _derive_alternatives_considered(screens, data.constraints)
    navigation_model = _derive_navigation_model(screens)
    component_mapping = _derive_component_mapping(screens, components)
    flow_screen_matrix = _derive_flow_screen_matrix(flows, screens)
    state_coverage_matrix = _derive_state_coverage_matrix(screens, states)
    component_ownership_matrix = _derive_component_ownership_matrix(screens, components)
    breakpoint_matrix = _derive_breakpoint_matrix(screens, data.constraints)
    component_contract_matrix = _derive_component_contract_matrix(components, states)

    lines: list[str] = []
    lines.append(f"# Figma UI Architecture Spec: {data.product_name}")
    lines.append("")
    lines.append("## Product Goal")
    lines.append("")
    lines.append(data.product_goal.strip())
    lines.append("")
    lines.append("## Observed Signals")
    lines.append("")
    lines.extend([f"- {item}" for item in observed_signals])
    lines.append("")
    lines.append("## Inferred Decisions")
    lines.append("")
    lines.extend([f"- {item}" for item in inferred_decisions])
    lines.append("")
    lines.append("## Decision Log")
    lines.append("")
    lines.extend([f"- {item}" for item in decision_log])
    lines.append("")
    lines.append("## Tradeoffs")
    lines.append("")
    lines.extend([f"- {item}" for item in tradeoffs])
    lines.append("")
    lines.append("## Alternatives Considered")
    lines.append("")
    lines.extend([f"- {item}" for item in alternatives_considered])
    lines.append("")
    lines.append("## Users")
    lines.append("")
    lines.extend([f"- {user}" for user in users])
    lines.append("")
    lines.append("## JTBD")
    lines.append("")
    lines.extend([f"- {jtbd}" for jtbd in jtbds])
    lines.append("")
    lines.append("## Assumptions")
    lines.append("")
    if assumptions:
        lines.extend([f"- {item}" for item in assumptions])
    else:
        lines.append("- No major defaults were required beyond the supplied input.")
    lines.append("")
    if data.architecture_context:
        lines.append("## Upstream Architecture Context")
        lines.append("")
        lines.extend([f"- {item}" for item in data.architecture_context[:6]])
        lines.append("")
    lines.append("## Flows")
    lines.append("")
    lines.extend(flows)
    lines.append("")
    lines.append("## Screens")
    lines.append("")
    lines.extend([f"- {screen}" for screen in screens])
    lines.append("")
    lines.append("## Navigation Model")
    lines.append("")
    lines.extend([f"- {item}" for item in navigation_model])
    lines.append("")
    lines.append("## Flow-to-Screen Matrix")
    lines.append("")
    lines.extend([f"- {item}" for item in flow_screen_matrix])
    lines.append("")
    lines.append("## Frame Naming")
    lines.append("")
    for index, screen in enumerate(screens, start=1):
        lines.append(f"- `{index:02d}_{_screen_slug(screen)}/Primary_Default`")
    lines.append("")
    lines.append("## Components")
    lines.append("")
    lines.extend([f"- {component}" for component in components])
    lines.append("")
    lines.append("## Screen-to-Component Mapping")
    lines.append("")
    lines.extend([f"- {item}" for item in component_mapping])
    lines.append("")
    lines.append("## Component Ownership Matrix")
    lines.append("")
    lines.extend([f"- {item}" for item in component_ownership_matrix])
    lines.append("")
    lines.append("## Component Contract Matrix")
    lines.append("")
    lines.extend([f"- {item}" for item in component_contract_matrix])
    lines.append("")
    lines.append("## States")
    lines.append("")
    lines.extend([f"- {state}" for state in states])
    lines.append("")
    lines.append("## State Coverage Matrix")
    lines.append("")
    lines.extend([f"- {item}" for item in state_coverage_matrix])
    lines.append("")
    lines.append("## Breakpoint Matrix")
    lines.append("")
    lines.extend([f"- {item}" for item in breakpoint_matrix])
    lines.append("")
    lines.append("## Handoff Notes")
    lines.append("")
    lines.append(f"- Platform target: {data.preferred_platform}")
    lines.append(f"- Visual tone: {data.design_tone}")
    if data.constraints:
        lines.extend([f"- Constraint: {constraint}" for constraint in data.constraints])
    if any("mobile" in constraint.lower() for constraint in data.constraints):
        lines.append("- Define primary navigation and input ergonomics for mobile-first execution.")
    else:
        lines.append("- Define responsive behavior for desktop-first admin workflows and a compact tablet layout.")
    lines.append("- Align spacing/typography tokens with existing design system before final polish.")
    lines.append("- Attach interaction notes to all flows with branching conditions.")
    lines.append("")
    lines.append("## Open Questions")
    lines.append("")
    lines.extend([f"- {question}" for question in open_questions])
    lines.append("")
    return "\n".join(lines)


def _count_open_questions(markdown: str) -> int:
    in_section = False
    count = 0
    for line in markdown.splitlines():
        if line == "## Open Questions":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("- "):
            count += 1
    return count


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
        metadata=build_run_metadata(
            artifact_type="ui_architecture_spec",
            subject=data.product_name,
            subject_type="product",
            warning_count=_count_open_questions(markdown),
            extra={
                "product_name": data.product_name,
                "platform": data.preferred_platform,
                "user_count": len(data.users or _default_users()),
                "jtbd_count": len(data.jtbds or _default_jtbds()),
                "heuristic_mode": True,
                "confidence": _estimate_confidence(data),
            },
        ),
    )
