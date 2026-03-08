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
    parser = argparse.ArgumentParser(description="Run ai-skills-toolkit repo-analyzer.")
    parser.add_argument("--target-repo", required=True, help="Repository to analyze.")
    parser.add_argument("--toolkit-path", default=None, help="Path to ai-skills-toolkit repository.")
    parser.add_argument("--output-name", default="skill-repo-analysis", help="Output file stem.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files in the scan.")
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
        "repo-analyzer",
        "--repo-path",
        str(target_repo),
        "--output-dir",
        str(output_dir),
        "--output-name",
        args.output_name,
        "--overwrite",
    ]
    if args.include_hidden:
        command.append("--include-hidden")

    completed = subprocess.run(command, cwd=str(toolkit_path), env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
