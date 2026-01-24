from __future__ import annotations

import sympy as sp

from peetsfea.domain.type1.sampled_models import Type1Sample
from peetsfea.geometry.plan import (
    BoxPlan,
    DesignVariable,
    GeometryPlan,
    ParametricBoxPlan,
    ParametricGeometryPlan,
)
from peetsfea.sampling.rng import half_size


def _add_box(
    boxes: list[BoxPlan],
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    material: str,
    model: bool,
) -> None:
    if size[0] <= 0 or size[1] <= 0 or size[2] <= 0:
        return
    boxes.append(
        BoxPlan(
            name=name,
            center_mm=center,
            size_mm=size,
            material=material,
            model=model,
        )
    )


def build_type1_geometry(sample: Type1Sample) -> GeometryPlan:
    boxes: list[BoxPlan] = []

    if sample.tx_module.present:
        tx_center_x = sample.wall_plane_x_mm + half_size(sample.tx_module.thickness_mm)
        _add_box(
            boxes,
            name="TX_Module_Region",
            center=(tx_center_x, sample.tx_position.center_y_mm, sample.tx_position.center_z_mm),
            size=(sample.tx_module.thickness_mm, sample.tx_module.outer_w_mm, sample.tx_module.outer_h_mm),
            material="core",
            model=sample.tx_module.model,
        )

    if sample.rx_module.present:
        rx_center_x = sample.wall_plane_x_mm + half_size(sample.rx_module.thickness_mm)
        _add_box(
            boxes,
            name="RX_Module_Region",
            center=(rx_center_x, sample.rx_position.center_y_mm, sample.rx_position.center_z_mm),
            size=(sample.rx_module.thickness_mm, sample.rx_module.outer_w_mm, sample.rx_module.outer_h_mm),
            material="core",
            model=sample.rx_module.model,
        )

    if sample.tv.present:
        _add_box(
            boxes,
            name="TV_NonModel",
            center=(
                sample.tv.position.center_x_mm,
                sample.tv.position.center_y_mm,
                sample.tv.position.center_z_mm,
            ),
            size=(sample.tv.thickness_mm, sample.tv.width_mm, sample.tv.height_mm),
            material="vacuum",
            model=sample.tv.model,
        )

    if sample.wall.present:
        _add_box(
            boxes,
            name="Wall_NonModel",
            center=(
                sample.wall.position.center_x_mm,
                sample.wall.position.center_y_mm,
                sample.wall.position.center_z_mm,
            ),
            size=(sample.wall.thickness_mm, sample.wall.size_y_mm, sample.wall.size_z_mm),
            material="vacuum",
            model=sample.wall.model,
        )

    if sample.floor.present:
        _add_box(
            boxes,
            name="Floor_NonModel",
            center=(
                sample.floor.position.center_x_mm,
                sample.floor.position.center_y_mm,
                sample.floor.position.center_z_mm,
            ),
            size=(sample.floor.size_x_mm, sample.floor.size_y_mm, sample.floor.thickness_mm),
            material="vacuum",
            model=sample.floor.model,
        )

    return GeometryPlan(units_length=sample.units_length, boxes=boxes)


def _lit(value: float, units: str) -> str:
    return f"{value}{units}"


