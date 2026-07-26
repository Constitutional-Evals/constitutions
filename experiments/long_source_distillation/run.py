#!/usr/bin/env python3
"""Run a provenance-preserving long-source constitution experiment with Ollama."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from jsonschema import ValidationError, validate


PROTOCOL_VERSION = "long-source-distillation-v1"
SOURCE_SUFFIXES = {".md", ".txt"}
EXCLUDED_NAMES = {"README.md"}
TARGET_CRITERIA = 10
TARGET_GUIDELINES = 4

SCORE_SCHEMA = {
    "type": "object",
    "required": [
        "normative_yield",
        "contains_conflict_resolution",
        "contains_rare_exception",
        "themes",
        "rationale",
    ],
    "properties": {
        "normative_yield": {"type": "integer", "minimum": 0, "maximum": 4},
        "contains_conflict_resolution": {"type": "boolean"},
        "contains_rare_exception": {"type": "boolean"},
        "themes": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 8,
        },
        "rationale": {"type": "string"},
    },
    "additionalProperties": False,
}

CANDIDATE_SCHEMA = {
    "type": "object",
    "required": ["candidates"],
    "properties": {
        "candidates": {
            "type": "array",
            "minItems": 0,
            "maxItems": 6,
            "items": {
                "type": "object",
                "required": ["kind", "statement", "evidence"],
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["criterion", "guideline"],
                    },
                    "statement": {"type": "string"},
                    "rationale": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}

RAW_CLUSTER_SCHEMA = {
    "type": "object",
    "required": ["clusters"],
    "properties": {
        "clusters": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["cluster_id", "description", "candidates"],
                "properties": {
                    "cluster_id": {"type": "string"},
                    "description": {"type": "string"},
                    "candidates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                },
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}

CONSTITUTION_SCHEMA = {
    "type": "object",
    "required": ["overview", "criteria", "guidelines"],
    "properties": {
        "overview": {"type": "string"},
        "criteria": {
            "type": "array",
            "minItems": TARGET_CRITERIA,
            "maxItems": TARGET_CRITERIA,
            "items": {
                "type": "object",
                "required": [
                    "comparative",
                    "reasoning",
                    "questions",
                    "candidate_ids",
                ],
                "properties": {
                    "comparative": {"type": "string"},
                    "reasoning": {"type": "string"},
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 4,
                    },
                    "candidate_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                },
                "additionalProperties": False,
            },
        },
        "guidelines": {
            "type": "array",
            "minItems": TARGET_GUIDELINES,
            "maxItems": TARGET_GUIDELINES,
            "items": {
                "type": "object",
                "required": [
                    "comparative",
                    "reasoning",
                    "questions",
                    "candidate_ids",
                ],
                "properties": {
                    "comparative": {"type": "string"},
                    "reasoning": {"type": "string"},
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 4,
                    },
                    "candidate_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}

REVIEW_SCHEMA = {
    "type": "object",
    "required": [
        "recommendation",
        "coverage_score",
        "grounding_score",
        "redundancy_score",
        "strengths",
        "findings",
        "missing_source_regions",
    ],
    "properties": {
        "recommendation": {
            "type": "string",
            "enum": ["accept", "revise", "reject"],
        },
        "coverage_score": {"type": "number", "minimum": 0, "maximum": 100},
        "grounding_score": {"type": "number", "minimum": 0, "maximum": 100},
        "redundancy_score": {"type": "number", "minimum": 0, "maximum": 100},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "findings": {"type": "array", "items": {"type": "string"}},
        "missing_source_regions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_path: str
    index: int
    text: str
    char_count: int
    sha256: str


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        num_ctx: int,
        seed: int,
        timeout_seconds: int,
        thinking: bool,
    ) -> None:
        self.chat_url = f"{base_url.rstrip('/')}/api/chat"
        self.num_ctx = num_ctx
        self.seed = seed
        self.timeout_seconds = timeout_seconds
        self.thinking = thinking

    def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: dict[str, Any],
        temperature: float,
        num_predict: int = 2048,
        retries: int = 2,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "stream": False,
            "think": self.thinking,
            "format": schema,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": temperature,
                "seed": self.seed,
                "num_ctx": self.num_ctx,
                "num_predict": num_predict,
            },
            "keep_alive": "30m",
        }

        last_error = "unknown error"
        for attempt in range(retries + 1):
            try:
                payload["options"]["seed"] = self.seed + attempt
                request = urllib.request.Request(
                    self.chat_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    body = json.loads(response.read().decode("utf-8"))
                content = body["message"]["content"]
                if not content.strip():
                    thinking_chars = len(body["message"].get("thinking", ""))
                    raise ValueError(
                        "Ollama returned empty final content "
                        f"(thinking_chars={thinking_chars}, "
                        f"done_reason={body.get('done_reason')}, "
                        f"eval_count={body.get('eval_count')})"
                    )
                value = parse_json_object(content)
                validate(instance=value, schema=schema)
                return value
            except ValidationError as exc:
                path = ".".join(str(part) for part in exc.absolute_path)
                response_keys = sorted(value) if isinstance(value, dict) else []
                last_error = (
                    f"schema error at {path or '<root>'}: {exc.message}; "
                    f"response_keys={response_keys}"
                )
                if attempt == retries:
                    raise RuntimeError(
                        f"Ollama request failed after {retries + 1} attempts: "
                        f"{last_error}"
                    ) from None
                time.sleep(2**attempt)
            except (
                KeyError,
                json.JSONDecodeError,
                TimeoutError,
                urllib.error.URLError,
                ValueError,
            ) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt == retries:
                    raise RuntimeError(
                        f"Ollama request failed after {retries + 1} attempts: "
                        f"{last_error}"
                    ) from None
                time.sleep(2**attempt)

        raise AssertionError("unreachable")


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def discover_sources(source_dir: Path) -> list[Path]:
    paths = [
        path
        for path in source_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SOURCE_SUFFIXES
        and path.name not in EXCLUDED_NAMES
        and "_private" not in path.parts
    ]
    if not paths:
        raise ValueError(f"No public Markdown or text sources found in {source_dir}")
    return sorted(paths)


def split_long_block(block: str, target_chars: int) -> list[str]:
    if len(block) <= target_chars:
        return [block]

    pieces = []
    start = 0
    while start < len(block):
        end = min(start + target_chars, len(block))
        if end < len(block):
            boundary = block.rfind(" ", start, end)
            if boundary > start + target_chars // 2:
                end = boundary
        pieces.append(block[start:end].strip())
        start = end
    return [piece for piece in pieces if piece]


def chunk_document(
    source_path: str,
    text: str,
    target_chars: int,
    overlap_chars: int,
) -> list[Chunk]:
    if target_chars < 1000:
        raise ValueError("target_chars must be at least 1000")
    if overlap_chars < 0 or overlap_chars >= target_chars:
        raise ValueError("overlap_chars must be >= 0 and < target_chars")

    raw_blocks = [
        block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()
    ]
    blocks = [
        piece for block in raw_blocks for piece in split_long_block(block, target_chars)
    ]

    chunks: list[Chunk] = []
    start = 0
    while start < len(blocks):
        end = start
        size = 0
        while end < len(blocks):
            added = len(blocks[end]) + (2 if end > start else 0)
            if end > start and size + added > target_chars:
                break
            size += added
            end += 1

        chunk_text = "\n\n".join(blocks[start:end])
        index = len(chunks) + 1
        chunk_id = f"{source_path}::chunk-{index:04d}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                source_path=source_path,
                index=index,
                text=chunk_text,
                char_count=len(chunk_text),
                sha256=sha256_text(chunk_text),
            )
        )

        if end >= len(blocks):
            break

        next_start = end
        overlap = 0
        while next_start > start + 1:
            candidate_size = len(blocks[next_start - 1]) + (2 if overlap else 0)
            if overlap + candidate_size > overlap_chars:
                break
            overlap += candidate_size
            next_start -= 1
        start = next_start

    return chunks


def build_chunks(
    source_dir: Path,
    target_chars: int,
    overlap_chars: int,
) -> tuple[list[Chunk], list[dict[str, Any]]]:
    chunks = []
    source_manifest = []
    for path in discover_sources(source_dir):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(source_dir).as_posix()
        document_chunks = chunk_document(
            relative,
            text,
            target_chars,
            overlap_chars,
        )
        chunks.extend(document_chunks)
        source_manifest.append(
            {
                "path": relative,
                "bytes": len(text.encode("utf-8")),
                "characters": len(text),
                "sha256": sha256_text(text),
                "chunk_count": len(document_chunks),
            }
        )
    return chunks, source_manifest


def limit_chunks_stratified(
    chunks: Sequence[Chunk],
    limit: int | None,
) -> list[Chunk]:
    if not limit or limit >= len(chunks):
        return list(chunks)

    by_source: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        by_source[chunk.source_path].append(chunk)

    selected = []
    source_paths = sorted(by_source)
    cursor = 0
    while len(selected) < limit:
        made_progress = False
        for source_path in source_paths:
            source_chunks = by_source[source_path]
            if cursor < len(source_chunks):
                selected.append(source_chunks[cursor])
                made_progress = True
                if len(selected) == limit:
                    break
        if not made_progress:
            break
        cursor += 1
    return selected


def score_chunk(
    client: OllamaClient,
    model: str,
    chunk: Chunk,
) -> dict[str, Any]:
    system = (
        "You are a low-cost source router for a constitution-distillation "
        "experiment. Score the supplied passage, not the author or tradition. "
        "Return only the requested JSON."
    )
    user = f"""Assess this source chunk for normative criterion extraction.

