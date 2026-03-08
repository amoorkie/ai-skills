---
name: design-chain
description: Run the local ai-skills-toolkit design workflow chain and return linked repository-analysis, architecture, and Figma-oriented UI planning artifacts. Use when the user wants a structured product/design handoff pack for a repository and product concept.
---

# Design Chain

Use this skill to run the `ai_skills_toolkit` `design-chain` command.

## Workflow

1. Resolve the target repository.
2. Resolve product context from the user's request:
   - `product_name`
   - `product_goal`
   - at least one JTBD when possible
3. Resolve the toolkit repository.
4. Run the bundled launcher:

```powershell
python "<skill-dir>\\scripts\\run_design_chain.py" --target-repo "<repo-path>" --product-name "<name>" --product-goal "<goal>" --jtbd "<jtbd>"
```

5. Read the summary artifact and summarize:
   - repository/runtime constraints
   - architecture priorities
   - key UI flows/screens
   - artifact paths
