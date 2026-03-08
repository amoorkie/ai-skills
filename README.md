# ai-skills-toolkit

Modular local toolkit for AI coding and product-design agents.

This repository now contains a production-style CLI, eight practical skills, built-in readiness benchmarks, and linked workflow chains for design and engineering use cases.

## Status
- Runtime: Python 3.11+
- Packaging: installable via `pyproject.toml`
- Test suite: `pytest`
- Output safety: no silent overwrite
- Readiness: built-in eval suites for every major skill
- Workflows: linked `design-chain`, `engineering-chain`, and `full-suite` commands

## Implemented Skills
- `repo_analyzer`: inspect local repositories and produce structured scan reports
- `doc_writer`: generate markdown project docs from repository analysis
- `prompt_debugger`: diagnose prompts and generate stronger prompt variants
- `architecture_designer`: generate technical architecture specs for engineering teams
- `figma_ui_architect`: generate UI/UX planning specs for mini apps, dashboards, and admin tools
- `test_generator`: generate actionable pytest test plans from local source inspection
- `code_reviewer`: run heuristic static code review and produce prioritized findings
- `deploy_helper`: generate platform-aware deployment plans and checklists

## Readiness and Workflow Commands
```bash
python -m ai_skills_toolkit benchmark-all --output-name toolkit-readiness --overwrite
python -m ai_skills_toolkit design-chain --repo-path . --product-name "Ops Console" --product-goal "Help operators review workflows safely." --jtbd "When reviewing queue health, I want actionable status so I can resolve issues quickly." --output-name design-pack --overwrite
python -m ai_skills_toolkit engineering-chain --repo-path . --test-focus-path src/ai_skills_toolkit/cli.py --output-name engineering-pack --overwrite
python -m ai_skills_toolkit full-suite --repo-path . --product-name "Ops Console" --product-goal "Help operators review workflows safely." --jtbd "When reviewing queue health, I want actionable status so I can resolve issues quickly." --test-focus-path src/ai_skills_toolkit/cli.py --output-name release-pack --overwrite
```

## Workflow Catalog
- `benchmark-all`: run the built-in eval corpus for all core skills and generate a readiness report.
- `design-chain`: run `repo_analyzer -> architecture_designer -> figma_ui_architect` as one linked design/handoff workflow.
- `engineering-chain`: run `repo_analyzer -> code_reviewer -> test_generator -> doc_writer` as one linked engineering workflow.
- `full-suite`: run readiness plus both linked chains and generate a release-pack report.

## Quick Start
```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run help:
```bash
python -m ai_skills_toolkit --help
```

Run tests:
```bash
python -m pytest
```

## CLI Commands
```bash
python -m ai_skills_toolkit repo-analyzer --repo-path .
python -m ai_skills_toolkit doc-writer --repo-path . --title "Engineering Overview"
python -m ai_skills_toolkit prompt-debugger --prompt "Design a safe deployment workflow with output format."
python -m ai_skills_toolkit architecture-designer --product-name "Ops Console" --product-goal "Reduce incident resolution time for operations."
python -m ai_skills_toolkit figma-ui-architect --product-name "Admin Workbench" --product-goal "Help admins triage and resolve workflow exceptions."
python -m ai_skills_toolkit test-generator --repo-path . --focus-path "src/ai_skills_toolkit"
python -m ai_skills_toolkit code-reviewer --repo-path . --max-findings 40
python -m ai_skills_toolkit deploy-helper --repo-path . --platform auto --app-name "ai-skills-toolkit"
```

## Context-Aware Design Commands
```bash
python -m ai_skills_toolkit architecture-designer --product-name "Ops Portal" --product-goal "Provide operational visibility for platform teams." --repo-context-repo-path .
python -m ai_skills_toolkit figma-ui-architect --product-name "Ops Console" --product-goal "Help operators review workflows and integrations safely." --repo-context-repo-path . --architecture-context-repo-path
```

## Output Contract
- All artifacts are written under `generated/<skill_name>/`.
- Existing files are never overwritten unless `--overwrite` is explicitly passed.
- Default output names are timestamped in CLI for safer repeated local runs.
- Workflow commands also produce summary artifacts that link to all downstream reports.

## Practical End-to-End Example
1. Analyze a repository:
```bash
python -m ai_skills_toolkit repo-analyzer --repo-path . --output-name baseline-scan
```
2. Generate onboarding docs from that repo:
```bash
python -m ai_skills_toolkit doc-writer --repo-path . --title "Project Onboarding" --output-name onboarding
```
3. Improve an engineering prompt:
```bash
python -m ai_skills_toolkit prompt-debugger --prompt "Create CI and release checklist." --output-name ci-prompt-debug
```
4. Generate a test plan:
```bash
python -m ai_skills_toolkit test-generator --repo-path . --output-name test-plan
```
5. Generate a code review report:
```bash
python -m ai_skills_toolkit code-reviewer --repo-path . --output-name code-review
```
6. Generate a deployment plan:
```bash
python -m ai_skills_toolkit deploy-helper --repo-path . --platform auto --output-name deploy-plan
```

## Python API Example
```python
from pathlib import Path

from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput, run

result = run(
    RepoAnalyzerInput(repo_path=Path(".")),
    output_dir=Path("generated"),
    output_name="repo-analysis",
)
print(result.output_path)
```

## Repository Layout
```text
.
|-- pyproject.toml
|-- README.md
|-- src/
|   `-- ai_skills_toolkit/
|       |-- cli.py
|       |-- core/
|       `-- skills/
|           |-- repo_analyzer/
|           |-- doc_writer/
|           |-- prompt_debugger/
|           |-- architecture_designer/
|           |-- figma_ui_architect/
|           |-- test_generator/
|           |-- code_reviewer/
|           `-- deploy_helper/
`-- tests/
```

## Development
- Install dev dependencies: `pip install -e ".[dev]"`
- Run tests: `python -m pytest`
- Entry point: `python -m ai_skills_toolkit`
- Run readiness suite: `python -m ai_skills_toolkit benchmark-all --output-name toolkit-readiness --overwrite`
- Run release pack: `python -m ai_skills_toolkit full-suite --repo-path . --product-name "Ops Console" --product-goal "Help operators review workflows safely." --jtbd "When reviewing queue health, I want actionable status so I can resolve issues quickly." --test-focus-path src/ai_skills_toolkit/cli.py --output-name release-pack --overwrite`

## Limitations (Current)
- Outputs are heuristic-driven and deterministic; they do not replace human product, design, or release approval.
- Cross-skill chains improve context flow, but they are still bounded by local source heuristics rather than live production telemetry.
- Architecture/UI specs are stronger handoff artifacts now, but they still need validation against the actual implementation plan.

## Roadmap
- Add additional workflow packs beyond the current design and engineering chains
- Deepen repository understanding with richer ownership and boundary analysis
- Add pluggable rendering and export formats
