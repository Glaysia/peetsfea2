from __future__ import annotations

from typing import Any, Optional

from ..errors import SpecValidationError
from .spec_models import (
    ConstraintsSpec,
    CoordinateSystemSpec,
    FloorSpec,
    IntRangeSpec,
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
    TxCoilInstanceSpec,
    TxCoilSpec,
    TxSpec,
    Type1Spec,
    UnitsSpec,
    WallSpec,
)

DEFAULT_CORE_W_MM = 100.0
DEFAULT_CORE_H_MM = 100.0


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


def _int_range_from_value(value: Any, default: Any) -> IntRangeSpec:
    if value is None:
        value = default
    if isinstance(value, IntRangeSpec):
        return value
    if isinstance(value, list):
        if len(value) == 3:
            return IntRangeSpec(_as_int(value[0], 0), _as_int(value[1], 0), _as_int(value[2], 0))
        if len(value) >= 1:
            single = _as_int(value[0], 0)
            return IntRangeSpec(single, single, 0)
        return IntRangeSpec(0, 0, 0)
    if value is None:
        return IntRangeSpec(0, 0, 0)
    single = _as_int(value, 0)
    return IntRangeSpec(single, single, 0)


def _require_keys(data: dict[str, Any], prefix: str, keys: list[str]) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        missing_str = ", ".join(f"{prefix}.{key}" for key in missing)
        raise SpecValidationError(f"Missing required keys: {missing_str}")


def _parse_int_range_vec(value: Any, key: str, expected_len: int) -> tuple[IntRangeSpec, ...]:
    if not isinstance(value, list):
        raise SpecValidationError(f"Expected list for {key}")
    if len(value) != expected_len:
        raise SpecValidationError(f"{key} must have length {expected_len}, got {len(value)}")
    return tuple(_int_range_from_value(item, item) for item in value)


def _parse_range_vec(value: Any, key: str, expected_len: int) -> tuple[RangeSpec, ...]:
    if not isinstance(value, list):
        raise SpecValidationError(f"Expected list for {key}")
    if len(value) != expected_len:
        raise SpecValidationError(f"{key} must have length {expected_len}, got {len(value)}")
    return tuple(_range_from_value(item, item) for item in value)


def _validate_range_spec(name: str, spec: RangeSpec) -> None:
    if spec.min > spec.max:
        raise SpecValidationError(f"{name} must satisfy min <= max")
    if spec.step < 0:
        raise SpecValidationError(f"{name} must satisfy step >= 0")


