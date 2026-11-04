# What the tail-fitting pilot establishes

Implemented opt-in feasibility-gated allocated-score aggregation, batch evidence
and independent final-sample qualification. Legacy defaults are retained; a
feasible decision remains available even when distribution qualification fails.
The full211-test suite passes, including42 fitting tests and a replay-guard test.

## Measured outcome

All96 runs completed with55,296 observations and35,651 allocation attempts.
Independent audit rescored35,503 feasible cached allocations (maximum F residual
2.71e-20) and verified325 raw input/run/setup/source hashes. Three plots inspected.

At N20/576 observations, tail-minus-mean F averages-0.40% (7 wins/1 tie/4 losses).
At N12 it is+0.79% (0/11/1). Negative means better; these are related development
training scores, not returns or significance. Tail vs uniform averages-0.01% at
N20, with5 wins/7 losses. Tail remains+7.35% worse than allocation-aware swap,
losing all12 N20 pairs. There is no robust overall performance qualification.

All48 fitted runs' final64-shot batches pass the empirical95% feasibility gate;
this is not population certification. Mean final feasibility is99.22% for mean
and98.96% for tail. Tests separately exercise failed gates and unknown outcomes.

## Interpretation

- Aggregation changes results but does not establish a useful overall frontier
  against informed classical portfolio search. Keep tail experimental/defaults
  unchanged. Do not tune alpha/seeds until a win or escalate model size.
- COST remains equal-weight B; feedback uses allocated F. This is neither a fix
  for their mismatch nor a coherent quantum F oracle.
-576 observations/run differs from the old88-observation configuration. Changes
  across studies cannot be attributed solely to this code. Within-pilot mean/tail
  budgets are matched. Equal observations do not imply equal complete cost.

## Timing and data limits

Recorded117.32s run time plus1.07s setup time exclude input preparation, source
hashing/snapshotting and, on resume, repeated compile/setup checks. These are
recorded run/setup times, not complete adaptation cost or hardware advantage.
Local host timing is descriptive. No model, Modal call or new paid reservation.

Only previously opened first126 observations of the conditional2010 US corpus
were used. Families/mandates/seeds are dependent, and artificial policy buckets
are not audited sectors. No financial holdout scored; market admission blocked.

Next dependency: test/improve selection-versus-allocation formulation with strong
classical controls before LLM circuit adaptation. A future protocol must account
for outer-loop cost and binary-subproblem difficulty. No follow-up scheduled.

See [full measurements](RESULTS.md), [protocol](../../../docs/research/TAIL_FITTING_PROTOCOL.md)
and [raw completion](completion.json). This additional interpretation preserves
the original raw/generated outputs.
