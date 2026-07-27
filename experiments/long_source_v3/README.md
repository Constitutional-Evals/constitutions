# Long-Source Constitution Distillation v3

Status: implementation complete; no model run has been performed.

This suite tests three methods that were proposed after the v2.6 negative
result but were not tested by v2.6. It is isolated from
`experiments/long_source_atom_census` and never rewrites those results.

## Frozen Comparison

All conditions use the same source files, reference census, writer, output
contract, seeds, and blinded external auditors.

- `oracle`: one-shot writing from every reference cluster. This is the
  high-context baseline, not a claimed practical solution.
- `iterative`: divide every reference cluster into bounded packets, create
  local drafts, merge the drafts in a balanced tree, and finalize only after
  every packet has been observed.
- `adaptive`: order clusters by mandatory conflict/source coverage and weighted
  diversity, revise as batches arrive, and stop only after all three frozen
  conditions hold: at least 85% weighted input mass, all mandatory clusters,
  and text stability above 0.78 for two consecutive additions.
- `pre-extraction`: score raw chunks before atom extraction, preserve every
  source's best chunk and all flagged conflicts/exceptions, add a deterministic
  low-score audit sample, and build a constitution from the routed census.

Iterative and adaptive operate on the same exhaustive atom census. This
isolates the effect of aggregation from the effect of source selection.
Pre-extraction is a separate intervention. Its savings are not publishable
unless `router/audit.json` exists and reports recall against the full census.

Every intermediate draft carries `observed_cluster_ids`; the runner rejects a
merge that omits or invents an ID. These fields are excluded from blinded
evaluation.

## Evaluation

The primary source-coverage metric is an explicit blinded mapping from final
constitution text to reference clusters. Material links receive full credit,
partial links half credit, and absent links zero. Writer provenance is not used
to compute this metric.

Evaluation files are never shown to writers. The repository's existing
`held_out_sensitivity_files` are not assumed independent: some are alternate
translations or related works. Final preparation therefore requires explicit
`--evaluation-files`; the old sensitivity set is available only behind
`--development-use-sensitivity-files` and cannot support a final claim.
`evaluate.py prepare` builds cases and an annotation template. Pairwise evaluation refuses
to run until every case has two human annotations, an adjudicated A/B label,
and `status: "accepted"`. This prevents model-authored probe labels from being
reported as independent validation.

## Plan Without Inference

```bash
python3 -m experiments.long_source_v3.run_matrix \
  --repo-root . \
  --output-root /data/eigenbench/long-source-v3 \
  --plan-only
```

This reads local source manifests and writes `plan.json` files. It makes no
Ollama or embedding calls.

## Spark Run

Reuse the v2.6 full censuses when they are available:

```bash
.venv-atom-census/bin/python -m experiments.long_source_v3.run_matrix \
  --repo-root . \
  --reference-root /data/eigenbench/v2.6-preregistered \
  --output-root /data/eigenbench/long-source-v3
```

Without `--reference-root`, the runner builds a new exhaustive census. All
model calls are checkpointed and request-hashed; a changed prompt or schema
cannot silently reuse an old response.

Prepare held-out material after generation:

```bash
.venv-atom-census/bin/python -m experiments.long_source_v3.evaluate prepare \
  --tradition stoicism \
  --repo-root . \
  --evaluation-files independent-stoic-source.md \
  --output-root /data/eigenbench/long-source-v3
```

After two-person annotation and adjudication:

```bash
.venv-atom-census/bin/python -m experiments.long_source_v3.evaluate evaluate \
  --tradition stoicism \
  --output-root /data/eigenbench/long-source-v3 \
  --run-root /data/eigenbench/long-source-v3 \
  --cases /data/eigenbench/long-source-v3/stoicism/heldout/cases.checkpoint.json \
  --labels /data/eigenbench/long-source-v3/stoicism/heldout/adjudicated.json
```

Then recompute the summary:

```bash
.venv-atom-census/bin/python -m experiments.long_source_v3.analyze \
  --root /data/eigenbench/long-source-v3 \
  --tradition stoicism
```

## Interpretation Gate

No method is a final recommendation from this code alone. A useful result
requires:

1. the 95% paired-bootstrap lower bound against `oracle` is at least -0.05 on
   blinded weighted cluster recall;
2. the unsupported-item-rate difference's upper bound is at most +0.05;
3. replicated held-out pair accuracy across traditions and multiple judges;
4. maximum evidence context per writer call is at most 60% of `oracle`;
5. pre-extraction, when used, extracts at most 70% of chunks and retains at
   least 90% of reference conflict/exception clusters.

Adaptive thresholds are frozen defaults for the first run. Tune them only on a
separate development tradition, never after inspecting these test results.
`analyze.py` reports these gates, but leaves the overall decision pending until
independent held-out evaluation exists. Passing one tradition is not a
cross-tradition result.
