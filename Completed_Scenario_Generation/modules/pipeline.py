"""Multicover selection, checkpointed orchestration, and JSON exports."""

import zipfile
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from . import config as cfg
from .core import atomic_json, normalized_text, read_json, sample_coverage, sort_criterion_ids
from .labels import apply_human_overrides, label_new_survivors, populate_baseline, redundancy_screen
from .stages import (
    batch_stage, choose_target, coverage_table,
    coverage_totals, development_judges_for, generate_batch,
    generation_model_for_batch, m3_supplements,
    make_slots,
    quality_process,
)

def optimize_additions(const, existing, candidates):
    """Lexicographic MILP: quota shortfall → breadth shortfall → fewest additions."""
    counts, hits = sample_coverage(const, existing)
    pool = [row for row in candidates if row.get("relevance")]
    deficits = {c: max(0, cfg.SCENARIO_QUOTA - counts[c]) for c in const}
    breadth = {
        c: max(0, min(cfg.MIN_DISTINCT_CRITERIA, len(spec["criteria"]))
               - sum(hits[c][k["id"]] > 0 for k in spec["criteria"]))
        for c, spec in const.items()
    }
    if not pool:
        return [], {"feasible": not (any(deficits.values()) or any(breadth.values())),
                    "optimal": True, "solver_status": "no_candidates",
                    "remaining_shortfall": sum(deficits.values()),
                    "breadth_shortfall": sum(breadth.values())}

    # x: select candidate; y: newly covered criterion;
    # s/t: nonnegative shortfall slacks (so partial runs remain solvable).
    n = len(pool)
    criteria = [(c, item["id"]) for c, spec in const.items() for item in spec["criteria"]
                if not hits[c][item["id"]]
                and any(item["id"] in row["relevance"].get(c, []) for row in pool)]
    names = list(const)
    y = {pair: n + i for i, pair in enumerate(criteria)}
    s = {c: n + len(y) + i for i, c in enumerate(names)}
    t = {c: n + len(y) + len(names) + i for i, c in enumerate(names)}
    size = n + len(y) + 2 * len(names)
    constraints = []

    for name in names:
        if deficits[name]:
            coefficients = {i: 1 for i, row in enumerate(pool)
                            if row["relevance"].get(name)}
            constraints.append(({**coefficients, s[name]: 1}, deficits[name], np.inf))
        if breadth[name]:
            coefficients = {y[pair]: 1 for pair in criteria if pair[0] == name}
            constraints.append(({**coefficients, t[name]: 1}, breadth[name], np.inf))
    for (name, criterion), index in y.items():
        coefficients = {index: 1}
        coefficients.update({i: -1 for i, row in enumerate(pool)
                             if criterion in row["relevance"].get(name, [])})
        constraints.append((coefficients, -np.inf, 0))

    upper_bounds = np.ones(size)
    for name in names:
        upper_bounds[s[name]], upper_bounds[t[name]] = deficits[name], breadth[name]

    def solve(objective, fixed=()):
        rows = constraints + list(fixed)
        matrix = lil_matrix((len(rows), size), dtype=float)
        lower, upper = [], []
        for i, (coefficients, lo, hi) in enumerate(rows):
            for j, value in coefficients.items():
                matrix[i, j] = value
            lower.append(lo)
            upper.append(hi)
        result = milp(
            c=objective, integrality=np.ones(size, dtype=int),
            bounds=Bounds(np.zeros(size), upper_bounds),
            constraints=LinearConstraint(matrix.tocsr(), lower, upper),
            options={"time_limit": 90, "mip_rel_gap": 0.001},
        )
        if result.x is None:
            raise RuntimeError(f"MILP failed: {result.message}")
        return result

    def objective(indices):
        values = np.zeros(size)
        values[list(indices)] = 1
        return values

    # Fix each optimum before optimizing the next objective.
    first_goal = objective(s.values())
    first = solve(first_goal)
    fixed_quota = ({index: 1 for index in s.values()},
                   int(round(first_goal @ first.x)), int(round(first_goal @ first.x)))
    second_goal = objective(t.values())
    second = solve(second_goal, [fixed_quota])
    fixed_breadth = ({index: 1 for index in t.values()},
                     int(round(second_goal @ second.x)), int(round(second_goal @ second.x)))
    final = solve(objective(range(n)), [fixed_quota, fixed_breadth])

    selected = [row for i, row in enumerate(pool) if final.x[i] > 0.5]
    totals = coverage_totals(coverage_table(const, existing + selected))
    return selected, {
        "feasible": totals["shortfall"] == 0 and totals["breadth_shortfall"] == 0,
        "optimal": all(result.status == 0 for result in (first, second, final)),
        "solver_status": str(final.message), "selected_additions": len(selected),
        "remaining_shortfall": totals["shortfall"],
        "breadth_shortfall": totals["breadth_shortfall"], "capped_slots": totals["capped"],
    }


