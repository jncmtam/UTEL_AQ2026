# Weighted-QAOA conditioning control

Opened conditional-US development; no model/financial/quantum advantage qualification.

| N | Weight policy | Method | Seed | Status | Allocated objective | Probability supports | Qubits | CX | Depth |
|---:|---|---|---:|---|---:|---:|---:|---:|---:|
| 10 | continuous | raw | 11 | feasible | 2.732958773353487e-05 | 120 | 12 | 236 | 417 |
| 10 | continuous | raw | 23 | feasible | 2.732958773353487e-05 | 120 | 12 | 236 | 417 |
| 10 | continuous | raw | 37 | feasible | 2.732958773353487e-05 | 120 | 12 | 236 | 417 |
| 10 | continuous | paper_rms | 11 | feasible | 2.732958773353487e-05 | 120 | 12 | 236 | 417 |
| 10 | continuous | paper_rms | 23 | feasible | 2.6450897307358637e-05 | 120 | 12 | 236 | 417 |
| 10 | continuous | paper_rms | 37 | feasible | 2.6450897307358637e-05 | 120 | 12 | 236 | 417 |
| 10 | continuous | uniform_total_shots | 11 | feasible | 2.6450897307358637e-05 | — | — | — | — |
| 10 | continuous | uniform_total_shots | 23 | feasible | 2.6450897307358637e-05 | — | — | — | — |
| 10 | continuous | uniform_total_shots | 37 | feasible | 2.6450897307358637e-05 | — | — | — | — |
| 10 | equal_weight_target | raw | 11 | feasible | 2.8719493561970276e-05 | 120 | 12 | 236 | 417 |
| 10 | equal_weight_target | raw | 23 | feasible | 2.8719493561970276e-05 | 120 | 12 | 236 | 417 |
| 10 | equal_weight_target | raw | 37 | feasible | 2.8719493561970276e-05 | 120 | 12 | 236 | 417 |
| 10 | equal_weight_target | paper_rms | 11 | feasible | 2.8719493561970276e-05 | 120 | 12 | 236 | 417 |
| 10 | equal_weight_target | paper_rms | 23 | feasible | 2.8719493561970276e-05 | 120 | 12 | 236 | 417 |
| 10 | equal_weight_target | paper_rms | 37 | feasible | 2.8719493561970276e-05 | 120 | 12 | 236 | 417 |
| 10 | equal_weight_target | uniform_total_shots | 11 | feasible | 2.8719493561970276e-05 | — | — | — | — |
| 10 | equal_weight_target | uniform_total_shots | 23 | feasible | 2.8719493561970276e-05 | — | — | — | — |
| 10 | equal_weight_target | uniform_total_shots | 37 | feasible | 2.8719493561970276e-05 | — | — | — | — |
| 30 | continuous | raw | 11 | feasible | 1.80832990946419e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | continuous | raw | 23 | feasible | 1.6648053392435252e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | continuous | raw | 37 | feasible | 1.7062502711347864e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | continuous | paper_rms | 11 | feasible | 1.7440785588108002e-05 | 593774 | 33 | 1798 | 2428 |
| 30 | continuous | paper_rms | 23 | feasible | 1.922930129973441e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | continuous | paper_rms | 37 | feasible | 1.8196935466486798e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | continuous | uniform_total_shots | 11 | feasible | 1.619346931795113e-05 | — | — | — | — |
| 30 | continuous | uniform_total_shots | 23 | feasible | 1.6320439069973724e-05 | — | — | — | — |
| 30 | continuous | uniform_total_shots | 37 | feasible | 1.664297754953452e-05 | — | — | — | — |
| 30 | equal_weight_target | raw | 11 | feasible | 2.259890542321891e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | equal_weight_target | raw | 23 | feasible | 2.079006739318021e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | equal_weight_target | raw | 37 | feasible | 2.4396956201713527e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | equal_weight_target | paper_rms | 11 | feasible | 2.0518602812538245e-05 | 593774 | 33 | 1798 | 2428 |
| 30 | equal_weight_target | paper_rms | 23 | feasible | 2.270317919872037e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | equal_weight_target | paper_rms | 37 | feasible | 2.156878155755589e-05 | 593775 | 33 | 1798 | 2428 |
| 30 | equal_weight_target | uniform_total_shots | 11 | feasible | 1.8341542816830014e-05 | — | — | — | — |
| 30 | equal_weight_target | uniform_total_shots | 23 | feasible | 2.0379129384799684e-05 | — | — | — | — |
| 30 | equal_weight_target | uniform_total_shots | 37 | feasible | 2.089464550410792e-05 | — | — | — | — |

## Interpretation limits

Counter-Dicke is a distinct compiler-owned construction, not a replication of the ancilla-free paper. Workspace is physically counted and proven clean before cost/mixer execution. Large ideal simulation eliminates that clean workspace; full large-register Qiskit comparison is not claimed.

Within each weight policy the fixed mixer graph, immutable coefficients, shot limits and post-allocation policy are shared. RMS conditioning changes optimizer coordinates and loss scale, not the Hamiltonian. Uniform classical draws additionally avoid all circuit overhead. Increased preparation depth may erase any benefit under noise; this run is ideal CPU simulation.

Read proxy and allocated objectives separately. More support coverage alone does not establish better decisions. Three seeds, opened data and selection-conditioned membership do not qualify an LLM or unbiased investment strategy.

H1 financial value: inconclusive. H2 LLM value: inconclusive (no LLM run). H3 adaptive QAOA value: inconclusive. Quantum advantage: unsupported by these ideal classical simulations.