def _validate_int_range_spec(
    name: str,
    spec: IntRangeSpec,
    *,
    step_allowed: set[int] | None = None,
    min_allowed: int | None = None,
    max_allowed: int | None = None,
) -> None:
    if spec.min > spec.max:
        raise SpecValidationError(f"{name} must satisfy min <= max")
    if spec.step < 0:
        raise SpecValidationError(f"{name} must satisfy step >= 0")
    if step_allowed is not None and spec.step not in step_allowed:
        allowed = ", ".join(str(s) for s in sorted(step_allowed))
        raise SpecValidationError(f"{name}.step must be one of {{{allowed}}}")
    if min_allowed is not None and spec.min < min_allowed:
        raise SpecValidationError(f"{name}.min must be >= {min_allowed}")
    if max_allowed is not None and spec.max > max_allowed:
        raise SpecValidationError(f"{name}.max must be <= {max_allowed}")

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

    schema = str(tx_coil_data.get("schema", ""))
    if schema != "instances_v1":
        raise SpecValidationError("tx.coil.schema must be 'instances_v1'")

    _require_keys(
        tx_coil_data,
        "tx.coil",
        [
            "type",
            "pattern",
            "min_trace_width_mm",
            "min_trace_gap_mm",
            "edge_clearance_mm",
            "fill_scale",
            "pitch_duty",
            "layer_mode_idx",
            "radial_split_top_turn_fraction",
            "radial_split_outer_is_top",
            "max_spiral_count",
            "spiral_count",
            "spiral_turns",
            "spiral_direction_idx",
            "spiral_start_edge_idx",
            "dd_split_axis_idx",
            "dd_gap_mm",
            "dd_split_ratio",
            "trace_layer_count",
            "inner_plane_axis_idx",
            "max_inner_pcb_count",
            "inner_pcb_count",
            "inner_spacing_ratio_half",
            "instances",
        ],
    )

    max_spiral_count = _as_int(tx_coil_data.get("max_spiral_count"), 2)
    if max_spiral_count != 2:
        raise SpecValidationError("tx.coil.max_spiral_count must be 2 (fixed)")

    max_inner_pcb_count = _as_int(tx_coil_data.get("max_inner_pcb_count"), 8)
    half_len = ((max_inner_pcb_count + 1) + 1) // 2

    raw_instances = tx_coil_data.get("instances")
    if not isinstance(raw_instances, list) or not raw_instances:
        raise SpecValidationError("tx.coil.instances must be a non-empty list")

    allowed_faces = {"pos_x", "neg_x", "pos_y", "neg_y", "pos_z", "neg_z"}
    seen_names: set[str] = set()
    instances: list[TxCoilInstanceSpec] = []
    for idx, item in enumerate(raw_instances):
        if not isinstance(item, dict):
            raise SpecValidationError(f"tx.coil.instances[{idx}] must be a table")
        face = str(item.get("face", ""))
        if face not in allowed_faces:
            raise SpecValidationError(f"tx.coil.instances[{idx}].face must be one of {sorted(allowed_faces)}")
        name = str(item.get("name", "")).strip()
        if not name:
            name = f"i{idx}_{face}"
        if not (name[0].isalpha() or name[0] == "_") or not all(c.isalnum() or c == "_" for c in name):
            raise SpecValidationError(
                f"tx.coil.instances[{idx}].name must match [A-Za-z_][A-Za-z0-9_]*, got {name!r}"
            )
        if name in seen_names:
            raise SpecValidationError(f"tx.coil.instances[{idx}].name must be unique, got duplicate {name!r}")
        seen_names.add(name)
        present = _int_range_from_value(item.get("present"), item.get("present"))
        instances.append(TxCoilInstanceSpec(name=name, face=face, present=present))

    spiral_turns = _parse_int_range_vec(tx_coil_data.get("spiral_turns"), "tx.coil.spiral_turns", max_spiral_count)
    spiral_direction_idx = _parse_int_range_vec(
        tx_coil_data.get("spiral_direction_idx"), "tx.coil.spiral_direction_idx", max_spiral_count
    )
    spiral_start_edge_idx = _parse_int_range_vec(
        tx_coil_data.get("spiral_start_edge_idx"), "tx.coil.spiral_start_edge_idx", max_spiral_count
    )

    inner_spacing_ratio_half = _parse_range_vec(
        tx_coil_data.get("inner_spacing_ratio_half"), "tx.coil.inner_spacing_ratio_half", half_len
    )

    tx_coil = TxCoilSpec(
        schema=schema,
        type=str(tx_coil_data.get("type")),
        pattern=str(tx_coil_data.get("pattern")),
        min_trace_width_mm=_range_from_value(tx_coil_data.get("min_trace_width_mm"), tx_coil_data.get("min_trace_width_mm")),
        min_trace_gap_mm=_range_from_value(tx_coil_data.get("min_trace_gap_mm"), tx_coil_data.get("min_trace_gap_mm")),
        edge_clearance_mm=_range_from_value(tx_coil_data.get("edge_clearance_mm"), tx_coil_data.get("edge_clearance_mm")),
        fill_scale=_range_from_value(tx_coil_data.get("fill_scale"), tx_coil_data.get("fill_scale")),
        pitch_duty=_range_from_value(tx_coil_data.get("pitch_duty"), tx_coil_data.get("pitch_duty")),
        layer_mode_idx=_int_range_from_value(tx_coil_data.get("layer_mode_idx"), tx_coil_data.get("layer_mode_idx")),
        radial_split_top_turn_fraction=_range_from_value(
            tx_coil_data.get("radial_split_top_turn_fraction"), tx_coil_data.get("radial_split_top_turn_fraction")
        ),
        radial_split_outer_is_top=_int_range_from_value(
            tx_coil_data.get("radial_split_outer_is_top"), tx_coil_data.get("radial_split_outer_is_top")
        ),
        max_spiral_count=max_spiral_count,
        spiral_count=_int_range_from_value(tx_coil_data.get("spiral_count"), tx_coil_data.get("spiral_count")),
        spiral_turns=spiral_turns,
        spiral_direction_idx=spiral_direction_idx,
        spiral_start_edge_idx=spiral_start_edge_idx,
        dd_split_axis_idx=_int_range_from_value(tx_coil_data.get("dd_split_axis_idx"), tx_coil_data.get("dd_split_axis_idx")),
        dd_gap_mm=_range_from_value(tx_coil_data.get("dd_gap_mm"), tx_coil_data.get("dd_gap_mm")),
        dd_split_ratio=_range_from_value(tx_coil_data.get("dd_split_ratio"), tx_coil_data.get("dd_split_ratio")),
        trace_layer_count=_int_range_from_value(tx_coil_data.get("trace_layer_count"), tx_coil_data.get("trace_layer_count")),
        inner_plane_axis_idx=_int_range_from_value(tx_coil_data.get("inner_plane_axis_idx"), tx_coil_data.get("inner_plane_axis_idx")),
        max_inner_pcb_count=max_inner_pcb_count,
        inner_pcb_count=_int_range_from_value(tx_coil_data.get("inner_pcb_count"), tx_coil_data.get("inner_pcb_count")),
        inner_spacing_ratio_half=inner_spacing_ratio_half,
        instances=tuple(instances),
    )

    _validate_range_spec("tx.coil.min_trace_width_mm", tx_coil.min_trace_width_mm)
    if tx_coil.min_trace_width_mm.min <= 0:
        raise SpecValidationError("tx.coil.min_trace_width_mm.min must be > 0")
    _validate_range_spec("tx.coil.min_trace_gap_mm", tx_coil.min_trace_gap_mm)
    if tx_coil.min_trace_gap_mm.min < 0:
        raise SpecValidationError("tx.coil.min_trace_gap_mm.min must be >= 0")
    _validate_range_spec("tx.coil.edge_clearance_mm", tx_coil.edge_clearance_mm)
    if tx_coil.edge_clearance_mm.min < 0:
        raise SpecValidationError("tx.coil.edge_clearance_mm.min must be >= 0")
    _validate_range_spec("tx.coil.fill_scale", tx_coil.fill_scale)
    if not (0.0 < tx_coil.fill_scale.min <= tx_coil.fill_scale.max <= 1.0):
        raise SpecValidationError("tx.coil.fill_scale must be within (0, 1]")
    _validate_range_spec("tx.coil.pitch_duty", tx_coil.pitch_duty)
    if not (0.0 < tx_coil.pitch_duty.min <= tx_coil.pitch_duty.max <= 1.0):
        raise SpecValidationError("tx.coil.pitch_duty must be within (0, 1]")
    _validate_int_range_spec("tx.coil.layer_mode_idx", tx_coil.layer_mode_idx, step_allowed={0, 1})
    _validate_range_spec("tx.coil.radial_split_top_turn_fraction", tx_coil.radial_split_top_turn_fraction)
    if not (0.0 <= tx_coil.radial_split_top_turn_fraction.min <= tx_coil.radial_split_top_turn_fraction.max <= 1.0):
        raise SpecValidationError("tx.coil.radial_split_top_turn_fraction must be within [0, 1]")
    _validate_int_range_spec("tx.coil.radial_split_outer_is_top", tx_coil.radial_split_outer_is_top, step_allowed={0, 1}, min_allowed=0, max_allowed=1)
    _validate_int_range_spec("tx.coil.spiral_count", tx_coil.spiral_count, step_allowed={0, 1}, min_allowed=1, max_allowed=tx_coil.max_spiral_count)
    for idx, spec_ in enumerate(tx_coil.spiral_turns, start=1):
        _validate_int_range_spec(f"tx.coil.spiral_turns[{idx}]", spec_, step_allowed={0, 1}, min_allowed=1)
    for idx, spec_ in enumerate(tx_coil.spiral_direction_idx, start=1):
        _validate_int_range_spec(f"tx.coil.spiral_direction_idx[{idx}]", spec_, step_allowed={0, 1}, min_allowed=0, max_allowed=1)
    for idx, spec_ in enumerate(tx_coil.spiral_start_edge_idx, start=1):
        _validate_int_range_spec(f"tx.coil.spiral_start_edge_idx[{idx}]", spec_, step_allowed={0, 1}, min_allowed=0, max_allowed=3)
    _validate_int_range_spec("tx.coil.dd_split_axis_idx", tx_coil.dd_split_axis_idx, step_allowed={0, 1}, min_allowed=0, max_allowed=1)
    _validate_range_spec("tx.coil.dd_gap_mm", tx_coil.dd_gap_mm)
    _validate_range_spec("tx.coil.dd_split_ratio", tx_coil.dd_split_ratio)
    if not (0.0 < tx_coil.dd_split_ratio.min <= tx_coil.dd_split_ratio.max < 1.0):
        raise SpecValidationError("tx.coil.dd_split_ratio must be within (0, 1)")
    _validate_int_range_spec("tx.coil.trace_layer_count", tx_coil.trace_layer_count, step_allowed={0, 1}, min_allowed=1, max_allowed=2)
    _validate_int_range_spec("tx.coil.inner_plane_axis_idx", tx_coil.inner_plane_axis_idx, step_allowed={0, 1}, min_allowed=0, max_allowed=2)
    _validate_int_range_spec("tx.coil.inner_pcb_count", tx_coil.inner_pcb_count, step_allowed={0, 1}, min_allowed=0, max_allowed=tx_coil.max_inner_pcb_count)
    if tx_coil.inner_spacing_ratio_half and tx_coil.inner_spacing_ratio_half[0].max <= 0:
        raise SpecValidationError("tx.coil.inner_spacing_ratio_half[0].max must be > 0")
    for idx, spec_ in enumerate(tx_coil.inner_spacing_ratio_half, start=1):
        _validate_range_spec(f"tx.coil.inner_spacing_ratio_half[{idx}]", spec_)
    for idx, inst in enumerate(tx_coil.instances):
        _validate_int_range_spec(
            f"tx.coil.instances[{idx}].present",
            inst.present,
            step_allowed={0, 1},
            min_allowed=0,
            max_allowed=1,
        )
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
