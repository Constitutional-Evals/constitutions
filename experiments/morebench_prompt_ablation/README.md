# Conventional vs MoReBench-Informed Prompt Ablation

Status: implementation complete; no model run has been performed.

This is an optional experiment. It does not replace the repository's
conventional v1.3 constitution-generation workflow.

## Question

Does a MoReBench-informed construction and review protocol improve the final
constitution beyond the existing v1.3 prompt, which already asks for grounded,
atomic, behaviorally checkable criteria?

The design is a 2x2 factorial:

| Generator | Reviewer | Condition |
| --- | --- | --- |
| conventional | conventional | current-workflow control |
| conventional | MoReBench-informed | review contribution |
| MoReBench-informed | conventional | generation contribution |
| MoReBench-informed | MoReBench-informed | combined protocol |

Each cell receives the identical source-derived reference packet, models,
seeds, constitution schema, and `JUDGE_SCHEMA`. The MoReBench reviewer writes
tags such as `[ATOMICITY]`, `[REDUNDANCY]`, and `[GROUNDING]` into the existing
`weaknesses` and `revision_suggestions` arrays. No JSON field is added.

Each candidate gets one critique/revision round. The primary outcomes come from
common blinded external text-to-cluster audits, not the reviewer that supplied
the revision or its scalar self-score.

If the current conventional run uses a worked example, pass it with
`--example-path`. The identical example is injected into both generator arms
and its hash is recorded; leaving the option out creates a no-example ablation.

## Plan Without Inference

```bash
python3 -m experiments.morebench_prompt_ablation.run_matrix \
  --reference-root /data/eigenbench/v2.6-preregistered \
  --output-root /data/eigenbench/morebench-ablation \
  --plan-only
```

## Spark Run

```bash
.venv-atom-census/bin/python \
  -m experiments.morebench_prompt_ablation.run_matrix \
  --reference-root /data/eigenbench/v2.6-preregistered \
  --output-root /data/eigenbench/morebench-ablation
```

Prompt, constitution-schema, and judge-schema hashes are stored in every plan
or run configuration. Analyze one tradition with:

```bash
.venv-atom-census/bin/python \
  -m experiments.morebench_prompt_ablation.analyze \
  --root /data/eigenbench/morebench-ablation/stoicism \
  --reference-clusters \
    /data/eigenbench/v2.6-preregistered/stoicism/reference_clusters.json
```

Use seed-paired contrasts or a mixed model with seed and auditor effects before
claiming either a generator or reviewer contribution. Tagged-diagnostic counts
are secondary process measures, not evidence of better constitutions by
themselves.

For a final contribution claim, run the same independently sourced,
two-annotator held-out cases through all four conditions using
`experiments.long_source_v3.evaluate`, then pass its `evaluation.json` to the
analyzer with `--heldout-evaluation`. The combined protocol gate requires a
strictly positive lower confidence bound for weighted reference recall and
held-out accuracy, with no increase in unsupported-item rate. Replication in
all three traditions is still required.

## Provenance and Citation

The control prompt is loaded directly from
`generation/Meta-prompts/7_21_26 Meta Prompt (v1.3) copy.md`. The addenda are
methodological adaptations, not copied case rubrics.

If this protocol or its framing is used in a paper, cite:

> Chiu, Y. Y., et al. *MoReBench: Evaluating Procedural and Pluralistic Moral
> Reasoning in Language Models, More than Outcomes*. arXiv:2510.16380,
> version 2 (2026).

If MoReBench-Theory records are later used as examples or evaluation data, also
record the Hugging Face dataset revision and preserve row-level provenance.
