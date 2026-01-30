# Long-Term Plan

## Goal
Capture high-value operational events ("manager-facing" milestones) via a decorator so that remote runs can be audited and summarized quickly.

## Recommended Logging Dependency
- **structlog**
  - Widely used for structured logging in Python
  - Plays well with standard `logging`
  - Makes JSON output straightforward for log aggregation

## High-Value Events (Decorator Targets)
- Pipeline entry points
  - `run_type1`, `run_type1_from_path`, `run_type1_aedt_from_path`
- Geometry generation
  - `build_type1_parametric_geometry`
- AEDT integration
  - `apply_parametric_geometry_plan`

## Logged Fields (Baseline)
- `event`: short action name (e.g., `run_type1_start`, `aedt_apply_done`)
- `timestamp`: ISO8601
- `seed`, `spec_path`, `project_name`, `design_name`
- `duration_ms`
- `success` / `error`
- `commit` (optional: git hash if available)

## Proposed Decorator Shape
- `@log_action(event="...")`
  - logs `start` and `end`
  - catches exceptions to log `error`
  - measures runtime

## Output Format
- JSON lines (one event per line) to stdout
- Compatible with common log collectors

## Minimal Integration Steps (later)
1) Add dependency: `structlog`
2) Configure JSON renderer + standard logging integration
3) Implement decorator in a small utility module
4) Apply decorator to targets above

## Notes
- Keep logs concise; avoid dumping full specs unless explicitly requested
- All logs should remain compatible with local runs (stdout only)
