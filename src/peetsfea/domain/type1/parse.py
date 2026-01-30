from __future__ import annotations

from typing import Any, Optional

from ..errors import SpecValidationError
from .spec_models import (
    ConstraintsSpec,
    CoordinateSystemSpec,
    FloorSpec,
    LayoutSpec,
    MaterialCoreSpec,
    MaterialsSpec,
    ModuleSpec,
    PcbSpec,
    PositionSpec,
    RangeSpec,
    RxSpec,
    RxStackSpec,
    TvSpec,
    TxCoilOuterFacesSpec,
    TxCoilSpec,
    TxSpec,
    Type1Spec,
    UnitsSpec,
    WallSpec,
)

DEFAULT_CORE_W_MM = 100.0
DEFAULT_CORE_H_MM = 100.0
VALID_INNER_PLANE_AXES = {"xy", "yz", "zx"}
PCB_TOTAL_THK_MIN = 1.6
PCB_TOTAL_THK_MAX = 1.7


def _validate_tx_inner_pcb_spec(tx_pcb: PcbSpec, tx_coil: TxCoilSpec) -> None:
    if tx_coil.inner_plane_axis not in VALID_INNER_PLANE_AXES:
        raise SpecValidationError(
            f"tx.coil.inner_plane_axis must be one of {sorted(VALID_INNER_PLANE_AXES)}, got {tx_coil.inner_plane_axis!r}"
        )
    if tx_coil.inner_pcb_count < 0:
        raise SpecValidationError("tx.coil.inner_pcb_count must be >= 0")
    if tx_coil.inner_pcb_count > tx_coil.max_inner_pcb_count:
        raise SpecValidationError("tx.coil.inner_pcb_count must be <= tx.coil.max_inner_pcb_count")
    required_len = tx_coil.inner_pcb_count + 1
    if len(tx_coil.inner_spacing_ratio) < required_len:
        raise SpecValidationError(
            f"tx.coil.inner_spacing_ratio must have at least {required_len} entries, got {len(tx_coil.inner_spacing_ratio)}"
        )
    if sum(tx_coil.inner_spacing_ratio[:required_len]) <= 0:
        raise SpecValidationError("tx.coil.inner_spacing_ratio sum must be > 0 for used entries")
    if tx_pcb.layer_count != 2:
        raise SpecValidationError("tx.pcb.layer_count must be 2 (fixed PCB spec)")
    if not (PCB_TOTAL_THK_MIN <= tx_pcb.total_thickness_mm <= PCB_TOTAL_THK_MAX):
        raise SpecValidationError(
            f"tx.pcb.total_thickness_mm must be between {PCB_TOTAL_THK_MIN} and {PCB_TOTAL_THK_MAX}"
        )


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    return bool(value)


def _as_float(value: Any, default: float) -> float:
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SpecValidationError(f"Expected numeric value, got {value!r}") from exc


def _as_int(value: Any, default: int) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise SpecValidationError(f"Expected integer value, got {value!r}") from exc


def _range_from_value(value: Any, default: Any) -> RangeSpec:
    if value is None:
        value = default
    if isinstance(value, RangeSpec):
        return value
    if isinstance(value, list):
        if len(value) == 3:
            return RangeSpec(_as_float(value[0], 0.0), _as_float(value[1], 0.0), _as_float(value[2], 0.0))
        if len(value) >= 1:
            single = _as_float(value[0], 0.0)
            return RangeSpec(single, single, 0.0)
        return RangeSpec(0.0, 0.0, 0.0)
    if value is None:
        return RangeSpec(0.0, 0.0, 0.0)
    single = _as_float(value, 0.0)
    return RangeSpec(single, single, 0.0)


def _get_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SpecValidationError(f"Expected table for {key}, got {type(value).__name__}")
    return value


