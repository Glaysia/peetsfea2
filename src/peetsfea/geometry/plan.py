from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BoxPlan:
    name: str
    center_mm: tuple[float, float, float]
    size_mm: tuple[float, float, float]
    material: str
    model: bool


@dataclass(frozen=True)
class OperationPlan:
    op: str  # "unite" | "subtract"
    targets: list[str]
    tools: list[str] = field(default_factory=list)
    keep_originals: bool = False


@dataclass(frozen=True)
class GeometryPlan:
    units_length: str
    boxes: list[BoxPlan]
    operations: list[OperationPlan] = field(default_factory=list)


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
    operations: list[OperationPlan] = field(default_factory=list)
