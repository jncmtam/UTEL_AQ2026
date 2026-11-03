# Controlled follow-up findings

Opened US development data, ideal CPU simulation and no new model inference. These controls diagnose the algorithm; they do not qualify a production LLM or investment strategy.

## Broad-support preparation

| N30 control | Mean allocated training objective | Meaningful supports | Physical qubits | CX | Logical depth |
|---|---:|---:|---:|---:|---:|
| three_pair | 2.0790048e-05 | [34, 67, 222] | 30 | 998 | 445 |
| counter_dicke | 1.7264618e-05 | [593775, 593775, 593775] | 33 | 1798 | 2428 |
| uniform | 1.87669e-05 | 128 draws | — | — | — |
| uniform_total_shots (post-run audit) | 1.6385629e-05 | 2176 draws | — | — | — |

The counter prepares the complete uniform K-of-N state without dense synthesis. It uses a distinct binary-counter construction with clean workspace, not the cited ancilla-free algorithm. It removes sparse coverage, while increasing N30 depth from445 to2428. Uniform sampling with the same total draw allowance remains stronger on this case.

## Financial formulation identity

| Scenario | Target-weight policy | Identity gate | Proxy-optimal allocation regret |
|---|---|---|---:|
| base | continuous | None | 3.32% |
| base | equal_weight_target | True | 0.00% |
| exclude_incumbent | continuous | None | 7.13% |
| exclude_incumbent | equal_weight_target | True | 0.00% |

Equal-weight targets give exact B=F on feasible supports within numerical tolerance. They are a different explicit mandate; the primary continuous-allocation task is retained. Its proxy distortion is not solved by broader initialization.

## Paper-based optimizer conditioning

The [published Eq8 RMS rule](https://arxiv.org/html/2305.15201v3#S3.SS2) is applied as gamma and loss coordinates on the unchanged Hamiltonian. Defaults and older frozen runs are retained. Means below are descriptive across three seeds on the same opened case.

| N | Financial policy | Raw coordinates | Paper RMS coordinates | Uniform2176 draws |
|---:|---|---:|---:|---:|
| 10 | continuous | 2.7329588e-05 | 2.6743794e-05 | 2.6450897e-05 |
| 10 | equal_weight_target | 2.8719494e-05 | 2.8719494e-05 | 2.8719494e-05 |
| 30 | continuous | 1.7264618e-05 | 1.8289007e-05 | 1.6385629e-05 |
| 30 | equal_weight_target | 2.259531e-05 | 2.1596855e-05 | 1.9871773e-05 |

Paper RMS scaling improves the mean selection-proxy expectation on these cases, but that is not a universal allocated-objective improvement. In N30 continuous allocation, the mean financial objective worsens. Under the equal-weight target it improves, yet the matched-draw classical reference remains stronger.

Circuit postprocessing uses only final samples; the uniform2176 control uses the maximum optimizer-plus-final draw count. A next protocol must explicitly decide whether all measured optimizer bitstrings join the candidate pool. No hidden pooling is applied retrospectively.

## Decision before more inference

- Keep counter-Dicke and paper RMS as explicit non-LLM controls; do not replace earlier methods silently.
- Resolve the financial target and proxy faithfulness before a model sweep. Continuous and equal-weight scores must remain separate.
- Predeclare candidate pooling, total-draw/time budgets and strong classical comparisons.
- Preserve original US investment-data blockers; the published corpus has full-year selection conditioning.
- Freeze a revised study before evaluating any LLM on unopened structures. Current results do not select a model or demonstrate quantum advantage.

No inferential significance claim: only two opened sizes and three seeds per case. Seed variation is not independent market evidence.