def write_exports(root, const, existing, selected, quality_pool, screening, optimization):
    """Export one master benchmark, one JSON per constitution, and audit reports."""
    root = Path(root)
    export = root / "exports"
    by_const = export / "scenarios_by_constitution"
    by_const.mkdir(parents=True, exist_ok=True)
    bank = existing + selected

    ids = [row["scenario_id"] for row in bank]
    texts = [normalized_text(row["scenario"]) for row in bank]
    if len(set(ids)) != len(ids) or len(set(texts)) != len(texts):
        raise ValueError("Duplicate scenario ID or text in final benchmark")

    for name, spec in const.items():
        statements = {item["id"]: item["text"] for item in spec["criteria"]}
        output = []
        for row in bank:
            keys = sort_criterion_ids(set(row.get("relevance", {}).get(name, [])))
            if not set(keys) <= set(statements):
                raise ValueError(f"Invalid criterion label for {name}")
            if keys:
                output.append({
                    "scenario": row["scenario"],
                    "criteria": [{"id": key, "text": statements[key]} for key in keys],
                })
        atomic_json(by_const / f"{name}.json", output)

    master = [{"scenario_id": row["scenario_id"], "scenario": row["scenario"],
               "relevance": {name: ids for name, ids in row.get("relevance", {}).items() if ids}}
              for row in bank]
    atomic_json(export / "benchmark.json", master)
    atomic_json(export / "optimization_status.json", optimization)

    table = coverage_table(const, bank)
    atomic_json(export / "coverage_by_constitution.json", table)
    _, before = sample_coverage(const, existing)
    _, after = sample_coverage(const, bank)
    criterion_table = [
        {"constitution": name, "criterion_id": item["id"],
         "criterion": item["text"],
         "existing_count": before[name][item["id"]],
         "final_count": after[name][item["id"]]}
        for name, spec in const.items() for item in spec["criteria"]
    ]
    atomic_json(export / "coverage_by_criterion.json", criterion_table)
    atomic_json(export / "generation_gap_plan.json", {
        "quota": cfg.SCENARIO_QUOTA, "min_distinct_criteria": cfg.MIN_DISTINCT_CRITERIA,
        "missing_scenarios": {r["constitution"]: r["shortfall"] for r in table if r["shortfall"]},
        "missing_breadth": {r["constitution"]: r["breadth_shortfall"]
                            for r in table if r["breadth_shortfall"]},
        "uncovered_atomic_criteria": {
            name: [item["id"] for item in spec["criteria"] if not after[name][item["id"]]]
            for name, spec in const.items()},
    })

    totals = coverage_totals(table)
    atomic_json(export / "run_summary.json", {
        "run_name": cfg.RUN_NAME, "constitutions": len(const),
        "existing_scenarios": len(existing), "quality_pool": len(quality_pool),
        "selected_additions": len(selected), "final_unique_scenarios": len(bank),
        "capped_coverage": totals["capped"], "target_coverage": len(const) * cfg.SCENARIO_QUOTA,
        "remaining_slots": totals["shortfall"], "breadth_deficits": totals["breadth_shortfall"],
        "redundancy": screening.get("metrics", {}), "optimizer": optimization,
    })

    usage = [event for path in sorted((root / "audit/api_usage_chunks").glob("usage_*.json"))
             for event in read_json(path, [])]
    atomic_json(root / "audit/api_usage.json", usage)
    archive_path = export / "scenario_generation_pipeline_results.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(export.rglob("*.json")):
            archive.write(path, path.relative_to(export))
        for path in sorted((root / "audit").glob("*.json")):
            archive.write(path, Path("audit") / path.name)
        for path in sorted((root / "batches").rglob("*.json")):
            archive.write(path, path.relative_to(root))
        archive.write(root / "run_manifest.json", "run_manifest.json")
        archive.write(root / "review/manual_relevance_overrides.json",
                      "review/manual_relevance_overrides.json")
    return archive_path, table


