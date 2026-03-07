# doc_writer Instructions

## Purpose
Generate a practical markdown document by using local repository analysis as source truth.

## Inputs
- `repo_path`
- `title`
- `audience`
- `include_setup_checklist`

## Output Contract
- Save markdown into `/generated/doc_writer/`
- Never overwrite existing files silently
- Include sections for summary, structure, technology signals, and next documentation work

## Writing Guidance
- Keep claims tied to observed repo evidence
- Prefer concise operational language over generic prose
- Surface uncertainty explicitly when scan coverage is partial

