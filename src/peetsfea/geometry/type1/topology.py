from __future__ import annotations

from dataclasses import dataclass

from peetsfea.geometry.type1.layer_modes import Segment2D


PointKey = tuple[float, float]


def _key(point: tuple[float, float], *, ndigits: int = 6) -> PointKey:
    return (round(point[0], ndigits), round(point[1], ndigits))


@dataclass(frozen=True)
class TopologyReport2D:
    component_count: int
    endpoints_count: int
    has_branch: bool


def topology_from_segments(
    segments: tuple[Segment2D, ...],
    *,
    ndigits: int = 6,
) -> TopologyReport2D:
    adj: dict[PointKey, set[PointKey]] = {}

    def add_edge(a: tuple[float, float], b: tuple[float, float]) -> None:
        ka = _key(a, ndigits=ndigits)
        kb = _key(b, ndigits=ndigits)
        if ka == kb:
            return
        adj.setdefault(ka, set()).add(kb)
        adj.setdefault(kb, set()).add(ka)

    for seg in segments:
        add_edge(seg.a, seg.b)

    if not adj:
        return TopologyReport2D(component_count=0, endpoints_count=0, has_branch=False)

    visited: set[PointKey] = set()
    component_count = 0

    for node in adj:
        if node in visited:
            continue
        component_count += 1
        stack = [node]
        visited.add(node)
        while stack:
            cur = stack.pop()
            for nxt in adj.get(cur, ()):
                if nxt in visited:
                    continue
                visited.add(nxt)
                stack.append(nxt)

    degrees = {node: len(neigh) for node, neigh in adj.items()}
    endpoints_count = sum(1 for d in degrees.values() if d == 1)
    has_branch = any(d > 2 for d in degrees.values())

    return TopologyReport2D(
        component_count=component_count,
        endpoints_count=endpoints_count,
        has_branch=has_branch,
    )

