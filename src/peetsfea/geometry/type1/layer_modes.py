from __future__ import annotations

from dataclasses import dataclass

from peetsfea.geometry.type1.spiral_mask import Point2D, RectSpiralMask2D


@dataclass(frozen=True)
class Segment2D:
    a: Point2D
    b: Point2D
    width_mm: float


@dataclass(frozen=True)
class OverlapEstimate2D:
    top_area_est_mm2: float
    bottom_area_est_mm2: float
    overlap_area_est_mm2: float
    overlap_ratio_est: float
    grid_step_mm: float


@dataclass(frozen=True)
class LayeredSpiral2D:
    layer_mode_idx: int
    top_segments: tuple[Segment2D, ...]
    bottom_segments: tuple[Segment2D, ...]
    via_points: tuple[Point2D, ...]
    terminal_a: Point2D
    terminal_b: Point2D
    terminal_a_is_top: bool
    terminal_b_is_top: bool
    overlap_estimate: OverlapEstimate2D


@dataclass(frozen=True)
class _Rect:
    u_min: float
    u_max: float
    v_min: float
    v_max: float


def _segment_rect(seg: Segment2D) -> _Rect:
    (u1, v1) = seg.a
    (u2, v2) = seg.b
    half = seg.width_mm * 0.5
    if u1 == u2 and v1 == v2:
        return _Rect(u1 - half, u1 + half, v1 - half, v1 + half)
    if v1 == v2:
        u_min = min(u1, u2) - half
        u_max = max(u1, u2) + half
        return _Rect(u_min, u_max, v1 - half, v1 + half)
    if u1 == u2:
        v_min = min(v1, v2) - half
        v_max = max(v1, v2) + half
        return _Rect(u1 - half, u1 + half, v_min, v_max)
    raise ValueError("Only axis-aligned segments are supported")


def _estimate_overlap(
    top: tuple[Segment2D, ...],
    bottom: tuple[Segment2D, ...],
    *,
    default_grid_step_mm: float = 2.0,
    max_points: int = 120_000,
) -> OverlapEstimate2D:
    top_rects = [_segment_rect(s) for s in top]
    bottom_rects = [_segment_rect(s) for s in bottom]

    rects = top_rects + bottom_rects
    if not rects:
        return OverlapEstimate2D(
            top_area_est_mm2=0.0,
            bottom_area_est_mm2=0.0,
            overlap_area_est_mm2=0.0,
            overlap_ratio_est=0.0,
            grid_step_mm=default_grid_step_mm,
        )

    u_min = min(r.u_min for r in rects)
    u_max = max(r.u_max for r in rects)
    v_min = min(r.v_min for r in rects)
    v_max = max(r.v_max for r in rects)
    span_u = u_max - u_min
    span_v = v_max - v_min
    if span_u <= 0 or span_v <= 0:
        return OverlapEstimate2D(
            top_area_est_mm2=0.0,
            bottom_area_est_mm2=0.0,
            overlap_area_est_mm2=0.0,
            overlap_ratio_est=0.0,
            grid_step_mm=default_grid_step_mm,
        )

    grid = max(default_grid_step_mm, (span_u * span_v / float(max_points)) ** 0.5)
    nx = max(1, int(span_u / grid) + 1)
    ny = max(1, int(span_v / grid) + 1)
    grid = max(grid, span_u / float(nx), span_v / float(ny))

    def contains(rects_: list[_Rect], u: float, v: float) -> bool:
        for r in rects_:
            if r.u_min <= u <= r.u_max and r.v_min <= v <= r.v_max:
                return True
        return False

    top_count = 0
    bottom_count = 0
    overlap_count = 0

    for ix in range(nx):
        u = u_min + (ix + 0.5) * grid
        for iy in range(ny):
            v = v_min + (iy + 0.5) * grid
            in_top = contains(top_rects, u, v)
            in_bottom = contains(bottom_rects, u, v)
            if in_top:
                top_count += 1
            if in_bottom:
                bottom_count += 1
            if in_top and in_bottom:
                overlap_count += 1

    cell_area = grid * grid
    top_area = float(top_count) * cell_area
    bottom_area = float(bottom_count) * cell_area
    overlap_area = float(overlap_count) * cell_area
    denom = min(top_area, bottom_area)
    overlap_ratio = (overlap_area / denom) if denom > 0 else 0.0

    return OverlapEstimate2D(
        top_area_est_mm2=top_area,
        bottom_area_est_mm2=bottom_area,
        overlap_area_est_mm2=overlap_area,
        overlap_ratio_est=overlap_ratio,
        grid_step_mm=grid,
    )


