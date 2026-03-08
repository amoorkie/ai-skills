"""Implementation for repo_analyzer."""

from __future__ import annotations

from collections import Counter
import ast
import json
from pathlib import Path
import tomllib

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.core.repo_scan import DEFAULT_EXCLUDED_DIRS, iter_repo_files
from ai_skills_toolkit.skills.repo_analyzer.schema import FileStat, RepoAnalysis, RepoAnalyzerInput

EXCLUDED_DIRS = DEFAULT_EXCLUDED_DIRS

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
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
}

ENTRYPOINT_CANDIDATES = {
    "cli.py",
    "__main__.py",
    "main.py",
    "app.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
}


def _iter_repo_files(repo_path: Path, include_hidden: bool) -> tuple[list[Path], int]:
    return iter_repo_files(repo_path, include_hidden=include_hidden, excluded_dirs=EXCLUDED_DIRS)


def _extension_to_language(path: Path) -> str:
    if path.suffix:
        return LANGUAGE_MAP.get(path.suffix.lower(), "Other")
    return "Other"


def _detect_entrypoints(repo_path: Path, files: list[Path]) -> list[str]:
    return sorted(
        file_path.relative_to(repo_path).as_posix()
        for file_path in files
        if file_path.name in ENTRYPOINT_CANDIDATES
    )[:10]


def _load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _has_github_workflows(repo_path: Path) -> bool:
    workflows_dir = repo_path / ".github" / "workflows"
    if not workflows_dir.exists() or not workflows_dir.is_dir():
        return False
    return any(item.is_file() for item in workflows_dir.rglob("*"))


def _detect_tooling_signals(repo_path: Path, files: list[Path]) -> list[str]:
    names = {file_path.name for file_path in files}
    paths = {file_path.as_posix() for file_path in files}
    signals: list[str] = []
    if "pyproject.toml" in names:
        signals.append("Python packaging manifest (`pyproject.toml`)")
    if "requirements.txt" in names:
        signals.append("pip requirements manifest (`requirements.txt`)")
    if "package.json" in names:
        signals.append("Node package manifest (`package.json`)")
    if "pnpm-lock.yaml" in names:
        signals.append("pnpm workspace/lockfile (`pnpm-lock.yaml`)")
    if "package-lock.json" in names:
        signals.append("npm lockfile (`package-lock.json`)")
    if "yarn.lock" in names:
        signals.append("Yarn lockfile (`yarn.lock`)")
    if "Dockerfile" in names:
        signals.append("Docker container build (`Dockerfile`)")
    if "render.yaml" in names or "render.yml" in names:
        signals.append("Render deployment blueprint (`render.yaml`)")
    if "vercel.json" in names:
        signals.append("Vercel deployment config (`vercel.json`)")
    if "wrangler.toml" in names:
        signals.append("Cloudflare Workers config (`wrangler.toml`)")
    if _has_github_workflows(repo_path) or any(".github/workflows/" in path for path in paths):
        signals.append("GitHub Actions CI/CD (`.github/workflows`)")
    if any("/tests/" in path or path.startswith("tests/") for path in paths):
        signals.append("Dedicated test suite directory (`tests/`)")
    return signals


def _detect_project_kind(files: list[Path], entrypoints: list[str], language_breakdown: Counter[str]) -> str:
    names = {file_path.name for file_path in files}
    top_level_dirs = {file_path.parts[0] for file_path in files if len(file_path.parts) > 1}
    has_python = "Python" in language_breakdown
    has_typescript = "TypeScript" in language_breakdown
    has_javascript = "JavaScript" in language_breakdown
    has_frontend_assets = any(file_path.suffix.lower() in {".html", ".css", ".scss", ".tsx", ".jsx"} for file_path in files)
    has_cli_entrypoint = any(path.endswith(("cli.py", "__main__.py", "main.py")) for path in entrypoints)
    python_manifest_count = sum(1 for file_path in files if file_path.name == "pyproject.toml")
    node_manifest_count = sum(1 for file_path in files if file_path.name == "package.json")
    likely_monorepo = (
        python_manifest_count > 1
        or node_manifest_count > 1
        or bool({"apps", "services", "packages"} & top_level_dirs)
    )

    if likely_monorepo and (has_python or has_javascript or has_typescript):
        return "monorepo"

    if has_python and has_cli_entrypoint:
        return "python_cli"
    if has_python and any(name in names for name in {"wsgi.py", "asgi.py", "app.py", "manage.py"}):
        return "python_service"
    if (has_javascript or has_typescript) and has_frontend_assets and "package.json" in names:
        return "frontend_app"
    if has_python and "pyproject.toml" in names:
        return "python_package"
    if has_python and has_javascript:
        return "multi_language_toolkit"
    return "generic_repository"


