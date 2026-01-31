from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from peetsfea.domain.type1.sampled_models import MaterialSample
from peetsfea.geometry.plan import DesignVariable, ParametricGeometryPlan
from peetsfea.logging_utils import log_action


@dataclass(frozen=True)
class Maxwell3dConfig:
    solution_type: str = "Magnetostatic"
    non_graphical: bool = False
    new_desktop: bool = False
    close_on_exit: bool = False


def _material_name(core: MaterialSample) -> str:
    return "CoreMaterial"


def _resolve_material_name(material: str, core_name: str) -> str:
    if material == "core":
        return core_name
    if material == "copper":
        return "copper"
    if material == "fr4":
        return "FR4_epoxy"
    return "vacuum"


def _set_object_color(obj: Any, material: str) -> None:
    try:
        if material == "copper":
            obj.color = (184, 115, 51)
        elif material == "fr4":
            obj.color = (30, 110, 30)
    except Exception:
        return


def _format_design_value(value: float | str, units: str | None, default_units: str) -> str:
    if isinstance(value, str):
        return value
    use_units = units or default_units
    return f"{value}{use_units}"


def _apply_material_override_prefix(
    modeler: Any,
    materials: Any,
    *,
    prefix: str,
    material: str,
) -> dict[str, Any]:
    try:
        if material not in getattr(materials, "material_keys", []):
            try:
                materials.add_material(material)
            except Exception:
                pass
    except Exception:
        pass

    object_names = []
    try:
        object_names = list(getattr(modeler, "object_names", []))
    except Exception:
        object_names = []

    targets = [name for name in object_names if name.startswith(prefix)]

    applied = 0
    failed: list[str] = []
    for name in targets:
        try:
            obj = modeler.get_object_from_name(name)
            if obj:
                obj.material_name = material
                applied += 1
        except Exception:
            failed.append(name)

    return {
        "prefix": prefix,
        "material": material,
        "matched_count": len(targets),
        "applied_count": applied,
        "failed_count": len(failed),
        "failed_names": failed[:20],
    }


@log_action(
    "apply_parametric_geometry_plan",
    lambda plan, project_path, design_name, **kwargs: {
        "project_path": str(project_path),
        "design_name": design_name,
        "box_count": len(plan.boxes),
        "variable_count": len(plan.variables),
        "operation_count": len(plan.operations),
    },
)
def apply_parametric_geometry_plan(
    plan: ParametricGeometryPlan,
    project_path: Path,
    design_name: str,
    core_material: MaterialSample | None = None,
    config: Maxwell3dConfig | None = None,
) -> dict[str, Any]:
    from ansys.aedt.core import Maxwell3d

    cfg = config or Maxwell3dConfig()
    app: Maxwell3d | None = None
    report: dict[str, Any] = {"material_overrides": []}
    try:
        app = Maxwell3d(
            project=str(project_path),
            design=design_name,
            solution_type=cfg.solution_type,
            non_graphical=cfg.non_graphical,
            new_desktop=cfg.new_desktop,
            close_on_exit=cfg.close_on_exit,
        )
        from ansys.aedt.core.modeler.modeler_3d import Modeler3D
        from ansys.aedt.core.modules.material_lib import Materials
        assert isinstance(app.modeler, Modeler3D)
        assert isinstance(app.materials, Materials)
        
        modeler = app.modeler
        materials = app.materials
        modeler.model_units = plan.units_length

        mat_name = "vacuum"
        if core_material is not None:
            try:
                mat_name = _material_name(core_material)
                if mat_name not in materials.material_keys:
                    mat = materials.add_material(mat_name)
                else:
                    mat = materials[mat_name]
                if not mat:
                    raise RuntimeError("Material creation failed")
                if core_material.mu_r != -1:
                    mat.permeability = core_material.mu_r
                if core_material.epsilon_r != -1:
                    mat.permittivity = core_material.epsilon_r
                if core_material.conductivity_s_per_m != -1:
                    mat.conductivity = core_material.conductivity_s_per_m
            except Exception:
                mat_name = "vacuum"

        for var in plan.variables:
            if var.is_expression:
                continue
            app[var.name] = _format_design_value(var.value, var.units, plan.units_length)

        for var in plan.variables:
            if not var.is_expression:
                continue
            expr = _format_design_value(var.value, var.units, plan.units_length)
            app[var.name] = expr

        for box in plan.boxes:
            mat = _resolve_material_name(box.material, mat_name)
            if mat not in materials.material_keys:
                try:
                    materials.add_material(mat)
                except Exception:
                    mat = "vacuum"
            obj = modeler.create_box(
                list(box.corner_expr),
                list(box.size_expr),
                name=box.name,
                matname=mat,
            )
            if obj:
                _set_object_color(obj, box.material)
                try:
                    modeler.set_object_model_state([obj.name], model=box.model)
                except Exception:
                    obj.model = box.model

        existing = set(modeler.object_names)
        for op in plan.operations:
            if op.op == "unite":
                targets = [name for name in op.targets if name in existing]
                if len(targets) < 2:
                    continue
                modeler.unite(targets, purge=False, keep_originals=op.keep_originals)
                existing = set(modeler.object_names)
                continue

            if op.op == "subtract":
                blanks = [name for name in op.targets if name in existing]
                tools = [name for name in op.tools if name in existing]
                if not blanks or not tools:
                    continue
                modeler.subtract(blanks, tools, keep_originals=op.keep_originals)
                existing = set(modeler.object_names)
                continue

            raise ValueError(f"Unknown operation: {op.op!r}")

        # Boolean ops can result in incorrect material assignment in some AEDT workflows.
        # Force key prefixes back to copper as a last step.
        report["material_overrides"].append(
            _apply_material_override_prefix(modeler, materials, prefix="TX_Coil", material="copper")
        )

        app.save_project()
        return report
    finally:
        if app is not None:
            app.release_desktop(close_projects=False, close_desktop=False)
