from __future__ import annotations

import random

from peetsfea.domain.type1.sampled_models import (
    FloorSampleMaybe,
    MaterialSample,
    ModuleSample,
    PositionSample,
    PositionSampleMaybe,
    TvSampleMaybe,
    Type1SampleInput,
    WallSampleMaybe,
)
from peetsfea.domain.type1.spec_models import RangeSpec, Type1Spec
from peetsfea.sampling.rng import sample_range


def _sample_optional(rng: random.Random, spec: RangeSpec | None) -> float | None:
    if spec is None:
        return None
    return sample_range(rng, spec)


def _sample_position_optional(rng: random.Random, position) -> PositionSampleMaybe:
    return PositionSampleMaybe(
        center_x_mm=_sample_optional(rng, position.center_x_mm),
        center_y_mm=_sample_optional(rng, position.center_y_mm),
        center_z_mm=_sample_optional(rng, position.center_z_mm),
    )


def _sample_position(rng: random.Random, position) -> PositionSample:
    return PositionSample(
        center_x_mm=sample_range(rng, position.center_x_mm),
        center_y_mm=sample_range(rng, position.center_y_mm),
        center_z_mm=sample_range(rng, position.center_z_mm),
    )


def _sample_module(rng: random.Random, module) -> ModuleSample:
    return ModuleSample(
        present=module.present,
        model=module.model,
        outer_w_mm=sample_range(rng, module.outer_w_mm),
        outer_h_mm=sample_range(rng, module.outer_h_mm),
        thickness_mm=sample_range(rng, module.thickness_mm),
        offset_from_coil_mm=sample_range(rng, module.offset_from_coil_mm),
    )


def sample_type1(spec: Type1Spec, seed: int) -> Type1SampleInput:
    rng = random.Random(seed)

    wall_plane_x = sample_range(rng, spec.coordinate_system.wall_plane_x_mm)
    floor_plane_z = sample_range(rng, spec.coordinate_system.floor_plane_z_mm)
    core_core_gap = sample_range(rng, spec.constraints.core_core_gap_mm)
    rx_total_thickness_mm_max = sample_range(rng, spec.constraints.rx_total_thickness_mm_max)
    tx_gap_from_tv_bottom = sample_range(rng, spec.constraints.tx_gap_from_tv_bottom_mm)

    materials_core = MaterialSample(
        mu_r=sample_range(rng, spec.materials.core.mu_r),
        epsilon_r=sample_range(rng, spec.materials.core.epsilon_r),
        conductivity_s_per_m=sample_range(rng, spec.materials.core.conductivity_s_per_m),
    )

    tx_module = _sample_module(rng, spec.tx.module)
    rx_module = _sample_module(rng, spec.rx.module)

    tx_position = _sample_position(rng, spec.tx.position)
    rx_position = _sample_position(rng, spec.rx.position)

    tv = TvSampleMaybe(
        present=spec.tv.present,
        model=spec.tv.model,
        width_mm=sample_range(rng, spec.tv.width_mm),
        height_mm=sample_range(rng, spec.tv.height_mm),
        thickness_mm=sample_range(rng, spec.tv.thickness_mm),
        position=_sample_position_optional(rng, spec.tv.position),
    )

    wall = WallSampleMaybe(
        present=spec.wall.present,
        model=spec.wall.model,
        thickness_mm=sample_range(rng, spec.wall.thickness_mm),
        size_y_mm=sample_range(rng, spec.wall.size_y_mm),
        size_z_mm=sample_range(rng, spec.wall.size_z_mm),
        position=_sample_position_optional(rng, spec.wall.position),
    )

    floor = FloorSampleMaybe(
        present=spec.floor.present,
        model=spec.floor.model,
        thickness_mm=sample_range(rng, spec.floor.thickness_mm),
        size_x_mm=sample_range(rng, spec.floor.size_x_mm),
        size_y_mm=sample_range(rng, spec.floor.size_y_mm),
        position=_sample_position_optional(rng, spec.floor.position),
    )

    return Type1SampleInput(
        units_length=spec.units.length,
        wall_plane_x_mm=wall_plane_x,
        floor_plane_z_mm=floor_plane_z,
        core_core_gap_mm=core_core_gap,
        rx_total_thickness_mm_max=rx_total_thickness_mm_max,
        tx_gap_from_tv_bottom_mm=tx_gap_from_tv_bottom,
        rx_stack_total_thickness_mm=sample_range(rng, spec.rx.stack.total_thickness_mm),
        materials_core=materials_core,
        tx_module=tx_module,
        tx_position=tx_position,
        rx_module=rx_module,
        rx_position=rx_position,
        tv=tv,
        wall=wall,
        floor=floor,
    )
