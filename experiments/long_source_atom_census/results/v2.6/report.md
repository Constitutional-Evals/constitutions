# Long-Source Atom-Census v2 Results

This report applies the thresholds recorded in the experiment README before generation.

## Gate Summary

| Tradition | Selected weight | Coverage diff (95% CI) | Unsupported | Pair agreement | Input reduction | Result |
|---|---:|---:|---:|---:|---:|---|
| stoicism | 0.581 | -8.0 [-16.0, 0.0] | 0.000 | 1.000 | 0.505 | FAIL |
| christianity | 0.573 | -16.0 [-20.0, -8.0] | 0.000 | 0.750 | 0.507 | FAIL |
| lockean-rights | 0.581 | -8.0 [-16.4, 0.4] | 0.000 | 1.000 | 0.503 | FAIL |

## Aggregate

- Paired coverage difference: -10.67 (95% bootstrap CI -16.00 to -5.47).
- All preregistered gates passed in every tradition: False.

## Condition Medians

| Tradition | Condition | Coverage | Grounding | Specificity | Recovered weighted recall | Probe target accuracy |
|---|---|---:|---:|---:|---:|---:|
| stoicism | exhaustive | 85.0 | 100.0 | 95.0 | 0.434 | 1.000 |
| stoicism | budgeted | 85.0 | 100.0 | 100.0 | 0.404 | 1.000 |
| stoicism | truncated | 65.0 | 100.0 | 100.0 | 0.371 | 1.000 |
| christianity | exhaustive | 85.0 | 100.0 | 100.0 | 0.437 | 1.000 |
| christianity | budgeted | 65.0 | 100.0 | 95.0 | 0.427 | 0.750 |
| christianity | truncated | 65.0 | 100.0 | 95.0 | 0.275 | 0.833 |
| lockean-rights | exhaustive | 85.0 | 100.0 | 95.0 | 0.462 | 1.000 |
| lockean-rights | budgeted | 83.0 | 100.0 | 95.0 | 0.419 | 1.000 |
| lockean-rights | truncated | 65.0 | 100.0 | 96.0 | 0.325 | 1.000 |

## Interpretation Rule

The budgeted method is supported only if every preregistered gate passes in all three traditions. Individual metric improvements do not override a failed gate.
