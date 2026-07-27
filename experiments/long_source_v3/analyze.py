#!/usr/bin/env python3
"""Aggregate long-source v3 audits without using hidden writer provenance."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from experiments.long_source_distillation.run import write_json
from experiments.long_source_v3.run import cluster_ids


def link_metrics(
    audit: dict[str, Any],
    clusters: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    best: dict[str, float] = defaultdict(float)
    for link in audit["links"]:
        credit = 1.0 if link["status"] == "material" else 0.5
        best[link["cluster_id"]] = max(best[link["cluster_id"]], credit)
    weights = {
        item["cluster_id"]: float(item.get("weight", 1.0)) for item in clusters
    }
    return {
        "cluster_recall": sum(best.get(item, 0.0) for item in weights)
        / max(1, len(weights)),
        "weighted_cluster_recall": sum(
            weights[item] * best.get(item, 0.0) for item in weights
        )
        / max(1.0, sum(weights.values())),
        "material_cluster_recall": sum(best.get(item, 0.0) == 1.0 for item in weights)
        / max(1, len(weights)),
        "unsupported_items": len(set(audit["unsupported_item_ids"])),
        "unsupported_item_rate": len(set(audit["unsupported_item_ids"])) / 14,
        "finding_count": len(audit["findings"]),
    }


def mean(values: Sequence[float]) -> float | None:
    return statistics.mean(values) if values else None


def percentile(values: Sequence[float], proportion: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def bootstrap_interval(
    values: Sequence[float],
    *,
    seed: int = 20260727,
    replicates: int = 10000,
) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "ci95": [None, None]}
    rng = random.Random(seed)
    samples = [
        statistics.mean(rng.choice(values) for _ in values)
        for _ in range(replicates)
    ]
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "ci95": [percentile(samples, 0.025), percentile(samples, 0.975)],
    }


def condition_contrast(
    records: Sequence[dict[str, Any]],
    condition: str,
    baseline: str,
    outcome: str,
) -> dict[str, Any]:
    by_cell: dict[tuple[str, int], list[float]] = defaultdict(list)
    for record in records:
        by_cell[(record["condition"], record["seed"])].append(
            float(record[outcome])
        )
    common_seeds = sorted(
        {
            seed
            for current, seed in by_cell
            if current == condition and (baseline, seed) in by_cell
        }
    )
    differences = [
        statistics.mean(by_cell[(condition, seed)])
        - statistics.mean(by_cell[(baseline, seed)])
        for seed in common_seeds
    ]
    result = bootstrap_interval(differences)
    result.update(
        {
            "contrast": f"{condition} - {baseline}",
            "outcome": outcome,
            "unit": "seed; auditors averaged within seed",
        }
    )
    return result


def decision_gates(
    paired: dict[str, Any],
    resources: Sequence[dict[str, Any]],
    router: dict[str, Any],
    heldout: dict[str, Any],
    heldout_contrasts: dict[str, Any],
) -> dict[str, Any]:
    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in resources:
        by_condition[record["condition"]].append(record)
    oracle_peak = mean(
        [
            float(item["maximum_initial_evidence_call_chars"])
            for item in by_condition.get("oracle", [])
        ]
    )
    gates = {}
    for condition, outcomes in paired.items():
        quality_ci = outcomes["weighted_cluster_recall"]["ci95"]
        unsupported_ci = outcomes["unsupported_item_rate"]["ci95"]
        quality = (
            "pending"
            if quality_ci[0] is None
            else ("pass" if quality_ci[0] >= -0.05 else "fail")
        )
        unsupported = (
            "pending"
            if unsupported_ci[1] is None
            else ("pass" if unsupported_ci[1] <= 0.05 else "fail")
        )
        peaks = [
            float(item["maximum_initial_evidence_call_chars"])
            for item in by_condition.get(condition, [])
        ]
        mean_peak = mean(peaks)
        peak_ratio = (
            mean_peak / oracle_peak
            if (
                mean_peak is not None
                and oracle_peak is not None
                and oracle_peak != 0
            )
            else None
        )
        peak_context = (
            "pending"
            if peak_ratio is None
            else ("pass" if peak_ratio <= 0.60 else "fail")
        )
        heldout_result = heldout_contrasts.get(condition)
        heldout_ci = heldout_result["ci95"] if heldout_result else [None, None]
        heldout_gate = (
            "pending"
            if not heldout.get("final_validation") or heldout_ci[0] is None
            else ("pass" if heldout_ci[0] >= -0.05 else "fail")
        )
        condition_gates = {
            "weighted_recall_noninferiority_margin_minus_0_05": quality,
            "unsupported_rate_difference_at_most_plus_0_05": unsupported,
            "peak_evidence_context_at_most_60pct_oracle": peak_context,
            "independent_heldout_accuracy_margin_minus_0_05": heldout_gate,
        }
        if condition == "pre-extraction":
            chunk_fraction = router.get("selected_chunk_fraction")
            conflict_recall = router.get("conflict_exception_cluster_recall")
            condition_gates.update(
                {
                    "extract_at_most_70pct_chunks": (
                        "pending"
                        if chunk_fraction is None
                        else ("pass" if chunk_fraction <= 0.70 else "fail")
                    ),
                    "router_conflict_exception_recall_at_least_0_90": (
                        "pending"
                        if conflict_recall is None
                        else ("pass" if conflict_recall >= 0.90 else "fail")
                    ),
                }
            )
        values = list(condition_gates.values())
        overall = (
            "fail"
            if "fail" in values
            else ("pending" if "pending" in values else "pass")
        )
        gates[condition] = {
            "overall": overall,
            "gates": condition_gates,
            "peak_context_ratio_vs_oracle": peak_ratio,
        }
    return gates


def analyze(root: Path, tradition: str) -> dict[str, Any]:
    base = root / tradition
    clusters = json.loads(
        (base / "reference_clusters.json").read_text(encoding="utf-8")
    )
    cluster_ids(clusters)
    records = []
    for audit_path in sorted((base / "runs").glob("*/*/audits/*.json")):
        seed_dir = audit_path.parents[1]
        condition = audit_path.parents[2].name
        seed = int(seed_dir.name.removeprefix("seed-"))
        audit_value = json.loads(audit_path.read_text(encoding="utf-8"))
        audit = audit_value.get("result", audit_value)
        records.append(
            {
                "condition": condition,
                "seed": seed,
                "reviewer": audit_path.stem,
                **link_metrics(audit, clusters),
            }
        )
    grouped = {}
    for condition in sorted({record["condition"] for record in records}):
        subset = [record for record in records if record["condition"] == condition]
        grouped[condition] = {
            "n_audits": len(subset),
            "mean_cluster_recall": mean(
                [item["cluster_recall"] for item in subset]
            ),
            "mean_weighted_cluster_recall": mean(
                [item["weighted_cluster_recall"] for item in subset]
            ),
            "mean_material_cluster_recall": mean(
                [item["material_cluster_recall"] for item in subset]
            ),
            "mean_unsupported_items": mean(
                [item["unsupported_items"] for item in subset]
            ),
            "mean_unsupported_item_rate": mean(
                [item["unsupported_item_rate"] for item in subset]
            ),
        }
    paired_contrasts = {
        condition: {
            outcome: condition_contrast(
                records,
                condition,
                "oracle",
                outcome,
            )
            for outcome in (
                "weighted_cluster_recall",
                "material_cluster_recall",
                "unsupported_item_rate",
            )
        }
        for condition in sorted({item["condition"] for item in records} - {"oracle"})
    }
    heldout_path = base / "heldout" / "evaluation.json"
    heldout = (
        json.loads(heldout_path.read_text(encoding="utf-8"))
        if heldout_path.exists()
        else {
            "status": "blocked-pending-human-adjudication-and-evaluation",
            "records": [],
        }
    )
    router_path = base / "router" / "audit.json"
    router = (
        json.loads(router_path.read_text(encoding="utf-8"))
        if router_path.exists()
        else {"status": "pending-full-census-router-audit"}
    )
    resources = []
    for path in sorted((base / "runs").glob("*/*/resource_manifest.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        value["seed"] = int(path.parent.name.removeprefix("seed-"))
        resources.append(value)
    heldout_contrasts = {}
    if heldout.get("records"):
        heldout_contrasts = {
            condition: condition_contrast(
                heldout["records"],
                condition,
                "oracle",
                "accuracy",
            )
            for condition in sorted(
                {item["condition"] for item in heldout["records"]} - {"oracle"}
            )
        }
    gates = decision_gates(
        paired_contrasts,
        resources,
        router,
        heldout,
        heldout_contrasts,
    )
    return {
        "tradition": tradition,
        "primary_metrics_use_blinded_text_to_cluster_links": True,
        "writer_provenance_excluded_from_primary_metrics": True,
        "records": records,
        "condition_summary": grouped,
        "paired_bootstrap_contrasts": paired_contrasts,
        "resource_records": resources,
        "router_audit": router,
        "heldout_evaluation": heldout,
        "heldout_accuracy_contrasts": heldout_contrasts,
        "preregistered_decision_gates": gates,
        "inference_note": (
            "Confidence intervals resample seed-level paired differences. With "
            "five seeds they are descriptive; tradition is the replication unit "
            "for cross-tradition claims."
        ),
    }


def write_csv(path: Path, records: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "condition",
        "seed",
        "reviewer",
        "cluster_recall",
        "weighted_cluster_recall",
        "material_cluster_recall",
        "unsupported_items",
        "unsupported_item_rate",
        "finding_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--tradition", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = analyze(args.root, args.tradition)
    output = args.root / args.tradition
    write_json(output / "analysis.json", result)
    write_csv(output / "audit_records.csv", result["records"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