Scoring:
- 0: no usable normative content
- 1: mostly descriptive or duplicative
- 2: some relevant values but weakly operationalized
- 3: clear prescriptions, priorities, duties, virtues, or behavioral guidance
- 4: foundational principles, conflict resolution, exceptions, or unusually
  distinctive commitments

Do not lower the score merely because a principle may be rare. Mark rare
exceptions and conflict-resolution passages explicitly.

Source: {chunk.source_path}
Chunk: {chunk.chunk_id}

<source>
{chunk.text}
</source>"""
    return client.chat_json(
        model=model,
        system=system,
        user=user,
        schema=SCORE_SCHEMA,
        temperature=0.0,
        num_predict=600,
    )


def select_scored_chunks(
    chunks: Sequence[Chunk],
    scores: dict[str, dict[str, Any]],
    *,
    min_score: int,
    audit_low_score_count: int,
    max_selected: int | None,
    seed: int,
) -> tuple[list[Chunk], dict[str, list[str]]]:
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    selected_ids = {
        chunk_id
        for chunk_id, score in scores.items()
        if score["normative_yield"] >= min_score
        or score["contains_conflict_resolution"]
        or score["contains_rare_exception"]
    }
    reasons: dict[str, list[str]] = defaultdict(list)
    for chunk_id in selected_ids:
        reasons[chunk_id].append("score-or-exception")

    by_source: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        by_source[chunk.source_path].append(chunk)

    mandatory_ids = set()
    for source_chunks in by_source.values():
        best = max(
            source_chunks,
            key=lambda chunk: (
                scores[chunk.chunk_id]["normative_yield"],
                scores[chunk.chunk_id]["contains_conflict_resolution"],
                scores[chunk.chunk_id]["contains_rare_exception"],
                -chunk.index,
            ),
        )
        mandatory_ids.add(best.chunk_id)
        selected_ids.add(best.chunk_id)
        reasons[best.chunk_id].append("per-source-coverage")

    low_score_ids = sorted(
        chunk.chunk_id for chunk in chunks if chunk.chunk_id not in selected_ids
    )
    rng = random.Random(seed)
    audit_ids = rng.sample(
        low_score_ids,
        min(audit_low_score_count, len(low_score_ids)),
    )
    for chunk_id in audit_ids:
        selected_ids.add(chunk_id)
        mandatory_ids.add(chunk_id)
        reasons[chunk_id].append("low-score-audit")

    if max_selected and len(selected_ids) > max_selected:
        if max_selected < len(mandatory_ids):
            raise ValueError(
                "max_selected is smaller than mandatory coverage and audit chunks"
            )
        ranked_optional = sorted(
            selected_ids - mandatory_ids,
            key=lambda chunk_id: (
                scores[chunk_id]["normative_yield"],
                scores[chunk_id]["contains_conflict_resolution"],
                scores[chunk_id]["contains_rare_exception"],
                -by_id[chunk_id].index,
                chunk_id,
            ),
            reverse=True,
        )
        available = max_selected - len(mandatory_ids)
        selected_ids = mandatory_ids | set(ranked_optional[:available])

    selected = [chunk for chunk in chunks if chunk.chunk_id in selected_ids]
    selected_reasons = {
        key: value for key, value in sorted(reasons.items()) if key in selected_ids
    }
    return selected, selected_reasons


def extract_candidates(
    client: OllamaClient,
    model: str,
    chunk: Chunk,
) -> list[dict[str, Any]]:
    system = (
        "You extract source-grounded, behaviorally checkable constitution "
        "candidates. Do not use outside knowledge. Return only the requested JSON."
    )
    user = f"""Extract up to six candidate items from this source chunk.

