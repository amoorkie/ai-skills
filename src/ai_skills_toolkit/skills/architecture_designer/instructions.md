# architecture_designer Instructions

## Purpose
Produce a technical architecture specification that can be handed to engineers for implementation planning.

## Inputs
- `product_name`
- `product_goal`
- `primary_users`
- `functional_requirements`
- `non_functional_requirements`
- `constraints`
- `assumptions`

## Output Contract
- Save markdown to `/generated/architecture_designer/`
- Include:
  - technical component model
  - API and data design baseline
  - deployment/security/observability considerations
  - risks and open questions
- Never overwrite files silently

## Quality Bar
- Prefer concrete technical decisions over abstract templates
- Show explicit tradeoffs and default assumptions
- Keep spec usable for phase planning and architecture review

