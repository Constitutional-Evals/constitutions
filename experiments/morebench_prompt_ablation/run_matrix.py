#!/usr/bin/env python3
"""Run or plan the MoReBench ablation over available reference censuses."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from experiments.long_source_atom_census.run import load_traditions


DEFAULT_TRADITIONS = ("stoicism", "christianity", "lockean-rights")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--traditions", default=",".join(DEFAULT_TRADITIONS))
    parser.add_argument("--seeds", default="17,29,43,71,101")
    parser.add_argument("--example-path", type=Path)
    parser.add_argument(
        "--traditions-config",
        type=Path,
        default=Path(__file__).parents[1]
        / "long_source_atom_census"
        / "traditions.json",
    )
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_traditions(args.traditions_config)
    traditions = [
        item.strip() for item in args.traditions.split(",") if item.strip()
    ]
    for tradition in traditions:
        reference_path = (
            args.reference_root / tradition / "reference_clusters.json"
        )
        if not reference_path.exists():
            raise FileNotFoundError(reference_path)
        run_root = args.output_root / tradition
        command = [
            sys.executable,
            "-m",
            "experiments.morebench_prompt_ablation.run",
            "--value-system",
            config[tradition]["value_system"],
            "--reference-clusters",
            str(reference_path),
            "--output-root",
            str(run_root),
            "--seeds",
            args.seeds,
        ]
        if args.plan_only:
            command.append("--plan-only")
        if args.example_path:
            command.extend(["--example-path", str(args.example_path)])
        subprocess.run(command, check=True)
        if not args.plan_only:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "experiments.morebench_prompt_ablation.analyze",
                    "--root",
                    str(run_root),
                    "--reference-clusters",
                    str(reference_path),
                ],
                check=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
