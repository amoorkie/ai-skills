# code_reviewer Instructions

## Purpose
Perform a static heuristic review of local source code and produce prioritized findings.

## Inputs
- `repo_path`
- `include_tests`
- `max_findings`
- `include_low_severity`

## Output Contract
- Save markdown report to `/generated/code_reviewer/`
- Never overwrite existing files silently
- Include severity, file/line, issue title, and remediation guidance

## Current Heuristics
- bare `except:`
- `eval(...)` usage
- debug `print(...)` in source code
- unresolved TODO/FIXME markers
- runtime `assert` in non-test modules

