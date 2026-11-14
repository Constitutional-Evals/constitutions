"""Coverage planning, generation, quality judging, and M3."""

import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

from . import config as cfg
from .core import (
    atomic_json, check_is_str, criterion_id, normalized_text, read_json,
    sample_coverage, slug, sort_criterion_ids, word_count,
)

def validate_m3(data, other_ids, limit):
    picks = data.get("picks") if isinstance(data, dict) else None
    if not isinstance(picks, list) or len(picks) > limit:
        raise ValueError("Invalid M3 picks")
    for pick in picks:
        name = slug(pick.get("constitution", ""))
        if name not in other_ids or criterion_id(pick.get("id")) not in other_ids[name]:
            raise ValueError(f"Unknown M3 criterion: {pick}")
        check_is_str(pick.get("why"), "M3 rationale")


def validate_generation(data, expected):
    rows = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError("Missing or incomplete generated candidate array")
    ids = [row.get("slot_id") for row in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(expected):
        raise ValueError("Generated slot IDs do not match the request")
    for row in rows:
        check_is_str(row.get("scenario"), "generated scenario")


def validate_quality(data):
    scores = data.get("scores") if isinstance(data, dict) else None
    if not isinstance(scores, dict) or set(scores) != set(cfg.QUALITY_DIMS):
        raise ValueError("Missing quality dimensions")
    if any(type(v) not in (int, float) or not 0 <= v <= 100 for v in scores.values()):
        raise ValueError("Quality scores must be numbers between 0 and 100")
    check_is_str(data.get("reason"), "quality explanation")
    if not isinstance(data.get("repair", ""), str):
        raise ValueError("Invalid repair advice")


def validate_revision(data):
    check_is_str(data.get("scenario") if isinstance(data, dict) else None, "revision")


def validate_dup(data):
    if not isinstance(data, dict) or type(data.get("score")) not in (int, float):
        raise ValueError("Missing numerical redundancy score")
    if not 0 <= data["score"] <= 100:
        raise ValueError("Redundancy score outside 0–100")
    check_is_str(data.get("reason"), "redundancy explanation")


def validate_relevance(data, constitution):
    matches = data.get("matches") if isinstance(data, dict) else None
    if not isinstance(matches, list):
        raise ValueError("Missing relevance matches")
    allowed = {c["id"] for c in constitution["criteria"]}
    ids = []
    for match in matches:
        key = criterion_id(match.get("id"))
        if key not in allowed or key in ids:
            raise ValueError(f"Unknown or repeated criterion: {key}")
        check_is_str(match.get("evidence"), "relevance evidence")
        ids.append(key)
    if not isinstance(data.get("none_reason", ""), str):
        raise ValueError("Invalid none_reason")
    return sort_criterion_ids(ids)


def passes_quality(report):
    values = list(report["scores"].values())
    return (sum(values) / len(values) >= cfg.QUALITY_MIN_AVERAGE
            and min(values) >= cfg.QUALITY_MIN_DIMENSION)


def repairable_quality(report):
    values = list(report["scores"].values())
    return (sum(values) / len(values) >= cfg.REVISION_ELIGIBLE_AVERAGE
            and min(values) >= cfg.REVISION_ELIGIBLE_MIN_DIMENSION)


def deterministic_validation(scenario, constitution_ids=()):
    if not isinstance(scenario, str):
        return "Scenario is not text"
    count = word_count(scenario)
    if count < cfg.MIN_WORDS or count > cfg.HARD_MAX_WORDS or len(scenario.split()) < cfg.MIN_WORDS:
        return f"Word count outside limits: {count}"
    if len(scenario) > 1800:
        return "Scenario exceeds character limit"
    if re.search(r"(?i)\b(according to (the )?(constitution|criterion)|which ethical framework|for this benchmark)\b", scenario):
        return "Explicit benchmark terminology"
    for name in constitution_ids:
        if "-" in name and re.search(r"(?i)\b" + re.escape(name.replace("-", " ")) + r"\b", scenario):
            return f"Constitution named explicitly: {name}"
    return None


def coverage_table(const, scenarios):
    counts, hits = sample_coverage(const, scenarios)
    table = []
    for name, spec in const.items():
        criteria = spec["criteria"]
        breadth = sum(hits[name][item["id"]] > 0 for item in criteria)
        minimum = min(cfg.MIN_DISTINCT_CRITERIA, len(criteria))
        table.append({
            "constitution": name, "scenarios": counts[name],
            "capped": min(counts[name], cfg.SCENARIO_QUOTA),
            "shortfall": max(0, cfg.SCENARIO_QUOTA - counts[name]),
            "distinct_criteria": breadth, "breadth_target": minimum,
            "breadth_shortfall": max(0, minimum - breadth),
            "uncovered_criteria": len(criteria) - breadth,
        })
    return sorted(table, key=lambda row: row["constitution"])


def coverage_totals(table):
    return {key: sum(row[key] for row in table)
            for key in ("capped", "shortfall", "breadth_shortfall")}


def show_coverage(table):
    keys = ("constitution", "scenarios", "shortfall", "distinct_criteria", "breadth_shortfall")
    widths = (24, 10, 10, 18, 17)
    print("  ".join(k.ljust(w) for k, w in zip(keys, widths)))
    for row in table:
        print("  ".join(str(row[k]).ljust(w) for k, w in zip(keys, widths)))


def choose_target(const, rows):
    """Prioritize constitution deficits; use criterion breadth to break close ties."""
    unfinished = [r for r in coverage_table(const, rows)
                  if r["shortfall"] or r["breadth_shortfall"]]
    if not unfinished:
        return None

    def priority(row):
        return (row["shortfall"] / cfg.SCENARIO_QUOTA
                + 0.50 * row["breadth_shortfall"] / max(1, row["breadth_target"])
                + 0.08 * row["uncovered_criteria"] / len(const[row["constitution"]]["criteria"]))

    return min(unfinished, key=lambda row: (-priority(row), row["constitution"]))["constitution"]


def make_slots(const, target, rows, batch_no, count):
    """Spread new targets across undercovered criteria and scenario settings."""
    _, hits = sample_coverage(const, rows)
    criteria = [c["id"] for c in const[target]["criteria"]]
    assigned, slots = Counter(), []
    rng = random.Random(cfg.SEED + 1009 * batch_no)
    for index in range(count):
        key = min(criteria, key=lambda k: (hits[target][k] + assigned[k], rng.random()))
        assigned[key] += 1
        number = batch_no * cfg.GENERATION_BATCH_SIZE + index
        slots.append({
            "slot_id": f"slot_{number:07d}", "target_constitution": target,
            "criterion_ids": [key],
            "scenario_type": cfg.SCENARIO_TYPES[(number + cfg.SEED) % len(cfg.SCENARIO_TYPES)],
            "setting": cfg.SETTINGS[(number * 7 + cfg.SEED) % len(cfg.SETTINGS)],
        })
    return slots


def m3_supplements(client, root, const, target):
    if len(const) == 1:
        return []  # No supplementary-criterion selection for a single constitution.
    path = Path(root) / "audit" / f"m3_{target}.json"
    saved = read_json(path)
    if saved is not None:
        return saved["selected"]

    others = {name: {item["id"] for item in spec["criteria"]}
              for name, spec in const.items() if name != target}
    cards = [{"constitution": name, "criteria": const[name]["criteria"]}
             for name in others]
    ballots = []
    for model in cfg.M3_MODELS:
        result = client.chat(model, cfg.PROMPTS["m3"], {
            "target": const[target], "others": cards, "N": cfg.M3_SUPPLEMENTARY_COUNT,
        }, lambda data: validate_m3(data, others, cfg.M3_SUPPLEMENTARY_COUNT))
        ballots.append({"model": model, "picks": result["picks"]})

    votes = Counter((slug(pick["constitution"]), criterion_id(pick["id"]))
                    for ballot in ballots for pick in ballot["picks"])
    ranked = sorted(votes, key=lambda pair: (-votes[pair], pair[0], str(pair[1])))
    chosen = [
        {"constitution": name, "id": key,
         "text": next(item["text"] for item in const[name]["criteria"] if item["id"] == key),
         "votes": votes[(name, key)]}
        for name, key in ranked[:cfg.M3_SUPPLEMENTARY_COUNT]
    ]
    atomic_json(path, {"target": target, "ballots": ballots, "selected": chosen})
    return chosen


def batch_stage(root, batch_no, filename, build):
    """Save each batch step once; reusing it never makes a duplicate API call."""
    path = Path(root) / "batches" / f"batch_{batch_no:04d}" / filename
    saved = read_json(path)
    if saved is not None:
        return saved
    result = build()
    atomic_json(path, result)
    return result


def generation_model_for_batch(batch_no):
    return cfg.GENERATION_MODELS[batch_no % len(cfg.GENERATION_MODELS)]


def development_judges_for(generator):
    if generator not in cfg.GENERATION_MODELS:
        raise ValueError(f"Unexpected generator: {generator}")
    return [model for model in cfg.GENERATION_MODELS if model != generator]


def generate_batch(client, const, target, slots, previous, supplements, generator):
    seen = [row["scenario"] for row in previous if row.get("target") == target][-30:]
    payload = {
        "constitution": const[target], "slots": slots,
        "supplementary_criteria": supplements, "previous_scenarios_to_avoid": seen,
        "word_target": {"maximum": cfg.TARGET_MAX_WORDS, "hard_maximum": cfg.HARD_MAX_WORDS},
    }
    expected = {slot["slot_id"] for slot in slots}
    result = client.chat(generator, cfg.PROMPTS["generate"], payload,
                         lambda data: validate_generation(data, expected))
    generated = {item["slot_id"]: item["scenario"].strip()
                 for item in result["candidates"]}
    return [{
        "scenario_id": "cand_" + slot["slot_id"],
        "scenario": generated[slot["slot_id"]],
        "target": target, "target_criteria": slot["criterion_ids"],
        "generation_model": generator, **slot,
    } for slot in slots]


def judge_candidate(client, row):
    payload = {"scenario": row["scenario"], "quality_dimensions": cfg.QUALITY_DIMS,
               "target_constitution_is_not_a_quality_requirement": True}
    def evaluate(model):
        result = client.chat(model, cfg.PROMPTS["quality"], payload, validate_quality)
        return {"model": model, **result, "passed": passes_quality(result),
                "repairable": repairable_quality(result)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(evaluate, development_judges_for(row["generation_model"])))


def quality_process(client, const, generated):
    """Deterministic checks → development judges → optional repair → held-out judge."""
    accepted, rejected, seen = [], [], set()
    for candidate in generated:
        row = deepcopy(candidate)
        error = deterministic_validation(row["scenario"], const)
        key = normalized_text(row["scenario"])
        if key in seen:
            error = "Exact duplicate within this batch"
        seen.add(key)
        if error:
            rejected.append({"scenario_id": row["scenario_id"],
                             "stage": "deterministic", "reason": error})
            continue

        reviews = judge_candidate(client, row)
        history = [{"version": 0, "scenario": row["scenario"], "development": reviews}]
        passed = all(item["passed"] for item in reviews)
        if not passed and cfg.MAX_REVISION_CYCLES and all(r["repairable"] for r in reviews):
            revision = client.chat(row["generation_model"], cfg.PROMPTS["revise"], {
                "scenario": row["scenario"], "reviewer_feedback": reviews,
                "target_criteria": row["target_criteria"],
                "constitution": const[row["target"]],
            }, validate_revision)["scenario"].strip()
            if not deterministic_validation(revision, const):
                row["scenario"] = revision
                reviews = judge_candidate(client, row)
                history.append({"version": 1, "scenario": revision, "development": reviews})
                passed = all(item["passed"] for item in reviews)
        if not passed:
            rejected.append({"scenario_id": row["scenario_id"],
                             "stage": "development", "attempts": history})
            continue

        # Frozen candidate: the held-out judge cannot trigger revisions.
        heldout = client.chat(cfg.HELDOUT_JUDGE, cfg.PROMPTS["quality"], {
            "scenario": row["scenario"], "quality_dimensions": cfg.QUALITY_DIMS,
            "target_constitution_is_not_a_quality_requirement": True,
        }, validate_quality)
        if not passes_quality(heldout):
            rejected.append({"scenario_id": row["scenario_id"],
                             "stage": "heldout", "attempts": history,
                             "heldout": heldout})
            continue

        row["quality"] = {
            "development": reviews, "heldout": heldout,
            "heldout_average": sum(heldout["scores"].values()) / len(cfg.QUALITY_DIMS),
            "revision_used": len(history) > 1,
        }
        accepted.append(row)
    return {"passed": accepted, "rejected": rejected,
            "metrics": {"generated": len(generated), "heldout_passed": len(accepted),
                        "rejected": len(rejected)}}


