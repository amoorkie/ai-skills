# test_generator Instructions

## Purpose
Generate a practical local testing plan by inspecting repository source files.

## Inputs
- `repo_path`
- `focus_paths` (optional)
- `test_framework` (phase 2 supports `pytest`)
- `include_edge_cases`
- `max_targets`

## Output Contract
- Save markdown report to `/generated/test_generator/`
- Never overwrite existing files silently
- Include target matrix, suggested cases, and starter pytest template

## Quality Guidance
- Prefer discoverable public functions/classes
- Flag risky files (bare `except`, TODO/FIXME, incomplete paths)
- Keep output actionable for immediate test authoring

