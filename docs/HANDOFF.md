# HANDOFF: tv_wpt_coil non-model reproduction in peetsfea2

## Purpose
This repo now reproduces the **non-model** part of tv_wpt_coil as clean, modular Python.
Primary usage is **importing the library from other Python modules** (not CLI).

## Environment
- Venv: `/home/harry/Projects/PythonProjects/.venv`
- Install: `uv pip install -e /home/harry/Projects/PythonProjects/peetsfea2`

## Current status (what works)
- Spec → sampling → domain interpretation → geometry plan (boxes) works.
- AEDT application works via **parametric-only** path (variables + SymPy expressions).
- Domain validation rules are enforced.

## Key APIs
- Parse + run (no AEDT):
  - `peetsfea.pipeline.runner.run_type1_from_path(path, seed)`
- AEDT (parametric only):
  - `peetsfea.pipeline.runner.run_type1_aedt_from_path(path, seed, project_name, out_dir=..., design_name=..., config=...)`
- Project naming rule:
  - `build_project_name(base, spec_path, seed)` → `name_hash_3_seed`

## AEDT behavior
- Non-parametric path has been removed. **Always parametric.**
- All numeric inputs are registered as AEDT variables; all derived values are SymPy expressions.
- Parametric plan uses:
  - tx_center_z = tv_bottom - tx_gap_from_tv_bottom - tx_core_h/2
  - rx_center_z = tx_center_z + tx_core_h/2 + core_core_gap + rx_core_h/2

## Spec constraints (current)
- `constraints.tx_gap_from_tv_bottom_mm`: controls TV→TX top distance.
- `constraints.core_core_gap_mm`: controls TX↔RX closest distance.
- TV and RX are **not** forced to touch anymore.

## Core files
- Domain rules: `src/peetsfea/domain/type1/interpreter.py`
- Spec parsing: `src/peetsfea/domain/type1/parse.py`
- Sampling: `src/peetsfea/sampling/type1_sampler.py`
- Parametric geometry: `src/peetsfea/geometry/type1/builder.py`
- AEDT adapter: `src/peetsfea/aedt/maxwell3d_adapter.py`
- Pipeline: `src/peetsfea/pipeline/runner.py`

## Notes
- `sympy` is required for parametric plan generation.
- `examples/type1.toml` is the current sample spec.
- CLI exists but is secondary.

## Next suggested steps
- Add tests for validation + determinism.
- Consider documenting variable naming conventions for AEDT Optimetrics.
