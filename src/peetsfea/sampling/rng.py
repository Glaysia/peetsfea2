from __future__ import annotations

import random

from peetsfea.domain.type1.spec_models import IntRangeSpec, RangeSpec


def sample_range(rng: random.Random, spec: RangeSpec) -> float:
    if spec.min == -1 or spec.max == -1:
        return -1.0
    if spec.step == 0 or spec.max == spec.min:
        return spec.min
    steps = int(round((spec.max - spec.min) / spec.step))
    if steps <= 0:
        return spec.min
    return spec.min + rng.randint(0, steps) * spec.step


def sample_int_range(rng: random.Random, spec: IntRangeSpec) -> int:
    if spec.step == 0 or spec.max == spec.min:
        return spec.min
    steps = (spec.max - spec.min) // spec.step
    if steps <= 0:
        return spec.min
    return spec.min + rng.randint(0, steps) * spec.step


def half_size(value: float) -> float:
    return value / 2.0 if value > 0 else 0.0
