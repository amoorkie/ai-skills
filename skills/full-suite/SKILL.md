---
name: full-suite
description: Run the local ai-skills-toolkit full workflow suite and return readiness, design-chain, and engineering-chain artifacts as one release pack. Use when the user wants the most complete toolkit-backed pass on a repository.
---

# Full Suite

Use this skill to run the `ai_skills_toolkit` `full-suite` command.

## Workflow

1. Resolve the target repository.
2. Resolve product context:
   - `product_name`
   - `product_goal`
   - at least one JTBD when possible
3. Resolve the toolkit repository.
4. Run the bundled launcher:

```powershell
python "<skill-dir>\\scripts\\run_full_suite.py" --target-repo "<repo-path>" --product-name "<name>" --product-goal "<goal>" --jtbd "<jtbd>"
```

5. Read the generated release-pack artifact and summarize:
   - readiness status
   - design workflow highlights
   - engineering workflow highlights
   - artifact paths
