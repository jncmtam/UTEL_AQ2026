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

## Reproduction and provenance

Protocols are frozen before runs. SHA256 identifies data, requests, financial
specifications, Hamiltonians and model revisions. Cache hits are labeled replay
or cached-live evidence. A fallback cannot be attributed to QAOA. Historical raw
responses and results are immutable; derived reports retain their source path.

Historical documentation is preserved under `docs/legacy/` and Git history.
