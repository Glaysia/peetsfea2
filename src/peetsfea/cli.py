from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from peetsfea.pipeline.runner import run_type1_from_path
from peetsfea.pipeline.serialize import to_dict


def _build_payload(result) -> dict[str, Any]:
    return {
        "sample": to_dict(result.sample),
        "geometry": to_dict(result.geometry),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="peetsfea non-model pipeline")
    parser.add_argument("spec", type=Path, help="Path to spec TOML")
    parser.add_argument("--seed", type=int, default=599, help="Seed for deterministic sampling")
    parser.add_argument("--out", type=Path, default=None, help="Write JSON output to file")
    args = parser.parse_args(argv)

    result = run_type1_from_path(args.spec, args.seed)
    payload = _build_payload(result)
    text = json.dumps(payload, indent=2, sort_keys=True)

    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
