from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from ai_skills_toolkit.cli import COMMAND_SPECS, CommandSpec, main


def test_cli_repo_analyzer_smoke(sample_repo: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "repo_analyzer" / "repo-smoke.md"
    rc = main(
        [
            "repo-analyzer",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "repo-smoke",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Repository Analysis" in text
    assert "## Key Files" in text


def test_cli_repo_analyzer_eval_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "repo_analyzer_eval" / "eval.md"
    rc = main(
        [
            "repo-analyzer-eval",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Repo Analyzer Evaluation" in text
    assert "Overall signal recall" in text


def test_cli_benchmark_all_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "readiness" / "eval.md"
    rc = main(
        [
            "benchmark-all",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Skills Readiness Report" in text
    assert "## Skill Evaluations" in text


def test_cli_prompt_debugger_smoke(tmp_path: Path) -> None:
    rc = main(
        [
            "prompt-debugger",
            "--prompt",
            "Design an API for incident tracking.",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "prompt-smoke",
        ]
    )
    assert rc == 0


def test_cli_prompt_debugger_eval_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "prompt_debugger_eval" / "eval.md"
    rc = main(
        [
            "prompt-debugger-eval",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Prompt Debugger Evaluation" in text
    assert "Overall language accuracy" in text


def test_cli_architecture_designer_eval_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "architecture_designer_eval" / "eval.md"
    rc = main(
        [
            "architecture-designer-eval",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Architecture Designer Evaluation" in text
    assert "Overall recall" in text


def test_cli_architecture_designer_supports_repo_context(sample_repo: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "architecture_designer" / "arch-context.md"
    rc = main(
        [
            "architecture-designer",
            "--product-name",
            "Ops Portal",
            "--product-goal",
            "Provide operational visibility for platform teams.",
            "--repo-context-repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "arch-context",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "Repository context carried into architecture planning" in text


def test_cli_figma_ui_architect_eval_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "figma_ui_architect_eval" / "eval.md"
    rc = main(
        [
            "figma-ui-architect-eval",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Figma UI Architect Evaluation" in text
    assert "Overall recall" in text


def test_cli_figma_ui_architect_supports_upstream_context(sample_repo: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "figma_ui_architect" / "figma-context.md"
    rc = main(
        [
            "figma-ui-architect",
            "--product-name",
            "Ops Console",
            "--product-goal",
            "Help operators review workflows and integrations safely.",
            "--repo-context-repo-path",
            str(sample_repo),
            "--architecture-context-repo-path",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "figma-context",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "## Upstream Architecture Context" in text


def test_cli_doc_writer_eval_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "doc_writer_eval" / "eval.md"
    rc = main(
        [
            "doc-writer-eval",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )

    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Doc Writer Evaluation" in text
    assert "Overall fragment recall" in text


def test_cli_repo_analyzer_overwrite_error(sample_repo: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"
    first = main(
        [
            "repo-analyzer",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(output_dir),
            "--output-name",
            "same-name",
        ]
    )
    second = main(
        [
            "repo-analyzer",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(output_dir),
            "--output-name",
            "same-name",
        ]
    )
    assert first == 0
    assert second == 2


def test_cli_validation_error_returns_non_zero(tmp_path: Path) -> None:
    rc = main(
        [
            "prompt-debugger",
            "--prompt",
            "short",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "invalid-prompt",
        ]
    )
    assert rc == 1


def test_cli_unexpected_errors_propagate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _boom(_data, **_kwargs):
        raise RuntimeError("unexpected boom")

    original = COMMAND_SPECS["repo-analyzer"]
    monkeypatch.setitem(
        COMMAND_SPECS,
        "repo-analyzer",
        CommandSpec(output_base=original.output_base, input_factory=original.input_factory, runner=_boom),
    )

    with pytest.raises(RuntimeError, match="unexpected boom"):
        main(
            [
                "repo-analyzer",
                "--output-dir",
                str(tmp_path / "generated"),
                "--output-name",
                "boom",
            ]
        )


def test_cli_test_generator_smoke(sample_repo: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "test_generator" / "test-plan.md"
    rc = main(
        [
            "test-generator",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "test-plan",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "## Target Matrix" in text


def test_cli_code_reviewer_smoke(sample_repo: Path, tmp_path: Path) -> None:
    rc = main(
        [
            "code-reviewer",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "review",
        ]
    )
    assert rc == 0


def test_cli_code_reviewer_changed_only_smoke(tmp_path: Path) -> None:
    repo = tmp_path / "git_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True, text=True)
    (repo / "src").mkdir()
    (repo / "src" / "tracked.py").write_text("def stable():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, capture_output=True, text=True)
    (repo / "src" / "tracked.py").write_text("def stable():\n    # TODO: changed path\n    return 1\n", encoding="utf-8")

    output_path = tmp_path / "generated" / "code_reviewer" / "review-diff.md"
    rc = main(
        [
            "code-reviewer",
            "--repo-path",
            str(repo),
            "--changed-only",
            "--diff-context-hops",
            "1",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "review-diff",
        ]
    )

    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "- **Review mode:** `ast+token+semantic+diff+graph`" in text


def test_cli_code_reviewer_eval_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "code_reviewer_eval" / "eval.md"
    rc = main(
        [
            "code-reviewer-eval",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )

    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Code Reviewer Evaluation" in text
    assert "Overall rule recall" in text


def test_cli_test_generator_eval_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "test_generator_eval" / "eval.md"
    rc = main(
        [
            "test-generator-eval",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )

    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Test Generator Evaluation" in text
    assert "Overall target recall" in text


def test_cli_deploy_helper_smoke(sample_repo: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "deploy_helper" / "deploy.md"
    rc = main(
        [
            "deploy-helper",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "deploy",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Deployment Helper Plan" in text
    assert "## Suggested Commands" in text


def test_cli_deploy_helper_eval_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "deploy_helper_eval" / "eval.md"
    rc = main(
        [
            "deploy-helper-eval",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "eval",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Deploy Helper Evaluation" in text
    assert "Overall platform accuracy" in text


def test_cli_deploy_helper_supports_prefer_platform_and_service_path(sample_repo: Path, tmp_path: Path) -> None:
    api_dir = sample_repo / "services" / "api"
    web_dir = sample_repo / "services" / "web"
    api_dir.mkdir(parents=True)
    web_dir.mkdir(parents=True)
    (api_dir / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (web_dir / "vercel.json").write_text('{"version": 2}\n', encoding="utf-8")

    output_path = tmp_path / "generated" / "deploy_helper" / "deploy-scoped.md"
    rc = main(
        [
            "deploy-helper",
            "--repo-path",
            str(sample_repo),
            "--service-path",
            "services/web",
            "--prefer-platform",
            "vercel",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "deploy-scoped",
        ]
    )

    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "- **Platform:** `vercel`" in text
    assert "`services/web/vercel.json`" in text


def test_cli_design_chain_smoke(sample_repo: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "design_chain" / "design-pack.md"
    rc = main(
        [
            "design-chain",
            "--repo-path",
            str(sample_repo),
            "--product-name",
            "Ops Console",
            "--product-goal",
            "Help operators review workflows and integrations safely.",
            "--jtbd",
            "When reviewing queue health, I want actionable status so I can resolve issues quickly.",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "design-pack",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Design Chain Report" in text


def test_cli_engineering_chain_smoke(sample_repo: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "engineering_chain" / "engineering-pack.md"
    rc = main(
        [
            "engineering-chain",
            "--repo-path",
            str(sample_repo),
            "--test-focus-path",
            "src/main.py",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "engineering-pack",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Engineering Chain Report" in text


def test_cli_full_suite_smoke(sample_repo: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "full_suite" / "release-pack.md"
    rc = main(
        [
            "full-suite",
            "--repo-path",
            str(sample_repo),
            "--product-name",
            "Ops Console",
            "--product-goal",
            "Help operators review workflows and integrations safely.",
            "--jtbd",
            "When reviewing queue health, I want actionable status so I can resolve issues quickly.",
            "--test-focus-path",
            "src/main.py",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "release-pack",
        ]
    )
    assert rc == 0
    text = output_path.read_text(encoding="utf-8")
    assert "# Full Workflow Suite Report" in text
