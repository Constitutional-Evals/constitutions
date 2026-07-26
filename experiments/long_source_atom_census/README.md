# Long-Source Normative-Atom Census v2

This is the preregistered replacement for the non-discriminative v1 chunk
router. It asks whether a token-budgeted set of explicit, source-grounded
normative atoms can produce constitutions that are non-inferior to exhaustive
atom-census generation.

## Primary Experiment

Traditions:

- Stoicism: five primary files; Casaubon and the interpretive essay held out.
- Christianity: WEB Sermon, Augustine, Aquinas, and Chrysostom; KJV held out.
- Lockean rights: two Locke files, toleration, and Spencer; Bastiat held out.

Shared census:

1. Chunk every primary source deterministically.
2. Extract atoms from every chunk with Qwen 3.6 35B-A3B and Gemma 4 31B.
3. Reject evidence excerpts that do not occur in the source chunk.
4. Embed atoms with Qwen3-Embedding 4B and partition them into exactly 40
   cosine average-linkage clusters. Clustering is stratified to reserve four
   clusters each for conflicts and exceptions when enough atoms exist.
5. Compute a fixed cluster weight from extractor agreement, source breadth,
   conflict/exception status, and support.

Chunks do not overlap in the primary analysis. This prevents evidence repeated
at a chunk boundary from being counted as independent support.

Conditions:

- `exhaustive`: writer sees every reference cluster.
- `budgeted`: writer sees a deterministic diversity/coverage selection under
  50% of the reference packet-character budget.
- `truncated`: writer sees the first 80,000 raw source characters.

Each condition uses the same Gemma 4 writer, exact 10-criterion/4-guideline
cardinality, a 65,536-token runtime context, and seeds `17,29,43,71,101`.

The writer was frozen before experimental generation. A pre-run contract smoke
test rejected Qwen 3.6 35B-A3B after three malformed constitution responses;
Gemma 4 and dense Qwen both passed, and Gemma 4 was selected for its lower
observed latency. No experiment result was inspected in making this correction.

The first two census launches stopped before clustering after extractors
returned 12 atoms against an eight-item cap and then 28 atoms against a
20-item cap. Version 2.3 removes the atom-count cap and asks extractors for all
meaningful atoms. Completed partial calls were archived and the census restarted
from empty; no downstream experimental output existed.

The complete v2.3 raw census then exposed a grounding-validator artifact before
reference clustering: Qwen commonly joined exact source spans with explicit
ellipses, causing valid quotations to fail a contiguous-substring check.
Version 2.4 accepts only exact spans found in source order, with each omitted
region explicitly marked by an ellipsis. It still rejects paraphrases and
unmarked omissions. The v2.3 raw census was archived and no downstream result
was retained.

The valid v2.4 Stoic census was retained, but its LLM clustering experiment was
rejected before probes or constitution generation. Even after ID and JSON
contract hardening, the global merger omitted 256 of 746 atoms and produced
266 clusters after the completeness audit restored omissions as singletons.
Version 2.5 replaces model-generated cluster assignments with deterministic
embedding clustering. This produces a complete, non-overlapping 40-cluster
partition by construction. Qwen3-Embedding 4B and the exact numerical package
versions are recorded in the run config and audit.

The v2.5 census-only integration then showed that internal candidate-ID lists
dominated packet character cost. Version 2.6 retains full provenance in the
audit artifact but excludes candidate IDs from model-facing packets. Selection,
writers, probe generation, and reviewers see only cluster synthesis, support
counts, source/model breadth, weights, and exact evidence.

Evaluation:

- blinded reviews from Gemma 4 31B, Command R 35B, and Qwen 3.6 dense 27B;
- recovered reference-cluster IDs and unsupported item IDs;
- 12 balanced response-pair probes generated once per tradition;
- fixed Command R pairwise judgments with deterministic A/B swapping.

## Run One Tradition

Install the pinned numerical dependencies and embedding model on Spark:

```bash
python3 -m venv .venv-atom-census
.venv-atom-census/bin/pip install -r \
  experiments/long_source_atom_census/requirements-spark.txt
ollama pull qwen3-embedding:4b
```

```bash
.venv-atom-census/bin/python -m experiments.long_source_atom_census.run \
  --tradition stoicism \
  --output-root experiments/long_source_atom_census/runs
```

Build only the shared census and selection:

```bash
.venv-atom-census/bin/python -m experiments.long_source_atom_census.run \
  --tradition stoicism \
  --output-root experiments/long_source_atom_census/runs \
  --census-only
```

Run the complete preregistered matrix and analysis:

```bash
.venv-atom-census/bin/python -m experiments.long_source_atom_census.run_matrix \
  --output-root experiments/long_source_atom_census/runs/v2.6-preregistered
```

## Preregistered Gates

The budgeted method is provisionally successful only if:

- the reference census is a complete, non-overlapping 40-cluster partition;
- selection preserves all high-confidence conflict/exception clusters;
- median independent-review coverage is no more than 5 points below exhaustive;
- unsupported item rate is no more than 0.05;
- pairwise agreement with the exhaustive-seed consensus is at least 0.90;
- strong-writer evidence input is reduced by at least 40%;
- conclusions replicate in all three traditions with paired bootstrap
  confidence intervals that do not cross the non-inferiority margin.

These thresholds are recorded before v2.6 results are generated. Failure is a
result, not a reason to retune the method on the same runs.

Selected raw cluster weight remains a descriptive statistic, not a gate:
requiring 90% of distinct-cluster weight under a 50% evidence-packet budget is
mathematically incompatible unless weights are extremely concentrated. The
blinded downstream coverage and pairwise tests measure whether compression
preserves usable normative content.

The analysis writes `analysis.json` and `report.md` into the output root. The
budgeted method is supported only if every gate passes independently in every
tradition; favorable aggregate metrics do not override a failed tradition.
