"""Command-line interface for ai-skills-toolkit."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Callable

from ai_skills_toolkit.core.io import utc_timestamp
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.design_chain import DesignChainInput, run_design_chain
from ai_skills_toolkit.engineering_chain import EngineeringChainInput, run_engineering_chain
from ai_skills_toolkit.full_suite import FullSuiteInput, run_full_suite
from ai_skills_toolkit.readiness import run_all_evaluations
from ai_skills_toolkit.skills.architecture_designer import ArchitectureDesignerInput
from ai_skills_toolkit.skills.architecture_designer import design_architecture
from ai_skills_toolkit.skills.architecture_designer import enrich_input_from_repo_analysis
from ai_skills_toolkit.skills.architecture_designer import run_builtin_evaluation as run_architecture_designer_eval
from ai_skills_toolkit.skills.architecture_designer import run as run_architecture_designer
from ai_skills_toolkit.skills.code_reviewer import CodeReviewerInput
from ai_skills_toolkit.skills.code_reviewer import run as run_code_reviewer
from ai_skills_toolkit.skills.code_reviewer import run_builtin_evaluation as run_code_reviewer_eval
from ai_skills_toolkit.skills.deploy_helper import DeployHelperInput
from ai_skills_toolkit.skills.deploy_helper import run_builtin_evaluation as run_deploy_helper_eval
from ai_skills_toolkit.skills.deploy_helper import run as run_deploy_helper
from ai_skills_toolkit.skills.doc_writer import DocWriterInput
from ai_skills_toolkit.skills.doc_writer import run_builtin_evaluation as run_doc_writer_eval
from ai_skills_toolkit.skills.doc_writer import run as run_doc_writer
from ai_skills_toolkit.skills.figma_ui_architect import FigmaUiArchitectInput
from ai_skills_toolkit.skills.figma_ui_architect import enrich_input_from_context as enrich_figma_input_from_context
from ai_skills_toolkit.skills.figma_ui_architect import run_builtin_evaluation as run_figma_ui_architect_eval
from ai_skills_toolkit.skills.figma_ui_architect import run as run_figma_ui_architect
from ai_skills_toolkit.skills.prompt_debugger import PromptDebuggerInput
from ai_skills_toolkit.skills.prompt_debugger import run_builtin_evaluation as run_prompt_debugger_eval
from ai_skills_toolkit.skills.prompt_debugger import run as run_prompt_debugger
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput
from ai_skills_toolkit.skills.repo_analyzer import analyze_repository
from ai_skills_toolkit.skills.repo_analyzer import run_builtin_evaluation as run_repo_analyzer_eval
from ai_skills_toolkit.skills.repo_analyzer import run as run_repo_analyzer
from ai_skills_toolkit.skills.test_generator import TestGeneratorInput
from ai_skills_toolkit.skills.test_generator import run as run_test_generator
from ai_skills_toolkit.skills.test_generator import run_builtin_evaluation as run_test_generator_eval


@dataclass(frozen=True)
class CommandSpec:
    output_base: str
    input_factory: Callable[[argparse.Namespace], Any]
    runner: Callable[..., SkillRunResult]


def _default_output_name(base: str) -> str:
    """Generate timestamped output names to reduce accidental collisions."""
    return f"{base}-{utc_timestamp()}"


def _add_shared_output_args(parser: argparse.ArgumentParser) -> None:
    """Attach common output arguments used by every skill command."""
    parser.add_argument("--output-dir", type=Path, default=Path("generated"), help="Output root directory.")
    parser.add_argument("--output-name", type=str, default=None, help="Output file stem (without extension).")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing output file.")


def _repo_analyzer_input(args: argparse.Namespace) -> RepoAnalyzerInput:
    return RepoAnalyzerInput(
        repo_path=args.repo_path,
        include_hidden=args.include_hidden,
        max_files=args.max_files,
        largest_file_count=args.largest_file_count,
    )


def _doc_writer_input(args: argparse.Namespace) -> DocWriterInput:
    return DocWriterInput(
        repo_path=args.repo_path,
        title=args.title,
        audience=args.audience,
        include_setup_checklist=not args.no_setup_checklist,
    )


def _prompt_debugger_input(args: argparse.Namespace) -> PromptDebuggerInput:
    return PromptDebuggerInput(
        prompt=args.prompt,
        goal=args.goal,
        context=args.context,
        target_model=args.target_model,
    )


def _architecture_designer_input(args: argparse.Namespace) -> ArchitectureDesignerInput:
    data = ArchitectureDesignerInput(
        product_name=args.product_name,
        product_goal=args.product_goal,
        primary_users=args.primary_user,
        functional_requirements=args.functional_requirement,
        non_functional_requirements=args.non_functional_requirement,
        constraints=args.constraint,
        assumptions=args.assumption,
        repo_context_signals=args.repo_context_signal,
    )
    if args.repo_context_repo_path:
        analysis = analyze_repository(RepoAnalyzerInput(repo_path=args.repo_context_repo_path))
        data = enrich_input_from_repo_analysis(data, analysis)
    return data


def _figma_ui_architect_input(args: argparse.Namespace) -> FigmaUiArchitectInput:
    data = FigmaUiArchitectInput(
        product_name=args.product_name,
        product_goal=args.product_goal,
        users=args.user,
        jtbds=args.jtbd,
        constraints=args.constraint,
        repo_context_signals=args.repo_context_signal,
        architecture_context=args.architecture_context,
        preferred_platform=args.preferred_platform,
        design_tone=args.design_tone,
    )
    repo_analysis = None
    if args.repo_context_repo_path:
        repo_analysis = analyze_repository(RepoAnalyzerInput(repo_path=args.repo_context_repo_path))
    if args.architecture_context_repo_path:
        spec_input = ArchitectureDesignerInput(
            product_name=args.product_name,
            product_goal=args.product_goal,
            primary_users=args.user,
            functional_requirements=args.jtbd,
            constraints=args.constraint,
        )
        if repo_analysis is not None:
            spec_input = enrich_input_from_repo_analysis(spec_input, repo_analysis)
        architecture_spec = design_architecture(spec_input)
        data = enrich_figma_input_from_context(data, architecture_spec=architecture_spec, repo_analysis=repo_analysis)
    elif repo_analysis is not None:
        data = enrich_figma_input_from_context(data, repo_analysis=repo_analysis)
    return data


def _test_generator_input(args: argparse.Namespace) -> TestGeneratorInput:
    return TestGeneratorInput(
        repo_path=args.repo_path,
        focus_paths=args.focus_path,
        include_edge_cases=not args.no_edge_cases,
        max_targets=args.max_targets,
    )


def _code_reviewer_input(args: argparse.Namespace) -> CodeReviewerInput:
    return CodeReviewerInput(
        repo_path=args.repo_path,
        include_tests=args.include_tests,
        max_findings=args.max_findings,
        include_low_severity=not args.no_low_severity,
        changed_only=args.changed_only,
        base_ref=args.base_ref,
        diff_context_hops=args.diff_context_hops,
    )


def _deploy_helper_input(args: argparse.Namespace) -> DeployHelperInput:
    return DeployHelperInput(
        repo_path=args.repo_path,
        platform=args.platform,
        environment=args.environment,
        app_name=args.app_name,
        required_env_vars=args.env_var,
        prefer_platform=args.prefer_platform,
        service_path=args.service_path,
    )


def _design_chain_input(args: argparse.Namespace) -> DesignChainInput:
    return DesignChainInput(
        repo_path=args.repo_path,
        product_name=args.product_name,
        product_goal=args.product_goal,
        users=args.user,
        jtbds=args.jtbd,
        functional_requirements=args.functional_requirement,
        non_functional_requirements=args.non_functional_requirement,
        constraints=args.constraint,
        assumptions=args.assumption,
        preferred_platform=args.preferred_platform,
        design_tone=args.design_tone,
    )


def _engineering_chain_input(args: argparse.Namespace) -> EngineeringChainInput:
    return EngineeringChainInput(
        repo_path=args.repo_path,
        review_changed_only=args.review_changed_only,
        review_base_ref=args.review_base_ref,
        review_diff_context_hops=args.review_diff_context_hops,
        include_review_tests=args.include_review_tests,
        review_max_findings=args.review_max_findings,
        test_focus_paths=args.test_focus_path,
        test_max_targets=args.test_max_targets,
        doc_title=args.doc_title,
        doc_audience=args.doc_audience,
    )


def _full_suite_input(args: argparse.Namespace) -> FullSuiteInput:
    return FullSuiteInput(
        repo_path=args.repo_path,
        product_name=args.product_name,
        product_goal=args.product_goal,
        users=args.user,
        jtbds=args.jtbd,
        functional_requirements=args.functional_requirement,
        non_functional_requirements=args.non_functional_requirement,
        constraints=args.constraint,
        assumptions=args.assumption,
        preferred_platform=args.preferred_platform,
        design_tone=args.design_tone,
        review_changed_only=args.review_changed_only,
        review_base_ref=args.review_base_ref,
        review_diff_context_hops=args.review_diff_context_hops,
        include_review_tests=args.include_review_tests,
        review_max_findings=args.review_max_findings,
        test_focus_paths=args.test_focus_path,
        test_max_targets=args.test_max_targets,
        doc_title=args.doc_title,
        doc_audience=args.doc_audience,
    )


COMMAND_SPECS: dict[str, CommandSpec] = {
    "repo-analyzer": CommandSpec(
        output_base="repo-analysis",
        input_factory=_repo_analyzer_input,
        runner=run_repo_analyzer,
    ),
    "benchmark-all": CommandSpec(
        output_base="skills-readiness",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_all_evaluations(**kwargs),
    ),
    "repo-analyzer-eval": CommandSpec(
        output_base="repo-analyzer-eval",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_repo_analyzer_eval(**kwargs),
    ),
    "doc-writer": CommandSpec(
        output_base="repository-documentation",
        input_factory=_doc_writer_input,
        runner=run_doc_writer,
    ),
    "doc-writer-eval": CommandSpec(
        output_base="doc-writer-eval",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_doc_writer_eval(**kwargs),
    ),
    "prompt-debugger": CommandSpec(
        output_base="prompt-debugger-report",
        input_factory=_prompt_debugger_input,
        runner=run_prompt_debugger,
    ),
    "prompt-debugger-eval": CommandSpec(
        output_base="prompt-debugger-eval",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_prompt_debugger_eval(**kwargs),
    ),
    "architecture-designer": CommandSpec(
        output_base="architecture-spec",
        input_factory=_architecture_designer_input,
        runner=run_architecture_designer,
    ),
    "architecture-designer-eval": CommandSpec(
        output_base="architecture-designer-eval",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_architecture_designer_eval(**kwargs),
    ),
    "figma-ui-architect": CommandSpec(
        output_base="figma-ui-architecture-spec",
        input_factory=_figma_ui_architect_input,
        runner=run_figma_ui_architect,
    ),
    "figma-ui-architect-eval": CommandSpec(
        output_base="figma-ui-architect-eval",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_figma_ui_architect_eval(**kwargs),
    ),
    "test-generator": CommandSpec(
        output_base="test-generation-plan",
        input_factory=_test_generator_input,
        runner=run_test_generator,
    ),
    "test-generator-eval": CommandSpec(
        output_base="test-generator-eval",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_test_generator_eval(**kwargs),
    ),
    "code-reviewer": CommandSpec(
        output_base="code-review-report",
        input_factory=_code_reviewer_input,
        runner=run_code_reviewer,
    ),
    "code-reviewer-eval": CommandSpec(
        output_base="code-review-eval",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_code_reviewer_eval(**kwargs),
    ),
    "deploy-helper": CommandSpec(
        output_base="deployment-plan",
        input_factory=_deploy_helper_input,
        runner=run_deploy_helper,
    ),
    "deploy-helper-eval": CommandSpec(
        output_base="deploy-helper-eval",
        input_factory=lambda _args: None,
        runner=lambda _data, **kwargs: run_deploy_helper_eval(**kwargs),
    ),
    "design-chain": CommandSpec(
        output_base="design-chain",
        input_factory=_design_chain_input,
        runner=run_design_chain,
    ),
    "engineering-chain": CommandSpec(
        output_base="engineering-chain",
        input_factory=_engineering_chain_input,
        runner=run_engineering_chain,
    ),
    "full-suite": CommandSpec(
        output_base="full-suite",
        input_factory=_full_suite_input,
        runner=run_full_suite,
    ),
}


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser with one subcommand per implemented skill."""
    parser = argparse.ArgumentParser(
        prog="ai-skills-toolkit",
        description="Modular local skill toolkit for AI coding/design agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    repo_parser = subparsers.add_parser("repo-analyzer", help="Inspect a local repository.")
    repo_parser.add_argument("--repo-path", type=Path, default=Path("."), help="Path to local repository.")
    repo_parser.add_argument("--include-hidden", action="store_true", help="Include hidden files.")
    repo_parser.add_argument("--max-files", type=int, default=5000, help="Maximum number of files to scan.")
    repo_parser.add_argument("--largest-file-count", type=int, default=12, help="Number of largest files to list.")
    _add_shared_output_args(repo_parser)

    benchmark_parser = subparsers.add_parser(
        "benchmark-all",
        help="Run all built-in skill evaluations and write a consolidated readiness report.",
    )
    _add_shared_output_args(benchmark_parser)

    repo_eval_parser = subparsers.add_parser(
        "repo-analyzer-eval",
        help="Run the built-in evaluation corpus for repo-analyzer.",
    )
    _add_shared_output_args(repo_eval_parser)

    doc_parser = subparsers.add_parser("doc-writer", help="Generate markdown documentation from repository analysis.")
    doc_parser.add_argument("--repo-path", type=Path, default=Path("."), help="Path to local repository.")
    doc_parser.add_argument("--title", type=str, default="Project Documentation")
    doc_parser.add_argument("--audience", type=str, default="Engineers and AI agents")
    doc_parser.add_argument(
        "--no-setup-checklist",
        action="store_true",
        help="Skip setup checklist section.",
    )
    _add_shared_output_args(doc_parser)

    doc_eval_parser = subparsers.add_parser(
        "doc-writer-eval",
        help="Run the built-in evaluation corpus for doc-writer.",
    )
    _add_shared_output_args(doc_eval_parser)

    prompt_parser = subparsers.add_parser("prompt-debugger", help="Diagnose and improve a prompt.")
    prompt_parser.add_argument("--prompt", type=str, required=True, help="Prompt text to debug.")
    prompt_parser.add_argument("--goal", type=str, default=None, help="Optional goal statement.")
    prompt_parser.add_argument("--context", type=str, default=None, help="Optional context statement.")
    prompt_parser.add_argument("--target-model", type=str, default=None, help="Optional model identifier.")
    _add_shared_output_args(prompt_parser)

    prompt_eval_parser = subparsers.add_parser(
        "prompt-debugger-eval",
        help="Run the built-in evaluation corpus for prompt-debugger.",
    )
    _add_shared_output_args(prompt_eval_parser)

    arch_parser = subparsers.add_parser("architecture-designer", help="Generate a technical architecture spec.")
    arch_parser.add_argument("--product-name", type=str, required=True)
    arch_parser.add_argument("--product-goal", type=str, required=True)
    arch_parser.add_argument("--primary-user", action="append", default=[], help="Add a primary user.")
    arch_parser.add_argument(
        "--functional-requirement",
        action="append",
        default=[],
        help="Add a functional requirement.",
    )
    arch_parser.add_argument(
        "--non-functional-requirement",
        action="append",
        default=[],
        help="Add a non-functional requirement.",
    )
    arch_parser.add_argument("--constraint", action="append", default=[], help="Add a delivery/technical constraint.")
    arch_parser.add_argument("--assumption", action="append", default=[], help="Add an architecture assumption.")
    arch_parser.add_argument(
        "--repo-context-signal",
        action="append",
        default=[],
        help="Add an observed repository/runtime signal to carry into architecture planning.",
    )
    arch_parser.add_argument(
        "--repo-context-repo-path",
        type=Path,
        default=None,
        help="Optional repository path to analyze and inject as upstream context.",
    )
    _add_shared_output_args(arch_parser)

    arch_eval_parser = subparsers.add_parser(
        "architecture-designer-eval",
        help="Run the built-in evaluation corpus for architecture-designer.",
    )
    _add_shared_output_args(arch_eval_parser)

    figma_parser = subparsers.add_parser(
        "figma-ui-architect",
        help="Generate UI architecture spec for Figma-based product design.",
    )
    figma_parser.add_argument("--product-name", type=str, required=True)
    figma_parser.add_argument("--product-goal", type=str, required=True)
    figma_parser.add_argument("--user", action="append", default=[], help="Add a user segment.")
    figma_parser.add_argument("--jtbd", action="append", default=[], help="Add a JTBD statement.")
    figma_parser.add_argument("--constraint", action="append", default=[], help="Add design/technical constraint.")
    figma_parser.add_argument(
        "--repo-context-signal",
        action="append",
        default=[],
        help="Add an observed repository/runtime signal to carry into the UI handoff.",
    )
    figma_parser.add_argument(
        "--architecture-context",
        action="append",
        default=[],
        help="Add an architecture decision or constraint to carry into the UI handoff.",
    )
    figma_parser.add_argument(
        "--repo-context-repo-path",
        type=Path,
        default=None,
        help="Optional repository path to analyze and inject as upstream context.",
    )
    figma_parser.add_argument(
        "--architecture-context-repo-path",
        action="store_true",
        help="Derive architecture context from the current figma-ui-architect input and optional repo context.",
    )
    figma_parser.add_argument("--preferred-platform", type=str, default="Web")
    figma_parser.add_argument("--design-tone", type=str, default="Professional, clear, data-forward")
    _add_shared_output_args(figma_parser)

    figma_eval_parser = subparsers.add_parser(
        "figma-ui-architect-eval",
        help="Run the built-in evaluation corpus for figma-ui-architect.",
    )
    _add_shared_output_args(figma_eval_parser)

    test_gen_parser = subparsers.add_parser(
        "test-generator",
        help="Generate actionable pytest test plan from repository source inspection.",
    )
    test_gen_parser.add_argument("--repo-path", type=Path, default=Path("."), help="Path to local repository.")
    test_gen_parser.add_argument(
        "--focus-path",
        action="append",
        default=[],
        help="Optional relative path to prioritize. Can be repeated.",
    )
    test_gen_parser.add_argument("--max-targets", type=int, default=20, help="Maximum number of test targets.")
    test_gen_parser.add_argument(
        "--no-edge-cases",
        action="store_true",
        help="Disable edge-case suggestions in output.",
    )
    _add_shared_output_args(test_gen_parser)

    test_gen_eval_parser = subparsers.add_parser(
        "test-generator-eval",
        help="Run the built-in evaluation corpus for test-generator.",
    )
    _add_shared_output_args(test_gen_eval_parser)

    code_review_parser = subparsers.add_parser(
        "code-reviewer",
        help="Run heuristic static review and produce prioritized findings.",
    )
    code_review_parser.add_argument("--repo-path", type=Path, default=Path("."), help="Path to local repository.")
    code_review_parser.add_argument("--include-tests", action="store_true", help="Include tests in review scope.")
    code_review_parser.add_argument("--max-findings", type=int, default=80, help="Maximum findings in output report.")
    code_review_parser.add_argument(
        "--no-low-severity",
        action="store_true",
        help="Exclude low-severity findings.",
    )
    code_review_parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Review only changed Python files and nearby sibling modules for local context.",
    )
    code_review_parser.add_argument(
        "--base-ref",
        type=str,
        default=None,
        help="Optional git base ref for diff-aware review (for example `main`).",
    )
    code_review_parser.add_argument(
        "--diff-context-hops",
        type=int,
        default=1,
        help="Import-graph expansion depth for diff-aware review.",
    )
    _add_shared_output_args(code_review_parser)

    code_review_eval_parser = subparsers.add_parser(
        "code-reviewer-eval",
        help="Run the built-in evaluation corpus for code-reviewer.",
    )
    _add_shared_output_args(code_review_eval_parser)

    deploy_parser = subparsers.add_parser(
        "deploy-helper",
        help="Generate deployment checklist and commands for target platform.",
    )
    deploy_parser.add_argument("--repo-path", type=Path, default=Path("."), help="Path to local repository.")
    deploy_parser.add_argument(
        "--platform",
        type=str,
        default="auto",
        choices=["auto", "generic", "docker", "render", "vercel", "cloudflare"],
        help="Deployment platform selection.",
    )
    deploy_parser.add_argument("--environment", type=str, default="production", help="Target deployment environment.")
    deploy_parser.add_argument("--app-name", type=str, default="app", help="Application name.")
    deploy_parser.add_argument(
        "--prefer-platform",
        type=str,
        default=None,
        choices=["generic", "docker", "render", "vercel", "cloudflare"],
        help="Preferred platform when auto-detection finds multiple candidates.",
    )
    deploy_parser.add_argument(
        "--service-path",
        type=str,
        default=None,
        help="Optional repository subpath to scope deployment detection.",
    )
    deploy_parser.add_argument(
        "--env-var",
        action="append",
        default=[],
        help="Required environment variable name. Can be repeated.",
    )
    _add_shared_output_args(deploy_parser)

    deploy_eval_parser = subparsers.add_parser(
        "deploy-helper-eval",
        help="Run the built-in evaluation corpus for deploy-helper.",
    )
    _add_shared_output_args(deploy_eval_parser)

    design_chain_parser = subparsers.add_parser(
        "design-chain",
        help="Run repo analysis, architecture design, and Figma UI planning as one linked workflow.",
    )
    design_chain_parser.add_argument("--repo-path", type=Path, default=Path("."), help="Path to local repository.")
    design_chain_parser.add_argument("--product-name", type=str, required=True)
    design_chain_parser.add_argument("--product-goal", type=str, required=True)
    design_chain_parser.add_argument("--user", action="append", default=[], help="Add a user segment.")
    design_chain_parser.add_argument("--jtbd", action="append", default=[], help="Add a JTBD statement.")
    design_chain_parser.add_argument(
        "--functional-requirement",
        action="append",
        default=[],
        help="Add a functional requirement.",
    )
    design_chain_parser.add_argument(
        "--non-functional-requirement",
        action="append",
        default=[],
        help="Add a non-functional requirement.",
    )
    design_chain_parser.add_argument("--constraint", action="append", default=[], help="Add design/technical constraint.")
    design_chain_parser.add_argument("--assumption", action="append", default=[], help="Add an assumption.")
    design_chain_parser.add_argument("--preferred-platform", type=str, default="Web")
    design_chain_parser.add_argument("--design-tone", type=str, default="Professional, clear, data-forward")
    _add_shared_output_args(design_chain_parser)

    engineering_chain_parser = subparsers.add_parser(
        "engineering-chain",
        help="Run repo analysis, code review, test generation, and documentation as one linked workflow.",
    )
    engineering_chain_parser.add_argument("--repo-path", type=Path, default=Path("."), help="Path to local repository.")
    engineering_chain_parser.add_argument("--review-changed-only", action="store_true", help="Run code review in changed-only mode.")
    engineering_chain_parser.add_argument("--review-base-ref", type=str, default=None, help="Optional git base ref for diff-aware review.")
    engineering_chain_parser.add_argument("--review-diff-context-hops", type=int, default=1)
    engineering_chain_parser.add_argument("--include-review-tests", action="store_true", help="Include tests in review scope.")
    engineering_chain_parser.add_argument("--review-max-findings", type=int, default=80)
    engineering_chain_parser.add_argument("--test-focus-path", action="append", default=[], help="Optional relative path to prioritize in test planning.")
    engineering_chain_parser.add_argument("--test-max-targets", type=int, default=20)
    engineering_chain_parser.add_argument("--doc-title", type=str, default="Engineering Workflow Documentation")
    engineering_chain_parser.add_argument("--doc-audience", type=str, default="Engineers and AI agents")
    _add_shared_output_args(engineering_chain_parser)

    full_suite_parser = subparsers.add_parser(
        "full-suite",
        help="Run readiness plus the design and engineering workflow chains as one release pack.",
    )
    full_suite_parser.add_argument("--repo-path", type=Path, default=Path("."), help="Path to local repository.")
    full_suite_parser.add_argument("--product-name", type=str, required=True)
    full_suite_parser.add_argument("--product-goal", type=str, required=True)
    full_suite_parser.add_argument("--user", action="append", default=[], help="Add a user segment.")
    full_suite_parser.add_argument("--jtbd", action="append", default=[], help="Add a JTBD statement.")
    full_suite_parser.add_argument(
        "--functional-requirement",
        action="append",
        default=[],
        help="Add a functional requirement.",
    )
    full_suite_parser.add_argument(
        "--non-functional-requirement",
        action="append",
        default=[],
        help="Add a non-functional requirement.",
    )
    full_suite_parser.add_argument("--constraint", action="append", default=[], help="Add design/technical constraint.")
    full_suite_parser.add_argument("--assumption", action="append", default=[], help="Add an assumption.")
    full_suite_parser.add_argument("--preferred-platform", type=str, default="Web")
    full_suite_parser.add_argument("--design-tone", type=str, default="Professional, clear, data-forward")
    full_suite_parser.add_argument("--review-changed-only", action="store_true", help="Run code review in changed-only mode.")
    full_suite_parser.add_argument("--review-base-ref", type=str, default=None, help="Optional git base ref for diff-aware review.")
    full_suite_parser.add_argument("--review-diff-context-hops", type=int, default=1)
    full_suite_parser.add_argument("--include-review-tests", action="store_true", help="Include tests in review scope.")
    full_suite_parser.add_argument("--review-max-findings", type=int, default=80)
    full_suite_parser.add_argument("--test-focus-path", action="append", default=[], help="Optional relative path to prioritize in test planning.")
    full_suite_parser.add_argument("--test-max-targets", type=int, default=20)
    full_suite_parser.add_argument("--doc-title", type=str, default="Engineering Workflow Documentation")
    full_suite_parser.add_argument("--doc-audience", type=str, default="Engineers and AI agents")
    _add_shared_output_args(full_suite_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run CLI entrypoint and return process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        spec = COMMAND_SPECS.get(args.command)
        if spec is None:  # pragma: no cover
            raise ValueError(f"Unhandled command: {args.command}")
        output_name = args.output_name or _default_output_name(spec.output_base)
        result = spec.runner(
            spec.input_factory(args),
            output_dir=args.output_dir,
            output_name=output_name,
            overwrite=args.overwrite,
        )
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1

    print(result.summary)
    print(f"Output: {result.output_path}")
    return 0
