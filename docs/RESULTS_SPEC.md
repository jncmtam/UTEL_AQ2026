# Result and evidence specification

Common artifact contract: `protocol.json`, `dataset_manifest.json`,
`decisions.jsonl`, `circuits/`, `metrics.csv`, `cost_report.json`, `RESULTS.md`,
`PROGRESS.md`. Task-specific raw records and requests are retained alongside it.

## Status semantics

- `completed`: requested software execution finished; read hypothesis outcomes.
- `blocked`: a prerequisite was not met; no decision is fabricated.
- `completed_with_data_blockers`: software stages ran; market conclusions blocked.
- `unknown`: the solver/budget did not determine a valid answer or proof.
- `infeasible`: supported by an explicit contradiction or solver certificate.
- `unsupported`: outside the supported circuit/register/resource domain.
- `failed`: execution or validation failed; retain it in the denominator.
- `interrupted`: external/user interruption; do not score as model incapability.

Each hypothesis is supported, unsupported or inconclusive. Software pass counts,
model-validity rates, circuit utility, investment value and quantum advantage are
separate claims. Ideal CPU simulation cannot establish hardware speedup.

## Financial and resource semantics

Selection proxy B(S) and allocated objective F(S) are reported separately.
One-way turnover in v3 is half L1 including cash; legacy records use their
original two-way conventions. Costs are per-side assumptions, tested separately
from historical liquidity estimates. Orders are self-financing and charged once.

Qubit counts include slack registers; gate/depth counts include state preparation
and all cost lowering. The Dicke reference uses dense synthesis and is labeled
accordingly. Gradient selection reports every extra classical energy evaluation.
All architecture candidates, invalid requests and allocation queries count.
Reservations are conservative bounds and never reported as actual invoices.
Current transpilation uses a logical all-to-all basis without hardware routing,
SWAP overhead or noise. CX/depth figures are not device execution estimates.

`optimal` in the decision interface requires a joint support/weight solver
certificate (subject to solver tolerances). A heuristic or sampled decision is
`feasible`; its conditional convex solution status is `allocation_status`.
Historical raw results retain their earlier labels and must be interpreted using
their original allocation scope. Trajectory v2 fixes this distinction and applies
the common 32-query sample allocator.

GateIR v2 widens the register while preserving v1. Large ideal simulations use
every fixed-cardinality support (plus slack), an analytic conservation certificate
and the independently crosschecked block executor. Report non-negligible support
coverage separately from basis size. No large-register full-Qiskit check is claimed.

## Reproduction and provenance

Protocols are frozen before runs. SHA256 identifies data, requests, financial
specifications, Hamiltonians and model revisions. Cache hits are labeled replay
or cached-live evidence. A fallback cannot be attributed to QAOA. Historical raw
responses and results are immutable; derived reports retain their source path.

Historical documentation is preserved under `docs/legacy/` and Git history.
