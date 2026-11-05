# Bounded full-pipeline Modal integration test

Date: 2026-11-04. Frozen before deployment and live inference for this test.
User explicitly requests deployment and execution on Modal. This supersedes the
previous no-new-job scheduling note for this bounded integration test only.

## Evidence, scope and alternatives

REMEDIATION_PLAN.md records the published sparse-tracking, warm-start and mixed-binary
research and local negative controls. This test checks integration; it does not
select a production model, resolve historical admission or establish superiority.
Choose existing pinned Qwen Coder30 as the established general-code integration
worker, rather than an untested model/runtime or a model-size sweep. Its previous
pilots and CPU tokenizer pass are compatibility evidence only.

The old pipeline's Modal branch is an isolated specialist probe. New execution
must link actual model responses to verified GateIR, numerical fitting, support
sampling, allocation, fees, circuit exports and reports. Keep existing commands,
protocols and source results unchanged.

## Frozen execution

- One new CPU deployment, `agqo-research-pipeline`, with pinned scientific packages
  and persistent private result volume. CPU stages:4 cores/8GiB, timeout900s,
  startup180s, max1 container, retries0. Release GPU during CPU evaluation.
- Run the existing offline software pipeline on cloud CPU, including baseline,
  two-period synthetic accounting and explicit blocked market artifacts. Transfer
  the historical manifest/audit metadata only; raw provider files stay local. This
  run does not repeat the completed source-hygiene audit or certify missing prices.
- Three deterministic synthetic development cases: N6 base, N6 mandatory exclusion,
  N8 base. They test mechanics; published and final-market returns are not opened.
- Common compiler-owned counter-Dicke preparation and paper RMS coordinates for
  circuit controls and LLM. Freeze a versioned grammar where the preparation field
  is a constant identifying compiler ownership. LLM chooses tree, schedule, groups
  and depth (1..2). Financial coefficients and Hamiltonian remain immutable.
- One live batch of three proposals from coder30;2048 output tokens/request,
  temperature0.4, seed100. No repair or model-size escalation in this run.
- Evaluate fixed/rules/LLM circuits with the same finite sampled allocated-F loss:
  six candidate angle evaluations,32 shots each,64 final shots, seeds11/23.
  All256 optimizer/final observations enter the candidate pool. Per-run caches
  avoid repeated allocation solves; no cache shared between methods or seeds.
- Uniform-cardinality control:256 draws, including invalid supports in the
  denominator. Allocation-aware swap and joint SCIP references are separately
  labeled work, not zero-cost same-budget controls. Enumerate small references.
- F loss uses bounded development-derived physical objective upper bound and a
  larger infeasible/unknown score. No actual optimum used to choose angles.
  Unknown allocation results remain explicit. Report allocated objective, sampled
  feasibility, unique allocation solves, cache hits, shots, wall time and resources.
- If an LLM proposal is malformed, retain it as rejected; no substitution credited
  to LLM. Genuine infeasible mandate is an explicit classical diagnosis control.

This is a variational support sampler with a QAOA circuit family and classical F
feedback. COST still implements B; F is not a coherent quantum oracle. Report this
distinction and all classical allocation work. Simulation is on Modal CPU, not QPU.

## Budget and stop rules

Use one shared local reservation ledger for all CPU/prefetch/GPU dispatches under
the existing USD150 ceiling. Check live billing before each dispatch; no balance
or credit is assumed. Bound one prefetch, one GPU batch and at most three pipeline
CPU calls (prepare, finish, optional resume after an infrastructure failure).
No automatic paid retry. Retain dispatch IDs, raw results, revision, usage and
billing snapshots. Reservation is not an invoice. Maximum GPU size:one A10080GB.

Before live execution, pass targeted allocation/grammar/checkpoint/bundle tests and
static checks. Before GPU dispatch, cloud preparation must return valid hashes and
requests. After inference, verify model/revision and exact request correspondence.
All remote artifacts are hash-checked on download; completed stages cannot be
silently overwritten. Failed calls remain charged conservatively in the ledger.

Integration is successful only when a live model-generated circuit reaches an
audited allocation/trade artifact. Rejected cases remain failures in the denominator.
If no proposal reaches that point, report integration failure. A blocked historical
market stage is expected and cannot be relabeled passed. No claim that this small
run meets95% reliability,20% improvement, market benefit or quantum advantage.

## Outputs

Persist protocol, data audit, stage receipts, requests/responses, reference records,
decisions, metrics, GateIR/QASM/QPY/verifier reports, source/package hashes, cost and
failure reports, English RESULTS/PROGRESS, diagnostic figures and a result archive.
Download artifacts locally; raw provider files and model weights are excluded.
