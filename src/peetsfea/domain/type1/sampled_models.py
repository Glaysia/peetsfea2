from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class MaterialSample:
    mu_r: float
    epsilon_r: float
    conductivity_s_per_m: float


@dataclass(frozen=True)
class ModuleSample:
    present: bool
    model: bool
    outer_w_mm: float
    outer_h_mm: float
    thickness_mm: float
    offset_from_coil_mm: float


@dataclass(frozen=True)
class PcbSample:
    layer_count: int
    total_thickness_mm: float
    dielectric_material: str
    dielectric_epsilon_r: float
    stackup: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class TxCoilOuterFacesSample:
    pos_x: bool
    neg_x: bool
    pos_y: bool
    neg_y: bool
    pos_z: bool
    neg_z: bool


@dataclass(frozen=True)
class TxCoilInstanceSample:
    name: str
    face: str
    present: bool

    min_trace_width_mm: float
    min_trace_gap_mm: float
    edge_clearance_mm: float
    fill_scale: float
    pitch_duty: float

    layer_mode_idx: int
    radial_split_top_turn_fraction: float
    radial_split_outer_is_top: bool

    spiral_count: int
    spiral_turns: tuple[int, ...]
    spiral_direction_idx: tuple[int, ...]
    spiral_start_edge_idx: tuple[int, ...]
    dd_split_axis_idx: int
    dd_gap_mm: float
    dd_split_ratio: float

    trace_layer_count: int
    inner_plane_axis_idx: int
    inner_plane_axis: str
    inner_pcb_count: int
    inner_spacing_ratio_half: tuple[float, ...]
    inner_spacing_ratio: tuple[float, ...]


@dataclass(frozen=True)
class TxCoilSample:
    schema: str
    type: str
    pattern: str
    max_spiral_count: int
    max_inner_pcb_count: int
    instances: tuple[TxCoilInstanceSample, ...]
    outer_faces: TxCoilOuterFacesSample


@dataclass(frozen=True)
class PositionSampleMaybe:
    center_x_mm: Optional[float]
    center_y_mm: Optional[float]
    center_z_mm: Optional[float]


@dataclass(frozen=True)
class PositionSample:
    center_x_mm: float
    center_y_mm: float
    center_z_mm: float


@dataclass(frozen=True)
class TvSampleMaybe:
    present: bool
    model: bool
    width_mm: float
    height_mm: float
    thickness_mm: float
    position: PositionSampleMaybe


@dataclass(frozen=True)
class WallSampleMaybe:
    present: bool
    model: bool
    thickness_mm: float
    size_y_mm: float
    size_z_mm: float
    position: PositionSampleMaybe


@dataclass(frozen=True)
class FloorSampleMaybe:
    present: bool
    model: bool
    thickness_mm: float
    size_x_mm: float
    size_y_mm: float
    position: PositionSampleMaybe


@dataclass(frozen=True)
class TvSample:
    present: bool
    model: bool
    width_mm: float
    height_mm: float
    thickness_mm: float
    position: PositionSample


@dataclass(frozen=True)
class WallSample:
    present: bool
    model: bool
    thickness_mm: float
    size_y_mm: float
    size_z_mm: float
    position: PositionSample


@dataclass(frozen=True)
class FloorSample:
    present: bool
    model: bool
    thickness_mm: float
    size_x_mm: float
    size_y_mm: float
    position: PositionSample


@dataclass(frozen=True)
class Type1SampleInput:
    units_length: str
    wall_plane_x_mm: float
    floor_plane_z_mm: float
    core_core_gap_mm: float
    rx_total_thickness_mm_max: float
    tx_gap_from_tv_bottom_mm: float
    rx_stack_total_thickness_mm: float
    materials_core: MaterialSample
    tx_module: ModuleSample
    tx_position: PositionSample
    tx_pcb: PcbSample
    tx_coil: TxCoilSample
    rx_module: ModuleSample
    rx_position: PositionSample
    tv: TvSampleMaybe
    wall: WallSampleMaybe
    floor: FloorSampleMaybe


@dataclass(frozen=True)
class Type1Sample:
    units_length: str
    wall_plane_x_mm: float
    floor_plane_z_mm: float
    core_core_gap_mm: float
    rx_total_thickness_mm_max: float
    tx_gap_from_tv_bottom_mm: float
    rx_stack_total_thickness_mm: float
    materials_core: MaterialSample
    tx_module: ModuleSample
    tx_position: PositionSample
    tx_pcb: PcbSample
    tx_coil: TxCoilSample
    rx_module: ModuleSample
    rx_position: PositionSample
    tv: TvSample
    wall: WallSample
    floor: FloorSample