def build_type1_parametric_geometry(sample: Type1Sample) -> ParametricGeometryPlan:
    units = sample.units_length
    sym = sp.Symbol
    half = sp.Rational(1, 2)

    def expr(value: sp.Expr) -> str:
        return sp.sstr(value)

    def var(name: str, value: float) -> DesignVariable:
        return DesignVariable(name=name, value=value, units=units)

    def dvar(name: str, value: sp.Expr) -> DesignVariable:
        return DesignVariable(name=name, value=expr(value), is_expression=True)

    wall_plane_x_s = sym("wall_plane_x")
    floor_plane_z_s = sym("floor_plane_z")
    core_core_gap_s = sym("core_core_gap")
    tx_gap_from_tv_bottom_s = sym("tx_gap_from_tv_bottom")

    tx_core_w_s = sym("tx_core_w")
    tx_core_h_s = sym("tx_core_h")
    rx_core_w_s = sym("rx_core_w")
    rx_core_h_s = sym("rx_core_h")
    tx_core_thk_s = sym("tx_core_thk")
    rx_core_thk_s = sym("rx_core_thk")

    tx_center_y_user_s = sym("tx_center_y_user")
    rx_center_y_user_s = sym("rx_center_y_user")
    tx_center_z_user_s = sym("tx_center_z_user")
    rx_center_z_user_s = sym("rx_center_z_user")

    tv_cx_s = sym("tv_center_x")
    tv_cy_s = sym("tv_center_y")
    tv_cz_s = sym("tv_center_z")
    tv_w_s = sym("tv_w")
    tv_h_s = sym("tv_h")
    tv_thk_s = sym("tv_thk")

    wall_cx_s = sym("wall_center_x")
    wall_cy_s = sym("wall_center_y")
    wall_cz_s = sym("wall_center_z")
    wall_thk_s = sym("wall_thk")
    wall_sy_s = sym("wall_sy")
    wall_sz_s = sym("wall_sz")

    floor_cx_s = sym("floor_center_x")
    floor_cy_s = sym("floor_center_y")
    floor_cz_s = sym("floor_center_z")
    floor_thk_s = sym("floor_thk")
    floor_sx_s = sym("floor_sx")
    floor_sy_s = sym("floor_sy")

    variables: list[DesignVariable] = [
        var("wall_plane_x", sample.wall_plane_x_mm),
        var("floor_plane_z", sample.floor_plane_z_mm),
        var("core_core_gap", sample.core_core_gap_mm),
        var("tx_gap_from_tv_bottom", sample.tx_gap_from_tv_bottom_mm),
        var("tx_core_w", sample.tx_module.outer_w_mm),
        var("tx_core_h", sample.tx_module.outer_h_mm),
        var("rx_core_w", sample.rx_module.outer_w_mm),
        var("rx_core_h", sample.rx_module.outer_h_mm),
        var("tx_core_thk", sample.tx_module.thickness_mm),
        var("rx_core_thk", sample.rx_module.thickness_mm),
        var("tx_center_y_user", sample.tx_position.center_y_mm),
        var("rx_center_y_user", sample.rx_position.center_y_mm),
        var("tx_center_z_user", sample.tx_position.center_z_mm),
        var("rx_center_z_user", sample.rx_position.center_z_mm),
        var("tv_center_x", sample.tv.position.center_x_mm),
        var("tv_center_y", sample.tv.position.center_y_mm),
        var("tv_center_z", sample.tv.position.center_z_mm),
        var("tv_w", sample.tv.width_mm),
        var("tv_h", sample.tv.height_mm),
        var("tv_thk", sample.tv.thickness_mm),
        var("wall_center_x", sample.wall.position.center_x_mm),
        var("wall_center_y", sample.wall.position.center_y_mm),
        var("wall_center_z", sample.wall.position.center_z_mm),
        var("wall_thk", sample.wall.thickness_mm),
        var("wall_sy", sample.wall.size_y_mm),
        var("wall_sz", sample.wall.size_z_mm),
        var("floor_center_x", sample.floor.position.center_x_mm),
        var("floor_center_y", sample.floor.position.center_y_mm),
        var("floor_center_z", sample.floor.position.center_z_mm),
        var("floor_thk", sample.floor.thickness_mm),
        var("floor_sx", sample.floor.size_x_mm),
        var("floor_sy", sample.floor.size_y_mm),
    ]

    if sample.tv.present:
        tv_bottom_z_expr = tv_cz_s - tv_h_s * half
        tx_center_y_expr = tv_cy_s
        rx_center_y_expr = tv_cy_s
        tx_center_z_expr = tv_bottom_z_expr - tx_gap_from_tv_bottom_s - tx_core_h_s * half
        rx_center_z_expr = tx_center_z_expr + tx_core_h_s * half + core_core_gap_s + rx_core_h_s * half
    else:
        tx_center_y_expr = tx_center_y_user_s
        rx_center_y_expr = rx_center_y_user_s
        tx_center_z_expr = tx_center_z_user_s
        rx_center_z_expr = tx_center_z_expr + tx_core_h_s * half + core_core_gap_s + rx_core_h_s * half

    tx_corner_y_expr = tx_center_y_expr - tx_core_w_s * half
    tx_corner_z_expr = tx_center_z_expr - tx_core_h_s * half
    rx_corner_y_expr = rx_center_y_expr - rx_core_w_s * half
    rx_corner_z_expr = rx_center_z_expr - rx_core_h_s * half

    tv_corner_x_expr = tv_cx_s - tv_thk_s * half
    tv_corner_y_expr = tv_cy_s - tv_w_s * half
    tv_corner_z_expr = tv_cz_s - tv_h_s * half

    wall_corner_x_expr = wall_cx_s - wall_thk_s * half
    wall_corner_y_expr = wall_cy_s - wall_sy_s * half
    wall_corner_z_expr = wall_cz_s - wall_sz_s * half

    floor_corner_x_expr = floor_cx_s - floor_sx_s * half
    floor_corner_y_expr = floor_cy_s - floor_sy_s * half
    floor_corner_z_expr = floor_cz_s - floor_thk_s * half

    variables.extend(
        [
            dvar("tx_center_y", tx_center_y_expr),
            dvar("rx_center_y", rx_center_y_expr),
            dvar("tx_center_z", tx_center_z_expr),
            dvar("rx_center_z", rx_center_z_expr),
            dvar("tx_corner_y", tx_corner_y_expr),
            dvar("tx_corner_z", tx_corner_z_expr),
            dvar("rx_corner_y", rx_corner_y_expr),
            dvar("rx_corner_z", rx_corner_z_expr),
            dvar("tv_corner_x", tv_corner_x_expr),
            dvar("tv_corner_y", tv_corner_y_expr),
            dvar("tv_corner_z", tv_corner_z_expr),
            dvar("wall_corner_x", wall_corner_x_expr),
            dvar("wall_corner_y", wall_corner_y_expr),
            dvar("wall_corner_z", wall_corner_z_expr),
            dvar("floor_corner_x", floor_corner_x_expr),
            dvar("floor_corner_y", floor_corner_y_expr),
            dvar("floor_corner_z", floor_corner_z_expr),
        ]
    )

    boxes: list[ParametricBoxPlan] = []
    if sample.tx_module.present:
        boxes.append(
            ParametricBoxPlan(
                name="TX_Module_Region",
                corner_expr=(
                    expr(wall_plane_x_s),
                    expr(tx_corner_y_expr),
                    expr(tx_corner_z_expr),
                ),
                size_expr=(expr(tx_core_thk_s), expr(tx_core_w_s), expr(tx_core_h_s)),
                material="core",
                model=sample.tx_module.model,
            )
        )

    if sample.rx_module.present:
        boxes.append(
            ParametricBoxPlan(
                name="RX_Module_Region",
                corner_expr=(
                    expr(wall_plane_x_s),
                    expr(rx_corner_y_expr),
                    expr(rx_corner_z_expr),
                ),
                size_expr=(expr(rx_core_thk_s), expr(rx_core_w_s), expr(rx_core_h_s)),
                material="core",
                model=sample.rx_module.model,
            )
        )

    if sample.tv.present:
        boxes.append(
            ParametricBoxPlan(
                name="TV_NonModel",
                corner_expr=(expr(tv_corner_x_expr), expr(tv_corner_y_expr), expr(tv_corner_z_expr)),
                size_expr=(expr(tv_thk_s), expr(tv_w_s), expr(tv_h_s)),
                material="vacuum",
                model=sample.tv.model,
            )
        )

    if sample.wall.present:
        boxes.append(
            ParametricBoxPlan(
                name="Wall_NonModel",
                corner_expr=(expr(wall_corner_x_expr), expr(wall_corner_y_expr), expr(wall_corner_z_expr)),
                size_expr=(expr(wall_thk_s), expr(wall_sy_s), expr(wall_sz_s)),
                material="vacuum",
                model=sample.wall.model,
            )
        )

    if sample.floor.present:
        boxes.append(
            ParametricBoxPlan(
                name="Floor_NonModel",
                corner_expr=(expr(floor_corner_x_expr), expr(floor_corner_y_expr), expr(floor_corner_z_expr)),
                size_expr=(expr(floor_sx_s), expr(floor_sy_s), expr(floor_thk_s)),
                material="vacuum",
                model=sample.floor.model,
            )
        )

    return ParametricGeometryPlan(units_length=units, variables=variables, boxes=boxes)