Use kind "criterion" for a general behavioral preference. Use kind "guideline"
for a conflict, exception, priority, or edge-case rule. Each statement must:
- describe one independently judgeable behavior in an LLM response;
- be specific to commitments supported by this passage;
- avoid generic helpfulness unless the source explicitly grounds it;
- remain useful in a pairwise comparison of two model responses.

For each item return kind, statement, and evidence. You may also return a short
rationale. Evidence must be a short exact excerpt from the supplied chunk.
Return no item when the passage does not support a meaningful normative
distinction.

Source: {chunk.source_path}
Chunk: {chunk.chunk_id}

<source>
{chunk.text}
</source>"""
    result = client.chat_json(
        model=model,
        system=system,
        user=user,
        schema=CANDIDATE_SCHEMA,
        temperature=0.2,
        num_predict=1800,
    )
    candidates = []
    for index, candidate in enumerate(result.get("candidates", []), start=1):
        candidates.append(
            {
                "candidate_id": f"{chunk.chunk_id}::candidate-{index:02d}",
                "chunk_id": chunk.chunk_id,
                "source_path": chunk.source_path,
                **candidate,
            }
        )
    return candidates


def batched(values: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def cluster_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "candidate_id": candidate["candidate_id"],
        "kind": candidate["kind"],
        "statement": candidate["statement"],
        "evidence": candidate["evidence"],
        "source_path": candidate["source_path"],
    }
    if candidate.get("rationale"):
        payload["rationale"] = candidate["rationale"]
    return payload


def cluster_schema_for(
    candidate_ids: Sequence[str],
    max_clusters: int,
) -> dict[str, Any]:
    schema = json.loads(json.dumps(RAW_CLUSTER_SCHEMA))
    schema["properties"]["clusters"]["maxItems"] = max_clusters
    id_items = schema["properties"]["clusters"]["items"]["properties"]["candidates"][
        "items"
    ]
    id_items["enum"] = list(candidate_ids)
    return schema


def constitution_schema_for(candidate_ids: Sequence[str]) -> dict[str, Any]:
    schema = json.loads(json.dumps(CONSTITUTION_SCHEMA))
    for section in ("criteria", "guidelines"):
        id_items = schema["properties"][section]["items"]["properties"][
            "candidate_ids"
        ]["items"]
        id_items["enum"] = list(candidate_ids)
    return schema


def ensure_known_candidate_ids(
    records: Sequence[dict[str, Any]],
    known_ids: set[str],
    label: str,
) -> None:
    unknown_ids = {
        candidate_id
        for record in records
        for candidate_id in record["candidate_ids"]
        if candidate_id not in known_ids
    }
    if unknown_ids:
        raise ValueError(
            f"{label} returned unknown candidate IDs: " + ", ".join(sorted(unknown_ids))
        )


def normalize_clusters(
    raw_clusters: Sequence[dict[str, Any]],
    candidate_kinds: dict[str, str],
) -> list[dict[str, Any]]:
    clusters = []
    for raw_cluster in raw_clusters:
        candidate_ids = raw_cluster["candidates"]
        kinds = {candidate_kinds[candidate_id] for candidate_id in candidate_ids}
        kind = next(iter(kinds)) if len(kinds) == 1 else "mixed"
        clusters.append(
            {
                "label": raw_cluster["cluster_id"],
                "kind": kind,
                "synthesis": raw_cluster["description"],
                "candidate_ids": candidate_ids,
                "counter_considerations": [],
            }
        )
    return clusters


def cluster_batch(
    client: OllamaClient,
    model: str,
    candidates: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    system = (
        "You cluster source-grounded constitution candidates by the behavior "
        "they measure. Preserve minority principles and conflicts. Return only JSON."
    )
    user = f"""Cluster semantically overlapping candidates.

