from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    rx_module: ModuleSample
    rx_position: PositionSample
    tv: TvSample
    wall: WallSample
    floor: FloorSample
