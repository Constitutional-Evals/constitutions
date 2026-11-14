"""Embedding-assisted redundancy and criterion mapping."""

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path

from . import config as cfg
from .core import (
    atomic_json, digest, normalized_text, read_json, sort_criterion_ids,
)
from .stages import validate_dup, validate_relevance

def redundancy_screen(client, root, existing, quality_pool):
    """Embedding retrieval (≥ threshold) followed by behavioral LLM review."""
    if not quality_pool:
        return {"kept": [], "removed": [], "pairs": [],
                "metrics": {"pairs_above_cutoff": 0, "reviewed": 0}}

    rows = existing + quality_pool
    similarities = client.embeddings([r["scenario"] for r in rows])
    cosine = similarities @ similarities.T
    fixed = {r["scenario_id"] for r in existing}
    jobs = [(i, j, float(cosine[i, j]))
            for i in range(len(rows)) for j in range(max(i + 1, len(existing)), len(rows))
            if cosine[i, j] >= cfg.REDUNDANCY_COSINE_THRESHOLD - 1e-12]
    if len(jobs) > cfg.MAX_REVIEW_PAIRS:
        raise RuntimeError(f"{len(jobs)} redundancy pairs exceed MAX_REVIEW_PAIRS")

    path = Path(root) / "audit/redundancy_judgments.json"
    ledger = read_json(path, {})

    def review(job):
        i, j, similarity = job
        first, second = rows[i], rows[j]
        cache_key = digest([sorted([first["scenario_id"], second["scenario_id"]]),
                            digest(first["scenario"]), digest(second["scenario"])])
        if cache_key in ledger:
            return cache_key, ledger[cache_key], False
        if normalized_text(first["scenario"]) == normalized_text(second["scenario"]):
            score, explanation, source = 100, "Identical scenario text", "exact"
        else:
            result = client.chat(cfg.REDUNDANCY_JUDGE, cfg.PROMPTS["redundancy"], {
                "scenario_a": first["scenario"], "scenario_b": second["scenario"],
            }, validate_dup)
            score, explanation, source = result["score"], result["reason"], "llm"
        record = {
            "a": first["scenario_id"], "b": second["scenario_id"],
            "cosine": similarity, "score": score, "reason": explanation,
            "conflict": score >= cfg.REDUNDANCY_LLM_THRESHOLD, "source": source,
        }
        return cache_key, record, True
    with ThreadPoolExecutor(max_workers=cfg.WORKERS) as pool:
        futures = [pool.submit(review, job) for job in jobs]
        for result in as_completed(futures):
            key, record, fresh = result.result()
            if fresh:
                ledger[key] = record
                atomic_json(path, ledger)

    pairs = [ledger[digest([
        sorted([rows[i]["scenario_id"], rows[j]["scenario_id"]]),
        digest(rows[i]["scenario"]), digest(rows[j]["scenario"])
    ])] for i, j, _ in jobs]

    blocked, conflicts = set(), defaultdict(set)
    for pair in pairs:
        if not pair["conflict"]:
            continue
        a, b = pair["a"], pair["b"]
        if a in fixed or b in fixed:
            blocked.add(b if a in fixed else a)
        else:
            conflicts[a].add(b)
            conflicts[b].add(a)

    kept, chosen = [], set()
    for row in sorted(quality_pool,
                      key=lambda r: (-r["quality"]["heldout_average"], r["scenario_id"])):
        sid = row["scenario_id"]
        if sid not in blocked and not conflicts[sid].intersection(chosen):
            kept.append(row)
            chosen.add(sid)

    removed = [{"scenario_id": row["scenario_id"],
                "reason": "Behavioral redundancy conflict"}
               for row in quality_pool if row["scenario_id"] not in chosen]
    return {"kept": kept, "removed": removed, "pairs": pairs, "metrics": {
        "pairs_above_cutoff": len(jobs), "pairs_reviewed": len(pairs),
        "conflicts": sum(pair["conflict"] for pair in pairs),
        "quality_pool": len(quality_pool), "survivors": len(kept),
    }}


def label_pair(client, constitution, scenario, name, model):
    result = client.chat(model, cfg.PROMPTS["relevance"], {
        "scenario": scenario, "constitution": constitution, "constitution_id": name,
    }, lambda data: validate_relevance(data, constitution))
    return {"ids": validate_relevance(result, constitution),
            "matches": result["matches"], "none_reason": result.get("none_reason", ""),
            "model": model}


def label_scenario(client, const, row):
    """Map each survivor to criteria, without trusting its original target labels."""
    labels, records = {}, {}
    for name, spec in const.items():
        votes = [label_pair(client, spec, row["scenario"], name, cfg.RELEVANCE_JUDGES[0])]
        if len(cfg.RELEVANCE_JUDGES) == 2:
            votes.append(label_pair(client, spec, row["scenario"], name, cfg.RELEVANCE_JUDGES[1]))
            if set(votes[0]["ids"]) != set(votes[1]["ids"]):
                votes.append(label_pair(client, spec, row["scenario"], name,
                                        cfg.RELEVANCE_TIEBREAKER))
        counts = Counter(key for vote in votes for key in vote["ids"])
        required = 2 if len(votes) == 3 else len(votes)
        accepted = sort_criterion_ids(key for key, count in counts.items()
                                          if count >= required)
        records[name] = {"votes": votes, "final_ids": accepted}
        if accepted:
            labels[name] = accepted
    return {"relevance": labels, "relevance_records": records}


def populate_baseline(client, root, const, original):
    """Only evaluate imported scenario/constitution pairs with unknown relevance."""
    path = Path(root) / "audit/baseline_labeled.json"
    cached = read_json(path)
    if cached is not None:
        if [r["scenario_id"] for r in cached] != [r["scenario_id"] for r in original]:
            raise RuntimeError("Saved baseline does not match input bank")
        return cached

    rows = deepcopy(original)
    progress_path = Path(root) / "audit/baseline_mapping_progress.json"
    progress = read_json(progress_path, {})
    for row in rows:
        sid = row["scenario_id"]
        for name in const:
            if name in row.get("relevance", {}):
                continue  # Including an explicit empty list: assessed and negative.
            if name not in progress.get(sid, {}):
                judgment = label_pair(client, const[name], row["scenario"], name,
                                      cfg.RELEVANCE_JUDGES[0])
                progress.setdefault(sid, {})[name] = judgment
                atomic_json(progress_path, progress)
            row.setdefault("relevance", {})[name] = progress[sid][name]["ids"]
    atomic_json(path, rows)
    return rows


def label_new_survivors(client, root, const, survivors):
    path = Path(root) / "audit/new_relevance_labels.json"
    recorded = read_json(path, {})
    for row in survivors:
        sid = row["scenario_id"]
        if sid not in recorded:
            recorded[sid] = label_scenario(client, const, row)
            atomic_json(path, recorded)
    # Preserve all model judgments for auditing; optimization ignores empty relevance.
    return [{**deepcopy(row), "relevance": recorded[row["scenario_id"]]["relevance"]}
            for row in survivors]