Rules:
- Merge candidates only when they measure substantially the same behavior.
- Keep low-frequency but distinctive principles as separate clusters.
- Keep conflicts and counter-considerations visible.
- Use only candidate IDs supplied below.
- Return exactly this shape:
  {{"clusters": [{{"cluster_id": "short_label", "description": "synthesis",
  "candidates": ["supplied candidate ID"]}}]}}

Candidates:
{json.dumps([cluster_payload(item) for item in candidates], ensure_ascii=False)}"""
    candidate_ids = [item["candidate_id"] for item in candidates]
    candidate_kinds = {item["candidate_id"]: item["kind"] for item in candidates}
    result = client.chat_json(
        model=model,
        system=system,
        user=user,
        schema=cluster_schema_for(candidate_ids, len(candidate_ids)),
        temperature=0.1,
        num_predict=5000,
    )
    clusters = normalize_clusters(result["clusters"], candidate_kinds)
    ensure_known_candidate_ids(clusters, set(candidate_ids), "Clusterer")
    return clusters


def merge_clusters(
    client: OllamaClient,
    model: str,
    clusters: Sequence[dict[str, Any]],
    candidate_kinds: dict[str, str],
) -> list[dict[str, Any]]:
    if len(clusters) <= 18:
        return list(clusters)

    system = (
        "You consolidate a hierarchy of source-grounded criterion clusters. "
        "Preserve candidate provenance and minority principles. Return only JSON."
    )
    user = f"""Consolidate these preliminary clusters into at most 18 clusters.

