from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class RangeSpec:
    min: float
    max: float
    step: float


@dataclass(frozen=True)
class IntRangeSpec:
    min: int
    max: int
    step: int


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
class TxCoilInstanceSpec:
    name: str
    face: str
    present: IntRangeSpec


@dataclass(frozen=True)
class TxCoilSpec:
    schema: str
    type: str
    pattern: str

    # Manufacturing-ish constraints (gene ranges)
    min_trace_width_mm: RangeSpec
    min_trace_gap_mm: RangeSpec
    edge_clearance_mm: RangeSpec
    fill_scale: RangeSpec
    pitch_duty: RangeSpec

    # 2-layer distribution (gene ranges)
    layer_mode_idx: IntRangeSpec
    radial_split_top_turn_fraction: RangeSpec
    radial_split_outer_is_top: IntRangeSpec

    # Spiral / DD (gene ranges)
    max_spiral_count: int
    spiral_count: IntRangeSpec
    spiral_turns: tuple[IntRangeSpec, ...]
    spiral_direction_idx: tuple[IntRangeSpec, ...]
    spiral_start_edge_idx: tuple[IntRangeSpec, ...]
    dd_split_axis_idx: IntRangeSpec
    dd_gap_mm: RangeSpec
    dd_split_ratio: RangeSpec

    # Structural (face stack) (gene ranges)
    trace_layer_count: IntRangeSpec
    inner_plane_axis_idx: IntRangeSpec
    max_inner_pcb_count: int
    inner_pcb_count: IntRangeSpec
    inner_spacing_ratio_half: tuple[RangeSpec, ...]
    instances: tuple[TxCoilInstanceSpec, ...]


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