def _parse_python_tree(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return None


def _dependency_surface(repo_path: Path, files: list[Path]) -> list[str]:
    python_files = [file_path for file_path in files if file_path.suffix == ".py"]
    if not python_files:
        return []

    internal_imports: Counter[str] = Counter()
    external_imports: Counter[str] = Counter()
    local_module_names = {file_path.stem for file_path in python_files}

    for file_path in python_files[:200]:
        tree = _parse_python_tree(file_path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", maxsplit=1)[0]
                    if root in local_module_names:
                        internal_imports[root] += 1
                    else:
                        external_imports[root] += 1
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".", maxsplit=1)[0]
                if root in local_module_names or node.level > 0:
                    internal_imports[root] += 1
                else:
                    external_imports[root] += 1

    summary: list[str] = []
    if internal_imports:
        top_internal = ", ".join(name for name, _count in internal_imports.most_common(5))
        summary.append(f"Most referenced internal Python modules: {top_internal}.")
    if external_imports:
        top_external = ", ".join(name for name, _count in external_imports.most_common(5))
        summary.append(f"Most referenced external Python modules: {top_external}.")
    if not summary:
        summary.append("No import graph hints were derived from Python source.")
    return summary


def _runtime_surface(
    project_kind: str,
    entrypoints: list[str],
    manifest_summary: list[str],
    tooling_signals: list[str],
) -> list[str]:
    surface: list[str] = []
    if entrypoints:
        surface.append("Likely runtime entry chain starts from: " + ", ".join(entrypoints[:3]) + ".")
    if project_kind == "python_cli":
        surface.append("Primary runtime looks CLI-driven, so command entrypoints are likely more important than long-lived services.")
    if project_kind == "python_service":
        surface.append("Primary runtime looks service-oriented, so request lifecycle, health checks, and deployment topology matter early.")
    if project_kind == "frontend_app":
        surface.append("Primary runtime looks frontend-centric, so build pipeline and browser-facing entrypoints are central.")
    if project_kind == "monorepo":
        surface.append("Runtime surface likely spans multiple packages/services and should be scoped before build, test, or deploy operations.")
    if any("Python CLI entrypoints" in item for item in manifest_summary):
        surface.append("Python manifest declares CLI entrypoints, which likely map to operational commands or end-user tooling.")
    if any("Node scripts" in item for item in manifest_summary):
        surface.append("Node scripts define part of the runnable surface and should be treated as part of the execution contract.")
    if any("Docker container build" in signal for signal in tooling_signals):
        surface.append("Container runtime may be the closest production-like execution path.")
    return surface[:6]


def _service_map(repo_path: Path, files: list[Path], entrypoints: list[str], project_kind: str) -> list[str]:
    manifests = [
        file_path.relative_to(repo_path).as_posix()
        for file_path in files
        if file_path.name in {"pyproject.toml", "package.json", "Dockerfile", "vercel.json", "wrangler.toml", "render.yaml", "render.yml"}
    ]
    scopes: list[str] = []
    for item in manifests:
        scope = str(Path(item).parent).replace("\\", "/")
        normalized_scope = "." if scope == "." else scope
        if normalized_scope not in scopes:
            scopes.append(normalized_scope)

    mapping: list[str] = []
    if project_kind == "monorepo":
        mapping.append("Repository appears to contain multiple service/package scopes that should be operated independently.")
    if entrypoints:
        mapping.append("Entrypoint scopes: " + ", ".join(sorted({Path(item).parent.as_posix() or "." for item in entrypoints[:5]})) + ".")
    if scopes:
        pretty_scopes = ", ".join(scopes[:6])
        mapping.append(f"Manifest/deploy scopes: {pretty_scopes}.")
    top_level_groups = sorted({file_path.parts[0] for file_path in files if len(file_path.parts) > 1 and file_path.parts[0] in {"src", "apps", "services", "packages", "tests"}})
    if top_level_groups:
        mapping.append("Primary top-level execution areas: " + ", ".join(top_level_groups) + ".")
    if not mapping:
        mapping.append("Repository topology looks flat; no strong service/package boundaries were inferred.")
    return mapping[:5]


def _boundary_hotspots(repo_path: Path, files: list[Path]) -> list[str]:
    python_files = [file_path for file_path in files if file_path.suffix == ".py"]
    import_pressure: Counter[str] = Counter()
    directory_pressure: Counter[str] = Counter()

    for file_path in python_files[:200]:
        rel_path = file_path.relative_to(repo_path).as_posix()
        directory_pressure[str(Path(rel_path).parent)] += 1
        tree = _parse_python_tree(file_path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                import_pressure[rel_path] += len(node.names)
            elif isinstance(node, ast.ImportFrom):
                import_pressure[rel_path] += len(node.names)

    hotspots: list[str] = []
    if import_pressure:
        path, count = import_pressure.most_common(1)[0]
        hotspots.append(f"Import hotspot: `{path}` references {count} imported modules/names and may sit on a boundary worth reviewing.")
    if directory_pressure:
        folder, count = directory_pressure.most_common(1)[0]
        hotspots.append(f"Directory hotspot: `{folder}` contains {count} Python files and likely concentrates core behavior or ownership.")
    if not hotspots:
        hotspots.append("No obvious Python boundary hotspots were derived from the scanned source.")
    return hotspots[:4]


def _internal_module_graph(repo_path: Path, files: list[Path]) -> list[str]:
    python_files = [file_path for file_path in files if file_path.suffix == ".py"]
    local_module_names = {file_path.stem for file_path in python_files}
    import_graph: Counter[str] = Counter()
    reverse_graph: Counter[str] = Counter()

    for file_path in python_files[:200]:
        rel_path = file_path.relative_to(repo_path).as_posix()
        tree = _parse_python_tree(file_path)
        if tree is None:
            continue
        imported_locals: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", maxsplit=1)[0]
                    if root in local_module_names:
                        imported_locals.add(root)
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0 and file_path.parent != repo_path:
                    imported_locals.add(file_path.parent.name)
                elif node.module:
                    root = node.module.split(".", maxsplit=1)[0]
                    if root in local_module_names:
                        imported_locals.add(root)
        import_graph[rel_path] += len(imported_locals)
        for imported in imported_locals:
            reverse_graph[imported] += 1

    summary: list[str] = []
    if import_graph:
        for path, count in import_graph.most_common(2):
            summary.append(f"Internal-import fan-out: `{path}` references {count} local modules.")
    if reverse_graph:
        for module, count in reverse_graph.most_common(2):
            summary.append(f"Internal-import fan-in: local module `{module}` is referenced by {count} modules.")
    if not summary:
        summary.append("No clear internal module graph summary was derived from Python imports.")
    return summary[:5]


def _hotspot_ranking(
    repo_path: Path,
    files: list[Path],
    entrypoints: list[str],
    project_kind: str,
) -> list[str]:
    python_files = [file_path for file_path in files if file_path.suffix == ".py"]
    scores: Counter[str] = Counter()

    for entrypoint in entrypoints:
        scores[entrypoint] += 5

    for file_path in python_files[:250]:
        rel_path = file_path.relative_to(repo_path).as_posix()
        tree = _parse_python_tree(file_path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                scores[rel_path] += len(node.names)
            elif isinstance(node, ast.ImportFrom):
                scores[rel_path] += len(node.names)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                scores[rel_path] += 1

    for file_path in files:
        if file_path.name in {"pyproject.toml", "package.json", "Dockerfile", "vercel.json", "wrangler.toml"}:
            rel_path = file_path.relative_to(repo_path).as_posix()
            scores[rel_path] += 4

    ranked: list[str] = []
    for path, score in scores.most_common(5):
        label = "runtime/config hotspot" if path in entrypoints or Path(path).name in {"pyproject.toml", "package.json", "Dockerfile"} else "module hotspot"
        ranked.append(f"`{path}` -> score {score} ({label})")

    if not ranked:
        ranked.append(f"No ranked hotspots were derived; repository currently looks low-signal for `{project_kind}` heuristics.")
    return ranked


def _manifest_summary(repo_path: Path, files: list[Path]) -> list[str]:
    summary: list[str] = []
    pyproject_paths = sorted(file_path for file_path in files if file_path.name == "pyproject.toml")
    package_paths = sorted(file_path for file_path in files if file_path.name == "package.json")

    for pyproject_path in pyproject_paths[:3]:
        pyproject = _load_toml(pyproject_path)
        project = pyproject.get("project", {})
        project_name = project.get("name")
        optional_deps = project.get("optional-dependencies", {})
        scripts = project.get("scripts", {})
        rel = pyproject_path.relative_to(repo_path).as_posix()
        if project_name:
            summary.append(f"Python package `{project_name}` declared in `{rel}`.")
        if optional_deps.get("dev"):
            summary.append(f"Python dev extras are defined in `{rel}`.")
        if scripts:
            summary.append(f"Python CLI entrypoints ({len(scripts)}) are declared in `{rel}`.")

    for package_path in package_paths[:3]:
        package_json = _load_json(package_path)
        package_name = package_json.get("name")
        scripts = package_json.get("scripts", {})
        rel = package_path.relative_to(repo_path).as_posix()
        if package_name:
            summary.append(f"Node package `{package_name}` declared in `{rel}`.")
        if scripts:
            script_names = ", ".join(sorted(list(scripts.keys()))[:4])
            summary.append(f"Node scripts in `{rel}`: {script_names}.")

    return summary[:8]


def _observed_signals(
    repo_path: Path,
    project_kind: str,
    entrypoints: list[str],
    tooling_signals: list[str],
    manifest_summary: list[str],
    dependency_surface: list[str],
    runtime_surface: list[str],
    language_counter: Counter[str],
) -> list[str]:
    signals = [
        f"Repository classified as `{project_kind}` from language mix, manifests, and entrypoints.",
    ]
    if language_counter:
        top_languages = ", ".join(f"{language} ({count})" for language, count in language_counter.most_common(3))
        signals.append(f"Top languages by file count: {top_languages}.")
    if entrypoints:
        signals.append("Likely entrypoints detected: " + ", ".join(entrypoints[:3]) + ".")
    if tooling_signals:
        signals.append("Operational/build markers detected: " + ", ".join(tooling_signals[:4]) + ".")
    if manifest_summary:
        signals.append("Manifest inspection found: " + "; ".join(manifest_summary[:3]))
    if dependency_surface:
        signals.append(dependency_surface[0])
    if runtime_surface:
        signals.append(runtime_surface[0])
    return signals[:5]


def _inferred_characteristics(
    project_kind: str,
    entrypoints: list[str],
    tooling_signals: list[str],
    test_file_count: int,
) -> list[str]:
    inferred: list[str] = []
    if project_kind == "monorepo":
        inferred.append("Repository likely contains multiple deployable services or packages and needs scoped operations.")
    if any("Docker" in signal for signal in tooling_signals):
        inferred.append("Container build and runtime parity likely matter for local validation and deployment workflows.")
    if any("GitHub Actions" in signal for signal in tooling_signals):
        inferred.append("CI behavior is likely encoded in GitHub Actions and should be treated as part of the delivery contract.")
    if entrypoints:
        inferred.append("Repository has identifiable runtime entrypoints, so onboarding can start from execution paths instead of a full tree scan.")
    if test_file_count == 0:
        inferred.append("Automated validation coverage may be incomplete because no dedicated test directory was discovered.")
    else:
        inferred.append("There is at least one explicit test suite location, so behavior changes should have an executable verification path.")
    return inferred[:5]


def _assumed_defaults(has_git_dir: bool, test_file_count: int, tooling_signals: list[str]) -> list[str]:
    assumptions: list[str] = []
    if not has_git_dir:
        assumptions.append("This folder is analyzed as a repository-like workspace without a local .git directory.")
    if not any("GitHub Actions" in signal for signal in tooling_signals):
        assumptions.append("CI provider is not explicit from detected files and may live outside the scanned markers.")
    if test_file_count == 0:
        assumptions.append("Smoke checks or manual validation may still exist even though a dedicated `tests/` directory was not found.")
    assumptions.append("Project kind is heuristic and should be confirmed against actual runtime and release workflows.")
    return assumptions[:4]


def _estimate_confidence(
    project_kind: str,
    entrypoints: list[str],
    tooling_signals: list[str],
    manifest_summary: list[str],
) -> str:
    evidence_points = 0
    if project_kind != "generic_repository":
        evidence_points += 1
    if entrypoints:
        evidence_points += 1
    if tooling_signals:
        evidence_points += 1
    if manifest_summary:
        evidence_points += 1
    if evidence_points >= 4:
        return "high"
    if evidence_points >= 2:
        return "medium"
    return "low"


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
    test_file_count = 0

    for file_path in files:
        rel_path = file_path.relative_to(repo_path).as_posix()
        language_counter[_extension_to_language(file_path)] += 1
        if rel_path.startswith("tests/") or "/tests/" in rel_path:
            test_file_count += 1

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
    entrypoints = _detect_entrypoints(repo_path, files)
    tooling_signals = _detect_tooling_signals(repo_path, files)
    project_kind = _detect_project_kind(files, entrypoints, language_counter)
    manifest_summary = _manifest_summary(repo_path, files)
    dependency_surface = _dependency_surface(repo_path, files)
    runtime_surface = _runtime_surface(project_kind, entrypoints, manifest_summary, tooling_signals)
    service_map = _service_map(repo_path, files, entrypoints, project_kind)
    boundary_hotspots = _boundary_hotspots(repo_path, files)
    internal_module_graph = _internal_module_graph(repo_path, files)
    hotspot_ranking = _hotspot_ranking(repo_path, files, entrypoints, project_kind)

    has_git_dir = (repo_path / ".git").exists()
    if not has_git_dir:
        notes.append("No .git directory found. Analysis still completed for local folder content.")
    observed_signals = _observed_signals(
        repo_path,
        project_kind,
        entrypoints,
        tooling_signals,
        manifest_summary,
        dependency_surface,
        runtime_surface,
        language_counter,
    )
    inferred_characteristics = _inferred_characteristics(project_kind, entrypoints, tooling_signals, test_file_count)
    assumed_defaults = _assumed_defaults(has_git_dir, test_file_count, tooling_signals)
    confidence = _estimate_confidence(project_kind, entrypoints, tooling_signals, manifest_summary)

    return RepoAnalysis(
        repo_path=str(repo_path),
        has_git_dir=has_git_dir,
        project_kind=project_kind,
        confidence=confidence,
        total_files=len(files),
        total_dirs=total_dirs,
        test_file_count=test_file_count,
        total_size_bytes=total_size_bytes,
        language_breakdown=dict(sorted(language_counter.items(), key=lambda item: item[1], reverse=True)),
        key_files=sorted(set(key_files)),
        entrypoints=entrypoints,
        tooling_signals=tooling_signals,
        manifest_summary=manifest_summary,
        dependency_surface=dependency_surface,
        runtime_surface=runtime_surface,
        service_map=service_map,
        boundary_hotspots=boundary_hotspots,
        internal_module_graph=internal_module_graph,
        hotspot_ranking=hotspot_ranking,
        observed_signals=observed_signals,
        inferred_characteristics=inferred_characteristics,
        assumed_defaults=assumed_defaults,
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
    lines.append(f"- **Project kind:** `{analysis.project_kind}`")
    lines.append(f"- **Confidence:** `{analysis.confidence}`")
    lines.append(f"- **Total files analyzed:** `{analysis.total_files}`")
    lines.append(f"- **Total directories discovered:** `{analysis.total_dirs}`")
    lines.append(f"- **Test files discovered:** `{analysis.test_file_count}`")
    lines.append(f"- **Total size analyzed:** `{analysis.total_size_bytes}` bytes")
    lines.append("")

    lines.append("## Observed Signals")
    lines.append("")
    lines.extend([f"- {item}" for item in analysis.observed_signals])
    lines.append("")

    lines.append("## Inferred Characteristics")
    lines.append("")
    lines.extend([f"- {item}" for item in analysis.inferred_characteristics])
    lines.append("")

    lines.append("## Runtime Signals")
    lines.append("")

    lines.append("## Runtime Surface")
    lines.append("")
    if analysis.runtime_surface:
        lines.extend([f"- {item}" for item in analysis.runtime_surface])
    else:
        lines.append("- No runtime surface summary derived.")
    lines.append("")

    lines.append("## Service Map")
    lines.append("")
    lines.extend([f"- {item}" for item in analysis.service_map])
    lines.append("")

    lines.append("## Boundary Hotspots")
    lines.append("")
    lines.extend([f"- {item}" for item in analysis.boundary_hotspots])
    lines.append("")

    lines.append("## Internal Module Graph")
    lines.append("")
    lines.extend([f"- {item}" for item in analysis.internal_module_graph])
    lines.append("")

    lines.append("## Hotspot Ranking")
    lines.append("")
    lines.extend([f"- {item}" for item in analysis.hotspot_ranking])
    lines.append("")

    lines.append("## Manifest Summary")
    lines.append("")
    if analysis.manifest_summary:
        lines.extend([f"- {item}" for item in analysis.manifest_summary])
    else:
        lines.append("- No additional manifest details detected.")
    lines.append("")

    lines.append("## Dependency Surface")
    lines.append("")
    if analysis.dependency_surface:
        lines.extend([f"- {item}" for item in analysis.dependency_surface])
    else:
        lines.append("- No dependency hints detected.")
    lines.append("")
    if analysis.entrypoints:
        lines.append("- Likely entrypoints:")
        lines.extend([f"  - `{entrypoint}`" for entrypoint in analysis.entrypoints])
    else:
        lines.append("- Likely entrypoints: none detected")
    if analysis.tooling_signals:
        lines.append("- Tooling signals:")
        lines.extend([f"  - {signal}" for signal in analysis.tooling_signals])
    else:
        lines.append("- Tooling signals: none detected")
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
    lines.append("## Assumptions")
    lines.append("")
    lines.extend([f"- {item}" for item in analysis.assumed_defaults])
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
        metadata=build_run_metadata(
            artifact_type="repository_analysis",
            subject=analysis.repo_path,
            subject_type="repository",
            warning_count=len(analysis.notes),
            extra={
                "repo_path": analysis.repo_path,
                "project_kind": analysis.project_kind,
                "file_count": analysis.total_files,
                "directory_count": analysis.total_dirs,
                "test_file_count": analysis.test_file_count,
                "entrypoint_count": len(analysis.entrypoints),
                "tooling_signal_count": len(analysis.tooling_signals),
                "language_count": len(analysis.language_breakdown),
                "manifest_summary_count": len(analysis.manifest_summary),
                "dependency_surface_count": len(analysis.dependency_surface),
                "runtime_surface_count": len(analysis.runtime_surface),
                "service_map_count": len(analysis.service_map),
                "boundary_hotspot_count": len(analysis.boundary_hotspots),
                "internal_module_graph_count": len(analysis.internal_module_graph),
                "hotspot_ranking_count": len(analysis.hotspot_ranking),
                "heuristic_mode": True,
                "confidence": analysis.confidence,
            },
        ),
    )
