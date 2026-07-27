#!/usr/bin/env python3
"""Produce post-collection reviewer and probe diagnostics for v2.6."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from experiments.long_source_atom_census.run import model_slug
from experiments.long_source_distillation.run import write_json


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while (
            end + 1 < len(order)
            and values[order[end + 1]] == values[order[start]]
        ):
            end += 1
        rank = (start + end) / 2
        for position in range(start, end + 1):
            ranks[order[position]] = rank
        start = end + 1
    return ranks


def pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = statistics.mean(left)
    right_mean = statistics.mean(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right)
    )
    left_scale = math.sqrt(sum((value - left_mean) ** 2 for value in left))
    right_scale = math.sqrt(sum((value - right_mean) ** 2 for value in right))
    if not left_scale or not right_scale:
        return None
    return numerator / (left_scale * right_scale)


def spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    return pearson(average_ranks(left), average_ranks(right))


def review_path(run_dir: Path, model: str) -> Path:
    return run_dir / "reviews" / f"{model_slug(model)}.json"


def audit_tradition(tradition_dir: Path) -> dict[str, Any]:
    config = read_json(tradition_dir / "experiment_config.json")
    analysis = read_json(tradition_dir.parent / "analysis.json")
    tradition_analysis = next(
        item
        for item in analysis["traditions"]
        if item["tradition"] == config["tradition"]
    )
    run_dirs = [
        tradition_dir / "replicates" / condition / f"seed-{seed}"
        for condition in config["conditions"]
        for seed in config["seeds"]
    ]
    reviews_by_model: dict[str, list[dict[str, Any]]] = {}
    for model in config["reviewer_models"]:
        reviews_by_model[model] = [
            read_json(review_path(run_dir, model)) for run_dir in run_dirs
        ]

    model_summaries = {}
    for model, reviews in reviews_by_model.items():
        coverage_scores = [review["coverage_score"] for review in reviews]
        model_summaries[model] = {
            "candidate_count": len(reviews),
            "coverage_score_distribution": {
                str(score): count
                for score, count in sorted(Counter(coverage_scores).items())
            },
            "median_coverage_score": statistics.median(coverage_scores),
        }

    pair_summaries = []
    models = config["reviewer_models"]
    for left_index, left_model in enumerate(models):
        for right_model in models[left_index + 1 :]:
            left_reviews = reviews_by_model[left_model]
            right_reviews = reviews_by_model[right_model]
            left_scores = [review["coverage_score"] for review in left_reviews]
            right_scores = [review["coverage_score"] for review in right_reviews]
            jaccards = []
            for left_review, right_review in zip(left_reviews, right_reviews):
                left_ids = set(left_review["recovered_cluster_ids"])
                right_ids = set(right_review["recovered_cluster_ids"])
                union = left_ids | right_ids
                jaccards.append(len(left_ids & right_ids) / len(union) if union else 1)
            pair_summaries.append(
                {
                    "left_model": left_model,
                    "right_model": right_model,
                    "coverage_spearman": spearman(left_scores, right_scores),
                    "mean_recovered_cluster_jaccard": statistics.mean(jaccards),
                }
            )

    probes = read_json(tradition_dir / "probe_cases.json")["cases"]
    return {
        "tradition": config["tradition"],
        "candidate_count": len(run_dirs),
        "review_count": sum(len(reviews) for reviews in reviews_by_model.values()),
        "ranking_count": sum(
            (run_dir / "pairwise_ranking.json").exists() for run_dir in run_dirs
        ),
        "reviewers": model_summaries,
        "reviewer_pairs": pair_summaries,
        "probe_count": len(probes),
        "probe_label_counts": dict(
            sorted(Counter(case["aligned_response"] for case in probes).items())
        ),
        "condition_probe_medians": {
            condition: summary["median_probe_target_accuracy"]
            for condition, summary in tradition_analysis["condition_summaries"].items()
        },
    }


def render_report(audit: dict[str, Any]) -> str:
    lines = [
        "# v2.6 Post-Collection Audit",
        "",
        "These diagnostics were specified after collection and do not alter the",
        "preregistered result.",
        "",
    ]
    for tradition in audit["traditions"]:
        lines.extend(
            [
                f"## {tradition['tradition']}",
                "",
                (
                    f"- Artifacts: {tradition['candidate_count']} candidates, "
                    f"{tradition['review_count']} reviews, "
                    f"{tradition['ranking_count']} rankings."
                ),
                (
                    f"- Probes: {tradition['probe_count']} "
                    f"({tradition['probe_label_counts']})."
                ),
                (
                    "- Median probe target accuracy: "
                    + ", ".join(
                        f"{condition}={value:.3f}"
                        for condition, value in tradition[
                            "condition_probe_medians"
                        ].items()
                    )
                    + "."
                ),
                "",
                "| Reviewer | Coverage score distribution | Median |",
                "|---|---|---:|",
            ]
        )
        for model, summary in tradition["reviewers"].items():
            lines.append(
                f"| {model} | {summary['coverage_score_distribution']} | "
                f"{summary['median_coverage_score']:.1f} |"
            )
        lines.extend(
            [
                "",
                "| Reviewer pair | Coverage Spearman | Recovered-cluster Jaccard |",
                "|---|---:|---:|",
            ]
        )
        for pair in tradition["reviewer_pairs"]:
            rho = pair["coverage_spearman"]
            rho_text = "n/a" if rho is None else f"{rho:.3f}"
            lines.append(
                f"| {pair['left_model']} / {pair['right_model']} | {rho_text} | "
                f"{pair['mean_recovered_cluster_jaccard']:.3f} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    traditions = [
        audit_tradition(path)
        for path in sorted(args.output_root.iterdir())
        if path.is_dir() and (path / "experiment_config.json").exists()
    ]
    audit = {
        "status": "post_collection_descriptive_audit",
        "traditions": traditions,
    }
    write_json(args.output_root / "post_collection_audit.json", audit)
    (args.output_root / "post_collection_audit.md").write_text(
        render_report(audit),
        encoding="utf-8",
    )
    print(args.output_root / "post_collection_audit.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
