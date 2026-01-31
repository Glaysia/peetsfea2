from __future__ import annotations

from dataclasses import dataclass

from peetsfea.geometry.type1.layer_modes import Segment2D


PointKey = tuple[float, float]


def _key(point: tuple[float, float], *, ndigits: int = 6) -> PointKey:
    return (round(point[0], ndigits), round(point[1], ndigits))


@dataclass(frozen=True)
class Rect2D:
    u_min: float
    u_max: float
    v_min: float
    v_max: float


def _segment_rect(seg: Segment2D) -> Rect2D:
    (u1, v1) = seg.a
    (u2, v2) = seg.b
    half = seg.width_mm * 0.5

    if u1 == u2 and v1 == v2:
        return Rect2D(u1 - half, u1 + half, v1 - half, v1 + half)

    if v1 == v2:
        u_min = min(u1, u2) - half
        u_max = max(u1, u2) + half
        return Rect2D(u_min, u_max, v1 - half, v1 + half)

    if u1 == u2:
        v_min = min(v1, v2) - half
        v_max = max(v1, v2) + half
        return Rect2D(u1 - half, u1 + half, v_min, v_max)

    raise ValueError("Only axis-aligned segments are supported")


def _rects_intersect(a: Rect2D, b: Rect2D) -> bool:
    return not (
        a.u_max < b.u_min
        or b.u_max < a.u_min
        or a.v_max < b.v_min
        or b.v_max < a.v_min
    )


@dataclass(frozen=True)
class SelfContactReport2D:
    detected: bool
    pair_count: int
    example_pairs: tuple[tuple[int, int], ...]


def detect_self_contact(
    segments: tuple[Segment2D, ...],
    *,
    ndigits: int = 6,
    max_pairs: int = 30,
) -> SelfContactReport2D:
    if not segments:
        return SelfContactReport2D(detected=False, pair_count=0, example_pairs=())

    rects = [_segment_rect(seg) for seg in segments]
    endpoints = [({_key(seg.a, ndigits=ndigits), _key(seg.b, ndigits=ndigits)}) for seg in segments]

    pairs: list[tuple[int, int]] = []
    count = 0
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            if endpoints[i].intersection(endpoints[j]):
                continue
            if _rects_intersect(rects[i], rects[j]):
                count += 1
                if len(pairs) < max_pairs:
                    pairs.append((i, j))

    return SelfContactReport2D(detected=(count > 0), pair_count=count, example_pairs=tuple(pairs))

