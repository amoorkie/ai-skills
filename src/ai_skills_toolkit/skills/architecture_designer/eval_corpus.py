"""Built-in evaluation corpus for architecture_designer."""

from __future__ import annotations

from ai_skills_toolkit.skills.architecture_designer.eval_types import EvaluationCase
from ai_skills_toolkit.skills.architecture_designer.schema import ArchitectureDesignerInput


def build_builtin_eval_cases() -> list[EvaluationCase]:
    """Create the built-in evaluation corpus."""
    return [
        EvaluationCase(
            name="approval-workflow-domain",
            input_data=ArchitectureDesignerInput(
                product_name="Approval Hub",
                product_goal="Help teams approve vendor invoices and audit policy decisions.",
                functional_requirements=[
                    "Support approval workflows for invoices",
                    "Track audit history for policy decisions",
                    "Integrate with ERP systems",
                ],
                constraints=["Single region"],
            ),
            expected_components={"Workflow Orchestrator", "Integration Adapter Layer"},
            expected_entities={"Invoice", "Audit Log"},
            expected_endpoints={"GET /api/v1/invoices", "POST /api/v1/invoices", "GET /api/v1/audit-logs"},
            expected_risks={"External integrations", "Compliance-sensitive data"},
        ),
        EvaluationCase(
            name="support-triage-domain",
            input_data=ArchitectureDesignerInput(
                product_name="Support Console",
                product_goal="Help support teams triage tickets and monitor SLA risk.",
                functional_requirements=["Track ticket queues", "Monitor SLA breaches"],
                non_functional_requirements=["Latency under 300ms"],
            ),
            expected_components={"Ticket Domain Service"},
            expected_entities={"Ticket"},
            expected_endpoints={"GET /api/v1/tickets", "POST /api/v1/tickets"},
            expected_risks={"Performance targets"},
            expected_questions={"integrations are mandatory"},
        ),
        EvaluationCase(
            name="job-processing-domain",
            input_data=ArchitectureDesignerInput(
                product_name="Batch Reporter",
                product_goal="Manage async export jobs and scheduled report delivery.",
                functional_requirements=["Queue export jobs", "Generate reports for operators"],
                constraints=["SOC2 controls"],
            ),
            expected_components={"Background Worker / Scheduler"},
            expected_entities={"Job"},
            expected_endpoints={"GET /api/v1/jobs", "POST /api/v1/jobs", "GET /api/v1/metrics/summary"},
            expected_risks={"Operational complexity"},
        ),
    ]
