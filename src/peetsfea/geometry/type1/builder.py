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
from peetsfea.geometry.type1 import pcb_faces
from peetsfea.logging_utils import log_action
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
    raise RuntimeError("Non-expression geometry is disabled; use build_type1_parametric_geometry.")


def _lit(value: float, units: str) -> str:
    return f"{value}{units}"


@log_action(
    "build_type1_parametric_geometry",
    lambda sample: {
        "units": sample.units_length,
        "tx_present": sample.tx_module.present,
        "rx_present": sample.rx_module.present,
        "pcb_layers": sample.tx_pcb.layer_count,
    },
)
def build_type1_parametric_geometry(sample: Type1Sample) -> ParametricGeometryPlan:
    units = sample.units_length
    sym = sp.Symbol
    half = sp.Rational(1, 2)  # pyright: ignore[reportOperatorIssue]

    def expr(value: sp.Expr) -> str:
        return sp.sstr(value)

    def var(name: str, value: float) -> DesignVariable:
        return DesignVariable(name=name, value=value, units=units)

    def dvar(name: str, value: sp.Expr) -> DesignVariable:
        return DesignVariable(name=name, value=expr(value), is_expression=True)

    def _face_enabled(flag: bool, dim_a: float, dim_b: float) -> bool:
        if not flag or dim_a <= 0 or dim_b <= 0:
            return False
        small = min(dim_a, dim_b)
        large = max(dim_a, dim_b)
        return (small / large) >= pcb_faces.ASPECT_MIN_RATIO

    def _layer_sequence(
        layer_count: int,
        pcb_thk_s: sp.Expr,
        outer_fr4_s: sp.Expr,
        inner_fr4_s: sp.Expr,
        copper_s: sp.Expr,
    ) -> list[tuple[str, str, sp.Expr]]:
        if layer_count == 1:
            middle_fr4 = pcb_thk_s - (outer_fr4_s + inner_fr4_s + copper_s)  # pyright: ignore[reportOperatorIssue]
            return [
                ("FR4_Outer", "fr4", outer_fr4_s),
                ("Cu_Outer", "copper", copper_s),
                ("FR4_Middle", "fr4", middle_fr4),
                ("FR4_Inner", "fr4", inner_fr4_s),
            ]
        middle_fr4 = pcb_thk_s - (outer_fr4_s + inner_fr4_s + copper_s + copper_s)  # pyright: ignore[reportOperatorIssue]
        return [
            ("FR4_Outer", "fr4", outer_fr4_s),
            ("Cu_Outer", "copper", copper_s),
            ("FR4_Middle", "fr4", middle_fr4),
            ("Cu_Inner", "copper", copper_s),
            ("FR4_Inner", "fr4", inner_fr4_s),
        ]

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

    pcb_thk_val = sample.tx_pcb.total_thickness_mm or pcb_faces.PCB_THICKNESS_MM
    fr4_outer_val = pcb_faces.FR4_OUTER_THICKNESS_MM
    fr4_inner_val = pcb_faces.FR4_INNER_THICKNESS_MM
    copper_val = pcb_faces.COPPER_THICKNESS_MM
    air_gap_val = pcb_faces.AIR_GAP_MM
    inward_offset_val = pcb_faces.INWARD_OFFSET_FACTOR * pcb_thk_val * 0.5

    variables: list[DesignVariable] = [
        var("wall_plane_x", sample.wall_plane_x_mm),
        var("floor_plane_z", sample.floor_plane_z_mm),
        var("core_core_gap", sample.core_core_gap_mm),
        var("tx_gap_from_tv_bottom", sample.tx_gap_from_tv_bottom_mm),
        var("pcb_thk", pcb_thk_val),
        var("pcb_fr4_outer", fr4_outer_val),
        var("pcb_fr4_inner", fr4_inner_val),
        var("pcb_copper_thk", copper_val),
        var("pcb_air_gap", air_gap_val),
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
        tv_bottom_z_expr = tv_cz_s - tv_h_s * half  # pyright: ignore[reportOperatorIssue]
        tx_center_y_expr = tv_cy_s
        rx_center_y_expr = tv_cy_s
        tx_center_z_expr = tv_bottom_z_expr - tx_gap_from_tv_bottom_s - tx_core_h_s * half  # pyright: ignore[reportOperatorIssue]
        rx_center_z_expr = tx_center_z_expr + tx_core_h_s * half + core_core_gap_s + rx_core_h_s * half  # pyright: ignore[reportOperatorIssue]
    else:
        tx_center_y_expr = tx_center_y_user_s
        rx_center_y_expr = rx_center_y_user_s
        tx_center_z_expr = tx_center_z_user_s
        rx_center_z_expr = tx_center_z_expr + tx_core_h_s * half + core_core_gap_s + rx_core_h_s * half  # pyright: ignore[reportOperatorIssue]

    tx_center_x_expr = wall_plane_x_s + tx_core_thk_s * half  # pyright: ignore[reportOperatorIssue]
    tx_corner_y_expr = tx_center_y_expr - tx_core_w_s * half  # pyright: ignore[reportOperatorIssue]
    tx_corner_z_expr = tx_center_z_expr - tx_core_h_s * half  # pyright: ignore[reportOperatorIssue]
    rx_corner_y_expr = rx_center_y_expr - rx_core_w_s * half  # pyright: ignore[reportOperatorIssue]
    rx_corner_z_expr = rx_center_z_expr - rx_core_h_s * half  # pyright: ignore[reportOperatorIssue]

    tv_corner_x_expr = tv_cx_s - tv_thk_s * half  # pyright: ignore[reportOperatorIssue]
    tv_corner_y_expr = tv_cy_s - tv_w_s * half  # pyright: ignore[reportOperatorIssue]
    tv_corner_z_expr = tv_cz_s - tv_h_s * half  # pyright: ignore[reportOperatorIssue]

    wall_corner_x_expr = wall_cx_s - wall_thk_s * half  # pyright: ignore[reportOperatorIssue]
    wall_corner_y_expr = wall_cy_s - wall_sy_s * half  # pyright: ignore[reportOperatorIssue]
    wall_corner_z_expr = wall_cz_s - wall_sz_s * half  # pyright: ignore[reportOperatorIssue]

    floor_corner_x_expr = floor_cx_s - floor_sx_s * half  # pyright: ignore[reportOperatorIssue]
    floor_corner_y_expr = floor_cy_s - floor_sy_s * half  # pyright: ignore[reportOperatorIssue]
    floor_corner_z_expr = floor_cz_s - floor_thk_s * half  # pyright: ignore[reportOperatorIssue]

    pcb_thk_s = sym("pcb_thk")
    fr4_outer_s = sym("pcb_fr4_outer")
    fr4_inner_s = sym("pcb_fr4_inner")
    copper_s = sym("pcb_copper_thk")
    air_gap_s = sym("pcb_air_gap")

    inward_offset_s = sp.Float(pcb_faces.INWARD_OFFSET_FACTOR) * pcb_thk_s * half  # pyright: ignore[reportOperatorIssue]
    scale_s = sp.Float(pcb_faces.IN_PLANE_SCALE)  # pyright: ignore[reportOperatorIssue]

    tx_thk_val = sample.tx_module.thickness_mm
    tx_w_val = sample.tx_module.outer_w_mm
    tx_h_val = sample.tx_module.outer_h_mm

    def _inner_pcb_available_val(axis: str, inner_count: int) -> float:
        half_thk = pcb_thk_val * 0.5
        if axis == "yz":
            neg_boundary = sample.wall_plane_x_mm + inward_offset_val + half_thk
            pos_boundary = sample.wall_plane_x_mm + sample.tx_module.thickness_mm - inward_offset_val - half_thk
        elif axis == "zx":
            tx_corner_y_val = sample.tx_position.center_y_mm - half_size(sample.tx_module.outer_w_mm)
            neg_boundary = tx_corner_y_val + inward_offset_val + half_thk
            pos_boundary = tx_corner_y_val + sample.tx_module.outer_w_mm - inward_offset_val - half_thk
        elif axis == "xy":
            tx_corner_z_val = sample.tx_position.center_z_mm - half_size(sample.tx_module.outer_h_mm)
            neg_boundary = tx_corner_z_val + inward_offset_val + half_thk
            pos_boundary = tx_corner_z_val + sample.tx_module.outer_h_mm - inward_offset_val - half_thk
        else:
            raise ValueError(f"Unsupported inner_plane_axis: {axis!r}")
        return (pos_boundary - neg_boundary) - inner_count * pcb_thk_val

    def _inner_pcb_boundaries(axis: str) -> tuple[sp.Expr, sp.Expr]:
        if axis == "yz":
            neg_boundary = wall_plane_x_s + inward_offset_s + pcb_thk_s * half  # pyright: ignore[reportOperatorIssue]
            pos_boundary = wall_plane_x_s + tx_core_thk_s - inward_offset_s - pcb_thk_s * half  # pyright: ignore[reportOperatorIssue]
            return neg_boundary, pos_boundary
        if axis == "zx":
            neg_boundary = tx_corner_y_expr + inward_offset_s + pcb_thk_s * half  # pyright: ignore[reportOperatorIssue]
            pos_boundary = tx_corner_y_expr + tx_core_w_s - inward_offset_s - pcb_thk_s * half  # pyright: ignore[reportOperatorIssue]
            return neg_boundary, pos_boundary
        if axis == "xy":
            neg_boundary = tx_corner_z_expr + inward_offset_s + pcb_thk_s * half  # pyright: ignore[reportOperatorIssue]
            pos_boundary = tx_corner_z_expr + tx_core_h_s - inward_offset_s - pcb_thk_s * half  # pyright: ignore[reportOperatorIssue]
            return neg_boundary, pos_boundary
        raise ValueError(f"Unsupported inner_plane_axis: {axis!r}")

    def _inner_pcb_centers(
        axis: str,
        inner_count: int,
        spacing_ratio: tuple[float, ...],
    ) -> list[sp.Expr]:
        if inner_count <= 0:
            return []
        available_val = _inner_pcb_available_val(axis, inner_count)
        if available_val <= 0:
            raise ValueError("TX inner PCB spacing invalid: available length must be positive")
        neg_boundary, pos_boundary = _inner_pcb_boundaries(axis)
        span = pos_boundary - neg_boundary  # pyright: ignore[reportOperatorIssue]
        available = span - sp.Float(inner_count) * pcb_thk_s  # pyright: ignore[reportOperatorIssue]

        weights = spacing_ratio[: inner_count + 1]
        total = sum(weights)
        total_expr = sp.Float(total)  # pyright: ignore[reportOperatorIssue]

        gap_exprs: list[sp.Expr] = []
        for weight in weights:
            gap_exprs.append(available * sp.Float(weight) / total_expr)  # pyright: ignore[reportOperatorIssue]

        centers: list[sp.Expr] = []
        center = neg_boundary + gap_exprs[0] + pcb_thk_s * half  # pyright: ignore[reportOperatorIssue]
        centers.append(center)
        for gap in gap_exprs[1:]:
            center = center + pcb_thk_s + gap  # pyright: ignore[reportOperatorIssue]
            centers.append(center)
        return centers

    face_flags = {
        "pos_x": _face_enabled(sample.tx_coil.outer_faces.pos_x, tx_w_val, tx_h_val),
        "neg_x": _face_enabled(sample.tx_coil.outer_faces.neg_x, tx_w_val, tx_h_val),
        "pos_y": _face_enabled(sample.tx_coil.outer_faces.pos_y, tx_thk_val, tx_h_val),
        "neg_y": _face_enabled(sample.tx_coil.outer_faces.neg_y, tx_thk_val, tx_h_val),
        "pos_z": _face_enabled(sample.tx_coil.outer_faces.pos_z, tx_thk_val, tx_w_val),
        "neg_z": _face_enabled(sample.tx_coil.outer_faces.neg_z, tx_thk_val, tx_w_val),
    }

    trim_dist_val = pcb_thk_val + air_gap_val
    trim_x_pos_val = trim_dist_val if face_flags["pos_x"] else 0.0
    trim_x_neg_val = trim_dist_val if face_flags["neg_x"] else 0.0
    trim_y_pos_val = trim_dist_val if face_flags["pos_y"] else 0.0
    trim_y_neg_val = trim_dist_val if face_flags["neg_y"] else 0.0
    trim_z_pos_val = trim_dist_val if face_flags["pos_z"] else 0.0
    trim_z_neg_val = trim_dist_val if face_flags["neg_z"] else 0.0

    if sample.tx_module.present:
        if tx_thk_val - trim_x_pos_val - trim_x_neg_val <= 0:
            raise ValueError("TX module trimmed thickness must remain positive")
        if tx_w_val - trim_y_pos_val - trim_y_neg_val <= 0:
            raise ValueError("TX module trimmed width must remain positive")
        if tx_h_val - trim_z_pos_val - trim_z_neg_val <= 0:
            raise ValueError("TX module trimmed height must remain positive")
        if sample.tx_coil.inner_pcb_count > 0:
            inner_centers = _inner_pcb_centers(
                sample.tx_coil.inner_plane_axis,
                sample.tx_coil.inner_pcb_count,
                sample.tx_coil.inner_spacing_ratio,
            )
        else:
            inner_centers = []

    trim_dist_s = pcb_thk_s + air_gap_s  # pyright: ignore[reportOperatorIssue]
    trim_x_pos = trim_dist_s if face_flags["pos_x"] else sp.Float(0.0)
    trim_x_neg = trim_dist_s if face_flags["neg_x"] else sp.Float(0.0)
    trim_y_pos = trim_dist_s if face_flags["pos_y"] else sp.Float(0.0)
    trim_y_neg = trim_dist_s if face_flags["neg_y"] else sp.Float(0.0)
    trim_z_pos = trim_dist_s if face_flags["pos_z"] else sp.Float(0.0)
    trim_z_neg = trim_dist_s if face_flags["neg_z"] else sp.Float(0.0)

    tx_corner_x_trim_expr = wall_plane_x_s + trim_x_neg  # pyright: ignore[reportOperatorIssue]
    tx_corner_y_trim_expr = tx_corner_y_expr + trim_y_neg  # pyright: ignore[reportOperatorIssue]
    tx_corner_z_trim_expr = tx_corner_z_expr + trim_z_neg  # pyright: ignore[reportOperatorIssue]
    tx_core_thk_trim_expr = tx_core_thk_s - trim_x_pos - trim_x_neg  # pyright: ignore[reportOperatorIssue]
    tx_core_w_trim_expr = tx_core_w_s - trim_y_pos - trim_y_neg  # pyright: ignore[reportOperatorIssue]
    tx_core_h_trim_expr = tx_core_h_s - trim_z_pos - trim_z_neg  # pyright: ignore[reportOperatorIssue]

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
        if not sample.tx_module.model:
            boxes.append(
                ParametricBoxPlan(
                    name="TX_Module_Region",
                    corner_expr=(
                        expr(wall_plane_x_s),
                        expr(tx_corner_y_expr),
                        expr(tx_corner_z_expr),
                    ),
                    size_expr=(expr(tx_core_thk_s), expr(tx_core_w_s), expr(tx_core_h_s)),
                    material="vacuum",
                    model=False,
                )
            )
        boxes.append(
            ParametricBoxPlan(
                name="TX_Core_Region",
                corner_expr=(
                    expr(tx_corner_x_trim_expr),
                    expr(tx_corner_y_trim_expr),
                    expr(tx_corner_z_trim_expr),
                ),
                size_expr=(expr(tx_core_thk_trim_expr), expr(tx_core_w_trim_expr), expr(tx_core_h_trim_expr)),
                material="core",
                model=sample.tx_module.model,
            )
        )

        def add_face_layers(
            name_prefix: str,
            axis: int,
            sign: int,
            center_exprs: tuple[sp.Expr, sp.Expr, sp.Expr],
            size_exprs: tuple[sp.Expr, sp.Expr, sp.Expr],
        ) -> None:
            layers = _layer_sequence(sample.tx_pcb.layer_count, pcb_thk_s, fr4_outer_s, fr4_inner_s, copper_s)
            outer_edge = center_exprs[axis] + sign * size_exprs[axis] * half  # pyright: ignore[reportOperatorIssue]
            offset = sp.Float(0.0)
            for label, material, thickness in layers:
                layer_center_axis = outer_edge - sign * (offset + thickness * half)  # pyright: ignore[reportOperatorIssue]
                centers = list(center_exprs)
                sizes = list(size_exprs)
                centers[axis] = layer_center_axis
                sizes[axis] = thickness
                corner_exprs_out: tuple[str, str, str] = (
                    expr(centers[0] - sizes[0] * half),  # pyright: ignore[reportOperatorIssue]
                    expr(centers[1] - sizes[1] * half),  # pyright: ignore[reportOperatorIssue]
                    expr(centers[2] - sizes[2] * half),  # pyright: ignore[reportOperatorIssue]
                )
                size_exprs_out: tuple[str, str, str] = (
                    expr(sizes[0]),
                    expr(sizes[1]),
                    expr(sizes[2]),
                )
                boxes.append(
                    ParametricBoxPlan(
                        name=f"{name_prefix}_{label}",
                        corner_expr=corner_exprs_out,
                        size_expr=size_exprs_out,
                        material=material,
                        model=True,
                    )
                )
                offset += thickness  # pyright: ignore[reportOperatorIssue]

        yz_size = (pcb_thk_s, tx_core_w_s * scale_s, tx_core_h_s * scale_s)  # pyright: ignore[reportOperatorIssue]
        xz_size = (tx_core_thk_s * scale_s, pcb_thk_s, tx_core_h_s * scale_s)  # pyright: ignore[reportOperatorIssue]
        xy_size = (tx_core_thk_s * scale_s, tx_core_w_s * scale_s, pcb_thk_s)  # pyright: ignore[reportOperatorIssue]

        face_center_x_pos = wall_plane_x_s + tx_core_thk_s - inward_offset_s  # pyright: ignore[reportOperatorIssue]
        face_center_x_neg = wall_plane_x_s + inward_offset_s  # pyright: ignore[reportOperatorIssue]
        face_center_y_pos = tx_corner_y_expr + tx_core_w_s - inward_offset_s  # pyright: ignore[reportOperatorIssue]
        face_center_y_neg = tx_corner_y_expr + inward_offset_s  # pyright: ignore[reportOperatorIssue]
        face_center_z_pos = tx_corner_z_expr + tx_core_h_s - inward_offset_s  # pyright: ignore[reportOperatorIssue]
        face_center_z_neg = tx_corner_z_expr + inward_offset_s  # pyright: ignore[reportOperatorIssue]

        if face_flags["pos_x"]:
            add_face_layers(
                "TX_PCB_Face_PosX",
                0,
                1,
                (face_center_x_pos, tx_center_y_expr, tx_center_z_expr),
                yz_size,
            )
        if face_flags["neg_x"]:
            add_face_layers(
                "TX_PCB_Face_NegX",
                0,
                -1,
                (face_center_x_neg, tx_center_y_expr, tx_center_z_expr),
                yz_size,
            )
        if face_flags["pos_y"]:
            add_face_layers(
                "TX_PCB_Face_PosY",
                1,
                1,
                (tx_center_x_expr, face_center_y_pos, tx_center_z_expr),
                xz_size,
            )
        if face_flags["neg_y"]:
            add_face_layers(
                "TX_PCB_Face_NegY",
                1,
                -1,
                (tx_center_x_expr, face_center_y_neg, tx_center_z_expr),
                xz_size,
            )
        if face_flags["pos_z"]:
            add_face_layers(
                "TX_PCB_Face_PosZ",
                2,
                1,
                (tx_center_x_expr, tx_center_y_expr, face_center_z_pos),
                xy_size,
            )
        if face_flags["neg_z"]:
            add_face_layers(
                "TX_PCB_Face_NegZ",
                2,
                -1,
                (tx_center_x_expr, tx_center_y_expr, face_center_z_neg),
                xy_size,
            )

        if inner_centers:
            axis_tag = sample.tx_coil.inner_plane_axis.upper()
            if sample.tx_coil.inner_plane_axis == "yz":
                axis = 0
                inner_size = yz_size
                for idx, center in enumerate(inner_centers, start=1):
                    add_face_layers(
                        f"TX_PCB_Inner_{axis_tag}_{idx:02d}",
                        axis,
                        1,
                        (center, tx_center_y_expr, tx_center_z_expr),
                        inner_size,
                    )
            elif sample.tx_coil.inner_plane_axis == "zx":
                axis = 1
                inner_size = xz_size
                for idx, center in enumerate(inner_centers, start=1):
                    add_face_layers(
                        f"TX_PCB_Inner_{axis_tag}_{idx:02d}",
                        axis,
                        1,
                        (tx_center_x_expr, center, tx_center_z_expr),
                        inner_size,
                    )
            elif sample.tx_coil.inner_plane_axis == "xy":
                axis = 2
                inner_size = xy_size
                for idx, center in enumerate(inner_centers, start=1):
                    add_face_layers(
                        f"TX_PCB_Inner_{axis_tag}_{idx:02d}",
                        axis,
                        1,
                        (tx_center_x_expr, tx_center_y_expr, center),
                        inner_size,
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
