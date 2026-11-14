# Scenario_Generation_Pipeline

Python implementation of the scenario-generation workflow. Works with one or multiple constitutions, with or without an existing scenario bank.

## Setup

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key"
```

## Run

```bash
python -m modules --constitutions /path/to/constitutions.zip \
  --run-name my-experiment --max-attempts 60
```

For an existing bank, add `--existing /path/to/benchmark.json`. You can also
supply a previous `scenario_generation_pipeline_results.zip` directly: the
loader imports its `benchmark.json` rather than its audit and report files. A single constitution JSON uses direct criterion targeting; multiple constitutions enable M3 and shared multicover selection.

Prompts, model IDs, quality thresholds, and other defaults are in `modules/config.py`. The command-line flags override run inputs, quota, batch size, and generation budget.

Results appear in `<run-dir>/<run-name>/exports/`, with resumable caches under the same run directory. Increase `--max-attempts` and reuse the same run name to continue. The quota is 50 relevant scenarios per constitution, with at least 8 distinct criteria by default.

No human labeling or interactive review is required. Missing API credentials produce a clear error rather than an interactive prompt. All output data and logs are JSON, with a downloadable ZIP. The pipeline reviews every candidate pair with embedding cosine similarity ≥0.70 using an LLM before criterion mapping.

The code makes paid OpenRouter calls when it needs missing labels or more scenarios. Run `--max-attempts 0` with a fully labeled existing bank to export without generating new candidates.

## Code organization

All Python source modules live in `modules/`.

- `config.py`: models, prompts, quotas, and thresholds
- `core.py`: input normalization, persistent run manifests, and JSON utilities
- `client.py`: cached OpenRouter calls and retry handling
- `stages.py`: scenario generation, M3, and quality evaluation
- `labels.py`: automatic redundancy screening and relevance mapping
- `pipeline.py`: MILP selection, export, and resumable controller

Launch with `python -m modules`. No notebooks or pandas are required.

## Before publishing or running at scale

Keep `runs/` and `.env` out of version control: they may contain private
scenarios, full model responses, and usage records. The included `.gitignore`
excludes these files. Run a small live pilot using your chosen model endpoints
before committing to a large paid run.
