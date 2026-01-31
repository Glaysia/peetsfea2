from __future__ import annotations

import argparse
from pathlib import Path

from peetsfea.aedt.maxwell3d_adapter import Maxwell3dConfig
from peetsfea.pipeline.dataset import write_type1_dataset_sample


def _seed_list(args) -> list[int]:
    if args.seed_range is not None:
        start, end = args.seed_range
        if end < start:
            raise ValueError("--seed-range END must be >= START")
        return list(range(start, end + 1))
    if args.seed:
        return list(args.seed)
    return [args.default_seed]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="peetsfea Type1 dataset pipeline")
    parser.add_argument("spec", type=Path, help="Path to spec TOML")
    parser.add_argument("--out", type=Path, default=Path("out"), help="Dataset root output directory")
    parser.add_argument("--project-name", type=str, default="type1", help="Base name for sample directories")

    seeds = parser.add_mutually_exclusive_group()
    seeds.add_argument("--seed", type=int, action="append", help="Seed (repeatable)")
    seeds.add_argument(
        "--seed-range",
        type=int,
        nargs=2,
        metavar=("START", "END"),
        help="Inclusive seed range [START..END]",
    )
    parser.add_argument("--default-seed", type=int, default=1, help="Seed when no --seed/--seed-range is provided")

    parser.add_argument("--aedt", action="store_true", help="Create Maxwell project per sample (no solve)")
    parser.add_argument("--non-graphical", action="store_true", help="Run AEDT in non-graphical mode")
    parser.add_argument("--new-desktop", action="store_true", help="Force new AEDT desktop instance")
    parser.add_argument("--close-on-exit", action="store_true", help="Close AEDT on exit (best effort)")
    parser.add_argument("--solution-type", type=str, default="Magnetostatic", help="Maxwell solution type")

    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing sample output")

    args = parser.parse_args(argv)

    seeds_list = _seed_list(args)
    cfg = Maxwell3dConfig(
        solution_type=args.solution_type,
        non_graphical=args.non_graphical,
        new_desktop=args.new_desktop,
        close_on_exit=args.close_on_exit,
    )

    for seed in seeds_list:
        result = write_type1_dataset_sample(
            args.spec,
            seed=seed,
            out_root=args.out,
            project_name=args.project_name,
            build_aedt=args.aedt,
            maxwell_config=cfg,
            overwrite=args.overwrite,
        )
        print(f"{result.status}: {result.sample_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

