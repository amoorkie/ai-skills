"""Implementation for repo_analyzer."""

from __future__ import annotations

from collections import Counter
import os
from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.skills.repo_analyzer.schema import FileStat, RepoAnalysis, RepoAnalyzerInput

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    "dist",
    "build",
}

LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".swift": "Swift",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".md": "Markdown",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".sh": "Shell",
    ".ps1": "PowerShell",
}

KEY_FILE_CANDIDATES = {
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
}


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def _iter_repo_files(repo_path: Path, include_hidden: bool) -> tuple[list[Path], int]:
    file_paths: list[Path] = []
    total_dirs = 0
    for root, dirs, files in os.walk(repo_path):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and (include_hidden or not d.startswith("."))]
        total_dirs += len(dirs)

        for filename in files:
            if filename in {".DS_Store"}:
                continue
            file_path = root_path / filename
            if not include_hidden and _is_hidden(file_path.relative_to(repo_path)):
                continue
            file_paths.append(file_path)

    return file_paths, total_dirs


def _extension_to_language(path: Path) -> str:
    if path.suffix:
        return LANGUAGE_MAP.get(path.suffix.lower(), "Other")
    return "Other"


def analyze_repository(data: RepoAnalyzerInput) -> RepoAnalysis:
    """Scan a local repository and return a structured metadata summary."""
    repo_path = data.repo_path.resolve()
    files, total_dirs = _iter_repo_files(repo_path, data.include_hidden)
    notes: list[str] = []

    if len(files) > data.max_files:
        notes.append(
            f"File scan limited to {data.max_files} files out of {len(files)} discovered. "
            "Increase max_files for full coverage."
        )
        files = files[: data.max_files]

    language_counter: Counter[str] = Counter()
    largest_files: list[FileStat] = []
    total_size_bytes = 0
    key_files: list[str] = []

    for file_path in files:
        rel_path = file_path.relative_to(repo_path).as_posix()
        language_counter[_extension_to_language(file_path)] += 1

        try:
            size = file_path.stat().st_size
        except OSError:
            size = 0
            notes.append(f"Could not read size for {rel_path}.")

        total_size_bytes += size

        if file_path.name in KEY_FILE_CANDIDATES:
            key_files.append(rel_path)

        largest_files.append(
            FileStat(
                path=rel_path,
                extension=(file_path.suffix.lower() or "none"),
                size_bytes=size,
            )
        )

    largest_files = sorted(largest_files, key=lambda item: item.size_bytes, reverse=True)[: data.largest_file_count]

    has_git_dir = (repo_path / ".git").exists()
    if not has_git_dir:
        notes.append("No .git directory found. Analysis still completed for local folder content.")

    return RepoAnalysis(
        repo_path=str(repo_path),
        has_git_dir=has_git_dir,
        total_files=len(files),
        total_dirs=total_dirs,
        total_size_bytes=total_size_bytes,
        language_breakdown=dict(sorted(language_counter.items(), key=lambda item: item[1], reverse=True)),
        key_files=sorted(set(key_files)),
        largest_files=largest_files,
        notes=notes,
    )


def render_markdown(analysis: RepoAnalysis) -> str:
    """Render repository analysis into a markdown report."""
    lines: list[str] = []
    lines.append("# Repository Analysis")
    lines.append("")
    lines.append(f"- **Repository path:** `{analysis.repo_path}`")
    lines.append(f"- **Has .git directory:** `{analysis.has_git_dir}`")
    lines.append(f"- **Total files analyzed:** `{analysis.total_files}`")
    lines.append(f"- **Total directories discovered:** `{analysis.total_dirs}`")
    lines.append(f"- **Total size analyzed:** `{analysis.total_size_bytes}` bytes")
    lines.append("")

    lines.append("## Language Breakdown")
    lines.append("")
    if analysis.language_breakdown:
        for language, count in analysis.language_breakdown.items():
            lines.append(f"- {language}: {count}")
    else:
        lines.append("- No files detected.")
    lines.append("")

    lines.append("## Key Files")
    lines.append("")
    if analysis.key_files:
        for key_file in analysis.key_files:
            lines.append(f"- `{key_file}`")
    else:
        lines.append("- No common key files detected.")
    lines.append("")

    lines.append("## Largest Files")
    lines.append("")
    if analysis.largest_files:
        lines.append("| Path | Extension | Size (bytes) |")
        lines.append("| --- | --- | ---: |")
        for file_stat in analysis.largest_files:
            lines.append(f"| `{file_stat.path}` | `{file_stat.extension}` | {file_stat.size_bytes} |")
    else:
        lines.append("- No files available.")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    if analysis.notes:
        for note in analysis.notes:
            lines.append(f"- {note}")
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def run(
    data: RepoAnalyzerInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "repo-analysis",
    overwrite: bool = False,
) -> SkillRunResult:
    """Execute repo_analyzer end-to-end and persist markdown output."""
    analysis = analyze_repository(data)
    markdown = render_markdown(analysis)
    output_path = build_output_path(output_dir, "repo_analyzer", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="repo_analyzer",
        output_path=output_path,
        summary=f"Repository analyzed: {analysis.total_files} files scanned.",
        metadata={
            "repo_path": analysis.repo_path,
            "file_count": analysis.total_files,
            "language_count": len(analysis.language_breakdown),
        },
    )
