from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect2D:
    u_min: float
    u_max: float
    v_min: float
    v_max: float

    @property
    def u_size(self) -> float:
        return self.u_max - self.u_min

    @property
    def v_size(self) -> float:
        return self.v_max - self.v_min

    @property
    def u_center(self) -> float:
        return (self.u_min + self.u_max) * 0.5

    @property
    def v_center(self) -> float:
        return (self.v_min + self.v_max) * 0.5


Point2D = tuple[float, float]


@dataclass(frozen=True)
class RectSpiralDerived:
    bounds: Rect2D
    pitch_mm: float
    trace_width_mm: float
    trace_gap_mm: float


@dataclass(frozen=True)
class RectSpiralMask2D:
    turns: int
    start_edge_idx: int
    direction_idx: int
    derived: RectSpiralDerived
    polyline: tuple[Point2D, ...]


@dataclass(frozen=True)
class DdSplit:
    axis_idx: int
    gap_mm: float
    ratio: float


def _shift_polyline(polyline: tuple[Point2D, ...], du: float, dv: float) -> tuple[Point2D, ...]:
    return tuple((u + du, v + dv) for u, v in polyline)


def derive_rect_spiral(
    *,
    u_size_mm: float,
    v_size_mm: float,
    turns: int,
    edge_clearance_mm: float,
    fill_scale: float,
    pitch_duty: float,
    min_trace_width_mm: float,
    min_trace_gap_mm: float,
) -> RectSpiralDerived:
    if turns <= 0:
        raise ValueError("turns must be > 0")
    if u_size_mm <= 0 or v_size_mm <= 0:
        raise ValueError("u_size_mm and v_size_mm must be > 0")
    if edge_clearance_mm < 0:
        raise ValueError("edge_clearance_mm must be >= 0")
    if not (0.0 < fill_scale <= 1.0):
        raise ValueError("fill_scale must be in (0, 1]")
    if pitch_duty <= 0:
        raise ValueError("pitch_duty must be > 0")
    if min_trace_width_mm <= 0 or min_trace_gap_mm < 0:
        raise ValueError("min_trace_width_mm must be > 0 and min_trace_gap_mm must be >= 0")

    usable_u = u_size_mm - 2.0 * edge_clearance_mm
    usable_v = v_size_mm - 2.0 * edge_clearance_mm
    span = min(usable_u, usable_v)
    if span <= 0:
        raise ValueError("Spiral usable area must be positive after edge_clearance")

    span_eff = span
    pitch = 0.0
    width = min_trace_width_mm
    for _ in range(8):
        if span_eff <= 0:
            raise ValueError("Spiral usable span must be positive")
        pitch = fill_scale * span_eff / (2.0 * float(turns) + pitch_duty)
        if pitch <= 0:
            raise ValueError("Derived pitch must be > 0")
        width = max(min_trace_width_mm, pitch_duty * pitch)
        span_eff = span - width

    gap = pitch - width
    if gap < min_trace_gap_mm:
        raise ValueError("Derived trace gap is below min_trace_gap_mm")

    u_min = -0.5 * u_size_mm + edge_clearance_mm + 0.5 * width
    u_max = 0.5 * u_size_mm - edge_clearance_mm - 0.5 * width
    v_min = -0.5 * v_size_mm + edge_clearance_mm + 0.5 * width
    v_max = 0.5 * v_size_mm - edge_clearance_mm - 0.5 * width
    bounds = Rect2D(u_min=u_min, u_max=u_max, v_min=v_min, v_max=v_max)
    if bounds.u_size <= 0 or bounds.v_size <= 0:
        raise ValueError("Spiral bounds must be positive after trace width margin")

    return RectSpiralDerived(bounds=bounds, pitch_mm=pitch, trace_width_mm=width, trace_gap_mm=gap)


def rect_spiral_polyline(
    *,
    bounds: Rect2D,
    turns: int,
    pitch_mm: float,
    start_edge_idx: int,
    direction_idx: int,
) -> tuple[Point2D, ...]:
    if turns <= 0:
        raise ValueError("turns must be > 0")
    if pitch_mm <= 0:
        raise ValueError("pitch_mm must be > 0")
    if start_edge_idx not in (0, 1, 2, 3):
        raise ValueError("start_edge_idx must be in {0,1,2,3}")
    if direction_idx not in (0, 1):
        raise ValueError("direction_idx must be 0(CW) or 1(CCW)")

    u_min = bounds.u_min
    u_max = bounds.u_max
    v_min = bounds.v_min
    v_max = bounds.v_max

    # Directions in (u, v): 0=+u(E), 1=+v(N), 2=-u(W), 3=-v(S)
    east, north, west, south = 0, 1, 2, 3

    is_ccw = direction_idx == 1

    if is_ccw:
        start_map = {
            3: ((u_min, v_min), east),  # -v (bottom)
            0: ((u_max, v_min), north),  # +u (right)
            2: ((u_max, v_max), west),  # +v (top)
            1: ((u_min, v_max), south),  # -u (left)
        }
        turn_delta = 1  # left turn
    else:
        start_map = {
            3: ((u_max, v_min), west),  # -v (bottom)
            0: ((u_max, v_max), south),  # +u (right)
            2: ((u_min, v_max), east),  # +v (top)
            1: ((u_min, v_min), north),  # -u (left)
        }
        turn_delta = -1  # right turn

    (u, v), direction = start_map[start_edge_idx]

    points: list[Point2D] = [(u, v)]

    left = u_min
    right = u_max
    bottom = v_min
    top = v_max

    def move_to_boundary(direction_: int, u0: float, v0: float) -> tuple[float, float]:
        if direction_ == east:
            return right, v0
        if direction_ == west:
            return left, v0
        if direction_ == north:
            return u0, top
        if direction_ == south:
            return u0, bottom
        raise RuntimeError("Invalid direction")

    def shrink_used_boundary(direction_: int, u0: float, v0: float) -> None:
        nonlocal left, right, bottom, top
        if direction_ in (east, west):
            if v0 == bottom:
                bottom += pitch_mm
            elif v0 == top:
                top -= pitch_mm
            else:
                raise RuntimeError("Spiral state error: expected v on top/bottom boundary")
        else:
            if u0 == left:
                left += pitch_mm
            elif u0 == right:
                right -= pitch_mm
            else:
                raise RuntimeError("Spiral state error: expected u on left/right boundary")

    for _ in range(turns):
        for _ in range(4):
            if left >= right or bottom >= top:
                raise ValueError("Spiral does not fit: bounds collapsed before completing requested turns")
            u_next, v_next = move_to_boundary(direction, u, v)
            if (u_next, v_next) != points[-1]:
                points.append((u_next, v_next))
            shrink_used_boundary(direction, u_next, v_next)
            direction = (direction + turn_delta) % 4
            u, v = u_next, v_next

    return tuple(points)


