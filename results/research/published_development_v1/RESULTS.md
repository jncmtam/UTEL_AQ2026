# Conditional published-US development results



Algorithm quality on this exact published US corpus under declared scenario constraints; not investable historical strategy performance.



**This corpus does not pass the separate historical DJIA investment-data gate.**



| Case | Method | Status | Allocated objective | Test daily tracking RMSE | Seconds |

|---|---|---|---:|---:|---:|

| n10_k3_base | fixed | optimal | 2.6450897307358637e-05 | 0.0052242265267626615 | 0.42 |

| n10_k3_base | rules | optimal | 2.6450897307358637e-05 | 0.0052242265267626615 | 0.05 |

| n10_k3_base | random | optimal | 2.6450897307358637e-05 | 0.0052242265267626615 | 0.13 |

| n10_k3_base | uniform | optimal | 2.6450897307358637e-05 | 0.0052242265267626615 | 0.10 |

| n10_k3_base | allocation_swap | optimal | 2.6450897307358637e-05 | 0.0052242265267626615 | 0.06 |

| n10_k3_base | joint_scip | optimal | 2.6450897307358637e-05 | 0.0052242265267626615 | 0.23 |

| n10_k3_exclude_incumbent | fixed | optimal | 3.0213133869894245e-05 | 0.005554743269648391 | 0.05 |

| n10_k3_exclude_incumbent | rules | optimal | 3.0213133869894245e-05 | 0.005554743269648391 | 0.05 |

| n10_k3_exclude_incumbent | random | optimal | 2.914535565702423e-05 | 0.005811583386211383 | 0.06 |

| n10_k3_exclude_incumbent | uniform | optimal | 2.914535565702423e-05 | 0.005811583386211383 | 0.09 |

| n10_k3_exclude_incumbent | allocation_swap | unknown | — | — | 0.00 |

| n10_k3_exclude_incumbent | joint_scip | optimal | 2.914535565702423e-05 | 0.005811583386211383 | 0.17 |

| n30_k6_base | fixed | optimal | 2.287842786168313e-05 | 0.004336151385223209 | 3.78 |

| n30_k6_base | rules | optimal | 2.287842786168313e-05 | 0.004336151385223209 | 3.91 |

| n30_k6_base | random | optimal | 2.2496712896876822e-05 | 0.004051487527312224 | 4.08 |

| n30_k6_base | uniform | optimal | 1.872175349116791e-05 | 0.004372915938110491 | 0.10 |

| n30_k6_base | allocation_swap | optimal | 1.9745857361761577e-05 | 0.004708496261952603 | 0.10 |

| n30_k6_base | joint_scip | optimal | 1.467769005703765e-05 | 0.0035749785365973585 | 15.03 |



## Interpretation



All 30 source-labelled assets participate in the larger family. Every 6-of-30 support is represented by the simulator; shallow circuits need not assign meaningful probability to all of them. See probability_supports in metrics.csv.

Families are hash-ordered resource-limited subsets of 386 source assets. The LLM does not pick these assets. The continuous 386-asset relaxation is a lower reference, not a measured restriction penalty or equal-budget algorithm.

Training and test rows remain chronological. The single trade occurs after the first test session, charges assumed costs, and then drifts without daily resets. Membership conditioning and uncertified publisher return semantics remain limitations.

Four objective evaluations and one seed only test execution and accounting. They do not tune circuits adequately or establish comparative superiority. Every failure remains in the denominator.

H1 (real-world financial value): inconclusive. H2 (LLM value): inconclusive; no LLM is run. H3 (adaptive QAOA value): inconclusive. Ideal classical simulation does not establish quantum advantage.
