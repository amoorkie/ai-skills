# prompt_debugger Instructions

## Purpose
Diagnose prompt quality and generate stronger alternatives suitable for production workflows.

## Inputs
- `prompt` (required)
- `goal` (optional)
- `context` (optional)
- `target_model` (optional)

## Output Contract
- Save report to `/generated/prompt_debugger/`
- Include:
  - diagnosis with severity labels
  - multiple improved prompt variants
  - rationale per variant
- Never overwrite existing files silently

## Debugging Heuristics
- Detect missing format contract
- Detect absent constraints/guardrails
- Detect likely ambiguity due to underspecification
- Provide variants optimized for different execution styles

