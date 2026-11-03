# Weighted-QAOA parameter conditioning: pre-experiment protocol

Date: 2026-11-03. Opened development comparison, no LLM/GPU inference.

## Published basis and observed trigger

[Sureshbabu et al., Quantum8,1231 (2024)](https://quantum-journal.org/papers/q-2024-01-18-1231/)
([full paper, Eq8 and Section6.2](https://arxiv.org/html/2305.15201v3)) study weighted
QAOA parameter setting. Their portfolio tests use280 random instances,7–20 qubits,
Dicke initialization and an XY mixer; the paper reports7.4× fewer local-optimizer
iterations on average. Those results are not US-equity repair measurements and
do not transfer as a promised AGQO improvement.

Our post-run diagnostic found a cost-phase span only0.056 radians at |gamma|=pi
on N30. An arbitrary small raw-angle initialization can confound architecture and
model comparisons. Apply the paper's general-objective Eq8 RMS normalization as
an explicit optimizer-coordinate transform, rather than alter immutable coefficients.

## Exact transform

For nonzero one-body coefficients h_i and two-body coefficients J_ij, use
a=sqrt(mean(h_i²)+mean(J_ij²)), omitting an absent degree. Optimize coordinates u
with physical gamma=u/a, beta unchanged; minimize sampled expectation H/a.
Return/export physical angles and score every portfolio using the original finance.
H and its hash remain unchanged. Zero a is a constant-H diagnostic, not a reason
to manufacture an active cost parameter. Rescaling alone is not a novel algorithm.

The control retains legacy raw angles. Do not change default/frozen runs. Unit tests
must match Eq8 directly and verify physical-unitary equivalence under positive
uniform H rescaling. No truth-table/optimum is supplied to the conditioner.

## Bounded comparison

Pinned opened US data, first126 rows. N10/K3 and N30/K6; seeds11,23,37.
Use counter-Dicke preparation and the same fixed mixer. Compare raw coordinates,
paper RMS coordinates, and classical uniform sampling with2176 draws. Each circuit
gets16 evaluations×128 shots plus128 final shots; all methods share32 allocator
queries. Circuit postprocessing remains final-samples-only, explicitly reported.

Run both declared financial policies: unchanged continuous allocation and the
equal-weight-target alternative audited separately. Never pool their scores or
quietly replace the primary task. Report B and F independently, allocation failures,
sample counts, full workspace/gates/depth, preprocessing time and source snapshots.
No model qualification or significance claim from these two opened cases.

Correctness acceptance: exact coefficient hash preservation and independent unitary
equivalence within1e-9; standard existing simulator/resource caps. Stop a candidate
on failed verification; no dense/fallback result is credited. No performance target
is chosen after observing results. Keep adverse or null findings.