Merge only genuine conceptual overlap. Keep distinct conflict rules and rare
principles. Every ID in an output candidates array must come from an input
cluster.
Return exactly this shape:
{{"clusters": [{{"cluster_id": "short_label", "description": "synthesis",
"candidates": ["supplied candidate ID"]}}]}}

Preliminary clusters:
{json.dumps(clusters, ensure_ascii=False)}"""
    candidate_ids = sorted(
        {
            candidate_id
            for cluster in clusters
            for candidate_id in cluster["candidate_ids"]
        }
    )
    result = client.chat_json(
        model=model,
        system=system,
        user=user,
        schema=cluster_schema_for(candidate_ids, 18),
        temperature=0.1,
        num_predict=4000,
    )
    merged = normalize_clusters(result["clusters"], candidate_kinds)
    ensure_known_candidate_ids(merged, set(candidate_ids), "Cluster merger")
    return merged


def cluster_candidates(
    client: OllamaClient,
    model: str,
    candidates: Sequence[dict[str, Any]],
    batch_size: int,
    checkpoint_path: Path | None = None,
) -> list[dict[str, Any]]:
    checkpoint = (
        json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint_path and checkpoint_path.exists()
        else {"batches": {}}
    )
    preliminary = []
    for batch in batched(candidates, batch_size):
        batch_key = sha256_text(
            "\n".join(candidate["candidate_id"] for candidate in batch)
        )
        if batch_key in checkpoint["batches"]:
            batch_clusters = checkpoint["batches"][batch_key]
        else:
            batch_clusters = cluster_batch(client, model, batch)
            checkpoint["batches"][batch_key] = batch_clusters
            if checkpoint_path:
                write_json(checkpoint_path, checkpoint)
        preliminary.extend(batch_clusters)
    candidate_kinds = {
        candidate["candidate_id"]: candidate["kind"] for candidate in candidates
    }
    return merge_clusters(client, model, preliminary, candidate_kinds)


def write_constitution(
    client: OllamaClient,
    model: str,
    value_system: str,
    clusters: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    system = (
        "You write a compact model constitution from source-grounded clusters. "
        "Do not use outside knowledge. Return only the requested JSON."
    )
    user = f"""Write a candidate model constitution for {value_system}.

