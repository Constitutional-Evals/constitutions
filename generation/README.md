# Generation methodology

How candidate constitutions are produced and reconciled. Goal: constitutions distilled from the
foundational bundle, not paraphrased from a supplied checklist.

## Pipeline
1. **Sources** \u2014 assemble `../sources/<id>/` (.md, spot-checked, 50k/doc, 120k/bundle).
2. **Generate** \u2014 run the current [`v1.3` meta-prompt](Meta-prompts/7_21_26%20Meta%20Prompt%20%28v1.3%29.md)
   per model, varying only the constitution name, the document bundle, and the format example.
3. **Critique** \u2014 have each model critique the others' candidates (what's missing / overemphasized).
   **Anonymize** candidates \u2014 do not reveal that another LLM authored a candidate, to avoid biased
   critique.
4. **Consensus** \u2014 reconcile to one constitution per value system.
5. **Researcher pass** \u2014 triage errors, anachronisms, framework leaks.
6. **Emit** \u2014 a JSON per the [schema](../schema/constitution.schema.json): `overview`, `criteria`
   (comparative, for EigenBench), `voices` (1st/2nd/3rd person, for OCT), `guidelines`.

### Review protocol

The critique and revision stages audit criteria for coverage, clarity, atomicity, non-redundancy,
set-level balance, source-grounded counter-considerations, and validity. Review findings use tagged
strings such as `[criteria 2, 7][redundancy][merge] ...`, preserving the existing judge JSON shape
while making targets, issue types, and proposed operations explicit to people, LLMs, and parsers.

This item-level quality-control pass adapts the rubric-review procedure in Appendix D.2 of
[Chiu et al., *MoReBench: Evaluating Procedural and Pluralistic Moral Reasoning in Language
Models, More than Outcomes*](https://arxiv.org/abs/2510.16380). No MoReBench rubric content is
included in the constitution prompt.

## Controls (so sensitivity probes mean something)
- **One fixed meta-prompt** across all constitutions; no per-constitution coverage list.
- **Web search OFF** for controlled runs \u2014 the bundle must be the sole source, or document-
  selection/ordering/format probes are confounded.
- **Frontier models via API** (LAISR OpenRouter) for the real runs \u2014 stateless, avoiding web-UI
  "memory" contamination. Free-tier web UIs are fine only for shaping the prompt.

## Probes
Vary the example constitution, and the selection/ordering/format of the bundle (incl. multiple
.md per document), and measure how much the output constitution moves.
