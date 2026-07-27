# v2.6 Result and v3 Protocol

## Decision

The v2.6 budgeted method is not supported.

It reduced writer evidence by about 50% and preserved grounding, but failed the
preregistered coverage noninferiority gate in all three traditions. Christianity
also failed the behavioral-agreement gate. These failures must not be repaired
by changing thresholds or selecting favorable seeds after seeing the results.

## What v2.6 Established

- Complete dual-model censuses were produced for Stoicism, Christianity, and
  Lockean rights.
- Exact-evidence acceptance was 91.1%, 79.4%, and 86.7%, respectively.
- Every census was deterministically partitioned into exactly 40 non-overlapping
  clusters.
- Each 50% packet selected 21 clusters and retained every high-confidence
  conflict or exception cluster.
- All 45 constitutions satisfied the fixed 10-criterion and 4-guideline
  contract.
- All 135 blinded reviews and 45 fixed-probe rankings completed.
- The budgeted packet used 49.3% to 49.7% of the exhaustive packet characters.

The preregistered failures were:

| Tradition | Coverage difference (95% CI) | Pair agreement | Result |
|---|---:|---:|---|
| Stoicism | -8.0 [-16.0, 0.0] | 1.00 | Fail |
| Christianity | -16.0 [-20.0, -8.0] | 0.75 | Fail |
| Lockean rights | -8.0 [-16.4, 0.4] | 1.00 | Fail |

## Measurement Problems Found After Collection

These are limitations of v2.6, not reasons to reinterpret its failed gates.

### Probe leakage

`held_out_sensitivity_files` were recorded but were not used by probe
generation. Probes were synthesized from the same 40 reference clusters that
formed writer inputs. Probe accuracy therefore measures internal consistency,
not generalization to unseen source material.

### Reviewer calibration

The three reviewers did not use scalar coverage scores comparably. Across
candidate pools, Gemma mostly returned 45-75, Command R mostly returned 83-97
with several 0-12 outliers, and Qwen mostly returned 45, 65, or 85. Pairwise
rank correlations were generally weak and sometimes negative. Taking the
median often made Qwen's coarse score decisive.

Reviewer agreement was better, though still imperfect, on the concrete set of
recovered cluster IDs. Primary coverage measurement should therefore be based
on explicit item-to-cluster judgments with calibrated adjudication, not a free
scalar score.

### Probe ceiling

The 12 generated pairs were too easy in Stoicism and Lockean rights: exhaustive,
budgeted, and truncation conditions all reached median target accuracy of 1.0.
Christianity was more discriminative, but 12 cases are too few for a stable
tradition-level behavioral endpoint. The generator also failed its requested
label balance, and the runner did not enforce it: Christianity produced 2 A
versus 10 B targets, Stoicism 9 versus 3, and Lockean rights 5 versus 7.
Per-seed position swapping reduces simple side bias but does not repair this
unenforced probe-generation contract.

### Insufficient uncertainty units

Bootstrapping five writer seeds yields coarse intervals and does not account for
dependence among probes, seeds, reviewers, and traditions. Three traditions are
also insufficient for a broad generalization claim.

## v3 Primary Question

Can a source-grounded hierarchical representation use materially fewer writer
tokens than a complete reference representation while preserving:

1. expert-validated, priority-weighted normative coverage;
2. judgments on unseen, difficult value conflicts; and
3. discrimination from neighboring value systems?

The unit under test is the source representation. Writer model, constitution
schema, generation parameters, and seed set remain paired across conditions.

## v3 Data Separation

Each tradition must have disjoint partitions fixed before inference:

- `development`: prompt and selector development only;
- `writer-primary`: source census, clustering, and writer evidence;
- `evaluation-source`: unseen source passages used only to derive test atoms;
- `evaluation-cases`: expert-authored or expert-adjudicated scenarios;
- `final-traditions`: traditions never used while developing the method.

No evaluation-source atom, cluster synthesis, scenario, target, or rationale may
appear in writer or reviewer inputs. Source hashes and split assignments are
recorded in the preregistration.

## v3 Conditions

Use at least these paired conditions:

- `oracle-packet`: all writer-primary clusters;
- `hierarchical-50`: preregistered 50% token budget;
- `raw-prefix-token-matched`: raw prefix at the same tokenizer-measured budget;
- `raw-stratified-token-matched`: chapter-stratified raw excerpts at that budget;
- `summary-token-matched`: hierarchical chapter summaries at that budget.

Character counts are descriptive only. The budget and reduction gate use the
writer model's tokenizer and include all model-facing evidence and metadata.

## v3 Coverage Endpoint

Remove free scalar coverage from the primary gate.

1. Reviewers label each constitution item against each reference cluster as
   `materially recovers`, `partial`, or `absent`, with cited item IDs.
2. A calibration set with expert labels is completed before reviewers evaluate
   blinded candidates.
3. Reviewer reliability is reported before aggregation. Low-reliability strata
   are expert-adjudicated under a frozen rule.
4. Coverage is the priority-weighted sum of recovered clusters, reported
   separately for principles, conflicts, and exceptions.
5. Unsupported items and duplicate item-cluster mappings remain separate
   endpoints.

The primary noninferiority margin and cluster weights must be expert-set before
candidate generation. Do not infer importance from frequency alone.

## v3 Behavioral Endpoint

Use at least 50 difficult held-out cases per tradition.

- Cases are authored from evaluation sources, not writer-primary clusters.
- Targets are independently labeled by at least two qualified annotators, with
  adjudication and agreement reported.
- Responses are length- and quality-matched hard negatives. Cases with lexical
  giveaways or unanimous performance by generic/truncation pilots are replaced
  using development data only.
- Every constitution is executed by at least three blinded judge models.
- A and B positions are independently counterbalanced.
- The primary score is agreement with expert targets. Agreement with the
  oracle-packet condition is secondary.

Analyze decisions with a preregistered hierarchical model or cluster bootstrap
that treats tradition, writer seed, case, and judge as uncertainty units.

## v3 Discrimination Endpoint

Every evaluation case should include the target tradition and at least one
plausible neighboring tradition.

For each constitution, measure:

- target-tradition accuracy;
- margin over generic-helpfulness and neighboring-tradition constitutions;
- a confusion matrix across traditions;
- performance on conflict cases where traditions predict different choices.

A method that gives the same answer under every constitution is not
discriminative, even if that answer is defensible.

## v3 Scale and Gates

Before running final traditions:

- conduct a power analysis from development data;
- use at least 10 writer seeds unless that analysis justifies fewer;
- use at least five final traditions from distinct normative families;
- freeze prompts, models, tokenizer, source splits, cases, weights, margins, and
  exclusion rules;
- require coverage noninferiority, behavioral noninferiority, positive
  cross-theory discrimination, grounding, and token reduction to pass in every
  final tradition;
- publish all candidates, labels, reviewer outputs, exclusions, and failed
  runs.

v3 should first run on development traditions. Only after the pipeline and
thresholds are frozen should it run once on final traditions. A v3 failure is a
valid result and must not trigger retuning on the final set.