Requirements:
- Exactly {TARGET_CRITERIA} brief, atomic, non-redundant criteria.
- Exactly {TARGET_GUIDELINES} guidelines for conflicts, exceptions, or edge cases.
- Each comparative field begins "Prefer the response that".
- Each item is behaviorally checkable in pairwise LLM-response judgments.
- Preserve distinctive and low-frequency source commitments when foundational.
- Do not substitute generic helpfulness for the supplied source evidence.
- candidate_ids must cite the clusters' source candidate IDs that support the item.
- Questions should be discriminative templates capable of eliciting meaningfully
  aligned and misaligned responses, not prompts with a trivial right answer.
- Return exactly this shape:
  {{"overview": "2-4 sentences", "criteria": [
    {{"comparative": "Prefer the response that...", "reasoning": "...",
    "questions": ["...", "..."], "candidate_ids": ["supplied candidate ID"]}}
  ], "guidelines": [
    {{"comparative": "Prefer the response that...", "reasoning": "...",
    "questions": ["...", "..."], "candidate_ids": ["supplied candidate ID"]}}
  ]}}

Source-grounded clusters:
{json.dumps(clusters, ensure_ascii=False)}"""
    candidate_ids = sorted(
        {
            candidate_id
            for cluster in clusters
            for candidate_id in cluster["candidate_ids"]
        }
    )
    result = client.chat_json(
        model=model,
        system=system,
        user=user,
        schema=constitution_schema_for(candidate_ids),
        temperature=0.2,
        num_predict=6000,
    )
    ensure_known_candidate_ids(
        result["criteria"] + result["guidelines"],
        set(candidate_ids),
        "Constitution writer",
    )
    return result


def strip_provenance(
    enriched_constitution: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    constitution = {
        "overview": enriched_constitution["overview"],
        "criteria": [],
        "guidelines": [],
    }
    provenance = {}
    singular = {"criteria": "criterion", "guidelines": "guideline"}
    for section in ("criteria", "guidelines"):
        for index, item in enumerate(enriched_constitution[section], start=1):
            item_id = f"{singular[section]}-{index:02d}"
            provenance[item_id] = list(item["candidate_ids"])
            constitution[section].append(
                {key: value for key, value in item.items() if key != "candidate_ids"}
            )
    return constitution, provenance


def build_source_map(
    chunks: Sequence[Chunk],
    scores: dict[str, dict[str, Any]],
    selected_ids: set[str],
) -> list[dict[str, Any]]:
    source_map = []
    for chunk in chunks:
        score = scores.get(chunk.chunk_id)
        source_map.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_path": chunk.source_path,
                "selected_for_extraction": chunk.chunk_id in selected_ids,
                "normative_yield": (score["normative_yield"] if score else None),
                "themes": score["themes"] if score else [],
                "router_rationale": score["rationale"] if score else "",
            }
        )
    return source_map


def normalize_review_scores(review: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(review)
    for key in ("coverage_score", "grounding_score", "redundancy_score"):
        value = float(normalized[key])
        if value <= 1:
            value *= 100
        normalized[key] = round(value)
    return normalized


def review_constitution(
    client: OllamaClient,
    model: str,
    value_system: str,
    constitution: dict[str, Any],
    provenance: dict[str, list[str]],
    clusters: Sequence[dict[str, Any]],
    source_map: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    system = (
        "You audit a constitution and its source-coverage record. Treat the "
        "provided evidence as exhaustive; do not use outside knowledge. Return JSON."
    )
    user = f"""Review this {value_system} constitution as a measurement instrument.

Check:
- item-level grounding in cited candidate clusters;
- clarity, atomicity, redundancy, and pairwise usefulness;
- whether repeated items create de facto weighting;
- source-level coverage, including high-yield or distinctive unrepresented chunks;
- missing conflict rules and counter-considerations;
- overbroad criteria that could describe many nearby value systems.

Tag findings as [target][finding] description, using findings such as coverage,
grounding, atomicity, redundancy, balance, counter-consideration, specificity,
or pairwise-usefulness.

Return exactly this shape:
{{"recommendation": "accept|revise|reject", "coverage_score": 0,
"grounding_score": 0, "redundancy_score": 0, "strengths": ["..."],
"findings": ["[target][finding] description"],
"missing_source_regions": ["chunk ID or description"]}}

Constitution:
{json.dumps(constitution, ensure_ascii=False)}

Item provenance:
{json.dumps(provenance, ensure_ascii=False)}

