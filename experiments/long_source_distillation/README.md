# Long-Source Hierarchical Distillation Experiment

This experiment tests two ways to construct a model constitution from a source
bundle larger than the configured inference context:

1. `all-chunks`: extract local criterion candidates from every source chunk.
2. `score-first`: use a small routing model to score every chunk, then send
   high-yield chunks, rare exceptions, conflict passages, mandatory
   per-document coverage, and a low-score audit sample to the writer.

Both conditions use the same deterministic chunker, candidate format,
hierarchical clustering, constitution writer, provenance export, and
coverage/grounding review.

The experimental writer emits exactly 10 criteria and 4 guidelines. Fixed
cardinality avoids treating small-model interpretations of an 8-12 or 3-5
range as an experimental difference between conditions.

## Default Pilot

The default source is the committed public Stoicism bundle. It contains seven
substantive source files totaling about 142,000 tokens, including the optional
translation and interpretive probes. `README.md`, `manifest.json`, and
everything under `_private` are excluded. The experiment configures a 32,768
token inference context, so the source cannot be passed in one request.

The Spark defaults are:

- Router: `qwen2.5:3b`
- Writer, clusterer, and reviewer: `qwen3.6:35b-a3b-q4_K_M`
- Ollama: `http://127.0.0.1:11434`
- Thinking: disabled for structured-output reliability

The model names are command-line options. A model substitution therefore does
not change the protocol. `--thinking` enables reasoning as an explicit
sensitivity condition; it is off by default because reasoning tokens can
consume the structured-output budget before a final JSON object is emitted.

## Run

From the repository root:

```bash
python3 -m experiments.long_source_distillation.run \
  --mode score-first \
  --source-dir sources/stoicism
```

Run the comparison arm into a separate directory:

```bash
python3 -m experiments.long_source_distillation.run \
  --mode all-chunks \
  --source-dir sources/stoicism
```

For a fast integration check:

```bash
python3 -m experiments.long_source_distillation.run \
  --mode score-first \
  --source-dir sources/stoicism \
  --max-chunks 7 \
  --max-selected 7 \
  --output-dir experiments/long_source_distillation/runs/smoke
```

`--max-chunks` uses round-robin selection across source files rather than
taking the first N chunks from the first document.

## Outputs

Each run writes:

- `run_config.json`: protocol, models, source hashes, and sampling settings
- `chunks.json`: complete chunk inventory and hashes
- `chunk_scores.json`: router outputs for `score-first`
- `selection.json`: selected chunks and selection reasons
- `candidates.json`: source-grounded local criterion candidates with exact
  evidence excerpts; local rationale is optional
- `clusters.json`: overlap aggregation with candidate IDs
- `preliminary_clusters.json`: checkpointed hierarchical clustering batches
- `constitution.json`: generation-pipeline candidate shape without experiment
  provenance fields; it is not a publication-ready repository constitution
- `constitution.enriched.json`: constitution with candidate IDs
- `provenance.json`: constitution-item to candidate-ID mapping
- `source_map.json`: selected and omitted chunk coverage
- `review.json`: grounding, coverage, redundancy, and missing-region audit

Scores and candidates are checkpointed after every model call. Clusters,
constitution artifacts, and the final review are checkpointed by stage, so
rerunning with the same output directory resumes completed work.

## Scientific Comparison

Keep source hashes, writer/reviewer model, context, seed, chunking, and output
constraints fixed between arms. Compare:

- constitution coverage and grounding scores
- unrepresented high-yield source regions
- criterion redundancy and de facto weighting
- item provenance breadth across files and chunks
- constitution stability across seeds and chunk order
- total writer tokens and wall-clock time

Pre-scoring is a routing hypothesis, not evidence that low-scoring passages are
unimportant. Mandatory document coverage and the low-score audit sample are
included to make false-negative selection observable.
