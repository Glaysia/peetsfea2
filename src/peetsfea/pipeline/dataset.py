from __future__ import annotations

import json
import platform
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from peetsfea.aedt.maxwell3d_adapter import Maxwell3dConfig, apply_parametric_geometry_plan
from peetsfea.geometry.type1.layer_modes import Segment2D, layer_rect_spirals
from peetsfea.geometry.type1.self_contact import detect_self_contact
from peetsfea.geometry.type1.spiral_mask import DdSplit, build_planar_rect_spiral_masks
from peetsfea.geometry.type1.topology import topology_from_segments
from peetsfea.geometry.type1.tx_coil_3d import tx_coil_face_frame_for_name
from peetsfea.pipeline.runner import PEETSFEA_VERSION, build_project_name, run_type1_from_path
from peetsfea.pipeline.serialize import to_dict


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _toml_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()[:6]


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _polyline_length_mm(polyline: tuple[tuple[float, float], ...]) -> float:
    length = 0.0
    for (u0, v0), (u1, v1) in zip(polyline[:-1], polyline[1:]):
        length += abs(u1 - u0) + abs(v1 - v0)
    return length


def _segments_length_mm(segments: tuple[Segment2D, ...]) -> float:
    length = 0.0
    for seg in segments:
        (u0, v0) = seg.a
        (u1, v1) = seg.b
        length += abs(u1 - u0) + abs(v1 - v0)
    return length