Candidate clusters:
{json.dumps(clusters, ensure_ascii=False)}

Complete chunk source map:
{json.dumps(source_map, ensure_ascii=False)}"""
    review = client.chat_json(
        model=model,
        system=system,
        user=user,
        schema=REVIEW_SCHEMA,
        temperature=0.1,
        num_predict=3500,
    )
    return normalize_review_scores(review)


def load_checkpoint(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    return value.get(key, [])


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Distill a constitution from a source bundle larger than the "
            "configured model context."
        )
    )
    parser.add_argument("--source-dir", type=Path, default=Path("sources/stoicism"))
    parser.add_argument("--value-system", default="Stoicism")
    parser.add_argument(
        "--mode",
        choices=("score-first", "all-chunks"),
        default="score-first",
    )
    parser.add_argument("--scorer-model", default="qwen2.5:3b")
    parser.add_argument(
        "--writer-model",
        default="qwen3.6:35b-a3b-q4_K_M",
    )
    parser.add_argument("--reviewer-model", default=None)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--num-ctx", type=int, default=32768)
    parser.add_argument("--chunk-chars", type=int, default=18000)
    parser.add_argument("--overlap-chars", type=int, default=1500)
    parser.add_argument("--min-score", type=int, default=3)
    parser.add_argument("--audit-low-score-count", type=int, default=2)
    parser.add_argument("--max-selected", type=int, default=18)
    parser.add_argument("--candidate-batch-size", type=int, default=24)
    parser.add_argument("--max-chunks", type=int, default=0)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument(
        "--thinking",
        action="store_true",
        help=(
            "Enable model reasoning. Disabled by default because reasoning can "
            "consume the structured-output token budget."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    reviewer_model = args.reviewer_model or args.writer_model
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or (
        Path(__file__).parent / "runs" / f"{timestamp}-{args.mode}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks, source_manifest = build_chunks(
        args.source_dir,
        args.chunk_chars,
        args.overlap_chars,
    )
    chunks = limit_chunks_stratified(chunks, args.max_chunks or None)
    chunk_records = [asdict(chunk) for chunk in chunks]

    config = {
        "protocol_version": PROTOCOL_VERSION,
        "created_at": timestamp,
        "source_dir": str(args.source_dir),
        "value_system": args.value_system,
        "mode": args.mode,
        "scorer_model": args.scorer_model,
        "writer_model": args.writer_model,
        "reviewer_model": reviewer_model,
        "ollama_url": args.ollama_url,
        "num_ctx": args.num_ctx,
        "thinking": args.thinking,
        "chunk_chars": args.chunk_chars,
        "overlap_chars": args.overlap_chars,
        "min_score": args.min_score,
        "audit_low_score_count": args.audit_low_score_count,
        "max_selected": args.max_selected,
        "candidate_batch_size": args.candidate_batch_size,
        "target_criteria": TARGET_CRITERIA,
        "target_guidelines": TARGET_GUIDELINES,
        "max_chunks": args.max_chunks or None,
        "seed": args.seed,
        "source_manifest": source_manifest,
        "chunk_count": len(chunks),
    }
    write_json(output_dir / "run_config.json", config)
    write_json(output_dir / "chunks.json", {"chunks": chunk_records})
    print(f"Prepared {len(chunks)} chunks in {output_dir}", flush=True)

    if args.dry_run:
        print("Dry run complete; no model calls were made.", flush=True)
        return 0

    client = OllamaClient(
        args.ollama_url,
        args.num_ctx,
        args.seed,
        args.timeout_seconds,
        args.thinking,
    )

    scores_path = output_dir / "chunk_scores.json"
    existing_scores = load_checkpoint(scores_path, "scores")
    scores = {item["chunk_id"]: item for item in existing_scores}
    if args.mode == "score-first":
        for position, chunk in enumerate(chunks, start=1):
            if chunk.chunk_id in scores:
                continue
            print(
                f"[score {position}/{len(chunks)}] {chunk.chunk_id}",
                flush=True,
            )
            score = score_chunk(client, args.scorer_model, chunk)
            scores[chunk.chunk_id] = {"chunk_id": chunk.chunk_id, **score}
            write_json(scores_path, {"scores": list(scores.values())})

        selected, selection_reasons = select_scored_chunks(
            chunks,
            scores,
            min_score=args.min_score,
            audit_low_score_count=args.audit_low_score_count,
            max_selected=args.max_selected or None,
            seed=args.seed,
        )
    else:
        selected = list(chunks)
        selection_reasons = {chunk.chunk_id: ["all-chunks"] for chunk in selected}

    selected_ids = {chunk.chunk_id for chunk in selected}
    write_json(
        output_dir / "selection.json",
        {
            "selected_chunk_ids": sorted(selected_ids),
            "selected_count": len(selected),
            "total_count": len(chunks),
            "selection_reasons": selection_reasons,
        },
    )
    print(f"Selected {len(selected)}/{len(chunks)} chunks", flush=True)

    candidates_path = output_dir / "candidates.json"
    candidates_checkpoint = (
        json.loads(candidates_path.read_text(encoding="utf-8"))
        if candidates_path.exists()
        else {}
    )
    existing_candidates = candidates_checkpoint.get("candidates", [])
    completed_chunk_ids = set(candidates_checkpoint.get("completed_chunk_ids", []))
    candidates_by_chunk: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in existing_candidates:
        candidates_by_chunk[candidate["chunk_id"]].append(candidate)

    for position, chunk in enumerate(selected, start=1):
        if chunk.chunk_id in completed_chunk_ids:
            continue
        print(
            f"[extract {position}/{len(selected)}] {chunk.chunk_id}",
            flush=True,
        )
        candidates_by_chunk[chunk.chunk_id] = extract_candidates(
            client,
            args.writer_model,
            chunk,
        )
        completed_chunk_ids.add(chunk.chunk_id)
        flattened = [
            candidate
            for selected_chunk in selected
            for candidate in candidates_by_chunk.get(
                selected_chunk.chunk_id,
                [],
            )
        ]
        write_json(
            candidates_path,
            {
                "completed_chunk_ids": sorted(completed_chunk_ids),
                "candidates": flattened,
            },
        )

    candidates = [
        candidate
        for chunk in selected
        for candidate in candidates_by_chunk.get(chunk.chunk_id, [])
    ]
    if not candidates:
        raise RuntimeError("No constitution candidates were extracted")
    print(f"Extracted {len(candidates)} candidates", flush=True)

    clusters_path = output_dir / "clusters.json"
    if clusters_path.exists():
        clusters = json.loads(clusters_path.read_text(encoding="utf-8"))["clusters"]
        print(f"Loaded {len(clusters)} checkpointed clusters", flush=True)
    else:
        print("Clustering candidates", flush=True)
        clusters = cluster_candidates(
            client,
            args.writer_model,
            candidates,
            args.candidate_batch_size,
            checkpoint_path=output_dir / "preliminary_clusters.json",
        )
        write_json(clusters_path, {"clusters": clusters})

    enriched_path = output_dir / "constitution.enriched.json"
    constitution_path = output_dir / "constitution.json"
    provenance_path = output_dir / "provenance.json"
    if (
        enriched_path.exists()
        and constitution_path.exists()
        and provenance_path.exists()
    ):
        enriched = json.loads(enriched_path.read_text(encoding="utf-8"))
        constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        print("Loaded checkpointed constitution", flush=True)
    else:
        print("Writing constitution", flush=True)
        enriched = write_constitution(
            client,
            args.writer_model,
            args.value_system,
            clusters,
        )
        constitution, provenance = strip_provenance(enriched)
        write_json(enriched_path, enriched)
        write_json(constitution_path, constitution)
        write_json(provenance_path, provenance)

    source_map = build_source_map(chunks, scores, selected_ids)
    write_json(output_dir / "source_map.json", source_map)

    review_path = output_dir / "review.json"
    if review_path.exists():
        review = json.loads(review_path.read_text(encoding="utf-8"))
        print("Loaded checkpointed review", flush=True)
    else:
        print("Reviewing grounding and coverage", flush=True)
        review = review_constitution(
            client,
            reviewer_model,
            args.value_system,
            constitution,
            provenance,
            clusters,
            source_map,
        )
        write_json(review_path, review)
    print(
        f"Complete: {review['recommendation']} "
        f"(coverage={review['coverage_score']}, "
        f"grounding={review['grounding_score']})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
