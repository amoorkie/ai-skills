# repo_analyzer Instructions

## Purpose
Inspect a local repository and generate a factual markdown report containing:
- file and directory inventory
- language distribution
- key operational files
- largest files
- notable scan caveats

## Inputs
- `repo_path` (local directory path)
- `include_hidden` (optional; default `false`)
- `max_files` (optional safety cap)
- `largest_file_count` (optional)

## Output Contract
- Write markdown report to `/generated/repo_analyzer/`
- Fail if output file already exists and overwrite is not explicitly enabled
- Include notes when scanning is partial or when metadata cannot be read

## Analyst Guidance
- Focus on local filesystem facts only
- Do not assume framework if evidence is missing
- Include caveats for incomplete scans

