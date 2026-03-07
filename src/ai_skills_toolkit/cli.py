"""Command-line interface for ai-skills-toolkit."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from ai_skills_toolkit.core.io import utc_timestamp
from ai_skills_toolkit.skills.architecture_designer import ArchitectureDesignerInput
from ai_skills_toolkit.skills.architecture_designer import run as run_architecture_designer
from ai_skills_toolkit.skills.code_reviewer import CodeReviewerInput
from ai_skills_toolkit.skills.code_reviewer import run as run_code_reviewer
from ai_skills_toolkit.skills.deploy_helper import DeployHelperInput
from ai_skills_toolkit.skills.deploy_helper import run as run_deploy_helper
from ai_skills_toolkit.skills.doc_writer import DocWriterInput
from ai_skills_toolkit.skills.doc_writer import run as run_doc_writer
from ai_skills_toolkit.skills.figma_ui_architect import FigmaUiArchitectInput
from ai_skills_toolkit.skills.figma_ui_architect import run as run_figma_ui_architect
from ai_skills_toolkit.skills.prompt_debugger import PromptDebuggerInput
from ai_skills_toolkit.skills.prompt_debugger import run as run_prompt_debugger
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput
from ai_skills_toolkit.skills.repo_analyzer import run as run_repo_analyzer
from ai_skills_toolkit.skills.test_generator import TestGeneratorInput
from ai_skills_toolkit.skills.test_generator import run as run_test_generator


def _default_output_name(base: str) -> str:
    """Generate timestamped output names to reduce accidental collisions."""
    return f"{base}-{utc_timestamp()}"


def _add_shared_output_args(parser: argparse.ArgumentParser) -> None:
    """Attach common output arguments used by every skill command."""
    parser.add_argument("--output-dir", type=Path, default=Path("generated"), help="Output root directory.")
    parser.add_argument("--output-name", type=str, default=None, help="Output file stem (without extension).")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing output file.")


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

    prompt_parser = subparsers.add_parser("prompt-debugger", help="Diagnose and improve a prompt.")
    prompt_parser.add_argument("--prompt", type=str, required=True, help="Prompt text to debug.")
    prompt_parser.add_argument("--goal", type=str, default=None, help="Optional goal statement.")
    prompt_parser.add_argument("--context", type=str, default=None, help="Optional context statement.")
    prompt_parser.add_argument("--target-model", type=str, default=None, help="Optional model identifier.")
    _add_shared_output_args(prompt_parser)

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
    _add_shared_output_args(arch_parser)

    figma_parser = subparsers.add_parser(
        "figma-ui-architect",
        help="Generate UI architecture spec for Figma-based product design.",
    )
    figma_parser.add_argument("--product-name", type=str, required=True)
    figma_parser.add_argument("--product-goal", type=str, required=True)
    figma_parser.add_argument("--user", action="append", default=[], help="Add a user segment.")
    figma_parser.add_argument("--jtbd", action="append", default=[], help="Add a JTBD statement.")
    figma_parser.add_argument("--constraint", action="append", default=[], help="Add design/technical constraint.")
    figma_parser.add_argument("--preferred-platform", type=str, default="Web")
    figma_parser.add_argument("--design-tone", type=str, default="Professional, clear, data-forward")
    _add_shared_output_args(figma_parser)

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
    _add_shared_output_args(code_review_parser)

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
        "--env-var",
        action="append",
        default=[],
        help="Required environment variable name. Can be repeated.",
    )
    _add_shared_output_args(deploy_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run CLI entrypoint and return process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "repo-analyzer":
            output_name = args.output_name or _default_output_name("repo-analysis")
            result = run_repo_analyzer(
                RepoAnalyzerInput(
                    repo_path=args.repo_path,
                    include_hidden=args.include_hidden,
                    max_files=args.max_files,
                    largest_file_count=args.largest_file_count,
                ),
                output_dir=args.output_dir,
                output_name=output_name,
                overwrite=args.overwrite,
            )
        elif args.command == "doc-writer":
            output_name = args.output_name or _default_output_name("repository-documentation")
            result = run_doc_writer(
                DocWriterInput(
                    repo_path=args.repo_path,
                    title=args.title,
                    audience=args.audience,
                    include_setup_checklist=not args.no_setup_checklist,
                ),
                output_dir=args.output_dir,
                output_name=output_name,
                overwrite=args.overwrite,
            )
        elif args.command == "prompt-debugger":
            output_name = args.output_name or _default_output_name("prompt-debugger-report")
            result = run_prompt_debugger(
                PromptDebuggerInput(
                    prompt=args.prompt,
                    goal=args.goal,
                    context=args.context,
                    target_model=args.target_model,
                ),
                output_dir=args.output_dir,
                output_name=output_name,
                overwrite=args.overwrite,
            )
        elif args.command == "architecture-designer":
            output_name = args.output_name or _default_output_name("architecture-spec")
            result = run_architecture_designer(
                ArchitectureDesignerInput(
                    product_name=args.product_name,
                    product_goal=args.product_goal,
                    primary_users=args.primary_user,
                    functional_requirements=args.functional_requirement,
                    non_functional_requirements=args.non_functional_requirement,
                    constraints=args.constraint,
                    assumptions=args.assumption,
                ),
                output_dir=args.output_dir,
                output_name=output_name,
                overwrite=args.overwrite,
            )
        elif args.command == "figma-ui-architect":
            output_name = args.output_name or _default_output_name("figma-ui-architecture-spec")
            result = run_figma_ui_architect(
                FigmaUiArchitectInput(
                    product_name=args.product_name,
                    product_goal=args.product_goal,
                    users=args.user,
                    jtbds=args.jtbd,
                    constraints=args.constraint,
                    preferred_platform=args.preferred_platform,
                    design_tone=args.design_tone,
                ),
                output_dir=args.output_dir,
                output_name=output_name,
                overwrite=args.overwrite,
            )
        elif args.command == "test-generator":
            output_name = args.output_name or _default_output_name("test-generation-plan")
            result = run_test_generator(
                TestGeneratorInput(
                    repo_path=args.repo_path,
                    focus_paths=args.focus_path,
                    include_edge_cases=not args.no_edge_cases,
                    max_targets=args.max_targets,
                ),
                output_dir=args.output_dir,
                output_name=output_name,
                overwrite=args.overwrite,
            )
        elif args.command == "code-reviewer":
            output_name = args.output_name or _default_output_name("code-review-report")
            result = run_code_reviewer(
                CodeReviewerInput(
                    repo_path=args.repo_path,
                    include_tests=args.include_tests,
                    max_findings=args.max_findings,
                    include_low_severity=not args.no_low_severity,
                ),
                output_dir=args.output_dir,
                output_name=output_name,
                overwrite=args.overwrite,
            )
        elif args.command == "deploy-helper":
            output_name = args.output_name or _default_output_name("deployment-plan")
            result = run_deploy_helper(
                DeployHelperInput(
                    repo_path=args.repo_path,
                    platform=args.platform,
                    environment=args.environment,
                    app_name=args.app_name,
                    required_env_vars=args.env_var,
                ),
                output_dir=args.output_dir,
                output_name=output_name,
                overwrite=args.overwrite,
            )
        else:  # pragma: no cover
            raise ValueError(f"Unhandled command: {args.command}")
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1

    print(result.summary)
    print(f"Output: {result.output_path}")
    return 0
