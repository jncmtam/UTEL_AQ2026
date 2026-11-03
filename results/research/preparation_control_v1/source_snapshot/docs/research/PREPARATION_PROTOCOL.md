# Broad-support initialization: protocol before implementation and experiments

Date: 2026-11-03. Opened development evidence only; no inference or market admission.

## Evidence and question

The previous N30/K6 study represented 593,775 supports but the three-pair/fixed-tree
circuit assigned meaningful probability to only21. The exact selection proxy also
distorts the allocated objective. A larger LLM does not repair these two facts.

[Bärtschi and Eidenbenz](https://arxiv.org/abs/1904.07358) provide deterministic
Dicke preparation with O(kn) gates and no ancillas. This establishes that generic
exponential StatePreparation is not the only reference. We will **not** label our
different counter construction as their implementation or inherit their resource
bound. [XY-mixer work](https://arxiv.org/abs/1904.09314) motivates evaluating initial
states. [Qiskit's UCRYGate](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.UCRYGate)
provides uniformly controlled Y rotations; measure the complete decomposition.

Question: does a verified uniform-cardinality initial state remove the observed
exploration bottleneck, and what are its full qubit/gate/depth and downstream
financial costs? No superiority result is assumed.

## Construction and proof obligation

Use a compiler-owned sequential counter, not dense state synthesis. A clean binary
counter starts at k. With m assets remaining and counter value j, rotate the next
zero asset by theta=2asin(sqrt(j/m)); conditionally decrement the counter if that
asset is1. The Dicke recurrence gives equal positive amplitudes to all K-of-N
strings. The final counter is zero and can be discarded without postselection.
Impossible j>m branches have zero amplitude and use zero rotation.

Fixed included/excluded assets are outside the free register. Workspace is
ceil(log2(k_free+1)), unless the state is trivial. Count workspace even though the
ideal simulator can eliminate it after proven cleanup. Cost Hamiltonian, fees,
financial constraints and mixer remain unchanged. This is a non-LLM control.

## Correctness gate before larger execution

- Test every n=1..8 and k=0..n: independent Qiskit amplitudes match the combinatorial
  reference within1e-9, including phases and clean workspace probability.
- Crosscheck complete QAOA evolution including frozen assets and explicit slack.
- A preparation claim must match the trusted domain exactly; arbitrary generated
  code or altered preparation metadata is rejected.
- Include every preparation gate and workspace qubit in resources. No counted
  opaque COST/preparation macro. Keep the existing classical state cap.
- Stop at any correctness/resource failure; do not substitute a dense circuit.

## Bounded development comparison

Use the exact pinned INDEX_2010 data and first126/last126 split already opened.
Cases N10/K3 and N30/K6, base mandates; fixed exchange graph for both initializations.
Compare existing three-pair preparation, counter-Dicke preparation, and a classical
uniform final-support sampler. Seeds11,23,37;16 finite-shot objective evaluations,
128 shots each and128 final shots. All sampled methods share a32-query allocator.
The uniform reference uses128 final draws; it does not pay QAOA's2048 optimizer
shots, and is not a matched total-compute comparison.

Report proxy expectation/regret, final allocated objective, feasible probability,
support coverage, workspace/gates/depth, full classical diagnostics and runtime.
The prior exact proxy/SCIP references are context only, not new held-out scores.
Three seeds are descriptive; financial, LLM and quantum-advantage claims remain
unqualified. Archive sources/protocol before execution. No GPU job or LLM call.

## Result interpretation and next gate

Uniform initialization can solve sparse coverage without solving proxy distortion,
angle optimization, noise, real investment-data admission or classical advantage.
Keep an adverse result if extra preparation costs outweigh measured improvement.
Only after these controls should a revised circuit grammar or model sweep be frozen.