def layer_rect_spiral(
    mask: RectSpiralMask2D,
    *,
    layer_mode_idx: int,
    radial_split_top_turn_fraction: float,
    radial_split_outer_is_top: bool,
) -> LayeredSpiral2D:
    if layer_mode_idx not in (0, 1, 2):
        raise ValueError("layer_mode_idx must be 0(single_layer_top), 1(radial_split), or 2(alternate_turns)")
    if not (0.0 <= radial_split_top_turn_fraction <= 1.0):
        raise ValueError("radial_split_top_turn_fraction must be within [0,1]")

    turns = mask.turns
    if turns <= 0:
        raise ValueError("mask.turns must be > 0")
    if len(mask.polyline) != 1 + 4 * turns:
        raise ValueError("mask.polyline must have length (1 + 4*turns)")

    # True => top, False => bottom
    assign_top: list[bool]
    if layer_mode_idx == 0:
        assign_top = [True] * turns
    elif layer_mode_idx == 2:
        assign_top = [(t % 2) == 0 for t in range(turns)]
    else:
        top_turns = int(round(float(turns) * radial_split_top_turn_fraction))
        top_turns = max(0, min(turns, top_turns))
        if top_turns == 0:
            top_turns = 1
        if radial_split_outer_is_top:
            assign_top = [t < top_turns for t in range(turns)]
        else:
            assign_top = [t >= (turns - top_turns) for t in range(turns)]

    width = mask.derived.trace_width_mm
    top_segments: list[Segment2D] = []
    bottom_segments: list[Segment2D] = []
    via_points: list[Point2D] = []

    for seg_idx, (a, b) in enumerate(zip(mask.polyline[:-1], mask.polyline[1:])):
        turn_idx = seg_idx // 4
        segment = Segment2D(a=a, b=b, width_mm=width)
        if assign_top[turn_idx]:
            top_segments.append(segment)
        else:
            bottom_segments.append(segment)

    for t in range(turns - 1):
        if assign_top[t] != assign_top[t + 1]:
            via_points.append(mask.polyline[4 * (t + 1)])

    terminal_a = mask.polyline[0]
    terminal_b = mask.polyline[-1]
    terminal_a_is_top = assign_top[0]
    terminal_b_is_top = assign_top[-1]

    overlap_estimate = _estimate_overlap(tuple(top_segments), tuple(bottom_segments))

    return LayeredSpiral2D(
        layer_mode_idx=layer_mode_idx,
        top_segments=tuple(top_segments),
        bottom_segments=tuple(bottom_segments),
        via_points=tuple(via_points),
        terminal_a=terminal_a,
        terminal_b=terminal_b,
        terminal_a_is_top=terminal_a_is_top,
        terminal_b_is_top=terminal_b_is_top,
        overlap_estimate=overlap_estimate,
    )


def layer_rect_spirals(
    masks: tuple[RectSpiralMask2D, ...],
    *,
    layer_mode_idx: int,
    radial_split_top_turn_fraction: float,
    radial_split_outer_is_top: bool,
) -> tuple[LayeredSpiral2D, ...]:
    return tuple(
        layer_rect_spiral(
            mask,
            layer_mode_idx=layer_mode_idx,
            radial_split_top_turn_fraction=radial_split_top_turn_fraction,
            radial_split_outer_is_top=radial_split_outer_is_top,
        )
        for mask in masks
    )
