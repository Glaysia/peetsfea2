from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from peetsfea.geometry.type1 import DdSplit, build_planar_rect_spiral_masks, layer_rect_spirals
from peetsfea.geometry.type1.tx_coil_3d import tx_coil_face_frame_for_name
from peetsfea.pipeline.runner import run_type1_from_path
from peetsfea.pipeline.serialize import to_dict


def _build_payload(result) -> dict[str, Any]:
    return {
        "sample": to_dict(result.sample),
        "geometry": to_dict(result.geometry),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="peetsfea non-model pipeline")
    parser.add_argument("spec", type=Path, help="Path to spec TOML")
    parser.add_argument("--seed", type=int, default=599, help="Seed for deterministic sampling")
    parser.add_argument("--out", type=Path, default=None, help="Write JSON output to file")
    parser.add_argument(
        "--debug-tx-planar-spiral",
        action="store_true",
        help="Include a derived planar rectangular spiral mask (2D) in JSON output (debug helper)",
    )
    args = parser.parse_args(argv)

    result = run_type1_from_path(args.spec, args.seed)
    payload = _build_payload(result)

    if args.debug_tx_planar_spiral:
        first = next((inst for inst in result.sample.tx_coil.instances if inst.present), None)
        if first is None:
            payload["debug"] = {
                "tx_planar_spiral_face": None,
                "tx_planar_spiral_masks": [],
                "tx_planar_spiral_layered": [],
            }
        else:
            frame = tx_coil_face_frame_for_name(result.sample, first.face)
            dd = None
            if first.spiral_count == 2:
                dd = DdSplit(axis_idx=first.dd_split_axis_idx, gap_mm=first.dd_gap_mm, ratio=first.dd_split_ratio)

            masks = build_planar_rect_spiral_masks(
                face_u_size_mm=frame.face_u_size_mm,
                face_v_size_mm=frame.face_v_size_mm,
                spiral_count=first.spiral_count,
                turns=first.spiral_turns,
                direction_idx=first.spiral_direction_idx,
                start_edge_idx=first.spiral_start_edge_idx,
                edge_clearance_mm=first.edge_clearance_mm,
                fill_scale=first.fill_scale,
                pitch_duty=first.pitch_duty,
                min_trace_width_mm=first.min_trace_width_mm,
                min_trace_gap_mm=first.min_trace_gap_mm,
                dd=dd,
            )

            effective_trace_layers = min(result.sample.tx_pcb.layer_count, first.trace_layer_count)
            layer_mode_idx_effective = first.layer_mode_idx if effective_trace_layers >= 2 else 0
            payload["debug"] = {
                "tx_planar_spiral_face": frame.name,
                "tx_planar_spiral_masks": [to_dict(mask) for mask in masks],
                "tx_planar_spiral_layered": [
                    to_dict(layered)
                    for layered in layer_rect_spirals(
                        masks,
                        layer_mode_idx=layer_mode_idx_effective,
                        radial_split_top_turn_fraction=first.radial_split_top_turn_fraction,
                        radial_split_outer_is_top=first.radial_split_outer_is_top,
                    )
                ],
            }

    text = json.dumps(payload, indent=2, sort_keys=True)

    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