def _get_value(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _parse_position(data: dict[str, Any], defaults: dict[str, Optional[Any]]) -> PositionSpec:
    cx = _get_value(data, "center_x_mm")
    cy = _get_value(data, "center_y_mm")
    cz = _get_value(data, "center_z_mm")

    def parse_optional(value: Any, default: Optional[Any]) -> Optional[RangeSpec]:
        if value is None:
            if default is None:
                return None
            return _range_from_value(default, default)
        return _range_from_value(value, value)

    return PositionSpec(
        center_x_mm=parse_optional(cx, defaults.get("center_x_mm")),
        center_y_mm=parse_optional(cy, defaults.get("center_y_mm")),
        center_z_mm=parse_optional(cz, defaults.get("center_z_mm")),
    )


def parse_type1_spec_dict(data: dict[str, Any]) -> Type1Spec:
    units = UnitsSpec(length=str(_get_value(data, "units", "length", default="mm")))

    coord = _get_dict(data, "coordinate_system")
    coordinate_system = CoordinateSystemSpec(
        wall_plane_x_mm=_range_from_value(
            coord.get("wall_plane_x_mm"),
            [0.0, 0.0, 0.0],
        ),
        floor_plane_z_mm=_range_from_value(
            coord.get("floor_plane_z_mm"),
            [0.0, 0.0, 0.0],
        ),
    )

    constraints_data = _get_dict(data, "constraints")
    constraints = ConstraintsSpec(
        core_core_gap_mm=_range_from_value(constraints_data.get("core_core_gap_mm"), [100.0, 100.0, 0.0]),
        rx_total_thickness_mm_max=_range_from_value(
            constraints_data.get("rx_total_thickness_mm_max"),
            [4.0, 4.0, 0.0],
        ),
        tx_gap_from_tv_bottom_mm=_range_from_value(
            constraints_data.get("tx_gap_from_tv_bottom_mm"),
            [0.0, 0.0, 0.0],
        ),
    )

    layout_data = _get_dict(data, "layout")
    layout = LayoutSpec(
        right_edge_y_mm=_range_from_value(layout_data.get("right_edge_y_mm"), [0.0, 0.0, 0.0])
    )

    materials_data = _get_dict(data, "materials")
    core_data = _get_dict(materials_data, "core")
    materials = MaterialsSpec(
        core=MaterialCoreSpec(
            mu_r=_range_from_value(core_data.get("mu_r"), [1200.0, 1200.0, 0.0]),
            epsilon_r=_range_from_value(core_data.get("epsilon_r"), [1.0, 1.0, 0.0]),
            conductivity_s_per_m=_range_from_value(core_data.get("conductivity_s_per_m"), [0.0, 0.0, 0.0]),
        )
    )

    tx_data = _get_dict(data, "tx")
    tx_pcb_data = _get_dict(tx_data, "pcb")
    raw_stackup = tx_pcb_data.get("stackup")
    if raw_stackup is None:
        stackup: tuple[dict[str, Any], ...] = ()
    elif isinstance(raw_stackup, list):
        stack_items: list[dict[str, Any]] = []
        for item in raw_stackup:
            if not isinstance(item, dict):
                raise SpecValidationError("Expected table entries for tx.pcb.stackup")
            stack_items.append(item)
        stackup = tuple(stack_items)
    else:
        raise SpecValidationError("Expected list for tx.pcb.stackup")
    tx_pcb = PcbSpec(
        layer_count=_as_int(tx_pcb_data.get("layer_count"), 2),
        total_thickness_mm=_as_float(tx_pcb_data.get("total_thickness_mm"), 0.0),
        dielectric_material=str(tx_pcb_data.get("dielectric_material", "FR4")),
        dielectric_epsilon_r=_as_float(tx_pcb_data.get("dielectric_epsilon_r"), 0.0),
        stackup=stackup,
    )
    tx_coil_data = _get_dict(tx_data, "coil")
    outer_faces_data = _get_dict(tx_coil_data, "outer_faces")
    tx_outer_faces = TxCoilOuterFacesSpec(
        pos_x=_as_bool(outer_faces_data.get("pos_x"), True),
        neg_x=_as_bool(outer_faces_data.get("neg_x"), True),
        pos_y=_as_bool(outer_faces_data.get("pos_y"), True),
        neg_y=_as_bool(outer_faces_data.get("neg_y"), True),
        pos_z=_as_bool(outer_faces_data.get("pos_z"), True),
        neg_z=_as_bool(outer_faces_data.get("neg_z"), True),
    )
    raw_inner_spacing = tx_coil_data.get("inner_spacing_ratio")
    if raw_inner_spacing is None:
        inner_spacing_ratio: tuple[float, ...] = ()
    elif isinstance(raw_inner_spacing, list):
        inner_spacing_ratio = tuple(_as_float(value, 0.0) for value in raw_inner_spacing)
    else:
        raise SpecValidationError("Expected list for tx.coil.inner_spacing_ratio")
    trace_layer_default = tx_pcb.layer_count if tx_pcb.layer_count > 0 else 0
    tx_coil = TxCoilSpec(
        type=str(tx_coil_data.get("type", "pcb_trace")),
        trace_layer_count=_as_int(tx_coil_data.get("trace_layer_count"), trace_layer_default),
        inner_plane_axis=str(tx_coil_data.get("inner_plane_axis", "yz")),
        max_inner_pcb_count=_as_int(tx_coil_data.get("max_inner_pcb_count"), 0),
        inner_pcb_count=_as_int(tx_coil_data.get("inner_pcb_count"), 0),
        inner_spacing_ratio=inner_spacing_ratio,
        outer_faces=tx_outer_faces,
    )
    _validate_tx_inner_pcb_spec(tx_pcb, tx_coil)
    tx_module_data = _get_dict(tx_data, "module")
    tx_module = ModuleSpec(
        present=_as_bool(tx_module_data.get("present"), False),
        model=_as_bool(tx_module_data.get("model"), True),
        outer_w_mm=_range_from_value(tx_module_data.get("outer_w_mm"), [DEFAULT_CORE_W_MM, DEFAULT_CORE_W_MM, 0.0]),
        outer_h_mm=_range_from_value(tx_module_data.get("outer_h_mm"), [DEFAULT_CORE_H_MM, DEFAULT_CORE_H_MM, 0.0]),
        thickness_mm=_range_from_value(tx_module_data.get("thickness_mm"), [0.0, 0.0, 0.0]),
        offset_from_coil_mm=_range_from_value(tx_module_data.get("offset_from_coil_mm"), [0.0, 0.0, 0.0]),
    )
    tx_position_defaults = {
        "center_x_mm": [0.0, 0.0, 0.0],
        "center_y_mm": [0.0, 0.0, 0.0],
        "center_z_mm": [0.0, 0.0, 0.0],
    }
    tx_position = _parse_position(_get_dict(tx_data, "position"), tx_position_defaults)
    tx = TxSpec(module=tx_module, position=tx_position, pcb=tx_pcb, coil=tx_coil)

    rx_data = _get_dict(data, "rx")
    rx_module_data = _get_dict(rx_data, "module")
    rx_module = ModuleSpec(
        present=_as_bool(rx_module_data.get("present"), False),
        model=_as_bool(rx_module_data.get("model"), True),
        outer_w_mm=_range_from_value(rx_module_data.get("outer_w_mm"), [DEFAULT_CORE_W_MM, DEFAULT_CORE_W_MM, 0.0]),
        outer_h_mm=_range_from_value(rx_module_data.get("outer_h_mm"), [DEFAULT_CORE_H_MM, DEFAULT_CORE_H_MM, 0.0]),
        thickness_mm=_range_from_value(rx_module_data.get("thickness_mm"), [0.0, 0.0, 0.0]),
        offset_from_coil_mm=_range_from_value(rx_module_data.get("offset_from_coil_mm"), [0.0, 0.0, 0.0]),
    )
    rx_position_defaults = {
        "center_x_mm": [0.0, 0.0, 0.0],
        "center_y_mm": [0.0, 0.0, 0.0],
        "center_z_mm": [0.0, 0.0, 0.0],
    }
    rx_position = _parse_position(_get_dict(rx_data, "position"), rx_position_defaults)
    rx_stack_data = _get_dict(rx_data, "stack")
    rx_stack = RxStackSpec(
        total_thickness_mm=_range_from_value(rx_stack_data.get("total_thickness_mm"), [0.0, 0.0, 0.0])
    )
    rx = RxSpec(module=rx_module, position=rx_position, stack=rx_stack)

    tv_data = _get_dict(data, "tv")
    tv_position_defaults = {
        "center_x_mm": None,
        "center_y_mm": [0.0, 0.0, 0.0],
        "center_z_mm": [0.0, 0.0, 0.0],
    }
    tv = TvSpec(
        present=_as_bool(tv_data.get("present"), False),
        model=_as_bool(tv_data.get("model"), False),
        width_mm=_range_from_value(tv_data.get("width_mm"), [0.0, 0.0, 0.0]),
        height_mm=_range_from_value(tv_data.get("height_mm"), [0.0, 0.0, 0.0]),
        thickness_mm=_range_from_value(tv_data.get("thickness_mm"), [0.0, 0.0, 0.0]),
        position=_parse_position(_get_dict(tv_data, "position"), tv_position_defaults),
    )

    wall_data = _get_dict(data, "wall")
    wall_position_defaults = {
        "center_x_mm": None,
        "center_y_mm": [0.0, 0.0, 0.0],
        "center_z_mm": [0.0, 0.0, 0.0],
    }
    wall = WallSpec(
        present=_as_bool(wall_data.get("present"), False),
        model=_as_bool(wall_data.get("model"), False),
        thickness_mm=_range_from_value(wall_data.get("thickness_mm"), [0.0, 0.0, 0.0]),
        size_y_mm=_range_from_value(wall_data.get("size_y_mm"), [0.0, 0.0, 0.0]),
        size_z_mm=_range_from_value(wall_data.get("size_z_mm"), [0.0, 0.0, 0.0]),
        position=_parse_position(_get_dict(wall_data, "position"), wall_position_defaults),
    )

    floor_data = _get_dict(data, "floor")
    floor_position_defaults = {
        "center_x_mm": [0.0, 0.0, 0.0],
        "center_y_mm": [0.0, 0.0, 0.0],
        "center_z_mm": None,
    }
    floor = FloorSpec(
        present=_as_bool(floor_data.get("present"), False),
        model=_as_bool(floor_data.get("model"), False),
        thickness_mm=_range_from_value(floor_data.get("thickness_mm"), [0.0, 0.0, 0.0]),
        size_x_mm=_range_from_value(floor_data.get("size_x_mm"), [0.0, 0.0, 0.0]),
        size_y_mm=_range_from_value(floor_data.get("size_y_mm"), [0.0, 0.0, 0.0]),
        position=_parse_position(_get_dict(floor_data, "position"), floor_position_defaults),
    )

    return Type1Spec(
        units=units,
        coordinate_system=coordinate_system,
        constraints=constraints,
        layout=layout,
        materials=materials,
        tx=tx,
        rx=rx,
        tv=tv,
        wall=wall,
        floor=floor,
    )
