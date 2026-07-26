#!/usr/bin/env python3
"""Analyze the preregistered long-source atom-census experiment."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

from experiments.long_source_distillation.run import write_json


NONINFERIORITY_MARGIN = -5.0
UNSUPPORTED_RATE_GATE = 0.05
PAIR_AGREEMENT_GATE = 0.90
INPUT_REDUCTION_GATE = 0.40
BOOTSTRAP_SAMPLES = 10_000


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def median(values: Iterable[float]) -> float:
    materialized = list(values)
    return statistics.median(materialized) if materialized else math.nan


def majority(values: Sequence[str]) -> str:
    counts = Counter(values)
    return max(sorted(counts), key=lambda value: counts[value])


def majority_ids(id_sets: Sequence[set[str]]) -> set[str]:
    threshold = len(id_sets) // 2 + 1
    counts = Counter(item for items in id_sets for item in items)
    return {item for item, count in counts.items() if count >= threshold}


def paired_bootstrap_interval(
    differences: Sequence[float],
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = 20260726,
) -> dict[str, float]:
    if not differences:
        return {"estimate": math.nan, "lower_95": math.nan, "upper_95": math.nan}
    rng = random.Random(seed)
    size = len(differences)
    estimates = sorted(
        statistics.mean(rng.choice(differences) for _ in range(size))
        for _ in range(samples)
    )
    return {
        "estimate": statistics.mean(differences),
        "lower_95": estimates[round(0.025 * (samples - 1))],
        "upper_95": estimates[round(0.975 * (samples - 1))],
    }


def analyze_replicate(
    run_dir: Path,
    cluster_weights: dict[str, float],
    reviewer_count: int,
    probe_targets: dict[str, str],
) -> dict[str, Any]:
    reviews = [read_json(path) for path in sorted((run_dir / "reviews").glob("*.json"))]
    if len(reviews) != reviewer_count:
        raise ValueError(
            f"{run_dir}: expected {reviewer_count} reviews, found {len(reviews)}"
        )
    recovered = majority_ids(
        [set(review["recovered_cluster_ids"]) for review in reviews]
    )
    unsupported = majority_ids(
        [set(review["unsupported_item_ids"]) for review in reviews]
    )
    reviewer_unsupported_rates = [
        len(set(review["unsupported_item_ids"])) / 14 for review in reviews
    ]
    total_weight = sum(cluster_weights.values())
    recovered_weight = sum(cluster_weights[item] for item in recovered)
    decisions = {
        item["case_id"]: item["preferred"]
        for item in read_json(run_dir / "pairwise_ranking.json")["decisions"]
    }
    if set(decisions) != set(probe_targets):
        raise ValueError(f"{run_dir}: pairwise decision IDs do not match probes")
    return {
        "coverage_score": median(review["coverage_score"] for review in reviews),
        "grounding_score": median(review["grounding_score"] for review in reviews),
        "redundancy_score": median(review["redundancy_score"] for review in reviews),
        "specificity_score": median(review["specificity_score"] for review in reviews),
        "recovered_cluster_ids": sorted(recovered),
        "recovered_weighted_recall": (
            recovered_weight / total_weight if total_weight else 0.0
        ),
        "unsupported_item_ids": sorted(unsupported),
        "consensus_unsupported_item_rate": len(unsupported) / 14,
        "unsupported_item_rate": median(reviewer_unsupported_rates),
        "pair_decisions": decisions,
        "probe_target_accuracy": sum(
            decisions[case_id] == target for case_id, target in probe_targets.items()
        )
        / len(probe_targets),
        "input_chars": read_json(run_dir / "input_manifest.json")["input_chars"],
    }


def summarize_condition(runs: Sequence[dict[str, Any]]) -> dict[str, float]:
    scalar_keys = (
        "coverage_score",
        "grounding_score",
        "redundancy_score",
        "specificity_score",
        "recovered_weighted_recall",
        "unsupported_item_rate",
        "probe_target_accuracy",
        "pair_agreement_with_exhaustive_consensus",
        "input_chars",
    )
    return {
        f"median_{key}": median(run[key] for run in runs)
        for key in scalar_keys
        if all(key in run for run in runs)
    }


def analyze_tradition(tradition_dir: Path) -> dict[str, Any]:
    config = read_json(tradition_dir / "experiment_config.json")
    census_atoms = read_json(tradition_dir / "census_atoms.json")
    clustering_audit = read_json(tradition_dir / "clustering_partition_audit.json")
    clusters = read_json(tradition_dir / "reference_clusters.json")["clusters"]
    selection = read_json(tradition_dir / "budgeted_selection.json")
    probes = read_json(tradition_dir / "probe_cases.json")["cases"]
    cluster_weights = {
        cluster["cluster_id"]: float(cluster["weight"]) for cluster in clusters
    }
    probe_targets = {case["case_id"]: case["aligned_response"] for case in probes}
    reviewer_count = len(config["reviewer_models"])
    replicates: dict[str, dict[str, dict[str, Any]]] = {}
    for condition in config["conditions"]:
        replicates[condition] = {}
        for seed in config["seeds"]:
            run_dir = tradition_dir / "replicates" / condition / f"seed-{seed}"
            replicates[condition][str(seed)] = analyze_replicate(
                run_dir,
                cluster_weights,
                reviewer_count,
                probe_targets,
            )

    exhaustive_runs = list(replicates["exhaustive"].values())
    exhaustive_consensus = {
        case_id: majority([run["pair_decisions"][case_id] for run in exhaustive_runs])
        for case_id in probe_targets
    }
    for condition_runs in replicates.values():
        for run in condition_runs.values():
            run["pair_agreement_with_exhaustive_consensus"] = sum(
                run["pair_decisions"][case_id] == preferred
                for case_id, preferred in exhaustive_consensus.items()
            ) / len(exhaustive_consensus)

    summaries = {
        condition: summarize_condition(list(condition_runs.values()))
        for condition, condition_runs in replicates.items()
    }
    budgeted_runs = replicates["budgeted"]
    coverage_differences = [
        budgeted_runs[str(seed)]["coverage_score"]
        - replicates["exhaustive"][str(seed)]["coverage_score"]
        for seed in config["seeds"]
    ]
    coverage_interval = paired_bootstrap_interval(coverage_differences)
    exhaustive_input = summaries["exhaustive"]["median_input_chars"]
    budgeted_input = summaries["budgeted"]["median_input_chars"]
    input_reduction = 1 - budgeted_input / exhaustive_input

    selected_ids = set(selection["selected_cluster_ids"])
    high_conflict_ids = {
        cluster["cluster_id"]
        for cluster in clusters
        if {"conflict", "exception"} & set(cluster["atom_kinds"])
        and (len(cluster["extractor_models"]) >= 2 or len(cluster["source_paths"]) >= 2)
    }
    gates = {
        "complete_reference_partition": (
            clustering_audit["complete_partition"]
            and clustering_audit["output_clusters"] == config["max_reference_clusters"]
        ),
        "high_confidence_conflicts_preserved": high_conflict_ids <= selected_ids,
        "coverage_noninferiority": (
            coverage_interval["lower_95"] >= NONINFERIORITY_MARGIN
        ),
        "unsupported_item_rate": (
            summaries["budgeted"]["median_unsupported_item_rate"]
            <= UNSUPPORTED_RATE_GATE
        ),
        "pairwise_agreement": (
            summaries["budgeted"]["median_pair_agreement_with_exhaustive_consensus"]
            >= PAIR_AGREEMENT_GATE
        ),
        "input_reduction": input_reduction >= INPUT_REDUCTION_GATE,
    }
    return {
        "tradition": config["tradition"],
        "config": config,
        "census": {
            "accepted_atoms": len(census_atoms["atoms"]),
            "rejected_atoms": len(census_atoms["rejected_atoms"]),
            "grounding_acceptance_rate": (
                len(census_atoms["atoms"])
                / (len(census_atoms["atoms"]) + len(census_atoms["rejected_atoms"]))
            ),
            "clusters": len(clusters),
            "selected_clusters": len(selected_ids),
            "high_confidence_conflict_clusters": len(high_conflict_ids),
            "weighted_selection_recall": selection["weighted_reference_recall"],
            "conflict_exception_recall": selection["conflict_exception_recall"],
            "clustering_audit": clustering_audit,
        },
        "condition_summaries": summaries,
        "coverage_budgeted_minus_exhaustive": {
            "paired_differences": coverage_differences,
            "bootstrap_95": coverage_interval,
        },
        "input_reduction": input_reduction,
        "exhaustive_pair_consensus": exhaustive_consensus,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "replicates": replicates,
    }


def render_report(results: Sequence[dict[str, Any]], aggregate: dict[str, Any]) -> str:
    lines = [
        "# Long-Source Atom-Census v2 Results",
        "",
        "This report applies the thresholds recorded in the experiment README "
        "before generation.",
        "",
        "## Gate Summary",
        "",
        "| Tradition | Selected weight | Coverage diff (95% CI) | Unsupported | "
        "Pair agreement | Input reduction | Result |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        summary = result["condition_summaries"]["budgeted"]
        interval = result["coverage_budgeted_minus_exhaustive"]["bootstrap_95"]
        lines.append(
            f"| {result['tradition']} | "
            f"{result['census']['weighted_selection_recall']:.3f} | "
            f"{interval['estimate']:.1f} "
            f"[{interval['lower_95']:.1f}, {interval['upper_95']:.1f}] | "
            f"{summary['median_unsupported_item_rate']:.3f} | "
            f"{summary['median_pair_agreement_with_exhaustive_consensus']:.3f} | "
            f"{result['input_reduction']:.3f} | "
            f"{'PASS' if result['all_gates_pass'] else 'FAIL'} |"
        )
    interval = aggregate["coverage_budgeted_minus_exhaustive"]["bootstrap_95"]
    lines.extend(
        [
            "",
            "## Aggregate",
            "",
            f"- Paired coverage difference: {interval['estimate']:.2f} "
            f"(95% bootstrap CI {interval['lower_95']:.2f} to "
            f"{interval['upper_95']:.2f}).",
            f"- All preregistered gates passed in every tradition: "
            f"{aggregate['all_traditions_pass']}.",
            "",
            "## Condition Medians",
            "",
            "| Tradition | Condition | Coverage | Grounding | Specificity | "
            "Recovered weighted recall | Probe target accuracy |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for result in results:
        for condition, summary in result["condition_summaries"].items():
            lines.append(
                f"| {result['tradition']} | {condition} | "
                f"{summary['median_coverage_score']:.1f} | "
                f"{summary['median_grounding_score']:.1f} | "
                f"{summary['median_specificity_score']:.1f} | "
                f"{summary['median_recovered_weighted_recall']:.3f} | "
                f"{summary['median_probe_target_accuracy']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "The budgeted method is supported only if every preregistered gate "
            "passes in all three traditions. Individual metric improvements do "
            "not override a failed gate.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--traditions",
        default="stoicism,christianity,lockean-rights",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    traditions = [item.strip() for item in args.traditions.split(",") if item.strip()]
    results = [
        analyze_tradition(args.output_root / tradition) for tradition in traditions
    ]
    all_differences = [
        difference
        for result in results
        for difference in result["coverage_budgeted_minus_exhaustive"][
            "paired_differences"
        ]
    ]
    aggregate = {
        "coverage_budgeted_minus_exhaustive": {
            "bootstrap_95": paired_bootstrap_interval(all_differences)
        },
        "all_traditions_pass": all(result["all_gates_pass"] for result in results),
    }
    payload = {"traditions": results, "aggregate": aggregate}
    write_json(args.output_root / "analysis.json", payload)
    (args.output_root / "report.md").write_text(
        render_report(results, aggregate),
        encoding="utf-8",
    )
    print(args.output_root / "report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