def split_dd_bounds(
    bounds: Rect2D,
    *,
    axis_idx: int,
    gap_mm: float,
    ratio: float,
) -> tuple[Rect2D, Rect2D]:
    if axis_idx not in (0, 1):
        raise ValueError("axis_idx must be 0(u split) or 1(v split)")
    if gap_mm < 0:
        raise ValueError("gap_mm must be >= 0")
    if not (0.0 < ratio < 1.0):
        raise ValueError("ratio must be in (0,1)")

    if axis_idx == 0:
        span = bounds.u_size
        if gap_mm >= span:
            raise ValueError("DD gap must be smaller than u span")
        available = span - gap_mm
        a_size = available * ratio
        b_size = available - a_size
        a = Rect2D(bounds.u_min, bounds.u_min + a_size, bounds.v_min, bounds.v_max)
        b = Rect2D(bounds.u_max - b_size, bounds.u_max, bounds.v_min, bounds.v_max)
        return a, b

    span = bounds.v_size
    if gap_mm >= span:
        raise ValueError("DD gap must be smaller than v span")
    available = span - gap_mm
    a_size = available * ratio
    b_size = available - a_size
    a = Rect2D(bounds.u_min, bounds.u_max, bounds.v_min, bounds.v_min + a_size)
    b = Rect2D(bounds.u_min, bounds.u_max, bounds.v_max - b_size, bounds.v_max)
    return a, b


def build_planar_rect_spiral_masks(
    *,
    face_u_size_mm: float,
    face_v_size_mm: float,
    spiral_count: int,
    turns: tuple[int, ...],
    direction_idx: tuple[int, ...],
    start_edge_idx: tuple[int, ...],
    edge_clearance_mm: float,
    fill_scale: float,
    pitch_duty: float,
    min_trace_width_mm: float,
    min_trace_gap_mm: float,
    dd: DdSplit | None = None,
) -> tuple[RectSpiralMask2D, ...]:
    if spiral_count not in (1, 2):
        raise ValueError("spiral_count must be 1 or 2")
    if spiral_count > len(turns) or spiral_count > len(direction_idx) or spiral_count > len(start_edge_idx):
        raise ValueError("Per-spiral arrays must include at least spiral_count entries")

    full = Rect2D(
        u_min=-0.5 * face_u_size_mm,
        u_max=0.5 * face_u_size_mm,
        v_min=-0.5 * face_v_size_mm,
        v_max=0.5 * face_v_size_mm,
    )

    if spiral_count == 1:
        derived = derive_rect_spiral(
            u_size_mm=full.u_size,
            v_size_mm=full.v_size,
            turns=turns[0],
            edge_clearance_mm=edge_clearance_mm,
            fill_scale=fill_scale,
            pitch_duty=pitch_duty,
            min_trace_width_mm=min_trace_width_mm,
            min_trace_gap_mm=min_trace_gap_mm,
        )
        poly = rect_spiral_polyline(
            bounds=derived.bounds,
            turns=turns[0],
            pitch_mm=derived.pitch_mm,
            start_edge_idx=start_edge_idx[0],
            direction_idx=direction_idx[0],
        )
        return (
            RectSpiralMask2D(
                turns=turns[0],
                start_edge_idx=start_edge_idx[0],
                direction_idx=direction_idx[0],
                derived=derived,
                polyline=poly,
            ),
        )

    if dd is None:
        raise ValueError("dd must be provided when spiral_count=2")

    a_bounds, b_bounds = split_dd_bounds(full, axis_idx=dd.axis_idx, gap_mm=dd.gap_mm, ratio=dd.ratio)
    masks: list[RectSpiralMask2D] = []
    for idx, region in enumerate((a_bounds, b_bounds)):
        derived = derive_rect_spiral(
            u_size_mm=region.u_size,
            v_size_mm=region.v_size,
            turns=turns[idx],
            edge_clearance_mm=edge_clearance_mm,
            fill_scale=fill_scale,
            pitch_duty=pitch_duty,
            min_trace_width_mm=min_trace_width_mm,
            min_trace_gap_mm=min_trace_gap_mm,
        )
        poly = rect_spiral_polyline(
            bounds=derived.bounds,
            turns=turns[idx],
            pitch_mm=derived.pitch_mm,
            start_edge_idx=start_edge_idx[idx],
            direction_idx=direction_idx[idx],
        )
        poly = _shift_polyline(poly, region.u_center, region.v_center)
        masks.append(
            RectSpiralMask2D(
                turns=turns[idx],
                start_edge_idx=start_edge_idx[idx],
                direction_idx=direction_idx[idx],
                derived=derived,
                polyline=poly,
            )
        )
    return (masks[0], masks[1])
