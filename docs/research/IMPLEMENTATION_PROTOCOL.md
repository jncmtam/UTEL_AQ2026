# Implementation protocol: evidence-derived completion

Date: 2026-11-02. This protocol precedes the following development experiments.
User requested implementation of the full reviewed workflow.

## Questions and permitted experiments

1. Does explicit omission of certified zero penalties change execution or reduce
   resources? Compare full penalty and fixed-cardinality-subspace encodings on
   the existing structural development cases, with identical angles/initialization.
   Prove omitted terms vanish on the declared subspace and test independently.
2. How do exchange preparation and an exact small Dicke reference differ? The
   Dicke reference uses explicit state synthesis, whose full gate cost is counted.
   This is not a claimed implementation of the O(kn) paper construction.
3. Can gradient-based exchange selection beat rule or random architecture at a
   measured total evaluation cost? Implement and label an ADAPT-inspired finite-
   difference exchange baseline, not a paper replication.
4. Can the public QUASAR specialist produce correct native QASM for two declared
   quantum primitives and transfer to one bounded financial GateIR request? The
   native tasks are interface/semantic probes, not a reproduction of the paper's
   optimization benchmark or a qualification sample. One initial batch, no paid
   repair. Three native/transfer requests, <=2048 output tokens each. Stop after
   the batch regardless of results. Run only after local quantum controls pass.

## Model and cost boundary

QUASAR checkpoint: Benyucong/rl_quantum_4b,
revision b9581279345436e2b7eadcdf80e4f1417748eb8b. Deployment uses BF16 inference,
one A100-80GB, no fine-tuning; this precision differs from stored F32 weights and
must be recorded. Use the existing authorized budget policy with checkpointed
reservations, one GPU worker at a time, and billing snapshots. No 397B/480B job.

## Software acceptance

A single English CLI must produce status/audit, baseline studies, structural
benchmarks, audited market walk-forward, bounded inference and offline replay.
Each branch emits the artifact contract even when the data gate blocks execution.
Artifacts and reported statuses distinguish blocked, failed, interrupted,
unsupported and completed. Frozen outputs cannot be silently overwritten.

Tests cover independent Hamiltonian checks, initialization and invariants,
accounting, gate rejection, data checksums/cutoffs, adaptive evaluation accounting,
continuous trajectories, replay integrity and complete output contracts.

## Dataset boundary

Do not manufacture a passed market audit. Implement source-evidence ingestion and
corporate-action lineage tracking, preserve the 30-security cohort, and produce a
blocked report if full identity/action/as-of evidence remains unavailable. This
is a scientific data dependency, not a reason to omit the software pipeline.

## Reporting and stop conditions

Record actual findings in WORKLOG.md and generated Markdown reports. No model is
selected as a winner from three probes. Final market conclusions require an
admitted dataset and a separate frozen experiment. Structural simulator results
cannot establish quantum advantage. Failed probes trigger diagnosis, not a larger
model sweep. Commit code, English docs and bounded evidence; keep raw provider
payloads local and retain historical evidence unchanged.
