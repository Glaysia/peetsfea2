# HANDOFF: peetsfea2 (Type1 spec → coil geometry → dataset artifacts)

## Purpose
This repo is a deterministic “spec-first” pipeline for building a **Type1** WPT scenario and generating a dataset:
- TOML spec → deterministic sampling (seed) → domain interpretation → parametric geometry plan
- Optional: apply the plan to AEDT Maxwell (project creation; solving is out of scope for now)
- Dataset pipeline that snapshots spec + writes `genes/derived/geometry` per seed

## Environment
- Venv: `/home/harry/Projects/PythonProjects/.venv`
- Install: `uv pip install -e /home/harry/Projects/PythonProjects/peetsfea2`

## Quick start
- Non-AEDT run (JSON to stdout):
  - `python -m peetsfea.cli examples/type1.toml --seed 1`
- Debug: planar spiral + layer split:
  - `python -m peetsfea.cli examples/type1.toml --seed 1 --debug-tx-planar-spiral --out /tmp/tx_debug.json`
- Dataset (no AEDT, fast):
  - `python -m peetsfea.dataset_cli examples/type1.toml --out out --seed-range 1 50`
- Dataset + Maxwell project creation (slow; requires AEDT):
  - `python -m peetsfea.dataset_cli examples/type1.toml --out out --seed-range 1 10 --aedt --non-graphical`

## Current status (what works)
- **Spec parsing**: `tx.coil.schema="instances_v1"` (no legacy/back-compat).
- **Sampling**: deterministic per seed; includes spiral-fit validation to avoid “mask doesn’t fit” crashes.
- **2D coil**:
  - Rect spiral / DD mask generation (per-face 2D `u,v` plane).
  - 2-layer distribution modes: single-layer, radial split, alternate turns (via points emitted).
  - Overlap estimate (grid sampling) is recorded.
- **3D coil (v1)**:
  - Box-strip approximation of traces per `[[tx.coil.instances]]` (each instance has a `face`).
  - Via boxes for layer transitions.
  - Terminal tabs (stable naming) + per-instance `unite` operation via `OperationPlan`.
- **Robustness**:
  - Sampler reject/resample for “meaningless wiring” (self-contact / closed loop / branching) before geometry build.
  - AEDT apply post-processing forces `TX_Coil*` materials back to `copper` after boolean ops.
- **Dataset pipeline (v1)**:
  - Writes per-sample directory with `spec_snapshot.toml`, `meta.json`, `genes.json`, `derived.json`, `geometry.json`.

## Key APIs
- Parse + run (no AEDT):
  - `peetsfea.pipeline.runner.run_type1_from_path(path, seed)`
- AEDT (parametric plan apply):
  - `peetsfea.pipeline.runner.run_type1_aedt_from_path(path, seed, project_name, out_dir=..., design_name=..., config=...)`
- Dataset writer:
  - `peetsfea.pipeline.dataset.write_type1_dataset_sample(spec_path, seed=..., out_root=..., build_aedt=...)`

## Geometry plan model
- `ParametricGeometryPlan` contains:
  - `variables`: design vars (numbers + SymPy expressions)
  - `boxes`: parametric boxes (corner/size expressions)
  - `operations`: boolean ops (`unite`/`subtract`) executed by AEDT adapter

## Naming conventions (important)
- Coil objects are named with `TX_Coil*` prefix.
- The final unified body name is stabilized by using the terminal-A tab name as the first unite target.

## Core files (code map)
- Logging: `src/peetsfea/logging_utils.py` (structlog JSON + `@log_action`)
- Spec parsing: `src/peetsfea/domain/type1/parse.py`
- Sampling: `src/peetsfea/sampling/type1_sampler.py`
- 2D coil:
  - Mask: `src/peetsfea/geometry/type1/spiral_mask.py`
  - Layer split: `src/peetsfea/geometry/type1/layer_modes.py`
- 3D coil: `src/peetsfea/geometry/type1/tx_coil_3d.py`
- Parametric geometry builder: `src/peetsfea/geometry/type1/builder.py`
- AEDT adapter: `src/peetsfea/aedt/maxwell3d_adapter.py`
- Dataset pipeline: `src/peetsfea/pipeline/dataset.py`, `src/peetsfea/dataset_cli.py`

## Known limitations / next steps
- Current coil is **box-strip** based (not polyline+sweep).
- Multi-instance coils are currently **independent conductors** (no cross-face series/parallel connectivity yet).
- “Inner PCB stack” genes (`inner_*`) are sampled and saved but not yet used to build additional PCBs.
