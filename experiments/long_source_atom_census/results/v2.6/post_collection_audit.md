# v2.6 Post-Collection Audit

These diagnostics were specified after collection and do not alter the
preregistered result.

## christianity

- Artifacts: 15 candidates, 45 reviews, 15 rankings.
- Probes: 12 ({'A': 2, 'B': 10}).
- Median probe target accuracy: exhaustive=1.000, budgeted=0.750, truncated=0.833.

| Reviewer | Coverage score distribution | Median |
|---|---|---:|
| gemma4:31b-it-q4_K_M | {'45': 3, '58': 1, '65': 11} | 65.0 |
| command-r:35b | {'0': 2, '12': 3, '84': 1, '86': 1, '88': 1, '95': 2, '96': 5} | 88.0 |
| qwen3.6:27b-q4_K_M | {'45': 1, '65': 7, '85': 7} | 65.0 |

| Reviewer pair | Coverage Spearman | Recovered-cluster Jaccard |
|---|---:|---:|
| gemma4:31b-it-q4_K_M / command-r:35b | -0.179 | 0.533 |
| gemma4:31b-it-q4_K_M / qwen3.6:27b-q4_K_M | -0.330 | 0.880 |
| command-r:35b / qwen3.6:27b-q4_K_M | 0.707 | 0.562 |

## lockean-rights

- Artifacts: 15 candidates, 45 reviews, 15 rankings.
- Probes: 12 ({'A': 5, 'B': 7}).
- Median probe target accuracy: exhaustive=1.000, budgeted=1.000, truncated=1.000.

| Reviewer | Coverage score distribution | Median |
|---|---|---:|
| gemma4:31b-it-q4_K_M | {'65': 11, '75': 4} | 65.0 |
| command-r:35b | {'56': 1, '58': 1, '83': 3, '95': 5, '96': 2, '97': 3} | 95.0 |
| qwen3.6:27b-q4_K_M | {'65': 4, '85': 11} | 85.0 |

| Reviewer pair | Coverage Spearman | Recovered-cluster Jaccard |
|---|---:|---:|
| gemma4:31b-it-q4_K_M / command-r:35b | -0.287 | 0.688 |
| gemma4:31b-it-q4_K_M / qwen3.6:27b-q4_K_M | 0.364 | 0.905 |
| command-r:35b / qwen3.6:27b-q4_K_M | -0.036 | 0.717 |

## stoicism

- Artifacts: 15 candidates, 45 reviews, 15 rankings.
- Probes: 12 ({'A': 9, 'B': 3}).
- Median probe target accuracy: exhaustive=1.000, budgeted=1.000, truncated=1.000.

| Reviewer | Coverage score distribution | Median |
|---|---|---:|
| gemma4:31b-it-q4_K_M | {'65': 14, '75': 1} | 65.0 |
| command-r:35b | {'12': 2, '56': 1, '95': 3, '96': 2, '97': 7} | 96.0 |
| qwen3.6:27b-q4_K_M | {'45': 1, '65': 6, '85': 8} | 85.0 |

| Reviewer pair | Coverage Spearman | Recovered-cluster Jaccard |
|---|---:|---:|
| gemma4:31b-it-q4_K_M / command-r:35b | 0.262 | 0.506 |
| gemma4:31b-it-q4_K_M / qwen3.6:27b-q4_K_M | 0.244 | 0.799 |
| command-r:35b / qwen3.6:27b-q4_K_M | 0.269 | 0.476 |
