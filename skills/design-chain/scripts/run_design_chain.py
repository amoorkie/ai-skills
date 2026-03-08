from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


DEFAULT_TOOLKIT_PATH = Path("A:\\Codex тесты")


def _looks_like_toolkit(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "pyproject.toml").exists()
        and (path / "src" / "ai_skills_toolkit" / "cli.py").exists()
    )


def _resolve_toolkit_path(explicit_path: str | None) -> Path:
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env_path = os.environ.get("AI_SKILLS_TOOLKIT_PATH")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path.cwd())
    candidates.append(DEFAULT_TOOLKIT_PATH)

    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if _looks_like_toolkit(resolved):
            return resolved
    raise SystemExit("Could not locate ai-skills-toolkit. Pass --toolkit-path or set AI_SKILLS_TOOLKIT_PATH.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ai-skills-toolkit design-chain.")
    parser.add_argument("--target-repo", required=True, help="Repository to analyze.")
    parser.add_argument("--toolkit-path", default=None, help="Path to ai-skills-toolkit repository.")
    parser.add_argument("--product-name", required=True, help="Product name.")
    parser.add_argument("--product-goal", required=True, help="Product goal.")
    parser.add_argument("--jtbd", action="append", default=[], help="JTBD statement. Can be repeated.")
    parser.add_argument("--user", action="append", default=[], help="User segment. Can be repeated.")
    parser.add_argument("--constraint", action="append", default=[], help="Constraint. Can be repeated.")
    parser.add_argument("--output-name", default="skill-design-chain", help="Output file stem.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    toolkit_path = _resolve_toolkit_path(args.toolkit_path)
    target_repo = Path(args.target_repo).expanduser().resolve()
    output_dir = toolkit_path / "generated"

    env = os.environ.copy()
    src_path = str(toolkit_path / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else src_path + os.pathsep + env["PYTHONPATH"]

    command = [
        sys.executable,
        "-m",
        "ai_skills_toolkit",
        "design-chain",
        "--repo-path",
        str(target_repo),
        "--product-name",
        args.product_name,
        "--product-goal",
        args.product_goal,
        "--output-dir",
        str(output_dir),
        "--output-name",
        args.output_name,
        "--overwrite",
    ]
    for item in args.jtbd:
        command.extend(["--jtbd", item])
    for item in args.user:
        command.extend(["--user", item])
    for item in args.constraint:
        command.extend(["--constraint", item])

    completed = subprocess.run(command, cwd=str(toolkit_path), env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
