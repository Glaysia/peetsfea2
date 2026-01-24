from __future__ import annotations

from pathlib import Path

from peetsfea.domain.type1.parse import parse_type1_spec_dict
from peetsfea.domain.type1.spec_models import Type1Spec
from peetsfea.spec.io import load_toml


def load_type1_spec(path: Path) -> Type1Spec:
    return parse_type1_spec_dict(load_toml(path))