def run_pipeline(root, const, input_bank, client):
    """Generate, evaluate, select, and checkpoint until the attempt budget is reached."""
    root = Path(root)
    original = populate_baseline(client, root, const, input_bank)
    quality_pool = read_json(root / "audit/quality_pool.json", [])
    progress_path = root / "audit/progress.json"
    progress = read_json(progress_path, {"completed_batches": 0, "attempts": 0})

    def refresh():
        screened = redundancy_screen(client, root, original, quality_pool)
        candidates = label_new_survivors(client, root, const, screened["kept"])
        existing, eligible, _ = apply_human_overrides(root, const, original, candidates)
        selected, result = optimize_additions(const, existing, eligible)
        archive, table = write_exports(root, const, existing, selected,
                                       quality_pool, screened, result)
        return existing, selected, result, archive, table

    existing, selected, status, archive, table = refresh()
    print(f"Starting coverage: {coverage_totals(table)['capped']}/{cfg.SCENARIO_QUOTA * len(const)}")

    while progress["attempts"] < cfg.MAX_NEW_ATTEMPTS:
        if cfg.STOP_WHEN_SATISFIED and status["feasible"]:
            print("All coverage targets satisfied")
            break
        target = choose_target(const, existing + selected)
        if target is None:
            break
        batch = progress["completed_batches"]
        budget = min(cfg.GENERATION_BATCH_SIZE, cfg.MAX_NEW_ATTEMPTS - progress["attempts"])
        slots = batch_stage(root, batch, "slots.json",
                            lambda: make_slots(const, target, existing + selected, batch, budget))
        if len(slots) != budget:
            raise RuntimeError("Saved partial batch conflicts with changed budget")

        supplements = m3_supplements(client, root, const, target)
        generator = generation_model_for_batch(batch)
        candidates = batch_stage(root, batch, "generated.json",
                                 lambda: generate_batch(client, const, target, slots,
                                                        existing + quality_pool,
                                                        supplements, generator))
        if any(row["generation_model"] != generator for row in candidates):
            raise RuntimeError("Cached generation model differs from configured rotation")
        judged = batch_stage(root, batch, "quality.json",
                             lambda: quality_process(client, const, candidates))
        previous_ids = {row["scenario_id"] for row in quality_pool}
        quality_pool.extend(row for row in judged["passed"]
                            if row["scenario_id"] not in previous_ids)
        atomic_json(root / "audit/quality_pool.json", quality_pool)

        existing, selected, status, archive, table = refresh()
        progress = {"completed_batches": batch + 1,
                    "attempts": progress["attempts"] + len(slots)}
        atomic_json(progress_path, progress)
        totals = coverage_totals(table)
        atomic_json(root / "batches" / f"batch_{batch:04d}" / "completed.json", {
            "target": target, "generation_model": generator,
            "development_judges": development_judges_for(generator),
            "attempted": len(slots), "quality_passed": len(judged["passed"]),
            "selected_total": len(selected), "coverage_slots": totals["capped"],
            "remaining_slots": totals["shortfall"],
        })
        print(f"Batch {batch + 1}: {target}; {len(judged['passed'])}/{len(slots)} quality pass; "
              f"{len(selected)} additions selected; {totals['capped']}/{cfg.SCENARIO_QUOTA * len(const)} slots")

    # Refresh exports to reflect any new manual overrides, even without generation.
    existing, selected, status, archive, table = refresh()
    return {"selected": selected, "existing": existing, "optimizer": status,
            "report": table, "archive": archive, "progress": progress}
