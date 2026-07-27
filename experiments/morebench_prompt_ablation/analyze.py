#!/usr/bin/env python3
"""Analyze the MoReBench generation/review 2x2 ablation."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from experiments.long_source_distillation.run import write_json
from experiments.long_source_v3.analyze import bootstrap_interval, link_metrics
from experiments.long_source_v3.run import load_reference_clusters


TAGS = (
    "ATOMICITY",
    "CLARITY",
    "REDUNDANCY",
    "BALANCE",
    "GROUNDING",
    "COVERAGE",
    "DISTINCTIVENESS",
    "CONFLICT",
    "ROBUSTNESS",
    "CHECKABILITY",
    "PROBE",
)


def mean(values: Sequence[float]) -> float | None:
    return statistics.mean(values) if values else None


def parse_condition(value: str) -> tuple[str, str]:
    generator, reviewer = value.split("-", 1)
    return generator, reviewer


def factorial_contrasts(
    records: Sequence[dict[str, Any]],
    outcome: str,
) -> dict[str, Any]:
    by_cell: dict[tuple[str, str, int], list[float]] = {}
    for row in records:
        key = (row["generator_style"], row["review_style"], row["seed"])
        by_cell.setdefault(key, []).append(float(row[outcome]))
    seeds = sorted({key[2] for key in by_cell})
    cells = (
        ("conventional", "conventional"),
        ("conventional", "morebench"),
        ("morebench", "conventional"),
        ("morebench", "morebench"),
    )
    complete = [
        seed
        for seed in seeds
        if all((generator, reviewer, seed) in by_cell for generator, reviewer in cells)
    ]

    def cell(generator: str, reviewer: str, seed: int) -> float:
        return statistics.mean(by_cell[(generator, reviewer, seed)])

    primary = [
        cell("morebench", "morebench", seed)
        - cell("conventional", "conventional", seed)
        for seed in complete
    ]
    generator_effect = [
        (
            cell("morebench", "conventional", seed)
            + cell("morebench", "morebench", seed)
            - cell("conventional", "conventional", seed)
            - cell("conventional", "morebench", seed)
        )
        / 2
        for seed in complete
    ]
    reviewer_effect = [
        (
            cell("conventional", "morebench", seed)
            + cell("morebench", "morebench", seed)
            - cell("conventional", "conventional", seed)
            - cell("morebench", "conventional", seed)
        )
        / 2
        for seed in complete
    ]
    interaction = [
        (
            cell("morebench", "morebench", seed)
            - cell("morebench", "conventional", seed)
            - cell("conventional", "morebench", seed)
            + cell("conventional", "conventional", seed)
        )
        for seed in complete
    ]
    return {
        "outcome": outcome,
        "unit": "seed; external auditors averaged within seed",
        "combined_minus_control": bootstrap_interval(primary),
        "generator_main_effect": bootstrap_interval(generator_effect),
        "review_main_effect": bootstrap_interval(reviewer_effect),
        "interaction": bootstrap_interval(interaction),
    }


def contribution_gate(
    contrasts: dict[str, Any],
    heldout_contrasts: dict[str, Any] | None,
) -> dict[str, Any]:
    coverage_ci = contrasts["weighted_cluster_recall"][
        "combined_minus_control"
    ]["ci95"]
    unsupported_ci = contrasts["unsupported_item_rate"][
        "combined_minus_control"
    ]["ci95"]
    heldout_ci = (
        heldout_contrasts["combined_minus_control"]["ci95"]
        if heldout_contrasts
        else [None, None]
    )
    gates = {
        "combined_weighted_recall_improves": (
            "pending"
            if coverage_ci[0] is None
            else ("pass" if coverage_ci[0] > 0 else "fail")
        ),
        "combined_unsupported_rate_not_worse": (
            "pending"
            if unsupported_ci[1] is None
            else ("pass" if unsupported_ci[1] <= 0 else "fail")
        ),
        "combined_independent_heldout_accuracy_improves": (
            "pending"
            if heldout_ci[0] is None
            else ("pass" if heldout_ci[0] > 0 else "fail")
        ),
    }
    values = list(gates.values())
    return {
        "overall": (
            "fail"
            if "fail" in values
            else ("pending" if "pending" in values else "pass")
        ),
        "gates": gates,
    }


def analyze(
    root: Path,
    reference_path: Path,
    heldout_path: Path | None = None,
) -> dict[str, Any]:
    clusters = load_reference_clusters(reference_path)
    external = []
    diagnostics = []
    for run_dir in sorted((root / "runs").glob("*/*")):
        condition = run_dir.parent.name
        generator, reviewer = parse_condition(condition)
        seed = int(run_dir.name.removeprefix("seed-"))
        for audit_path in sorted((run_dir / "external_audits").glob("*.json")):
            value = json.loads(audit_path.read_text(encoding="utf-8"))
            audit = value.get("result", value)
            external.append(
                {
                    "condition": condition,
                    "generator_style": generator,
                    "review_style": reviewer,
                    "seed": seed,
                    "auditor": audit_path.stem,
                    **link_metrics(audit, clusters),
                }
            )
        critique_path = run_dir / "critique_packet.json"
        if critique_path.exists():
            critique = json.loads(critique_path.read_text(encoding="utf-8"))
            texts = critique["weaknesses"] + critique["revision_suggestions"]
            counts = Counter(
                tag for tag in TAGS for text in texts if f"[{tag}]" in text
            )
            diagnostics.append(
                {
                    "condition": condition,
                    "generator_style": generator,
                    "review_style": reviewer,
                    "seed": seed,
                    "tag_counts": dict(counts),
                    "tagged_fraction": (
                        sum(counts.values()) / max(1, len(texts))
                    ),
                    "major_missing_dimension": critique[
                        "major_missing_dimension"
                    ],
                }
            )
    condition_summary = {}
    for condition in sorted({item["condition"] for item in external}):
        rows = [item for item in external if item["condition"] == condition]
        condition_summary[condition] = {
            "n_external_audits": len(rows),
            "mean_weighted_cluster_recall": mean(
                [item["weighted_cluster_recall"] for item in rows]
            ),
            "mean_material_cluster_recall": mean(
                [item["material_cluster_recall"] for item in rows]
            ),
            "mean_unsupported_items": mean(
                [item["unsupported_items"] for item in rows]
            ),
        }

    def main_effect(factor: str, outcome: str) -> dict[str, float | None]:
        return {
            style: mean(
                [
                    float(row[outcome])
                    for row in external
                    if row[f"{factor}_style"] == style
                ]
            )
            for style in ("conventional", "morebench")
        }

    factorial = {
        outcome: factorial_contrasts(external, outcome)
        for outcome in (
            "weighted_cluster_recall",
            "material_cluster_recall",
            "unsupported_item_rate",
        )
    }
    heldout_factorial = None
    heldout_metadata = None
    if heldout_path:
        heldout_metadata = json.loads(heldout_path.read_text(encoding="utf-8"))
        heldout_records = []
        for record in heldout_metadata["records"]:
            generator, reviewer = parse_condition(record["condition"])
            heldout_records.append(
                {
                    **record,
                    "generator_style": generator,
                    "review_style": reviewer,
                }
            )
        heldout_factorial = factorial_contrasts(heldout_records, "accuracy")
    return {
        "design": "2x2 generator-style by review-style factorial",
        "primary_outcomes": (
            "blinded external text-to-reference links; writer and review self-scores "
            "are diagnostic only"
        ),
        "external_records": external,
        "diagnostic_records": diagnostics,
        "condition_summary": condition_summary,
        "unadjusted_main_effect_means": {
            "generator_weighted_cluster_recall": main_effect(
                "generator", "weighted_cluster_recall"
            ),
            "review_weighted_cluster_recall": main_effect(
                "review", "weighted_cluster_recall"
            ),
            "generator_unsupported_items": main_effect(
                "generator", "unsupported_items"
            ),
            "review_unsupported_items": main_effect(
                "review", "unsupported_items"
            ),
        },
        "seed_paired_factorial_contrasts": factorial,
        "heldout_evaluation": heldout_metadata,
        "heldout_accuracy_factorial_contrasts": heldout_factorial,
        "preregistered_combined_protocol_gate": contribution_gate(
            factorial,
            heldout_factorial,
        ),
        "inference_note": (
            "Bootstrap intervals resample seed-level paired effects after "
            "averaging external auditors. Replicate across traditions before "
            "claiming a contribution."
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--reference-clusters", type=Path, required=True)
    parser.add_argument("--heldout-evaluation", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    write_json(
        args.root / "analysis.json",
        analyze(
            args.root,
            args.reference_clusters,
            args.heldout_evaluation,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
