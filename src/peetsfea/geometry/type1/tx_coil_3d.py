from __future__ import annotations

from dataclasses import dataclass

from peetsfea.domain.type1.sampled_models import TxCoilInstanceSample, Type1Sample
from peetsfea.geometry.plan import OperationPlan, ParametricBoxPlan
from peetsfea.geometry.type1.layer_modes import LayeredSpiral2D, Segment2D, layer_rect_spirals
from peetsfea.geometry.type1.pcb_faces import (
    ASPECT_MIN_RATIO,
    COPPER_THICKNESS_MM,
    IN_PLANE_SCALE,
    INWARD_OFFSET_FACTOR,
    PCB_THICKNESS_MM,
)
from peetsfea.geometry.type1.spiral_mask import DdSplit, RectSpiralMask2D, build_planar_rect_spiral_masks


def _num(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _lit(value: float, units: str) -> str:
    return f"{_num(value)}{units}"


@dataclass(frozen=True)
class TxFaceFrame:
    name: str
    normal_axis: int
    normal_sign: int
    u_axis: int
    v_axis: int
    center_xyz_mm: tuple[float, float, float]
    face_u_size_mm: float
    face_v_size_mm: float


def _enabled_face_names(sample: Type1Sample) -> list[str]:
    faces = sample.tx_coil.outer_faces
    if not sample.tx_module.present:
        return []

    tx_thk = sample.tx_module.thickness_mm
    tx_w = sample.tx_module.outer_w_mm
    tx_h = sample.tx_module.outer_h_mm

    def aspect_ok(dim_a: float, dim_b: float) -> bool:
        if dim_a <= 0 or dim_b <= 0:
            return False
        small = min(dim_a, dim_b)
        large = max(dim_a, dim_b)
        return (small / large) >= ASPECT_MIN_RATIO

    enabled = {
        "pos_x": faces.pos_x and aspect_ok(tx_w, tx_h),
        "neg_x": faces.neg_x and aspect_ok(tx_w, tx_h),
        "pos_y": faces.pos_y and aspect_ok(tx_thk, tx_h),
        "neg_y": faces.neg_y and aspect_ok(tx_thk, tx_h),
        "pos_z": faces.pos_z and aspect_ok(tx_thk, tx_w),
        "neg_z": faces.neg_z and aspect_ok(tx_thk, tx_w),
    }

    order = ["neg_x", "pos_x", "pos_y", "neg_y", "pos_z", "neg_z"]
    return [name for name in order if enabled[name]]


def _select_face_name(sample: Type1Sample) -> str | None:
    names = _enabled_face_names(sample)
    return names[0] if names else None


def tx_coil_face_frame_for_name(sample: Type1Sample, face_name: str) -> TxFaceFrame:
    pcb_thk = sample.tx_pcb.total_thickness_mm or PCB_THICKNESS_MM
    inward_offset = INWARD_OFFSET_FACTOR * 0.5 * pcb_thk

    tx_thk = sample.tx_module.thickness_mm
    tx_w = sample.tx_module.outer_w_mm
    tx_h = sample.tx_module.outer_h_mm

    tx_center_x = sample.wall_plane_x_mm + 0.5 * tx_thk
    tx_center_y = sample.tx_position.center_y_mm
    tx_center_z = sample.tx_position.center_z_mm
    tx_corner_y = tx_center_y - 0.5 * tx_w
    tx_corner_z = tx_center_z - 0.5 * tx_h

    if face_name == "pos_x":
        return TxFaceFrame(
            name="pos_x",
            normal_axis=0,
            normal_sign=1,
            u_axis=1,
            v_axis=2,
            center_xyz_mm=(sample.wall_plane_x_mm + tx_thk - inward_offset, tx_center_y, tx_center_z),
            face_u_size_mm=tx_w * IN_PLANE_SCALE,
            face_v_size_mm=tx_h * IN_PLANE_SCALE,
        )
    if face_name == "neg_x":
        return TxFaceFrame(
            name="neg_x",
            normal_axis=0,
            normal_sign=-1,
            u_axis=1,
            v_axis=2,
            center_xyz_mm=(sample.wall_plane_x_mm + inward_offset, tx_center_y, tx_center_z),
            face_u_size_mm=tx_w * IN_PLANE_SCALE,
            face_v_size_mm=tx_h * IN_PLANE_SCALE,
        )
    if face_name == "pos_y":
        return TxFaceFrame(
            name="pos_y",
            normal_axis=1,
            normal_sign=1,
            u_axis=0,
            v_axis=2,
            center_xyz_mm=(tx_center_x, tx_corner_y + tx_w - inward_offset, tx_center_z),
            face_u_size_mm=tx_thk * IN_PLANE_SCALE,
            face_v_size_mm=tx_h * IN_PLANE_SCALE,
        )
    if face_name == "neg_y":
        return TxFaceFrame(
            name="neg_y",
            normal_axis=1,
            normal_sign=-1,
            u_axis=0,
            v_axis=2,
            center_xyz_mm=(tx_center_x, tx_corner_y + inward_offset, tx_center_z),
            face_u_size_mm=tx_thk * IN_PLANE_SCALE,
            face_v_size_mm=tx_h * IN_PLANE_SCALE,
        )
    if face_name == "pos_z":
        return TxFaceFrame(
            name="pos_z",
            normal_axis=2,
            normal_sign=1,
            u_axis=0,
            v_axis=1,
            center_xyz_mm=(tx_center_x, tx_center_y, tx_corner_z + tx_h - inward_offset),
            face_u_size_mm=tx_thk * IN_PLANE_SCALE,
            face_v_size_mm=tx_w * IN_PLANE_SCALE,
        )
    if face_name == "neg_z":
        return TxFaceFrame(
            name="neg_z",
            normal_axis=2,
            normal_sign=-1,
            u_axis=0,
            v_axis=1,
            center_xyz_mm=(tx_center_x, tx_center_y, tx_corner_z + inward_offset),
            face_u_size_mm=tx_thk * IN_PLANE_SCALE,
            face_v_size_mm=tx_w * IN_PLANE_SCALE,
        )

    raise RuntimeError(f"Unhandled face_name: {face_name!r}")


def tx_coil_face_frame(sample: Type1Sample) -> TxFaceFrame | None:
    face_name = _select_face_name(sample)
    if face_name is None:
        return None
    return tx_coil_face_frame_for_name(sample, face_name)


def tx_coil_face_frames(sample: Type1Sample) -> list[TxFaceFrame]:
    return [tx_coil_face_frame_for_name(sample, name) for name in _enabled_face_names(sample)]


def _segment_rect(seg: Segment2D) -> tuple[float, float, float, float]:
    (u1, v1) = seg.a
    (u2, v2) = seg.b
    half = seg.width_mm * 0.5
    if u1 == u2:
        u_min = u1 - half
        u_max = u1 + half
        v_min = min(v1, v2) - half
        v_max = max(v1, v2) + half
        return u_min, u_max, v_min, v_max
    if v1 == v2:
        u_min = min(u1, u2) - half
        u_max = max(u1, u2) + half
        v_min = v1 - half
        v_max = v1 + half
        return u_min, u_max, v_min, v_max
    raise ValueError("Only axis-aligned segments are supported")


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _terminal_out_dir_from_mask(mask: RectSpiralMask2D, which: str) -> tuple[str, int]:
    if which not in ("a", "b"):
        raise ValueError("which must be 'a' or 'b'")
    if len(mask.polyline) < 2:
        raise ValueError("mask.polyline must contain at least 2 points")

    if which == "a":
        (u0, v0) = mask.polyline[0]
        (u1, v1) = mask.polyline[1]
        du = u1 - u0
        dv = v1 - v0
        if du != 0:
            return "u", -_sign(du)
        return "v", -_sign(dv)

    (u0, v0) = mask.polyline[-2]
    (u1, v1) = mask.polyline[-1]
    du = u1 - u0
    dv = v1 - v0
    if du != 0:
        return "u", _sign(du)
    return "v", _sign(dv)


def build_tx_planar_trace_coil(
    sample: Type1Sample,
    coil: TxCoilInstanceSample,
    *,
    name_prefix: str = "TX_Coil",
    frame: TxFaceFrame | None = None,
) -> tuple[list[ParametricBoxPlan], list[OperationPlan]]:
    if not sample.tx_module.present or not coil.present:
        return [], []

    units = sample.units_length
    pcb_thk = sample.tx_pcb.total_thickness_mm or PCB_THICKNESS_MM
    copper_thk = COPPER_THICKNESS_MM
    frame = frame or tx_coil_face_frame_for_name(sample, coil.face)
    if frame is None:
        return [], []

    dd = None
    if coil.spiral_count == 2:
        dd = DdSplit(axis_idx=coil.dd_split_axis_idx, gap_mm=coil.dd_gap_mm, ratio=coil.dd_split_ratio)

    masks = build_planar_rect_spiral_masks(
        face_u_size_mm=frame.face_u_size_mm,
        face_v_size_mm=frame.face_v_size_mm,
        spiral_count=coil.spiral_count,
        turns=coil.spiral_turns,
        direction_idx=coil.spiral_direction_idx,
        start_edge_idx=coil.spiral_start_edge_idx,
        edge_clearance_mm=coil.edge_clearance_mm,
        fill_scale=coil.fill_scale,
        pitch_duty=coil.pitch_duty,
        min_trace_width_mm=coil.min_trace_width_mm,
        min_trace_gap_mm=coil.min_trace_gap_mm,
        dd=dd,
    )

    effective_trace_layers = min(sample.tx_pcb.layer_count, coil.trace_layer_count)
    layer_mode_idx = coil.layer_mode_idx if effective_trace_layers >= 2 else 0

    layered = layer_rect_spirals(
        masks,
        layer_mode_idx=layer_mode_idx,
        radial_split_top_turn_fraction=coil.radial_split_top_turn_fraction,
        radial_split_outer_is_top=coil.radial_split_outer_is_top,
    )

    face_center_xyz = list(frame.center_xyz_mm)
    face_center_n = face_center_xyz[frame.normal_axis]
    outer_edge = face_center_n + frame.normal_sign * 0.5 * pcb_thk

    top_cu_center_n = outer_edge - frame.normal_sign * 0.5 * copper_thk
    bot_cu_center_n = outer_edge - frame.normal_sign * (pcb_thk - 0.5 * copper_thk)

    boxes: list[ParametricBoxPlan] = []
    unite_targets: list[str] = []

    def add_box(
        name: str,
        *,
        corner_xyz_mm: tuple[float, float, float],
        size_xyz_mm: tuple[float, float, float],
    ) -> None:
        if any(s <= 0 for s in size_xyz_mm):
            return
        boxes.append(
            ParametricBoxPlan(
                name=name,
                corner_expr=(
                    _lit(corner_xyz_mm[0], units),
                    _lit(corner_xyz_mm[1], units),
                    _lit(corner_xyz_mm[2], units),
                ),
                size_expr=(
                    _lit(size_xyz_mm[0], units),
                    _lit(size_xyz_mm[1], units),
                    _lit(size_xyz_mm[2], units),
                ),
                material="copper",
                model=True,
            )
        )
        unite_targets.append(name)

    def add_segment(
        seg: Segment2D,
        *,
        n_center_mm: float,
        name: str,
    ) -> None:
        u_min, u_max, v_min, v_max = _segment_rect(seg)
        corner = [0.0, 0.0, 0.0]
        size = [0.0, 0.0, 0.0]

        corner[frame.u_axis] = frame.center_xyz_mm[frame.u_axis] + u_min
        corner[frame.v_axis] = frame.center_xyz_mm[frame.v_axis] + v_min
        corner[frame.normal_axis] = n_center_mm - 0.5 * copper_thk

        size[frame.u_axis] = u_max - u_min
        size[frame.v_axis] = v_max - v_min
        size[frame.normal_axis] = copper_thk

        add_box(name, corner_xyz_mm=(corner[0], corner[1], corner[2]), size_xyz_mm=(size[0], size[1], size[2]))

    def add_via(point_uv: tuple[float, float], *, name: str, size_mm: float) -> None:
        (u, v) = point_uv
        half = 0.5 * size_mm
        corner = [0.0, 0.0, 0.0]
        size = [0.0, 0.0, 0.0]

        corner[frame.u_axis] = frame.center_xyz_mm[frame.u_axis] + (u - half)
        corner[frame.v_axis] = frame.center_xyz_mm[frame.v_axis] + (v - half)

        inner_edge = outer_edge - frame.normal_sign * pcb_thk
        n_min = min(outer_edge, inner_edge)
        n_max = max(outer_edge, inner_edge)
        corner[frame.normal_axis] = n_min
        size[frame.normal_axis] = n_max - n_min

        size[frame.u_axis] = size_mm
        size[frame.v_axis] = size_mm

        add_box(name, corner_xyz_mm=(corner[0], corner[1], corner[2]), size_xyz_mm=(size[0], size[1], size[2]))

    def ensure_on_top(
        point_uv: tuple[float, float],
        *,
        is_top: bool,
        name: str,
        size_mm: float,
    ) -> None:
        if effective_trace_layers < 2 or is_top:
            return
        add_via(point_uv, name=name, size_mm=size_mm)

    seg_i = 0
    via_i = 0

    for idx, (mask, lay) in enumerate(zip(masks, layered)):
        for seg in lay.top_segments:
            add_segment(seg, n_center_mm=top_cu_center_n, name=f"{name_prefix}_Top_{idx}_{seg_i:05d}")
            seg_i += 1
        if effective_trace_layers >= 2:
            for seg in lay.bottom_segments:
                add_segment(seg, n_center_mm=bot_cu_center_n, name=f"{name_prefix}_Bot_{idx}_{seg_i:05d}")
                seg_i += 1

            via_size = mask.derived.trace_width_mm
            for p in lay.via_points:
                add_via(p, name=f"{name_prefix}_Via_{idx}_{via_i:05d}", size_mm=via_size)
                via_i += 1

    bridge_width = min(m.derived.trace_width_mm for m in masks)

    def add_terminal_tab(
        point_uv: tuple[float, float],
        *,
        out_axis: str,
        out_sign: int,
        name: str,
        trace_width_mm: float,
    ) -> None:
        (u, v) = point_uv
        tab_len = max(3.0 * trace_width_mm, 1.0)
        tab_wid = max(3.0 * trace_width_mm, 1.0)
        overlap = 0.5 * trace_width_mm

        if out_axis == "u":
            if out_sign > 0:
                u_min = u - overlap
                u_max = u + tab_len
            else:
                u_min = u - tab_len
                u_max = u + overlap
            v_min = v - 0.5 * tab_wid
            v_max = v + 0.5 * tab_wid
        else:
            u_min = u - 0.5 * tab_wid
            u_max = u + 0.5 * tab_wid
            if out_sign > 0:
                v_min = v - overlap
                v_max = v + tab_len
            else:
                v_min = v - tab_len
                v_max = v + overlap

        corner = [0.0, 0.0, 0.0]
        size = [0.0, 0.0, 0.0]

        corner[frame.u_axis] = frame.center_xyz_mm[frame.u_axis] + u_min
        corner[frame.v_axis] = frame.center_xyz_mm[frame.v_axis] + v_min
        corner[frame.normal_axis] = top_cu_center_n - 0.5 * copper_thk
        size[frame.u_axis] = u_max - u_min
        size[frame.v_axis] = v_max - v_min
        size[frame.normal_axis] = copper_thk

        add_box(name, corner_xyz_mm=(corner[0], corner[1], corner[2]), size_xyz_mm=(size[0], size[1], size[2]))

    # Terminal A: spiral 0 start
    mask_a = masks[0]
    lay_a = layered[0]
    out_axis_a, out_sign_a = _terminal_out_dir_from_mask(mask_a, "a")
    add_terminal_tab(
        lay_a.terminal_a,
        out_axis=out_axis_a,
        out_sign=out_sign_a,
        name=name_prefix,
        trace_width_mm=mask_a.derived.trace_width_mm,
    )
    ensure_on_top(
        lay_a.terminal_a,
        is_top=lay_a.terminal_a_is_top,
        name=f"{name_prefix}_Terminal_A_Via",
        size_mm=bridge_width,
    )

    # Terminal B: last spiral end
    mask_b = masks[-1]
    lay_b = layered[-1]
    out_axis_b, out_sign_b = _terminal_out_dir_from_mask(mask_b, "b")
    add_terminal_tab(
        lay_b.terminal_b,
        out_axis=out_axis_b,
        out_sign=out_sign_b,
        name=f"{name_prefix}_Terminal_B_Tab",
        trace_width_mm=mask_b.derived.trace_width_mm,
    )
    ensure_on_top(
        lay_b.terminal_b,
        is_top=lay_b.terminal_b_is_top,
        name=f"{name_prefix}_Terminal_B_Via",
        size_mm=bridge_width,
    )

    if coil.spiral_count == 2:
        # Series connect: spiral0(B) -> spiral1(A) on top layer
        p0 = layered[0].terminal_b
        p1 = layered[1].terminal_a

        ensure_on_top(
            p0,
            is_top=layered[0].terminal_b_is_top,
            name=f"{name_prefix}_DD_Conn_Via0",
            size_mm=bridge_width,
        )
        ensure_on_top(
            p1,
            is_top=layered[1].terminal_a_is_top,
            name=f"{name_prefix}_DD_Conn_Via1",
            size_mm=bridge_width,
        )

        if p0[0] == p1[0] or p0[1] == p1[1]:
            add_segment(
                Segment2D(a=p0, b=p1, width_mm=bridge_width),
                n_center_mm=top_cu_center_n,
                name=f"{name_prefix}_Bridge_00000",
            )
        else:
            mid = (p1[0], p0[1])
            add_segment(
                Segment2D(a=p0, b=mid, width_mm=bridge_width),
                n_center_mm=top_cu_center_n,
                name=f"{name_prefix}_Bridge_00000",
            )
            add_segment(
                Segment2D(a=mid, b=p1, width_mm=bridge_width),
                n_center_mm=top_cu_center_n,
                name=f"{name_prefix}_Bridge_00001",
            )

    if not unite_targets:
        return [], []

    # Ensure `unite` keeps a stable final name (first object in list).
    # Move the anchor tab (name_prefix) to the front.
    if name_prefix in unite_targets:
        unite_targets = [name_prefix] + [n for n in unite_targets if n != name_prefix]

    operations = [OperationPlan(op="unite", targets=unite_targets)]
    return boxes, operations


def build_tx_planar_trace_coils(
    sample: Type1Sample,
    *,
    name_prefix: str = "TX_Coil",
) -> tuple[list[ParametricBoxPlan], list[OperationPlan]]:
    present_instances = [inst for inst in sample.tx_coil.instances if inst.present]
    if not present_instances:
        return [], []

    boxes: list[ParametricBoxPlan] = []
    operations: list[OperationPlan] = []
    for idx, inst in enumerate(present_instances):
        frame = tx_coil_face_frame_for_name(sample, inst.face)
        prefix = name_prefix if idx == 0 else f"{name_prefix}_{inst.name}"
        try:
            coil_boxes, coil_ops = build_tx_planar_trace_coil(sample, inst, name_prefix=prefix, frame=frame)
        except ValueError:
            if idx == 0:
                raise
            continue
        boxes.extend(coil_boxes)
        operations.extend(coil_ops)

    return boxes, operations
