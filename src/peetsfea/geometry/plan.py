from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoxPlan:
    name: str
    center_mm: tuple[float, float, float]
    size_mm: tuple[float, float, float]
    material: str
    model: bool


@dataclass(frozen=True)
class GeometryPlan:
    units_length: str
    boxes: list[BoxPlan]


@dataclass(frozen=True)
class DesignVariable:
    name: str
    value: float | str
    units: str | None = None
    is_expression: bool = False


@dataclass(frozen=True)
class ParametricBoxPlan:
    name: str
    corner_expr: tuple[str, str, str]
    size_expr: tuple[str, str, str]
    material: str
    model: bool


@dataclass(frozen=True)
class ParametricGeometryPlan:
    units_length: str
    variables: list[DesignVariable]
    boxes: list[ParametricBoxPlan]
