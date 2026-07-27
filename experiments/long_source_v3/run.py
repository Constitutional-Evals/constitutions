#!/usr/bin/env python3
"""Run iterative, adaptive, and pre-extraction long-source experiments.

The module is intentionally separate from the completed v2.6 experiment. It can
reuse a v2.6 reference census, but never modifies v2.6 artifacts.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from experiments.long_source_atom_census.run import (
    DEFAULT_EMBEDDING,
    DEFAULT_EXTRACTORS,
    DEFAULT_REVIEWERS,
    DEFAULT_WRITER,
    chunk_primary_sources,
    cluster_atoms_by_embedding,
    enrich_clusters,
    load_or_build_census,
    load_or_build_embeddings,
    load_traditions,
    model_facing_cluster_packet,
    model_slug,
    parse_csv,
    parse_int_csv,
    token_words,
)
from experiments.long_source_distillation.run import (
    Chunk,
    OllamaClient,
    score_chunk,
    select_scored_chunks,
    sha256_text,
    write_json,
)


PROTOCOL_VERSION = "long-source-v3-pre-registered-1"
TARGET_CRITERIA = 10
TARGET_GUIDELINES = 4
DEFAULT_CONDITIONS = ("oracle", "iterative", "adaptive", "pre-extraction")
DEFAULT_SEEDS = (17, 29, 43, 71, 101)

ITEM_SCHEMA = {
    "type": "object",
    "required": [
        "kind",
        "comparative",
        "reasoning",
        "questions",
        "cluster_ids",
    ],
    "properties": {
        "kind": {"type": "string", "enum": ["criterion", "guideline"]},
        "comparative": {"type": "string", "minLength": 1},
        "reasoning": {"type": "string", "minLength": 1},
        "questions": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 2,
            "maxItems": 4,
        },
        "cluster_ids": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
    },
    "additionalProperties": False,
}

DRAFT_SCHEMA = {
    "type": "object",
    "required": ["overview", "items", "observed_cluster_ids"],
    "properties": {
        "overview": {"type": "string", "minLength": 1},
        "items": {
            "type": "array",
            "items": ITEM_SCHEMA,
            "minItems": 1,
            "maxItems": 28,
        },
        "observed_cluster_ids": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
    },
    "additionalProperties": False,
}


def final_item_schema(kind: str) -> dict[str, Any]:
    schema = json.loads(json.dumps(ITEM_SCHEMA))
    schema["properties"]["kind"] = {"const": kind}
    return schema


FINAL_SCHEMA = {
    "type": "object",
    "required": ["overview", "criteria", "guidelines", "observed_cluster_ids"],
    "properties": {
        "overview": {"type": "string", "minLength": 1},
        "criteria": {
            "type": "array",
            "items": final_item_schema("criterion"),
            "minItems": TARGET_CRITERIA,
            "maxItems": TARGET_CRITERIA,
        },
        "guidelines": {
            "type": "array",
            "items": final_item_schema("guideline"),
            "minItems": TARGET_GUIDELINES,
            "maxItems": TARGET_GUIDELINES,
        },
        "observed_cluster_ids": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
    },
    "additionalProperties": False,
}

LINK_SCHEMA = {
    "type": "object",
    "required": ["links", "unsupported_item_ids", "findings"],
    "properties": {
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["item_id", "cluster_id", "status", "reason"],
                "properties": {
                    "item_id": {"type": "string"},
                    "cluster_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["material", "partial"],
                    },
                    "reason": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "unsupported_item_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "findings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}


def clone_schema_with_ids(
    schema: dict[str, Any],
    cluster_ids: Sequence[str],
) -> dict[str, Any]:
    value = json.loads(json.dumps(schema))
    if schema is DRAFT_SCHEMA:
        value["properties"]["items"]["items"]["properties"]["cluster_ids"]["items"][
            "enum"
        ] = list(cluster_ids)
    else:
        for section in ("criteria", "guidelines"):
            value["properties"][section]["items"]["properties"]["cluster_ids"]["items"][
                "enum"
            ] = list(cluster_ids)
    value["properties"]["observed_cluster_ids"]["items"]["enum"] = list(cluster_ids)
    return value


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def checkpointed_call(
    path: Path,
    client: OllamaClient,
    *,
    model: str,
    system: str,
    user: str,
    schema: dict[str, Any],
    temperature: float,
    num_predict: int,
) -> dict[str, Any]:
    """Return a checkpoint or make one structured model call."""
    request_hash = sha256_text(
        stable_json(
            {
                "model": model,
                "system": system,
                "user": user,
                "schema": schema,
                "temperature": temperature,
                "num_predict": num_predict,
            }
        )
    )
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("request_hash") != request_hash:
            raise ValueError(f"Checkpoint request drift: {path}")
        return saved["result"]
    result = client.chat_json(
        model=model,
        system=system,
        user=user,
        schema=schema,
        temperature=temperature,
        num_predict=num_predict,
    )
    write_json(path, {"request_hash": request_hash, "result": result})
    return result


def cluster_ids(clusters: Sequence[dict[str, Any]]) -> list[str]:
    ids = [str(cluster["cluster_id"]) for cluster in clusters]
    if len(ids) != len(set(ids)):
        raise ValueError("Reference cluster IDs must be unique")
    return ids


def validate_provenance(
    result: dict[str, Any],
    expected_observed: set[str],
    known_ids: set[str],
) -> None:
    observed = result.get("observed_cluster_ids", [])
    if set(observed) != expected_observed or len(observed) != len(set(observed)):
        missing = sorted(expected_observed - set(observed))
        extra = sorted(set(observed) - expected_observed)
        raise ValueError(
            f"Observed-cluster provenance mismatch; missing={missing}, extra={extra}"
        )
    items = result.get("items", [])
    items += result.get("criteria", [])
    items += result.get("guidelines", [])
    cited = {
        cited_id
        for item in items
        for cited_id in item.get("cluster_ids", [])
    }
    unknown = cited - known_ids
    if unknown:
        raise ValueError(f"Unknown cluster IDs in item provenance: {sorted(unknown)}")


def packet_chars(cluster: dict[str, Any]) -> int:
    return int(
        cluster.get(
            "packet_chars",
            len(stable_json(model_facing_cluster_packet(cluster))),
        )
    )


def cluster_batches(
    clusters: Sequence[dict[str, Any]],
    max_chars: int,
) -> list[list[dict[str, Any]]]:
    """Pack clusters in stable order without silently dropping oversized items."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for cluster in clusters:
        size = packet_chars(cluster)
        if current and current_chars + size > max_chars:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(cluster)
        current_chars += size
    if current:
        batches.append(current)
    flattened = [item["cluster_id"] for batch in batches for item in batch]
    if flattened != cluster_ids(clusters):
        raise AssertionError("Cluster batching changed order or coverage")
    return batches


