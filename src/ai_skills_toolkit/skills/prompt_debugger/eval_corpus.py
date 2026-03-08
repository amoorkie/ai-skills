"""Built-in evaluation corpus for prompt_debugger."""

from __future__ import annotations

from ai_skills_toolkit.skills.prompt_debugger.eval_types import EvaluationCase


def build_builtin_eval_cases() -> list[EvaluationCase]:
    """Create the built-in evaluation corpus."""
    return [
        EvaluationCase(
            name="english-deployment-prompt",
            prompt="Build a deployment plan for staging and production.",
            expected_issue_titles={"Prompt is underspecified", "No explicit output format", "Weak guardrails"},
            expected_variant_fragments={"rollout steps", "rollback criteria", "required owners"},
            expected_language="en",
            expected_task_type="deployment",
        ),
        EvaluationCase(
            name="russian-deployment-prompt",
            prompt=(
                "Подготовь план деплоя с проверками и откатом. "
                "Формат ответа: markdown. Не выдумывай детали окружения."
            ),
            forbidden_issue_titles={"No explicit output format", "Weak guardrails"},
            expected_variant_fragments={"Задача:", "Формат ответа:", "откат"},
            expected_language="ru",
            expected_task_type="deployment",
        ),
        EvaluationCase(
            name="design-prompt-specialization",
            prompt="Design a Figma handoff spec for a dashboard with edge cases, states, and user flows.",
            expected_issue_titles={"Prompt is underspecified"},
            expected_variant_fragments={"user flows", "states", "handoff notes"},
            expected_language="en",
            expected_task_type="design",
        ),
        EvaluationCase(
            name="already-good-constrained-prompt",
            prompt=(
                "You must produce a deployment checklist for staging and production. Include output format in markdown, "
                "do not invent environment details, provide rollback steps with clear constraints, and describe validation "
                "gates, owners, and post-release verification steps."
            ),
            expected_issue_titles={"No critical issues detected"},
            forbidden_issue_titles={"No explicit output format", "Weak guardrails"},
            expected_variant_fragments={"rollback criteria", "required owners"},
            expected_language="en",
            expected_task_type="deployment",
        ),
    ]
