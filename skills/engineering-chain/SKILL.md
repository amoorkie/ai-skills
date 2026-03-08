---
name: engineering-chain
description: Run the local ai-skills-toolkit engineering workflow chain against a repository and return linked repository-analysis, code-review, test-plan, and documentation artifacts. Use when the user wants a structured engineering pass on a repo instead of one isolated report.
---

# Engineering Chain

Use this skill to run the `ai_skills_toolkit` `engineering-chain` command.

## Workflow

1. Resolve the target repository.
2. Resolve the toolkit repository.
3. Run the bundled launcher:

```powershell
python "<skill-dir>\\scripts\\run_engineering_chain.py" --target-repo "<repo-path>"
```

4. Read the chain summary artifact and summarize:
   - repository kind
   - highest-priority review risks
   - top suggested test targets
   - documentation/report paths
