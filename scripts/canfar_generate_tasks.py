#!/usr/bin/env python3
"""Generate JSON task lists for CANFAR/HTCondor array jobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


RUBIN_BANDS = ("u", "g", "r", "i", "z", "y")


def parse_csv(text: str, cast=str) -> list:
    values = [item.strip() for item in text.split(",") if item.strip()]
    return [cast(value) for value in values]


def validate_bands(bands: Iterable[str]) -> list[str]:
    selected = list(bands)
    unknown = [band for band in selected if band not in RUBIN_BANDS]
    if not selected:
        raise ValueError("At least one band is required")
    if unknown:
        raise ValueError(f"Unknown Rubin band(s): {unknown}")
    return selected


def build_common_task(args, *, band: str, seed: int, name: str) -> dict:
    task = {
        "name": name,
        "mode": args.mode,
        "band": band,
        "n_clusters": args.n_clusters,
        "profile": args.profile,
        "method": args.method,
        "mag_min": args.mag_min,
        "mag_max": args.mag_max,
        "r_half_min": args.r_half_min,
        "r_half_max": args.r_half_max,
        "seed": seed,
    }
    if args.method == "discrete":
        task.update(
            {
                "n_stars_min": args.n_stars_min,
                "n_stars_max": args.n_stars_max,
                "imf": args.imf,
            }
        )
    return task


def generate_tasks(args) -> list[dict]:
    bands = validate_bands(parse_csv(args.bands))
    tasks = []
    seed = args.start_seed

    if args.mode == "rsp":
        tracts = parse_csv(args.tracts, int)
        patches = parse_csv(args.patches, int)
        if not tracts or not patches:
            raise ValueError("RSP task generation requires --tracts and --patches")

        for tract in tracts:
            for patch in patches:
                for band in bands:
                    name = f"{args.name_prefix}_tract{tract}_patch{patch}_{band}"
                    task = build_common_task(args, band=band, seed=seed, name=name)
                    task.update(
                        {
                            "repo": args.repo,
                            "collection": args.collection,
                            "tract": tract,
                            "patch": patch,
                        }
                    )
                    tasks.append(task)
                    seed += 1

    elif args.mode == "tap":
        ras = parse_csv(args.ras, float)
        decs = parse_csv(args.decs, float)
        if len(ras) != len(decs):
            raise ValueError("TAP task generation requires the same number of RA and Dec values")
        if not ras:
            raise ValueError("TAP task generation requires --ras and --decs")

        for field_index, (ra, dec) in enumerate(zip(ras, decs)):
            for band in bands:
                name = f"{args.name_prefix}_field{field_index:03d}_{band}"
                task = build_common_task(args, band=band, seed=seed, name=name)
                task.update(
                    {
                        "token_env": args.token_env,
                        "ra": ra,
                        "dec": dec,
                        "size": args.size,
                    }
                )
                tasks.append(task)
                seed += 1

    elif args.mode == "mock":
        for index in range(args.n_mock_tasks):
            for band in bands:
                name = f"{args.name_prefix}_mock{index:03d}_{band}"
                tasks.append(build_common_task(args, band=band, seed=seed, name=name))
                seed += 1
    else:
        raise ValueError(f"Unsupported mode: {args.mode}")

    return tasks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate CANFAR task JSON for INJECT jobs")
    parser.add_argument("--output", default="configs/canfar_tasks.generated.json")
    parser.add_argument("--mode", choices=["rsp", "tap", "mock"], default="rsp")
    parser.add_argument("--name-prefix", default="inject")
    parser.add_argument("--bands", default="i", help="Comma-separated bands, e.g. i or g,r,i")
    parser.add_argument("--start-seed", type=int, default=1000)

    parser.add_argument("--n-clusters", type=int, default=100)
    parser.add_argument("--profile", choices=["plummer", "king", "eff", "sersic"], default="plummer")
    parser.add_argument("--method", choices=["smooth", "discrete"], default="smooth")
    parser.add_argument("--mag-min", type=float, default=20.0)
    parser.add_argument("--mag-max", type=float, default=24.0)
    parser.add_argument("--r-half-min", type=float, default=3.0)
    parser.add_argument("--r-half-max", type=float, default=20.0)
    parser.add_argument("--n-stars-min", type=int, default=50)
    parser.add_argument("--n-stars-max", type=int, default=500)
    parser.add_argument("--imf", choices=["kroupa", "chabrier", "salpeter"], default="kroupa")

    parser.add_argument("--repo", default="dp02")
    parser.add_argument("--collection", default="2.2i/runs/DP0.2")
    parser.add_argument("--tracts", default="", help="Comma-separated tract IDs for RSP mode")
    parser.add_argument("--patches", default="", help="Comma-separated patch IDs for RSP mode")

    parser.add_argument("--token-env", default="RUBIN_TOKEN")
    parser.add_argument("--ras", default="", help="Comma-separated RA values for TAP mode")
    parser.add_argument("--decs", default="", help="Comma-separated Dec values for TAP mode")
    parser.add_argument("--size", type=float, default=120.0)

    parser.add_argument("--n-mock-tasks", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tasks = generate_tasks(args)
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump({"tasks": tasks}, handle, indent=2)
        handle.write("\n")

    print(f"[canfar-generate] wrote {len(tasks)} task(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())