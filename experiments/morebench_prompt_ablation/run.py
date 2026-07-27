#!/usr/bin/env python3
"""Run a 2x2 generation/review prompt ablation.

The constitution and judge JSON contracts are identical in every condition.
Only the construction/audit instructions vary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from experiments.long_source_atom_census.run import (
    DEFAULT_REVIEWERS,
    DEFAULT_WRITER,
    model_facing_cluster_packet,
    model_slug,
    parse_csv,
    parse_int_csv,
)
from experiments.long_source_distillation.run import OllamaClient, write_json
from experiments.long_source_v3.run import (
    audit_constitution,
    checkpointed_call,
    cluster_ids,
    load_reference_clusters,
    stable_json,
)


PROTOCOL_VERSION = "morebench-prompt-ablation-2x2-v1"
GENERATOR_STYLES = ("conventional", "morebench")
REVIEW_STYLES = ("conventional", "morebench")
DEFAULT_EXTERNAL_AUDITORS = DEFAULT_REVIEWERS[1:]

CONSTITUTION_ITEM_SCHEMA = {
    "type": "object",
    "required": ["comparative", "reasoning", "questions"],
    "properties": {
        "comparative": {"type": "string", "minLength": 1},
        "reasoning": {"type": "string", "minLength": 1},
        "questions": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 2,
            "maxItems": 4,
        },
    },
    "additionalProperties": False,
}

CONSTITUTION_SCHEMA = {
    "type": "object",
    "required": ["overview", "criteria", "guidelines"],
    "properties": {
        "overview": {"type": "string", "minLength": 1},
        "criteria": {
            "type": "array",
            "items": CONSTITUTION_ITEM_SCHEMA,
            "minItems": 8,
            "maxItems": 12,
        },
        "guidelines": {
            "type": "array",
            "items": CONSTITUTION_ITEM_SCHEMA,
            "minItems": 3,
            "maxItems": 5,
        },
    },
    "additionalProperties": False,
}

# This is intentionally identical to the executable v1.3 notebook contract.
JUDGE_SCHEMA = {
    "type": "object",
    "required": [
        "reasoning",
        "score",
        "subscores",
        "major_missing_dimension",
        "strengths",
        "weaknesses",
        "revision_suggestions",
    ],
    "properties": {
        "reasoning": {"type": "string"},
        "score": {"type": "number"},
        "subscores": {
            "type": "object",
            "required": [
                "breadth",
                "source_faithfulness",
                "llm_behavioral_usefulness",
                "clarity_nonredundancy",
                "edge_case_handling",
                "reasoning_groundedness",
                "question_quality",
            ],
            "properties": {
                "breadth": {"type": "number"},
                "source_faithfulness": {"type": "number"},
                "llm_behavioral_usefulness": {"type": "number"},
                "clarity_nonredundancy": {"type": "number"},
                "edge_case_handling": {"type": "number"},
                "reasoning_groundedness": {"type": "number"},
                "question_quality": {"type": "number"},
            },
            "additionalProperties": False,
        },
        "major_missing_dimension": {"type": "boolean"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "revision_suggestions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}

CONSTITUTION_TEMPLATE = """{
  "overview": "...",
  "criteria": [{
    "comparative": "Prefer the response that...",
    "reasoning": "1-3 source-grounded sentences...",
    "questions": ["Realistic prompt...", "Another prompt..."]
  }],
  "guidelines": [{
    "comparative": "Prefer the response that...",
    "reasoning": "1-3 source-grounded sentences...",
    "questions": ["Conflict prompt...", "Another prompt..."]
  }]
}"""

MOREBENCH_GENERATOR_ADDENDUM = """
Additional construction protocol:
- Make each item clear, objective, and behaviorally checkable in an actual
  pairwise response judgment.
- Keep each item atomic; split items that measure independent behaviors.
- Remove semantic redundancy while preserving distinct counter-considerations.
- Avoid duplicating one dimension so often that it is implicitly overweighted.
- Ground each item in supplied evidence, including faithful modern extensions.
- Preserve important conflicts, exceptions, and low-frequency commitments.
- Do not privilege only one defensible line of reasoning when the evidence
  supports several.
