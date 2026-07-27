#!/usr/bin/env python3
"""Run or plan the three-tradition long-source v3 matrix."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence


DEFAULT_TRADITIONS = ("stoicism", "christianity", "lockean-rights")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--reference-root", type=Path)
    parser.add_argument("--traditions", default=",".join(DEFAULT_TRADITIONS))
    parser.add_argument("--conditions", default="oracle,iterative,adaptive,pre-extraction")
    parser.add_argument("--seeds", default="17,29,43,71,101")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    traditions = [
        item.strip() for item in args.traditions.split(",") if item.strip()
    ]
    for tradition in traditions:
        command = [
            sys.executable,
            "-m",
            "experiments.long_source_v3.run",
            "--tradition",
            tradition,
            "--repo-root",
            str(args.repo_root),
            "--output-root",
            str(args.output_root),
            "--conditions",
            args.conditions,
            "--seeds",
            args.seeds,
        ]
        if args.reference_root:
            reference_path = (
                args.reference_root / tradition / "reference_clusters.json"
            )
            census_path = args.reference_root / tradition / "census_atoms.json"
            if reference_path.exists():
                command.extend(["--reference-clusters", str(reference_path)])
            if census_path.exists():
                command.extend(["--reference-census", str(census_path)])
        if args.plan_only:
            command.append("--plan-only")
        subprocess.run(command, check=True)
        if not args.plan_only:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "experiments.long_source_v3.analyze",
                    "--root",
                    str(args.output_root),
                    "--tradition",
                    tradition,
                ],
                check=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
