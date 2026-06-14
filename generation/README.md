# Generation methodology

How candidate constitutions are produced and reconciled. Goal: constitutions distilled from the
foundational bundle, not paraphrased from a supplied checklist.

## Pipeline
1. **Sources** \u2014 assemble `../sources/<id>/` (.md, spot-checked, 50k/doc, 120k/bundle).
2. **Generate** \u2014 run the single [`meta-prompt.md`](meta-prompt.md) per model, varying only the
   constitution name, the document bundle, and the format example.
3. **Critique** \u2014 have each model critique the others' candidates (what's missing / overemphasized).
   **Anonymize** candidates \u2014 do not reveal that another LLM authored a candidate, to avoid biased
   critique.
4. **Consensus** \u2014 reconcile to one constitution per value system.
5. **Researcher pass** \u2014 triage errors, anachronisms, framework leaks.
6. **Emit** \u2014 a JSON per the [schema](../schema/constitution.schema.json): `overview`, `criteria`
   (comparative, for EigenBench), `voices` (1st/2nd/3rd person, for OCT), `guidelines`.

## Controls (so sensitivity probes mean something)
- **One fixed meta-prompt** across all constitutions; no per-constitution coverage list.
- **Web search OFF** for controlled runs \u2014 the bundle must be the sole source, or document-
  selection/ordering/format probes are confounded.
- **Frontier models via API** (LAISR OpenRouter) for the real runs \u2014 stateless, avoiding web-UI
  "memory" contamination. Free-tier web UIs are fine only for shaping the prompt.

## Probes
Vary the example constitution, and the selection/ordering/format of the bundle (incl. multiple
.md per document), and measure how much the output constitution moves.
