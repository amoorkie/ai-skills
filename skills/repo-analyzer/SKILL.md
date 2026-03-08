---
name: repo-analyzer
description: Run the local ai-skills-toolkit repo analyzer against a repository and return a high-signal repository scan report. Use when the user asks to inspect, analyze, map, or understand a repository structure/runtime/tooling setup with the toolkit.
---

# Repo Analyzer

Use this skill to run the `ai_skills_toolkit` `repo-analyzer` command instead of manually scanning the repository tree.

## Workflow

1. Resolve the target repository.
   - If the user says "this repo" or "current directory", use the current workspace.
   - Otherwise use the path the user names.

2. Resolve the toolkit repository.
   - Prefer `AI_SKILLS_TOOLKIT_PATH` if present.
   - Otherwise the bundled launcher will try the current working directory and then the machine-local default toolkit path.

3. Run the bundled launcher:

```powershell
python "<skill-dir>\\scripts\\run_repo_analyzer.py" --target-repo "<repo-path>"
```

4. Read the generated markdown report and summarize:
   - project kind
   - runtime/tooling signals
   - service map / hotspot ranking
   - artifact path
