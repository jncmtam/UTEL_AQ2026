# Portfolio repair guide

Start with [USER_GUIDE.md](USER_GUIDE.md). The maintained workflow uses US equities,
verified mandates, common allocation and explicit tracking/cost trade-offs.

`trajectory --source synthetic` validates account integration. `trajectory --source
market` requires the source-backed dataset audit. `serve` opens the English decision
application. Inspect the hold alternative, required exits, turnover feasibility,
weight constraints, dollar trades and cost before interpreting solver quality.

Legacy `agqo-repair` remains a compatible equal-weight prototype. Historical
behavior and the original bilingual parser are preserved in code and archived docs;
they are not a substitute for the v3 financial semantics.