def derive_tx_coil_features(sample) -> dict[str, Any]:
    present_instances = [inst for inst in sample.tx_coil.instances if inst.present]
    if not present_instances:
        return {"status": "no_instance_present"}

    def derive_instance(inst) -> dict[str, Any]:
        try:
            frame = tx_coil_face_frame_for_name(sample, inst.face)
        except Exception as exc:
            return {"status": "error", "name": inst.name, "face": inst.face, "error_type": type(exc).__name__, "error": str(exc)}

        dd = None
        if inst.spiral_count == 2:
            dd = DdSplit(axis_idx=inst.dd_split_axis_idx, gap_mm=inst.dd_gap_mm, ratio=inst.dd_split_ratio)

        try:
            masks = build_planar_rect_spiral_masks(
                face_u_size_mm=frame.face_u_size_mm,
                face_v_size_mm=frame.face_v_size_mm,
                spiral_count=inst.spiral_count,
                turns=inst.spiral_turns,
                direction_idx=inst.spiral_direction_idx,
                start_edge_idx=inst.spiral_start_edge_idx,
                edge_clearance_mm=inst.edge_clearance_mm,
                fill_scale=inst.fill_scale,
                pitch_duty=inst.pitch_duty,
                min_trace_width_mm=inst.min_trace_width_mm,
                min_trace_gap_mm=inst.min_trace_gap_mm,
                dd=dd,
            )
        except Exception as exc:
            return {
                "status": "error",
                "name": inst.name,
                "face": inst.face,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

        effective_trace_layers = min(sample.tx_pcb.layer_count, inst.trace_layer_count)
        layer_mode_idx_effective = inst.layer_mode_idx if effective_trace_layers >= 2 else 0

        try:
            layered = layer_rect_spirals(
                masks,
                layer_mode_idx=layer_mode_idx_effective,
                radial_split_top_turn_fraction=inst.radial_split_top_turn_fraction,
                radial_split_outer_is_top=inst.radial_split_outer_is_top,
            )
        except Exception as exc:
            return {
                "status": "error",
                "name": inst.name,
                "face": inst.face,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

        per_spiral: list[dict[str, Any]] = []
        for mask, lay in zip(masks, layered):
            self_top = detect_self_contact(tuple(lay.top_segments))
            self_bottom = detect_self_contact(tuple(lay.bottom_segments))
            topology_all = topology_from_segments(tuple(lay.top_segments) + tuple(lay.bottom_segments))
            topology_top = topology_from_segments(tuple(lay.top_segments))
            topology_bottom = topology_from_segments(tuple(lay.bottom_segments))
            per_spiral.append(
                {
                    "turns": mask.turns,
                    "start_edge_idx": mask.start_edge_idx,
                    "direction_idx": mask.direction_idx,
                    "pitch_mm": mask.derived.pitch_mm,
                    "trace_width_mm": mask.derived.trace_width_mm,
                    "trace_gap_mm": mask.derived.trace_gap_mm,
                    "polyline_length_mm": _polyline_length_mm(mask.polyline),
                    "top_length_mm": _segments_length_mm(lay.top_segments),
                    "bottom_length_mm": _segments_length_mm(lay.bottom_segments),
                    "via_count": len(lay.via_points),
                    "terminal_a": lay.terminal_a,
                    "terminal_b": lay.terminal_b,
                    "terminal_a_is_top": lay.terminal_a_is_top,
                    "terminal_b_is_top": lay.terminal_b_is_top,
                    "overlap_estimate": to_dict(lay.overlap_estimate),
                    "self_contact_top": to_dict(self_top),
                    "self_contact_bottom": to_dict(self_bottom),
                    "self_contact_detected": bool(self_top.detected or self_bottom.detected),
                    "self_contact_pair_count": int(self_top.pair_count + self_bottom.pair_count),
                    "topology_all": to_dict(topology_all),
                    "topology_top": to_dict(topology_top),
                    "topology_bottom": to_dict(topology_bottom),
                }
            )

        # Total topology estimate (2D graph on segment endpoints).
        # For DD coils, include the planned series-connection bridge (as in tx_coil_3d).
        total_segments: list[Segment2D] = []
        for lay in layered:
            total_segments.extend(lay.top_segments)
            total_segments.extend(lay.bottom_segments)
        if inst.spiral_count == 2 and len(layered) >= 2:
            p0 = layered[0].terminal_b
            p1 = layered[1].terminal_a
            if p0[0] == p1[0] or p0[1] == p1[1]:
                total_segments.append(Segment2D(a=p0, b=p1, width_mm=0.0))
            else:
                mid = (p1[0], p0[1])
                total_segments.append(Segment2D(a=p0, b=mid, width_mm=0.0))
                total_segments.append(Segment2D(a=mid, b=p1, width_mm=0.0))
        topology_total = topology_from_segments(tuple(total_segments))
        open_path_total_est_ok = (
            topology_total.component_count == 1
            and topology_total.endpoints_count == 2
            and not topology_total.has_branch
        )

        overlap_total = {
            "top_area_est_mm2": float(sum(s["overlap_estimate"]["top_area_est_mm2"] for s in per_spiral)),
            "bottom_area_est_mm2": float(sum(s["overlap_estimate"]["bottom_area_est_mm2"] for s in per_spiral)),
            "overlap_area_est_mm2": float(sum(s["overlap_estimate"]["overlap_area_est_mm2"] for s in per_spiral)),
        }
        denom = min(overlap_total["top_area_est_mm2"], overlap_total["bottom_area_est_mm2"])
        overlap_total["overlap_ratio_est"] = (overlap_total["overlap_area_est_mm2"] / denom) if denom > 0 else 0.0

        self_contact_total = {
            "detected": bool(any(s["self_contact_detected"] for s in per_spiral)),
            "pair_count": int(sum(int(s["self_contact_pair_count"]) for s in per_spiral)),
            "spiral_count_detected": int(sum(1 for s in per_spiral if s["self_contact_detected"])),
        }

        return {
            "status": "ok",
            "name": inst.name,
            "face": frame.name,
            "face_u_size_mm": frame.face_u_size_mm,
            "face_v_size_mm": frame.face_v_size_mm,
            "effective_trace_layers": effective_trace_layers,
            "layer_mode_idx_effective": layer_mode_idx_effective,
            "spiral_count": inst.spiral_count,
            "dd": to_dict(dd) if dd is not None else None,
            "spirals": per_spiral,
            "topology_total": to_dict(topology_total),
            "open_path_total_est_ok": open_path_total_est_ok,
            "overlap_total_estimate": overlap_total,
            "self_contact_total": self_contact_total,
            "material_diagnostics": {
                "material_before_ops": None,
                "material_after_ops": None,
                "material_override_applied": False,
                "note": "Material diagnostics require AEDT-side inspection/override.",
            },
        }

    derived_instances = [derive_instance(inst) for inst in present_instances]
    ok_count = sum(1 for inst in derived_instances if inst.get("status") == "ok")

    return {
        "status": "ok",
        "instance_count": len(present_instances),
        "instance_ok_count": ok_count,
        "instances": derived_instances,
        "outer_faces": to_dict(sample.tx_coil.outer_faces),
    }

@dataclass(frozen=True)
class Type1DatasetWriteResult:
    sample_dir: Path
    status: str  # ok | skipped | error


def write_type1_dataset_sample(
    spec_path: Path,
    *,
    seed: int,
    out_root: Path,
    project_name: str = "type1",
    build_aedt: bool = False,
    maxwell_config: Maxwell3dConfig | None = None,
    overwrite: bool = False,
) -> Type1DatasetWriteResult:
    spec_hash = _toml_hash(spec_path)
    full_name = build_project_name(project_name, spec_path, seed, version=PEETSFEA_VERSION)

    sample_dir = out_root / "type1" / full_name
    sample_dir.mkdir(parents=True, exist_ok=True)

    marker = sample_dir / "meta.json"
    if marker.exists() and not overwrite:
        return Type1DatasetWriteResult(sample_dir=sample_dir, status="skipped")

    (sample_dir / "spec_snapshot.toml").write_bytes(spec_path.read_bytes())
    _write_json(
        marker,
        {
            "peetsfea_version": PEETSFEA_VERSION,
            "project_name": project_name,
            "full_name": full_name,
            "seed": seed,
            "spec_hash": spec_hash,
            "spec_path": str(spec_path),
            "created_at_utc": _utc_now_iso(),
            "python_version": sys.version,
            "platform": platform.platform(),
        },
    )

    try:
        result = run_type1_from_path(spec_path, seed)
    except Exception as exc:
        _write_json(
            sample_dir / "run_error.json",
            {
                "status": "error",
                "stage": "run_type1_from_path",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        return Type1DatasetWriteResult(sample_dir=sample_dir, status="error")

    _write_json(sample_dir / "genes.json", {"sample": to_dict(result.sample)})
    _write_json(sample_dir / "geometry.json", to_dict(result.geometry))
    tx_coil_derived = derive_tx_coil_features(result.sample)
    _write_json(sample_dir / "derived.json", {"tx_coil": tx_coil_derived})

    # Optional-but-useful debug snapshot for fast iteration.
    # Keep it separate from derived.json so consumers can ignore it cheaply.
    try:
        first = next((inst for inst in result.sample.tx_coil.instances if inst.present), None)
        if first is not None:
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
            layered = layer_rect_spirals(
                masks,
                layer_mode_idx=layer_mode_idx_effective,
                radial_split_top_turn_fraction=first.radial_split_top_turn_fraction,
                radial_split_outer_is_top=first.radial_split_outer_is_top,
            )
            _write_json(
                sample_dir / "debug_tx_planar.json",
                {
                    "instance": {"name": first.name, "face": frame.name},
                    "masks": [to_dict(m) for m in masks],
                    "layered": [to_dict(l) for l in layered],
                    "derived": tx_coil_derived,
                },
            )
    except Exception:
        # Debug snapshot should never break dataset output.
        pass

    if build_aedt:
        maxwell_dir = sample_dir / "maxwell"
        maxwell_dir.mkdir(parents=True, exist_ok=True)
        project_path = maxwell_dir / "project.aedt"
        design_name = full_name
        cfg = maxwell_config or Maxwell3dConfig()
        try:
            apply_report = apply_parametric_geometry_plan(
                result.geometry,
                project_path=project_path,
                design_name=design_name,
                core_material=result.sample.materials_core,
                config=cfg,
            )
            _write_json(
                maxwell_dir / "results.json",
                {
                    "status": "success",
                    "project_path": str(project_path),
                    "design_name": design_name,
                    "config": to_dict(cfg),
                    "apply_report": apply_report,
                },
            )
        except Exception as exc:
            _write_json(
                maxwell_dir / "results.json",
                {
                    "status": "error",
                    "project_path": str(project_path),
                    "design_name": design_name,
                    "config": to_dict(cfg),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )

    return Type1DatasetWriteResult(sample_dir=sample_dir, status="ok")
