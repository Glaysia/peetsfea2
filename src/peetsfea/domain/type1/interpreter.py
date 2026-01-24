from __future__ import annotations

from dataclasses import dataclass

from peetsfea.domain.errors import DomainValidationError
from peetsfea.domain.type1.sampled_models import (
    FloorSample,
    PositionSample,
    TvSample,
    Type1Sample,
    Type1SampleInput,
    WallSample,
)
from peetsfea.sampling.rng import half_size


def _require_positive(value: float, name: str) -> None:
    if value <= 0:
        raise DomainValidationError(f"{name} must be > 0")


def _validate(sample: Type1SampleInput) -> None:
    if sample.core_core_gap_mm < 0:
        raise DomainValidationError("core_core_gap_mm must be >= 0")

    if (
        sample.rx_stack_total_thickness_mm > 0
        and sample.rx_total_thickness_mm_max > 0
        and sample.rx_stack_total_thickness_mm > sample.rx_total_thickness_mm_max
    ):
        raise DomainValidationError(
            "rx.stack.total_thickness_mm must be <= constraints.rx_total_thickness_mm_max"
        )

    if sample.tx_module.present:
        _require_positive(sample.tx_module.thickness_mm, "tx.module.thickness_mm")
        _require_positive(sample.tx_module.outer_w_mm, "tx.module.outer_w_mm")
        _require_positive(sample.tx_module.outer_h_mm, "tx.module.outer_h_mm")

    if sample.rx_module.present:
        _require_positive(sample.rx_module.thickness_mm, "rx.module.thickness_mm")
        _require_positive(sample.rx_module.outer_w_mm, "rx.module.outer_w_mm")
        _require_positive(sample.rx_module.outer_h_mm, "rx.module.outer_h_mm")

    if sample.tv.present:
        _require_positive(sample.tv.width_mm, "tv.width_mm")
        _require_positive(sample.tv.height_mm, "tv.height_mm")
        _require_positive(sample.tv.thickness_mm, "tv.thickness_mm")
        if sample.rx_module.present:
            if sample.rx_module.outer_w_mm > 0.9 * sample.tv.width_mm:
                raise DomainValidationError("rx.module.outer_w_mm exceeds 90% of tv.width_mm")
            if sample.rx_module.outer_h_mm > 0.9 * sample.tv.height_mm:
                raise DomainValidationError("rx.module.outer_h_mm exceeds 90% of tv.height_mm")

    if sample.wall.present:
        _require_positive(sample.wall.thickness_mm, "wall.thickness_mm")
        _require_positive(sample.wall.size_y_mm, "wall.size_y_mm")
        _require_positive(sample.wall.size_z_mm, "wall.size_z_mm")

    if sample.floor.present:
        _require_positive(sample.floor.thickness_mm, "floor.thickness_mm")
        _require_positive(sample.floor.size_x_mm, "floor.size_x_mm")
        _require_positive(sample.floor.size_y_mm, "floor.size_y_mm")


def _pos_with_defaults(
    center_x: float | None,
    center_y: float | None,
    center_z: float | None,
    default_x: float,
    default_y: float,
    default_z: float,
) -> PositionSample:
    return PositionSample(
        center_x_mm=default_x if center_x is None else center_x,
        center_y_mm=default_y if center_y is None else center_y,
        center_z_mm=default_z if center_z is None else center_z,
    )


@dataclass(frozen=True)
class Type1Domain:
    sample: Type1Sample


def interpret_type1(sample: Type1SampleInput) -> Type1Domain:
    _validate(sample)
    core_core_gap = max(sample.core_core_gap_mm, 0.0)

    tv_center = _pos_with_defaults(
        sample.tv.position.center_x_mm,
        sample.tv.position.center_y_mm,
        sample.tv.position.center_z_mm,
        default_x=sample.wall_plane_x_mm + half_size(sample.tv.thickness_mm),
        default_y=0.0,
        default_z=0.0,
    )

    wall_center = _pos_with_defaults(
        sample.wall.position.center_x_mm,
        sample.wall.position.center_y_mm,
        sample.wall.position.center_z_mm,
        default_x=sample.wall_plane_x_mm - half_size(sample.wall.thickness_mm),
        default_y=0.0,
        default_z=0.0,
    )

    floor_center = _pos_with_defaults(
        sample.floor.position.center_x_mm,
        sample.floor.position.center_y_mm,
        sample.floor.position.center_z_mm,
        default_x=0.0,
        default_y=0.0,
        default_z=sample.floor_plane_z_mm - half_size(sample.floor.thickness_mm),
    )

    tx_position = PositionSample(
        center_x_mm=sample.tx_position.center_x_mm,
        center_y_mm=sample.tx_position.center_y_mm,
        center_z_mm=sample.tx_position.center_z_mm,
    )

    rx_position = PositionSample(
        center_x_mm=sample.rx_position.center_x_mm,
        center_y_mm=sample.rx_position.center_y_mm,
        center_z_mm=sample.rx_position.center_z_mm,
    )

    if sample.tv.present:
        tv_bottom_z = tv_center.center_z_mm - half_size(sample.tv.height_mm)
        tx_position = PositionSample(
            center_x_mm=tx_position.center_x_mm,
            center_y_mm=tv_center.center_y_mm,
            center_z_mm=tv_bottom_z
            - sample.tx_gap_from_tv_bottom_mm
            - half_size(sample.tx_module.outer_h_mm),
        )
        rx_position = PositionSample(
            center_x_mm=rx_position.center_x_mm,
            center_y_mm=tv_center.center_y_mm,
            center_z_mm=tx_position.center_z_mm
            + half_size(sample.tx_module.outer_h_mm)
            + core_core_gap
            + half_size(sample.rx_module.outer_h_mm),
        )
    else:
        rx_position = PositionSample(
            center_x_mm=rx_position.center_x_mm,
            center_y_mm=rx_position.center_y_mm,
            center_z_mm=tx_position.center_z_mm
            + half_size(sample.tx_module.outer_h_mm)
            + core_core_gap
            + half_size(sample.rx_module.outer_h_mm),
        )

    domain_sample = Type1Sample(
        units_length=sample.units_length,
        wall_plane_x_mm=sample.wall_plane_x_mm,
        floor_plane_z_mm=sample.floor_plane_z_mm,
        core_core_gap_mm=core_core_gap,
        rx_total_thickness_mm_max=sample.rx_total_thickness_mm_max,
        tx_gap_from_tv_bottom_mm=sample.tx_gap_from_tv_bottom_mm,
        rx_stack_total_thickness_mm=sample.rx_stack_total_thickness_mm,
        materials_core=sample.materials_core,
        tx_module=sample.tx_module,
        tx_position=tx_position,
        rx_module=sample.rx_module,
        rx_position=rx_position,
        tv=TvSample(
            present=sample.tv.present,
            model=sample.tv.model,
            width_mm=sample.tv.width_mm,
            height_mm=sample.tv.height_mm,
            thickness_mm=sample.tv.thickness_mm,
            position=tv_center,
        ),
        wall=WallSample(
            present=sample.wall.present,
            model=sample.wall.model,
            thickness_mm=sample.wall.thickness_mm,
            size_y_mm=sample.wall.size_y_mm,
            size_z_mm=sample.wall.size_z_mm,
            position=wall_center,
        ),
        floor=FloorSample(
            present=sample.floor.present,
            model=sample.floor.model,
            thickness_mm=sample.floor.thickness_mm,
            size_x_mm=sample.floor.size_x_mm,
            size_y_mm=sample.floor.size_y_mm,
            position=floor_center,
        ),
    )

    return Type1Domain(sample=domain_sample)