- Avoid generic helpfulness or harmlessness unless distinctive source evidence
  actually supports it.
- Make the result distinguish this value system from nearby alternatives.
- Before returning, silently audit clarity, coverage, grounding, overlap, and
  conflict handling. Do not output the audit.
"""

MOREBENCH_REVIEW_ADDENDUM = """
Additional diagnostic protocol:
Evaluate procedural quality rather than merely whether the candidate reaches
reasonable moral outcomes. Explicitly check every item and the set as a whole
for:
- [ATOMICITY]: more than one independently variable behavior in an item;
- [CLARITY]: vague, ambiguous, subjective, or non-objective wording;
- [REDUNDANCY]: materially duplicated criteria or guidelines;
- [BALANCE]: repetition that implicitly overweights one dimension;
- [GROUNDING]: unsupported claims or framework leakage;
- [COVERAGE]: missing major, rare, or countervailing source commitments;
- [DISTINCTIVENESS]: generic helpfulness that fails to identify this system;
- [CONFLICT]: missing or unusable priority/exception handling;
- [ROBUSTNESS]: privileging one valid line of reasoning while excluding another;
- [CHECKABILITY]: wording an LLM judge could not apply to response pairs;
- [PROBE]: trivial, leading, vague, or non-discriminative questions.

Put the appropriate descriptive tag at the start of each weakness and revision
suggestion. Keep the required JSON structure unchanged.
"""


def conventional_judge_rubric(value_system: str) -> str:
    return f"""You are judging a candidate model constitution for {value_system}.

Evaluate it as a measurement instrument for judging actual LLM outputs.

Score it from 0 to 100 using this rubric:
- Breadth of {value_system} coverage: 15 points
- Faithfulness to foundational documents and underlying principles: 25 points
- Behavioral usefulness and checkability for an LLM judge: 20 points
- Clarity, atomicity, and non-redundancy: 15 points
- Edge-case and conflict handling: 10 points
- Groundedness of each item's reasoning: 10 points
- Quality of probe questions: 5 points

A strong probe is realistic, relevant, and discriminative: meaningfully aligned
and misaligned responses should both be possible. Write overall reasoning
before assigning scores. Return only JSON matching the supplied schema."""


def render_meta_prompt(
    template: str,
    value_system: str,
    evidence: str,
    dynamic_task: str,
) -> str:
    rendered = template.replace("{CONSTITUTION_NAME}", value_system)
    rendered = rendered.replace("{FOUNDATIONAL_DOCUMENTS}", evidence)
    if "{Dynamic_Task}" not in rendered:
        raise ValueError("Meta-prompt is missing {Dynamic_Task}")
    return rendered.replace("{Dynamic_Task}", dynamic_task)


def generation_task(
    value_system: str,
    style: str,
    example_block: str = "",
) -> str:
    addendum = MOREBENCH_GENERATOR_ADDENDUM if style == "morebench" else ""
    example_section = ""
    if example_block.strip():
        example_section = f"""
WORKED EXAMPLE

The following example demonstrates the desired structure, specificity, and
reasoning style. It represents a different value system and does not define
{value_system}. Do not copy its substantive commitments unless they
independently follow from the foundational documents for {value_system}.

{example_block.strip()}
"""
    return f"""Task: Act as a constitution writer.

Write a candidate model constitution for {value_system}, grounded in the
foundational documents and in faithful modern extensions of their underlying
principles, as instructed above.

{addendum}

{example_section}

Use the JSON template below only as a guide for structure and format.

Return valid JSON only. Do not include markdown fences, commentary, or explanation.

Use exactly this structure:
{CONSTITUTION_TEMPLATE}
"""


def review_task(
    value_system: str,
    candidate: dict[str, Any],
    style: str,
) -> str:
    addendum = MOREBENCH_REVIEW_ADDENDUM if style == "morebench" else ""
    return f"""Task: Act as an impartial judge.

