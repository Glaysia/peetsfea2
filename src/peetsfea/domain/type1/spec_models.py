from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class RangeSpec:
    min: float
    max: float
    step: float


@dataclass(frozen=True)
class UnitsSpec:
    length: str


@dataclass(frozen=True)
class CoordinateSystemSpec:
    wall_plane_x_mm: RangeSpec
    floor_plane_z_mm: RangeSpec


@dataclass(frozen=True)
class ConstraintsSpec:
    core_core_gap_mm: RangeSpec
    rx_total_thickness_mm_max: RangeSpec
    tx_gap_from_tv_bottom_mm: RangeSpec


@dataclass(frozen=True)
class LayoutSpec:
    right_edge_y_mm: RangeSpec


@dataclass(frozen=True)
class PositionSpec:
    center_x_mm: Optional[RangeSpec]
    center_y_mm: Optional[RangeSpec]
    center_z_mm: Optional[RangeSpec]


@dataclass(frozen=True)
class MaterialCoreSpec:
    mu_r: RangeSpec
    epsilon_r: RangeSpec
    conductivity_s_per_m: RangeSpec


@dataclass(frozen=True)
class MaterialsSpec:
    core: MaterialCoreSpec


@dataclass(frozen=True)
class ModuleSpec:
    present: bool
    model: bool
    outer_w_mm: RangeSpec
    outer_h_mm: RangeSpec
    thickness_mm: RangeSpec
    offset_from_coil_mm: RangeSpec


@dataclass(frozen=True)
class PcbSpec:
    layer_count: int
    total_thickness_mm: float
    dielectric_material: str
    dielectric_epsilon_r: float
    stackup: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class TxCoilOuterFacesSpec:
    pos_x: bool
    neg_x: bool
    pos_y: bool
    neg_y: bool
    pos_z: bool
    neg_z: bool


@dataclass(frozen=True)
class TxCoilSpec:
    type: str
    trace_layer_count: int
    inner_plane_axis: str
    max_inner_pcb_count: int
    inner_pcb_count: int
    inner_spacing_ratio: tuple[float, ...]
    outer_faces: TxCoilOuterFacesSpec


@dataclass(frozen=True)
class TxSpec:
    module: ModuleSpec
    position: PositionSpec
    pcb: PcbSpec
    coil: TxCoilSpec


@dataclass(frozen=True)
class RxStackSpec:
    total_thickness_mm: RangeSpec


@dataclass(frozen=True)
class RxSpec:
    module: ModuleSpec
    position: PositionSpec
    stack: RxStackSpec


@dataclass(frozen=True)
class TvSpec:
    present: bool
    model: bool
    width_mm: RangeSpec
    height_mm: RangeSpec
    thickness_mm: RangeSpec
    position: PositionSpec


@dataclass(frozen=True)
class WallSpec:
    present: bool
    model: bool
    thickness_mm: RangeSpec
    size_y_mm: RangeSpec
    size_z_mm: RangeSpec
    position: PositionSpec


@dataclass(frozen=True)
class FloorSpec:
    present: bool
    model: bool
    thickness_mm: RangeSpec
    size_x_mm: RangeSpec
    size_y_mm: RangeSpec
    position: PositionSpec


@dataclass(frozen=True)
class Type1Spec:
    units: UnitsSpec
    coordinate_system: CoordinateSystemSpec
    constraints: ConstraintsSpec
    layout: LayoutSpec
    materials: MaterialsSpec
    tx: TxSpec
    rx: RxSpec
    tv: TvSpec
    wall: WallSpec
    floor: FloorSpec
