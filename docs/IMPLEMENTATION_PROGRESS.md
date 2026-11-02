# Implementation progress

Updated: 2026-11-02.

## Implemented, awaiting integrated qualification

- FinancialSpec v3, support/weight separation, convex allocation, SCIP reference.
- Direct QUBO/Ising compilation, slack penalties, circuit verification and export.
- Connected exchange design grammar with explicit design ownership.
- Self-financing portfolio accounting and corporate-action value maps.
- Free US data acquisition and fail-closed audit.

## Data gate

Historical DJIA cohort remains a candidate. Raw provider downloads are local-only.
Identity lineage, historical sectors, corporate actions and aligned prices require
review before any market investment-performance claims.

## Research-first correction

The user redirected execution to literature and data suitability before further
model/benchmark choices. Read [research/WORKLOG.md](research/WORKLOG.md),
[research/EVIDENCE_REVIEW.md](research/EVIDENCE_REVIEW.md), and
[research/TECHNICAL_DECISIONS.md](research/TECHNICAL_DECISIONS.md).
The active 80B call was cancelled; no paid continuation is scheduled.
All 101 software tests passed; this is not model or investment qualification.

## Superseded execution order (do not resume automatically)

Run focused tests, complete experiment runner and artifact contract, wire Modal
budget/model registry, run bounded live smoke, finish English migration and UI,
then perform full validation and commit/push. Consult AGENTS.md first.