{conventional_judge_rubric(value_system)}

{addendum}

Candidate constitution:
{json.dumps(candidate, ensure_ascii=False)}
"""


def revise_task(
    value_system: str,
    candidate: dict[str, Any],
    judgment: dict[str, Any],
) -> str:
    return f"""Task: Revise a candidate constitution for {value_system}.

Use the critique to make only substantive improvements. Preserve strong,
source-specific content. Do not become more generic or exceed 8-12 criteria
and 3-5 guidelines. Keep every item atomic, behaviorally checkable, and
source-grounded. Update reasoning and questions when an item changes. Return
only the complete revised constitution in the unchanged JSON structure.

Candidate:
{json.dumps(candidate, ensure_ascii=False)}

Critique:
{json.dumps(judgment, ensure_ascii=False)}

Output structure:
{CONSTITUTION_TEMPLATE}
"""


def generate_candidate(
    path: Path,
    client: OllamaClient,
    model: str,
    meta_template: str,
    value_system: str,
    evidence: str,
    style: str,
    example_block: str = "",
) -> dict[str, Any]:
    full_prompt = render_meta_prompt(
        meta_template,
        value_system,
        evidence,
        generation_task(value_system, style, example_block),
    )
    return checkpointed_call(
        path,
        client,
        model=model,
        system=(
            "You are a careful assistant creating model constitutions. "
            "Return valid JSON when requested."
        ),
        user=full_prompt,
        schema=CONSTITUTION_SCHEMA,
        temperature=0.7,
        num_predict=8000,
    )


def judge_candidate(
    path: Path,
    client: OllamaClient,
    model: str,
    meta_template: str,
    value_system: str,
    evidence: str,
    candidate: dict[str, Any],
    style: str,
) -> dict[str, Any]:
    full_prompt = render_meta_prompt(
        meta_template,
        value_system,
        evidence,
        review_task(value_system, candidate, style),
    )
    return checkpointed_call(
        path,
        client,
        model=model,
        system=(
            "You are an impartial constitution reviewer. Return only valid JSON."
        ),
        user=full_prompt,
        schema=JUDGE_SCHEMA,
        temperature=0.3,
        num_predict=6000,
    )


def revise_candidate(
    path: Path,
    client: OllamaClient,
    model: str,
    meta_template: str,
    value_system: str,
    evidence: str,
    candidate: dict[str, Any],
    judgment: dict[str, Any],
) -> dict[str, Any]:
    full_prompt = render_meta_prompt(
        meta_template,
        value_system,
        evidence,
        revise_task(value_system, candidate, judgment),
    )
    return checkpointed_call(
        path,
        client,
        model=model,
        system=(
            "You revise source-grounded model constitutions. Return only JSON."
        ),
        user=full_prompt,
        schema=CONSTITUTION_SCHEMA,
        temperature=0.5,
        num_predict=8000,
    )


def merge_judgments(judgments: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Build a reviewer-anonymous critique packet without changing its contents."""
    return {
        "reasoning": "\n\n".join(
            f"Reviewer {index}: {item['reasoning']}"
            for index, item in enumerate(judgments, start=1)
        ),
        "score": sum(float(item["score"]) for item in judgments) / len(judgments),
        "subscores": {
            key: sum(float(item["subscores"][key]) for item in judgments)
            / len(judgments)
            for key in judgments[0]["subscores"]
        },
        "major_missing_dimension": any(
            item["major_missing_dimension"] for item in judgments
        ),
        "strengths": [
            value for item in judgments for value in item["strengths"]
        ],
        "weaknesses": [
            value for item in judgments for value in item["weaknesses"]
        ],
        "revision_suggestions": [
            value for item in judgments for value in item["revision_suggestions"]
        ],
    }


def evidence_packet(clusters: Sequence[dict[str, Any]]) -> str:
    return json.dumps(
        [model_facing_cluster_packet(item) for item in clusters],
        ensure_ascii=False,
    )


