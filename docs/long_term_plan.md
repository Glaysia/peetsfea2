# Logging / Telemetry Plan (Current Status + Next)

## Goal
Capture high-value operational events (“manager-facing milestones”) so that long remote runs can be audited and summarized quickly.

## Current Status (Implemented)
- Structured logging is implemented via **structlog** in `src/peetsfea/logging_utils.py`.
- Decorator is implemented as `@log_action("event_name", context_fn=...)`:
  - emits `event_name_start` / `event_name_end`
  - emits `event_name_error` on exception
  - JSON lines to stdout (ISO timestamp, level, duration, context)

### Current decorated entry points (non-exhaustive)
- Pipeline:
  - `run_type1`, `run_type1_from_path`, `run_type1_aedt_from_path`
- Geometry:
  - `build_type1_parametric_geometry`
- AEDT apply:
  - `apply_parametric_geometry_plan`

## Logging Fields (Baseline)
- `event`: string key (e.g., `run_type1_from_path_start`)
- `timestamp`: ISO8601 UTC
- `duration_ms`
- Context fields when available:
  - `seed`, `spec_path`, `project_name`, `design_name`
  - `box_count`, `variable_count`, `operation_count`

## Next Improvements (Optional)
- Add dataset pipeline events:
  - `write_type1_dataset_sample_start/end/error`
- Add “spec hash / version / commit” stamping:
  - `peetsfea_version` is already available (runner); git hash could be added in CI or via env var.
- Add a “quiet mode” for CLI tools to reduce JSON logs during large sweeps.

## Notes
- Keep logs concise; avoid dumping full spec content by default.
- If a stable machine-readable run summary is needed, write it into dataset artifacts (`meta.json` / `results.json`) rather than logs.