def high_confidence_conflict(cluster: dict[str, Any]) -> bool:
    atom_kinds = set(cluster.get("atom_kinds", []))
    return bool({"conflict", "exception"} & atom_kinds) and (
        len(cluster.get("extractor_models", [])) >= 2
        or len(cluster.get("source_paths", [])) >= 2
    )


def adaptive_cluster_order(
    clusters: Sequence[dict[str, Any]],
    source_paths: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Order mandatory clusters first, then weighted diverse clusters."""
    by_id = {cluster["cluster_id"]: cluster for cluster in clusters}
    selected: list[str] = []
    reasons: dict[str, list[str]] = defaultdict(list)

    def add(cluster_id: str, reason: str) -> None:
        if cluster_id not in selected:
            selected.append(cluster_id)
        reasons[cluster_id].append(reason)

    for cluster in sorted(clusters, key=lambda item: item["cluster_id"]):
        if high_confidence_conflict(cluster):
            add(cluster["cluster_id"], "high-confidence-conflict-or-exception")

    for source_path in sorted(source_paths):
        supported = [
            cluster for cluster in clusters if source_path in cluster["source_paths"]
        ]
        if supported:
            best = max(
                supported,
                key=lambda item: (
                    float(item.get("weight", 1.0)),
                    int(item.get("support_count", 1)),
                    item["cluster_id"],
                ),
            )
            add(best["cluster_id"], "per-source-coverage")

    while len(selected) < len(clusters):
        selected_words = [
            token_words(by_id[cluster_id]["synthesis"]) for cluster_id in selected
        ]

        def score(candidate: dict[str, Any]) -> tuple[float, str]:
            words = token_words(candidate["synthesis"])
            max_overlap = max(
                (
                    len(words & prior) / len(words | prior)
                    for prior in selected_words
                    if words or prior
                ),
                default=0.0,
            )
            value = float(candidate.get("weight", 1.0)) * (1.0 - 0.5 * max_overlap)
            return value, candidate["cluster_id"]

        remaining = [
            cluster for cluster in clusters if cluster["cluster_id"] not in selected
        ]
        chosen = max(remaining, key=score)
        add(chosen["cluster_id"], "weighted-diversity-order")
    return [by_id[item] for item in selected], dict(sorted(reasons.items()))


def weighted_mass(
    selected_ids: set[str],
    clusters: Sequence[dict[str, Any]],
) -> float:
    total = sum(float(cluster.get("weight", 1.0)) for cluster in clusters)
    selected = sum(
        float(cluster.get("weight", 1.0))
        for cluster in clusters
        if cluster["cluster_id"] in selected_ids
    )
    return selected / total if total else 1.0


def constitution_items(constitution: dict[str, Any]) -> list[str]:
    return [
        item["comparative"]
        for section in ("criteria", "guidelines")
        for item in constitution.get(section, [])
    ]


def set_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    """Symmetric best-match Jaccard over constitution item text."""
    left_items = [token_words(text) for text in constitution_items(left)]
    right_items = [token_words(text) for text in constitution_items(right)]
    if not left_items and not right_items:
        return 1.0
    if not left_items or not right_items:
        return 0.0

    def directional(source: list[set[str]], target: list[set[str]]) -> float:
        scores = []
        for source_words in source:
            scores.append(
                max(
                    (
                        len(source_words & target_words)
                        / max(1, len(source_words | target_words))
                        for target_words in target
                    ),
                    default=0.0,
                )
            )
        return sum(scores) / len(scores)

    return (directional(left_items, right_items) + directional(right_items, left_items)) / 2


def local_draft(
    client: OllamaClient,
    model: str,
    value_system: str,
    clusters: Sequence[dict[str, Any]],
    checkpoint: Path,
) -> dict[str, Any]:
    ids = cluster_ids(clusters)
    prompt = f"""Extract a compact local draft for {value_system} from one evidence batch.

This is an intermediate representation, not the final constitution.
- Represent every supplied cluster somewhere in observed_cluster_ids.
- Preserve distinctive low-frequency commitments, conflicts, and exceptions.
- Merge only genuine overlap.
- Criteria must begin "Prefer the response that" and measure one observable
  response behavior.
- Guidelines may instead use "When X conflicts with Y, ..." when that is more
  precise than forcing a preference formula.
- Cite only supplied cluster IDs in each item's cluster_ids.
- Questions are discriminative scenario templates, not trivial right-answer prompts.

Return JSON matching the schema.

Evidence batch:
{json.dumps([model_facing_cluster_packet(item) for item in clusters], ensure_ascii=False)}"""
    result = checkpointed_call(
        checkpoint,
        client,
        model=model,
        system=(
            "You produce source-grounded intermediate constitution drafts. "
            "Use no outside knowledge and return only JSON."
        ),
        user=prompt,
        schema=clone_schema_with_ids(DRAFT_SCHEMA, ids),
        temperature=0.2,
        num_predict=7000,
    )
    validate_provenance(result, set(ids), set(ids))
    return result


def merge_drafts(
    client: OllamaClient,
    model: str,
    value_system: str,
    left: dict[str, Any],
    right: dict[str, Any],
    known_ids: Sequence[str],
    checkpoint: Path,
) -> dict[str, Any]:
    expected = set(left["observed_cluster_ids"]) | set(right["observed_cluster_ids"])
    prompt = f"""Merge two intermediate drafts for {value_system}.

Remove semantic duplication but preserve all materially distinct principles,
minority commitments, conflicts, and exceptions. Do not finalize to a fixed
item count yet. observed_cluster_ids must be the exact union of both inputs,
even when multiple clusters are compressed into one item. Each item's
cluster_ids must name the evidence clusters that actually support it.

Draft A:
{json.dumps(left, ensure_ascii=False)}

Draft B:
{json.dumps(right, ensure_ascii=False)}"""
    result = checkpointed_call(
        checkpoint,
        client,
        model=model,
        system=(
            "You consolidate source-grounded constitution drafts while preserving "
            "provenance. Return only JSON."
        ),
        user=prompt,
        schema=clone_schema_with_ids(DRAFT_SCHEMA, known_ids),
        temperature=0.1,
        num_predict=9000,
    )
    validate_provenance(result, expected, set(known_ids))
    return result


def finalize_draft(
    client: OllamaClient,
    model: str,
    value_system: str,
    draft: dict[str, Any],
    known_ids: Sequence[str],
    checkpoint: Path,
) -> dict[str, Any]:
    prompt = f"""Finalize this evidence-grounded draft into a constitution for {value_system}.

Return exactly {TARGET_CRITERIA} criteria and {TARGET_GUIDELINES} guidelines.
Criteria begin "Prefer the response that". Guidelines may use a direct
conflict rule such as "When X conflicts with Y, do Z"; do not force awkward
preference phrasing. Make every item atomic, behaviorally checkable,
non-redundant, distinctive to the source tradition, and supported by its cited
cluster_ids. Preserve serious counter-considerations and foundational
low-frequency principles. Questions must be difficult, realistic, and capable
of eliciting plausible responses on both sides.

observed_cluster_ids must remain unchanged. Silently audit clarity, coverage,
overlap, grounding, and conflict handling before returning JSON.

Intermediate draft:
{json.dumps(draft, ensure_ascii=False)}"""
    result = checkpointed_call(
        checkpoint,
        client,
        model=model,
        system=(
            "You finalize compact source-grounded model constitutions. "
            "Return only JSON."
        ),
        user=prompt,
        schema=clone_schema_with_ids(FINAL_SCHEMA, known_ids),
        temperature=0.2,
        num_predict=8000,
    )
    validate_provenance(
        result,
        set(draft["observed_cluster_ids"]),
        set(known_ids),
    )
    return result


def run_oracle(
    run_dir: Path,
    client: OllamaClient,
    model: str,
    value_system: str,
    clusters: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    draft = local_draft(
        client,
        model,
        value_system,
        clusters,
        run_dir / "oracle_draft.json",
    )
    return finalize_draft(
        client,
        model,
        value_system,
        draft,
        cluster_ids(clusters),
        run_dir / "constitution.checkpoint.json",
    )


def run_iterative(
    run_dir: Path,
    client: OllamaClient,
    model: str,
    value_system: str,
    clusters: Sequence[dict[str, Any]],
    batch_chars: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    ids = cluster_ids(clusters)
    batches = cluster_batches(clusters, batch_chars)
    drafts = []
    for index, batch in enumerate(batches, start=1):
        drafts.append(
            local_draft(
                client,
                model,
                value_system,
                batch,
                run_dir / "local" / f"batch-{index:03d}.json",
            )
        )
    level = 0
    trace = [{"level": 0, "draft_count": len(drafts)}]
    while len(drafts) > 1:
        level += 1
        merged = []
        for index in range(0, len(drafts), 2):
            if index + 1 == len(drafts):
                merged.append(drafts[index])
                continue
            merged.append(
                merge_drafts(
                    client,
                    model,
                    value_system,
                    drafts[index],
                    drafts[index + 1],
                    ids,
                    run_dir / "merge" / f"level-{level:02d}-pair-{index // 2 + 1:03d}.json",
                )
            )
        drafts = merged
        trace.append({"level": level, "draft_count": len(drafts)})
    constitution = finalize_draft(
        client,
        model,
        value_system,
        drafts[0],
        ids,
        run_dir / "constitution.checkpoint.json",
    )
    return constitution, {
        "batch_count": len(batches),
        "batch_cluster_ids": [
            [cluster["cluster_id"] for cluster in batch] for batch in batches
        ],
        "merge_trace": trace,
        "complete_input_coverage": set(constitution["observed_cluster_ids"]) == set(ids),
    }


def run_adaptive(
    run_dir: Path,
    client: OllamaClient,
    model: str,
    value_system: str,
    clusters: Sequence[dict[str, Any]],
    source_paths: Sequence[str],
    *,
    batch_size: int,
    minimum_weighted_mass: float,
    stability_threshold: float,
    stability_patience: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not 0 < minimum_weighted_mass <= 1:
        raise ValueError("minimum_weighted_mass must be in (0, 1]")
    if not 0 <= stability_threshold <= 1:
        raise ValueError("stability_threshold must be in [0, 1]")
    if batch_size <= 0 or stability_patience <= 0:
        raise ValueError("batch_size and stability_patience must be positive")

    ordered, reasons = adaptive_cluster_order(clusters, source_paths)
    ids = cluster_ids(clusters)
    mandatory = {
        cluster_id
        for cluster_id, why in reasons.items()
        if "high-confidence-conflict-or-exception" in why
        or "per-source-coverage" in why
    }
    current_draft: dict[str, Any] | None = None
    previous_final: dict[str, Any] | None = None
    stable_steps = 0
    trace = []
    final: dict[str, Any] | None = None

    for step, start in enumerate(range(0, len(ordered), batch_size), start=1):
        batch = ordered[start : start + batch_size]
        addition = local_draft(
            client,
            model,
            value_system,
            batch,
            run_dir / "steps" / f"step-{step:03d}-local.json",
        )
        if current_draft is None:
            current_draft = addition
        else:
            current_draft = merge_drafts(
                client,
                model,
                value_system,
                current_draft,
                addition,
                ids,
                run_dir / "steps" / f"step-{step:03d}-merge.json",
            )
        final = finalize_draft(
            client,
            model,
            value_system,
            current_draft,
            ids,
            run_dir / "steps" / f"step-{step:03d}-final.json",
        )
        selected = set(current_draft["observed_cluster_ids"])
        similarity = (
            set_similarity(previous_final, final) if previous_final is not None else None
        )
        stable_steps = (
            stable_steps + 1
            if similarity is not None and similarity >= stability_threshold
            else 0
        )
        mass = weighted_mass(selected, clusters)
        mandatory_complete = mandatory <= selected
        stop = (
            mass >= minimum_weighted_mass
            and mandatory_complete
            and stable_steps >= stability_patience
        )
        trace.append(
            {
                "step": step,
                "added_cluster_ids": [item["cluster_id"] for item in batch],
                "cumulative_cluster_ids": sorted(selected),
                "weighted_mass": mass,
                "mandatory_complete": mandatory_complete,
                "text_stability": similarity,
                "stable_steps": stable_steps,
                "stop": stop,
            }
        )
        previous_final = final
        if stop:
            break
    if final is None:
        raise ValueError("Adaptive run received no clusters")
    selected = set(final["observed_cluster_ids"])
    return final, {
        "cluster_order": [item["cluster_id"] for item in ordered],
        "selection_reasons": reasons,
        "mandatory_cluster_ids": sorted(mandatory),
        "minimum_weighted_mass": minimum_weighted_mass,
        "stability_threshold": stability_threshold,
        "stability_patience": stability_patience,
        "stopped_after_clusters": len(selected),
        "omitted_cluster_ids": sorted(set(ids) - selected),
        "trace": trace,
    }


def score_and_select_chunks(
    output_dir: Path,
    chunks: Sequence[Chunk],
    *,
    base_url: str,
    num_ctx: int,
    seed: int,
    timeout_seconds: int,
    router_model: str,
    min_score: int,
    audit_low_score_count: int,
    max_selected: int | None,
) -> tuple[list[Chunk], dict[str, Any]]:
    score_path = output_dir / "chunk_scores.json"
    checkpoint = (
        json.loads(score_path.read_text(encoding="utf-8"))
        if score_path.exists()
        else {"model": router_model, "scores": {}}
    )
    if checkpoint["model"] != router_model:
        raise ValueError(f"Router model drift in {score_path}")
    client = OllamaClient(
        base_url,
        num_ctx,
        seed,
        timeout_seconds,
        thinking=False,
    )
    for chunk in chunks:
        if chunk.chunk_id not in checkpoint["scores"]:
            checkpoint["scores"][chunk.chunk_id] = score_chunk(
                client, router_model, chunk
            )
            write_json(score_path, checkpoint)
    selected, reasons = select_scored_chunks(
        chunks,
        checkpoint["scores"],
        min_score=min_score,
        audit_low_score_count=audit_low_score_count,
        max_selected=max_selected,
        seed=seed,
    )
    selected_ids = {chunk.chunk_id for chunk in selected}
    manifest = {
        "router_model": router_model,
        "min_score": min_score,
        "audit_low_score_count": audit_low_score_count,
        "max_selected": max_selected,
        "total_chunks": len(chunks),
        "selected_chunks": len(selected),
        "selected_chunk_ids": sorted(selected_ids),
        "omitted_chunk_ids": sorted(
            chunk.chunk_id for chunk in chunks if chunk.chunk_id not in selected_ids
        ),
        "selection_reasons": reasons,
        "scores": checkpoint["scores"],
    }
    write_json(output_dir / "selection_manifest.json", manifest)
    return selected, manifest


def build_clusters(
    output_dir: Path,
    chunks: Sequence[Chunk],
    value_system: str,
    *,
    extractor_models: Sequence[str],
    embedding_model: str,
    max_clusters: int,
    base_url: str,
    num_ctx: int,
    seed: int,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    path = output_dir / "reference_clusters.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    atoms, _rejected = load_or_build_census(
        output_dir,
        chunks,
        value_system,
        extractor_models,
        base_url,
        num_ctx,
        seed,
        timeout_seconds,
    )
    embeddings = load_or_build_embeddings(
        output_dir,
        atoms,
        embedding_model,
        base_url,
        timeout_seconds,
    )
    raw_clusters, audit = cluster_atoms_by_embedding(
        atoms,
        embeddings,
        max_clusters,
    )
    audit["embedding_model"] = embedding_model
    clusters = enrich_clusters(raw_clusters, atoms)
    write_json(output_dir / "clustering_audit.json", audit)
    write_json(path, clusters)
    return clusters


def load_reference_clusters(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("clusters", value.get("reference_clusters"))
    if not isinstance(value, list) or not value:
        raise ValueError(f"Expected a non-empty cluster list in {path}")
    cluster_ids(value)
    return value


def router_audit(
    full_atoms: Sequence[dict[str, Any]],
    full_clusters: Sequence[dict[str, Any]],
    selection_manifest: dict[str, Any],
    routed_atoms: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    selected_chunks = set(selection_manifest["selected_chunk_ids"])
    available_atom_ids = {
        atom["candidate_id"]
        for atom in full_atoms
        if atom["chunk_id"] in selected_chunks
    }
    routed_atom_ids = (
        {atom["candidate_id"] for atom in routed_atoms}
        if routed_atoms is not None
        else available_atom_ids
    )
    all_atom_ids = {atom["candidate_id"] for atom in full_atoms}
    represented_cluster_ids = {
        cluster["cluster_id"]
        for cluster in full_clusters
        if set(cluster["candidate_ids"]) & routed_atom_ids
    }
    fully_represented_cluster_ids = {
        cluster["cluster_id"]
        for cluster in full_clusters
        if set(cluster["candidate_ids"]) <= routed_atom_ids
    }
    total_weight = sum(float(item.get("weight", 1.0)) for item in full_clusters)
    represented_weight = sum(
        float(item.get("weight", 1.0))
        for item in full_clusters
        if item["cluster_id"] in represented_cluster_ids
    )
    conflict_ids = {
        item["cluster_id"]
        for item in full_clusters
        if {"conflict", "exception"} & set(item.get("atom_kinds", []))
    }
    return {
        "selected_chunk_fraction": (
            selection_manifest["selected_chunks"]
            / max(1, selection_manifest["total_chunks"])
        ),
        "available_atom_recall_from_selected_chunks": len(available_atom_ids)
        / max(1, len(all_atom_ids)),
        "routed_atom_recall": len(routed_atom_ids & all_atom_ids)
        / max(1, len(all_atom_ids)),
        "routed_census_supplied": routed_atoms is not None,
        "represented_cluster_recall": len(represented_cluster_ids)
        / max(1, len(full_clusters)),
        "fully_represented_cluster_recall": len(fully_represented_cluster_ids)
        / max(1, len(full_clusters)),
        "weighted_represented_cluster_recall": represented_weight
        / max(1.0, total_weight),
        "conflict_exception_cluster_recall": len(
            represented_cluster_ids & conflict_ids
        )
        / max(1, len(conflict_ids)),
        "unrepresented_cluster_ids": sorted(
            set(cluster_ids(full_clusters)) - represented_cluster_ids
        ),
    }


def item_map(constitution: dict[str, Any]) -> dict[str, str]:
    mapped = {}
    for section in ("criteria", "guidelines"):
        singular = "criterion" if section == "criteria" else "guideline"
        for index, item in enumerate(constitution[section], start=1):
            mapped[f"{singular}-{index:02d}"] = item["comparative"]
    return mapped


def link_schema(
    item_ids: Sequence[str],
    reference_ids: Sequence[str],
) -> dict[str, Any]:
    schema = json.loads(json.dumps(LINK_SCHEMA))
    link = schema["properties"]["links"]["items"]["properties"]
    link["item_id"]["enum"] = list(item_ids)
    link["cluster_id"]["enum"] = list(reference_ids)
    schema["properties"]["unsupported_item_ids"]["items"]["enum"] = list(item_ids)
    return schema


def audit_constitution(
    path: Path,
    client: OllamaClient,
    model: str,
    constitution: dict[str, Any],
    reference_clusters: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    items = item_map(constitution)
    reference_ids = cluster_ids(reference_clusters)
    prompt = f"""Blindly map a candidate constitution to a source-derived reference census.

For each material or partial semantic match, return a link. Do not infer a
match from the candidate's hidden provenance fields; judge the displayed text.
Use status "material" only when the item preserves the cluster's actionable
normative distinction. Omitted links count as absent. Mark candidate items with
no defensible source support as unsupported. Findings must use descriptive tags
such as [REDUNDANCY], [ATOMICITY], [GROUNDING], [COVERAGE], [DISTINCTIVENESS],
or [CONFLICT].

Candidate items:
{json.dumps(items, ensure_ascii=False)}

Reference census:
{json.dumps([model_facing_cluster_packet(item) for item in reference_clusters], ensure_ascii=False)}"""
    result = checkpointed_call(
        path,
        client,
        model=model,
        system=(
            "You are an independent source-grounding auditor. Return only JSON."
        ),
        user=prompt,
        schema=link_schema(list(items), reference_ids),
        temperature=0.0,
        num_predict=8000,
    )
    return result


def write_plan(
    output_root: Path,
    args: argparse.Namespace,
    tradition: dict[str, Any],
    chunks: Sequence[Chunk],
) -> Path:
    conditions = parse_csv(args.conditions)
    seeds = parse_int_csv(args.seeds)
    calls = {
        "reference_extractions": (
            0
            if args.reference_clusters
            else len(chunks) * len(parse_csv(args.extractor_models))
        ),
        "router_scores": len(chunks) if "pre-extraction" in conditions else 0,
        "router_extractions_upper_bound": (
            len(chunks) * len(parse_csv(args.extractor_models))
            if "pre-extraction" in conditions
            else 0
        ),
        "writer_replicates": len(conditions) * len(seeds),
        "review_calls": (
            len(conditions) * len(seeds) * len(parse_csv(args.reviewer_models))
        ),
    }
    plan = {
        "protocol_version": PROTOCOL_VERSION,
        "mode": "plan-only",
        "no_model_calls_made": True,
        "tradition": args.tradition,
        "value_system": tradition["value_system"],
        "conditions": conditions,
        "seeds": seeds,
        "source_files": tradition["files"],
        "held_out_sensitivity_files_not_final_validation": tradition[
            "held_out_sensitivity_files"
        ],
        "chunk_count": len(chunks),
        "models": {
            "extractors": parse_csv(args.extractor_models),
            "embedding": args.embedding_model,
            "router": args.router_model,
            "writer": args.writer_model,
            "reviewers": parse_csv(args.reviewer_models),
        },
        "adaptive_stop": {
            "minimum_weighted_mass": args.adaptive_minimum_weighted_mass,
            "stability_threshold": args.adaptive_stability_threshold,
            "stability_patience": args.adaptive_stability_patience,
            "batch_size": args.adaptive_batch_size,
        },
        "estimated_call_counts": calls,
    }
    path = output_root / args.tradition / "plan.json"
    write_json(path, plan)
    return path


def resource_manifest(
    condition: str,
    clusters: Sequence[dict[str, Any]],
    constitution: dict[str, Any],
    trace: dict[str, Any],
    reference_clusters: Sequence[dict[str, Any]],
    selection_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    total_chars = sum(packet_chars(item) for item in clusters)
    reference_chars = sum(packet_chars(item) for item in reference_clusters)
    if condition == "iterative":
        batch_by_id = {item["cluster_id"]: item for item in clusters}
        batch_chars = [
            sum(packet_chars(batch_by_id[item]) for item in batch)
            for batch in trace["batch_cluster_ids"]
        ]
        model_calls = 2 * len(batch_chars)
        max_evidence_chars = max(batch_chars, default=0)
    elif condition == "adaptive":
        added = [step["added_cluster_ids"] for step in trace["trace"]]
        by_id = {item["cluster_id"]: item for item in clusters}
        batch_chars = [
            sum(packet_chars(by_id[item]) for item in batch) for batch in added
        ]
        model_calls = max(0, 3 * len(added) - 1)
        max_evidence_chars = max(batch_chars, default=0)
    else:
        batch_chars = [total_chars]
        model_calls = 2
        max_evidence_chars = total_chars
    selected_ids = set(constitution["observed_cluster_ids"])
    observed_packet_chars = sum(
        packet_chars(item)
        for item in clusters
        if item["cluster_id"] in selected_ids
    )
    value = {
        "condition": condition,
        "reference_cluster_count": len(reference_clusters),
        "reference_packet_chars": reference_chars,
        "condition_cluster_count": len(clusters),
        "observed_cluster_count": len(selected_ids),
        "condition_packet_chars": total_chars,
        "observed_packet_chars": observed_packet_chars,
        "initial_evidence_batch_chars": batch_chars,
        "maximum_initial_evidence_call_chars": max_evidence_chars,
        "writer_structured_call_count": model_calls,
        "input_weighted_mass_within_condition": weighted_mass(
            selected_ids, clusters
        ),
        "cost_metrics_are_proxies_not_api_token_counts": True,
    }
    if condition == "pre-extraction" and selection_manifest is not None:
        value["router"] = {
            "scored_chunks": selection_manifest["total_chunks"],
            "extracted_chunks": selection_manifest["selected_chunks"],
            "selected_chunk_fraction": (
                selection_manifest["selected_chunks"]
                / max(1, selection_manifest["total_chunks"])
            ),
        }
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tradition", required=True)
    parser.add_argument(
        "--traditions-config",
        type=Path,
        default=Path(__file__).parents[1]
        / "long_source_atom_census"
        / "traditions.json",
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reference-clusters", type=Path)
    parser.add_argument("--reference-census", type=Path)
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    parser.add_argument("--extractor-models", default=",".join(DEFAULT_EXTRACTORS))
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING)
    parser.add_argument("--router-model", default="qwen3.6:27b-q4_K_M")
    parser.add_argument("--writer-model", default=DEFAULT_WRITER)
    parser.add_argument("--reviewer-models", default=",".join(DEFAULT_REVIEWERS))
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--num-ctx", type=int, default=65536)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--chunk-chars", type=int, default=18000)
    parser.add_argument("--overlap-chars", type=int, default=0)
    parser.add_argument("--max-reference-clusters", type=int, default=40)
    parser.add_argument("--iterative-batch-chars", type=int, default=22000)
    parser.add_argument("--adaptive-batch-size", type=int, default=5)
    parser.add_argument("--adaptive-minimum-weighted-mass", type=float, default=0.85)
    parser.add_argument("--adaptive-stability-threshold", type=float, default=0.78)
    parser.add_argument("--adaptive-stability-patience", type=int, default=2)
    parser.add_argument("--router-min-score", type=int, default=3)
    parser.add_argument("--router-audit-low-score-count", type=int, default=3)
    parser.add_argument("--router-max-selected", type=int)
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    traditions = load_traditions(args.traditions_config)
    if args.tradition not in traditions:
        raise ValueError(f"Unknown tradition: {args.tradition}")
    tradition = traditions[args.tradition]
    conditions = parse_csv(args.conditions)
    unknown = set(conditions) - set(DEFAULT_CONDITIONS)
    if unknown:
        raise ValueError(f"Unknown conditions: {sorted(unknown)}")
    chunks, source_manifest = chunk_primary_sources(
        args.repo_root,
        tradition,
        args.chunk_chars,
        args.overlap_chars,
    )
    output_dir = args.output_root / args.tradition
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.reference_clusters and not args.reference_clusters.exists():
        raise FileNotFoundError(args.reference_clusters)
    if args.reference_census and not args.reference_census.exists():
        raise FileNotFoundError(args.reference_census)
    if args.plan_only:
        path = write_plan(args.output_root, args, tradition, chunks)
        print(path)
        return 0

    extractors = parse_csv(args.extractor_models)
    if args.reference_clusters:
        reference_clusters = load_reference_clusters(args.reference_clusters)
    else:
        reference_clusters = build_clusters(
            output_dir / "reference",
            chunks,
            tradition["value_system"],
            extractor_models=extractors,
            embedding_model=args.embedding_model,
            max_clusters=args.max_reference_clusters,
            base_url=args.ollama_url,
            num_ctx=args.num_ctx,
            seed=17,
            timeout_seconds=args.timeout_seconds,
        )
    write_json(output_dir / "reference_clusters.json", reference_clusters)

    routed_clusters = None
    selection_manifest = None
    if "pre-extraction" in conditions:
        selected_chunks, selection_manifest = score_and_select_chunks(
            output_dir / "router",
            chunks,
            base_url=args.ollama_url,
            num_ctx=args.num_ctx,
            seed=17,
            timeout_seconds=args.timeout_seconds,
            router_model=args.router_model,
            min_score=args.router_min_score,
            audit_low_score_count=args.router_audit_low_score_count,
            max_selected=args.router_max_selected,
        )
        routed_clusters = build_clusters(
            output_dir / "router" / "census",
            selected_chunks,
            tradition["value_system"],
            extractor_models=extractors,
            embedding_model=args.embedding_model,
            max_clusters=min(args.max_reference_clusters, max(1, len(selected_chunks) * 4)),
            base_url=args.ollama_url,
            num_ctx=args.num_ctx,
            seed=17,
            timeout_seconds=args.timeout_seconds,
        )
        census_path = args.reference_census or output_dir / "reference" / "census_atoms.json"
        if census_path.exists():
            census = json.loads(census_path.read_text(encoding="utf-8"))
            full_atoms = census.get("atoms", census)
            routed_census_path = (
                output_dir / "router" / "census" / "census_atoms.json"
            )
            routed_census = json.loads(
                routed_census_path.read_text(encoding="utf-8")
            )
            routed_atoms = routed_census.get("atoms", routed_census)
            write_json(
                output_dir / "router" / "audit.json",
                router_audit(
                    full_atoms,
                    reference_clusters,
                    selection_manifest,
                    routed_atoms,
                ),
            )
        else:
            write_json(
                output_dir / "router" / "audit_pending.json",
                {
                    "reason": "Full census atoms were not supplied; final router "
                    "claims are blocked until --reference-census is available."
                },
            )

    config = {
        "protocol_version": PROTOCOL_VERSION,
        "tradition": args.tradition,
        "value_system": tradition["value_system"],
        "conditions": conditions,
        "seeds": parse_int_csv(args.seeds),
        "source_manifest": source_manifest,
        "held_out_sensitivity_files_not_final_validation": tradition[
            "held_out_sensitivity_files"
        ],
        "models": {
            "extractors": extractors,
            "embedding": args.embedding_model,
            "router": args.router_model,
            "writer": args.writer_model,
            "reviewers": parse_csv(args.reviewer_models),
        },
        "parameters": vars(args) | {"repo_root": str(args.repo_root)},
    }
    for key, value in list(config["parameters"].items()):
        if isinstance(value, Path):
            config["parameters"][key] = str(value)
    write_json(output_dir / "experiment_config.json", config)

    source_paths = [item["path"] for item in source_manifest]
    for condition in conditions:
        condition_clusters = (
            routed_clusters if condition == "pre-extraction" else reference_clusters
        )
        if not condition_clusters:
            raise ValueError(f"No clusters available for {condition}")
        for seed in parse_int_csv(args.seeds):
            run_dir = output_dir / "runs" / condition / f"seed-{seed}"
            run_dir.mkdir(parents=True, exist_ok=True)
            client = OllamaClient(
                args.ollama_url,
                args.num_ctx,
                seed,
                args.timeout_seconds,
                thinking=False,
            )
            constitution_path = run_dir / "constitution.json"
            if not constitution_path.exists():
                if condition == "iterative":
                    constitution, trace = run_iterative(
                        run_dir,
                        client,
                        args.writer_model,
                        tradition["value_system"],
                        condition_clusters,
                        args.iterative_batch_chars,
                    )
                elif condition == "adaptive":
                    constitution, trace = run_adaptive(
                        run_dir,
                        client,
                        args.writer_model,
                        tradition["value_system"],
                        condition_clusters,
                        source_paths,
                        batch_size=args.adaptive_batch_size,
                        minimum_weighted_mass=args.adaptive_minimum_weighted_mass,
                        stability_threshold=args.adaptive_stability_threshold,
                        stability_patience=args.adaptive_stability_patience,
                    )
                else:
                    constitution = run_oracle(
                        run_dir,
                        client,
                        args.writer_model,
                        tradition["value_system"],
                        condition_clusters,
                    )
                    trace = {
                        "condition": condition,
                        "cluster_ids": cluster_ids(condition_clusters),
                    }
                write_json(run_dir / "trace.json", trace)
                write_json(constitution_path, constitution)
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            trace = json.loads((run_dir / "trace.json").read_text(encoding="utf-8"))
            write_json(
                run_dir / "resource_manifest.json",
                resource_manifest(
                    condition,
                    condition_clusters,
                    constitution,
                    trace,
                    reference_clusters,
                    selection_manifest,
                ),
            )
            for reviewer_index, reviewer in enumerate(
                parse_csv(args.reviewer_models)
            ):
                audit_path = run_dir / "audits" / f"{model_slug(reviewer)}.json"
                if audit_path.exists():
                    continue
                audit_client = OllamaClient(
                    args.ollama_url,
                    args.num_ctx,
                    seed + 10000 + reviewer_index * 1000,
                    args.timeout_seconds,
                    thinking=False,
                )
                audit_constitution(
                    audit_path,
                    audit_client,
                    reviewer,
                    constitution,
                    reference_clusters,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