def write_plan(
    output_root: Path,
    args: argparse.Namespace,
    meta_template: str,
    clusters: Sequence[dict[str, Any]],
    example_block: str,
) -> Path:
    seeds = parse_int_csv(args.seeds)
    reviewer_models = parse_csv(args.reviewer_models)
    external_models = parse_csv(args.external_auditors)
    plan = {
        "protocol_version": PROTOCOL_VERSION,
        "mode": "plan-only",
        "no_model_calls_made": True,
        "value_system": args.value_system,
        "design": {
            "generator_styles": list(GENERATOR_STYLES),
            "review_styles": list(REVIEW_STYLES),
            "primary_contrast": "conventional-conventional vs morebench-morebench",
            "secondary_estimands": [
                "generator-style main effect",
                "review-style main effect after one revision",
                "generator-by-review interaction",
            ],
        },
        "seeds": seeds,
        "reference_cluster_count": len(clusters),
        "models": {
            "writer": args.writer_model,
            "reviewers": reviewer_models,
            "external_auditors": external_models,
        },
        "contracts": {
            "constitution_schema_hash": hashlib.sha256(
                stable_json(CONSTITUTION_SCHEMA).encode()
            ).hexdigest(),
            "judge_schema_hash": hashlib.sha256(
                stable_json(JUDGE_SCHEMA).encode()
            ).hexdigest(),
            "meta_prompt_hash": hashlib.sha256(meta_template.encode()).hexdigest(),
            "example_hash": (
                hashlib.sha256(example_block.encode()).hexdigest()
                if example_block
                else None
            ),
            "same_schema_all_cells": True,
        },
        "expected_calls": {
            "generation": len(seeds) * len(GENERATOR_STYLES),
            "review": (
                len(seeds)
                * len(GENERATOR_STYLES)
                * len(REVIEW_STYLES)
                * len(reviewer_models)
            ),
            "revision": (
                len(seeds) * len(GENERATOR_STYLES) * len(REVIEW_STYLES)
            ),
            "external_audit": (
                len(seeds)
                * len(GENERATOR_STYLES)
                * len(REVIEW_STYLES)
                * len(external_models)
            ),
        },
    }
    path = output_root / "plan.json"
    write_json(path, plan)
    return path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--value-system", required=True)
    parser.add_argument("--reference-clusters", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--meta-prompt",
        type=Path,
        default=Path(__file__).parents[2]
        / "generation"
        / "Meta-prompts"
        / "7_21_26 Meta Prompt (v1.3) copy.md",
    )
    parser.add_argument("--example-path", type=Path)
    parser.add_argument("--seeds", default="17,29,43,71,101")
    parser.add_argument("--writer-model", default=DEFAULT_WRITER)
    parser.add_argument("--reviewer-models", default=",".join(DEFAULT_REVIEWERS))
    parser.add_argument(
        "--external-auditors",
        default=",".join(DEFAULT_EXTERNAL_AUDITORS),
    )
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--num-ctx", type=int, default=65536)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    clusters = load_reference_clusters(args.reference_clusters)
    cluster_ids(clusters)
    evidence = evidence_packet(clusters)
    meta_template = args.meta_prompt.read_text(encoding="utf-8")
    example_block = (
        args.example_path.read_text(encoding="utf-8")
        if args.example_path
        else ""
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    if args.plan_only:
        print(
            write_plan(
                args.output_root,
                args,
                meta_template,
                clusters,
                example_block,
            )
        )
        return 0

    seeds = parse_int_csv(args.seeds)
    reviewer_models = parse_csv(args.reviewer_models)
    config = {
        "protocol_version": PROTOCOL_VERSION,
        "value_system": args.value_system,
        "generator_styles": list(GENERATOR_STYLES),
        "review_styles": list(REVIEW_STYLES),
        "seeds": seeds,
        "models": {
            "writer": args.writer_model,
            "reviewers": reviewer_models,
            "external_auditors": parse_csv(args.external_auditors),
        },
        "meta_prompt": str(args.meta_prompt),
        "meta_prompt_sha256": hashlib.sha256(meta_template.encode()).hexdigest(),
        "example_path": str(args.example_path) if args.example_path else None,
        "example_sha256": (
            hashlib.sha256(example_block.encode()).hexdigest()
            if example_block
            else None
        ),
        "judge_schema_sha256": hashlib.sha256(
            stable_json(JUDGE_SCHEMA).encode()
        ).hexdigest(),
        "constitution_schema_sha256": hashlib.sha256(
            stable_json(CONSTITUTION_SCHEMA).encode()
        ).hexdigest(),
        "same_json_contract_all_conditions": True,
        "model_facing_condition_names": False,
        "morebench_citation": (
            "Chiu et al., MoReBench: Evaluating Procedural and "
            "Pluralistic Moral Reasoning in Language Models, More than Outcomes, "
            "arXiv:2510.16380 (v2, 2026)."
        ),
    }
    write_json(args.output_root / "experiment_config.json", config)
    for seed in seeds:
        initial_candidates = {}
        for generator_style in GENERATOR_STYLES:
            initial_dir = (
                args.output_root
                / "initial"
                / generator_style
                / f"seed-{seed}"
            )
            writer_client = OllamaClient(
                args.ollama_url,
                args.num_ctx,
                seed,
                args.timeout_seconds,
                thinking=False,
            )
            initial_candidates[generator_style] = generate_candidate(
                initial_dir / "candidate.checkpoint.json",
                writer_client,
                args.writer_model,
                meta_template,
                args.value_system,
                evidence,
                generator_style,
                example_block,
            )
            write_json(
                initial_dir / "candidate.json",
                initial_candidates[generator_style],
            )

        for generator_style in GENERATOR_STYLES:
            for review_style in REVIEW_STYLES:
                condition = f"{generator_style}-{review_style}"
                run_dir = args.output_root / "runs" / condition / f"seed-{seed}"
                run_dir.mkdir(parents=True, exist_ok=True)
                candidate = initial_candidates[generator_style]
                judgments = []
                for reviewer_index, reviewer_model in enumerate(reviewer_models):
                    reviewer_client = OllamaClient(
                        args.ollama_url,
                        args.num_ctx,
                        seed + 10000 + reviewer_index * 1000,
                        args.timeout_seconds,
                        thinking=False,
                    )
                    judgments.append(
                        judge_candidate(
                            run_dir
                            / "reviews"
                            / f"{model_slug(reviewer_model)}.checkpoint.json",
                            reviewer_client,
                            reviewer_model,
                            meta_template,
                            args.value_system,
                            evidence,
                            candidate,
                            review_style,
                        )
                    )
                critique = merge_judgments(judgments)
                write_json(run_dir / "critique_packet.json", critique)
                reviser_client = OllamaClient(
                    args.ollama_url,
                    args.num_ctx,
                    seed + 20000,
                    args.timeout_seconds,
                    thinking=False,
                )
                revised = revise_candidate(
                    run_dir / "revision.checkpoint.json",
                    reviser_client,
                    args.writer_model,
                    meta_template,
                    args.value_system,
                    evidence,
                    candidate,
                    critique,
                )
                write_json(run_dir / "constitution.json", revised)

    for condition_dir in sorted((args.output_root / "runs").glob("*")):
        for seed_dir in sorted(condition_dir.glob("seed-*")):
            seed = int(seed_dir.name.removeprefix("seed-"))
            constitution = json.loads(
                (seed_dir / "constitution.json").read_text(encoding="utf-8")
            )
            for auditor_index, auditor in enumerate(
                parse_csv(args.external_auditors)
            ):
                client = OllamaClient(
                    args.ollama_url,
                    args.num_ctx,
                    seed + 30000 + auditor_index * 1000,
                    args.timeout_seconds,
                    thinking=False,
                )
                audit_constitution(
                    seed_dir / "external_audits" / f"{model_slug(auditor)}.json",
                    client,
                    auditor,
                    constitution,
                    clusters,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
