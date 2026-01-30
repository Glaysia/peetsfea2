from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from peetsfea.aedt.maxwell3d_adapter import Maxwell3dConfig, apply_parametric_geometry_plan
from peetsfea.domain.type1.interpreter import Type1Domain, interpret_type1
from peetsfea.domain.type1.parse import parse_type1_spec_dict
from peetsfea.domain.type1.sampled_models import Type1Sample
from peetsfea.domain.type1.spec_models import Type1Spec
from peetsfea.geometry.plan import ParametricGeometryPlan
from peetsfea.geometry.type1.builder import build_type1_parametric_geometry
from peetsfea.logging_utils import log_action
from peetsfea.sampling.type1_sampler import sample_type1
from peetsfea.spec.io import load_toml

PEETSFEA_VERSION = "2.0.0"


@dataclass(frozen=True)
class Type1RunResult:
    spec: Type1Spec
    domain: Type1Domain
    sample: Type1Sample
    geometry: ParametricGeometryPlan


@dataclass(frozen=True)
class Type1AedtResult:
    result: Type1RunResult
    project_path: Path
    design_name: str


def _toml_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()[:6]


def build_project_name(base_name: str, spec_path: Path, seed: int, version: str = PEETSFEA_VERSION) -> str:
    suffix = f"{_toml_hash(spec_path)}_{version}_{seed}"
    return f"{base_name}_{suffix}"


@log_action("run_type1", lambda spec, seed: {"seed": seed})
def run_type1(spec: Type1Spec, seed: int) -> Type1RunResult:
    sample_input = sample_type1(spec, seed)
    domain = interpret_type1(sample_input)
    geometry = build_type1_parametric_geometry(domain.sample)
    return Type1RunResult(
        spec=spec,
        domain=domain,
        sample=domain.sample,
        geometry=geometry,
    )


@log_action("run_type1_from_path", lambda path, seed: {"spec_path": str(path), "seed": seed})
def run_type1_from_path(path: Path, seed: int) -> Type1RunResult:
    spec_dict = load_toml(path)
    spec = parse_type1_spec_dict(spec_dict)
    return run_type1(spec, seed)


@log_action(
    "run_type1_aedt_from_path",
    lambda path, seed, project_name, **kwargs: {
        "spec_path": str(path),
        "seed": seed,
        "project_name": project_name,
        "out_dir": str(kwargs.get("out_dir") or ""),
        "design_name": str(kwargs.get("design_name") or ""),
    },
)
def run_type1_aedt_from_path(
    path: Path,
    seed: int,
    project_name: str,
    *,
    out_dir: Path | None = None,
    design_name: str | None = None,
    config: Maxwell3dConfig | None = None,
) -> Type1AedtResult:
    result = run_type1_from_path(path, seed)
    out_dir = out_dir or path.parent / "aedt"
    out_dir.mkdir(parents=True, exist_ok=True)
    full_name = build_project_name(project_name, path, seed)
    project_path = out_dir / f"{full_name}.aedt"
    design_name = design_name or full_name

    plan: ParametricGeometryPlan = result.geometry
    apply_parametric_geometry_plan(
        plan,
        project_path=project_path,
        design_name=design_name,
        core_material=result.sample.materials_core,
        config=config,
    )

    return Type1AedtResult(
        result=result,
        project_path=project_path,
        design_name=design_name,
    )
