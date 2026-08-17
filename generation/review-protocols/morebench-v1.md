# MoReBench-Inspired Review Protocol (`morebench_v1`)

Status: experimental and opt-in.

The default constitution-generation pipeline uses `baseline_v1`. To enable this
review protocol in the current generation notebook, call:

```python
run_everything(
    constitutionName,
    docs_root,
    max_rounds,
    review_protocol="morebench_v1",
)
```

The selected protocol is written to `run_history.json` and
`review_protocol.txt` in the run directory.

## Generator Construction Rules

The generator receives a concise, constructive version of the protocol. It is
instructed to produce criteria that are behaviorally checkable in pairwise
judgments, atomic, non-redundant, and grounded in the source texts. Guidelines
should cover realistic conflicts, edge cases, and source-grounded
counter-considerations.

Before returning JSON, the generator silently checks the complete set for
clarity, coverage, overlap, and source grounding. It does not return this audit
or receive the diagnostic finding tags used by the judge.

## Judge Audit

Before scoring, audit the candidate item by item and as a complete set:

1. Coverage: identify source-grounded principles needed for a faithful
   measurement instrument that are absent.
2. Clarity: flag wording that does not identify an observable distinction
   between LLM outputs.
3. Atomicity: flag an item if satisfying it requires more than one
   independently judgeable behavior.
4. Non-redundancy and balance: flag items that measure substantially the same
   behavior, including clusters that give one principle disproportionate
   representation.
5. Counter-considerations: when an item gives a clear priority or action
   tendency, check whether the constitution captures serious competing
   considerations recognized by the foundational documents. Do not import
   generic balance or outside moral commitments.
6. Specificity and validity: flag subjective, non-behavioral, irrelevant,
   source-unsupported, overbroad, or generic items. Check whether the set
   distinguishes this value system from nearby value systems and whether each
   item can discriminate responses in a pairwise judgment.

Format every `weaknesses` entry as `[target][finding] description` and every
`revision_suggestions` entry as `[target][finding][operation] description`.

- Targets: `[criterion 3]`, `[guideline 2]`, `[criteria 2, 7]`, or
  `[constitution]`
- Findings: `[coverage]`, `[clarity]`, `[atomicity]`, `[redundancy]`,
  `[balance]`, `[counter-consideration]`, `[specificity]`, or `[validity]`
- Operations: `[add]`, `[remove]`, `[merge]`, `[split]`, or `[reword]`

Example:

```text
[criteria 2, 7][redundancy][merge] Replace them with one criterion that
preserves their shared source-grounded principle.
```

## Revision Audit

Apply item-level feedback with explicit operations. Check the revised set for
de facto weighting through repeated criteria. Preserve serious competing
considerations only when they are grounded in the foundational documents.

## Attribution

This protocol adapts the rubric-review procedure in Appendix D.2 of Chiu et al.,
[*MoReBench: Evaluating Procedural and Pluralistic Moral Reasoning in Language
Models, More than Outcomes*](https://arxiv.org/abs/2510.16380). It does not
include MoReBench rubric content.
