from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from peetsfea.domain.type1.sampled_models import MaterialSample
from peetsfea.geometry.plan import DesignVariable, ParametricGeometryPlan


@dataclass(frozen=True)
class Maxwell3dConfig:
    solution_type: str = "Magnetostatic"
    non_graphical: bool = False
    new_desktop: bool = False
    close_on_exit: bool = False


def _material_name(core: MaterialSample) -> str:
    return "CoreMaterial"


def _format_design_value(value: float | str, units: str | None, default_units: str) -> str:
    if isinstance(value, str):
        return value
    use_units = units or default_units
    return f"{value}{use_units}"


def apply_parametric_geometry_plan(
    plan: ParametricGeometryPlan,
    project_path: Path,
    design_name: str,
    core_material: MaterialSample | None = None,
    config: Maxwell3dConfig | None = None,
) -> None:
    from ansys.aedt.core import Maxwell3d

    cfg = config or Maxwell3dConfig()
    app: Maxwell3d | None = None
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
            mat = mat_name if box.material == "core" else "vacuum"
            obj = modeler.create_box(
                list(box.corner_expr),
                list(box.size_expr),
                name=box.name,
                matname=mat,
            )
            if obj:
                try:
                    modeler.set_object_model_state([obj.name], model=box.model)
                except Exception:
                    obj.model = box.model

        app.save_project()
    finally:
        if app is not None:
            app.release_desktop(close_projects=False, close_desktop=False)
