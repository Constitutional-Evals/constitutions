#!/usr/bin/env python3
"""Run the preregistered atom-census matrix and its analysis."""

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
    parser.add_argument("--reuse-census-root", type=Path)
    parser.add_argument(
        "--traditions",
        default=",".join(DEFAULT_TRADITIONS),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    traditions = [item.strip() for item in args.traditions.split(",") if item.strip()]
    for tradition in traditions:
        command = [
            sys.executable,
            "-m",
            "experiments.long_source_atom_census.run",
            "--tradition",
            tradition,
            "--repo-root",
            str(args.repo_root),
            "--output-root",
            str(args.output_root),
        ]
        reuse_dir = (
            args.reuse_census_root / tradition if args.reuse_census_root else None
        )
        if reuse_dir and (reuse_dir / "census_atoms.json").exists():
            command.extend(["--reuse-census-root", str(args.reuse_census_root)])
        subprocess.run(command, check=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "experiments.long_source_atom_census.analyze",
            "--output-root",
            str(args.output_root),
            "--traditions",
            ",".join(traditions),
        ],
        check=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
