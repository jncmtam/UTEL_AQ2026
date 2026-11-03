# Completion protocol: data, scale and model evidence

Date: 2026-11-03. Written before the following work.

## Remaining acceptance gaps

1. The 2013 US cohort lacks a complete source-backed membership/identity/action
   review. Do not close this by editing booleans or deleting UTX.
2. The market runner is therefore not evidence of financial usefulness.
3. The quantum simulator is limited to 12 asset/16 total qubits, even when the
   financial cohort has 30 assets. Smaller benchmark families are not full-cohort
   execution. Implement and independently test a conserved-subspace backend before
   considering a larger quantum study; no hardware-speedup claim follows.
4. QUASAR's three interface probes do not choose a model. Native evaluation must
   distinguish interface-contract failure from quantum semantics, while preserving
   the originally frozen scores.
5. The UI has API validation but lacks visual QA; complete it if browser tooling
   becomes available, otherwise retain the limitation explicitly.

## Data work and stop rules

Check the original DIA filing with the complete October 2013 holdings, rather
than inferring membership from today's list. Use its historical valuation as an
independent price anchor and source-backed RTX/UTX succession documentation as a
candidate mapping. Price anchors are diagnostics, not a complete action audit.
Record the publication/observation distinction and inaccessible sources.

Investigate the published sparseIndexTracking US dataset as a separate algorithm
benchmark. Its documentation conditions membership on the entire year, so it is
not an unbiased point-in-time investment universe and must not replace the main
cohort silently. No paid market data or new LLM sweep is authorized by this protocol.

## Technical implementation boundary

A conserved-subspace simulator may enumerate C(N,K) asset supports times explicit
slack states, while preserving every asset choice. It must apply XY pairs as blocks,
retain the full canonical cost, enforce a memory/state-count cap, and agree with the
full statevector on small cases including slack and frozen qubits. A new GateIR
version is required for larger registers; frozen v1 schema stays unchanged.

## Recording

Update WORKLOG.md with source facts, diagnostic outputs, supported conclusions and
remaining dependencies. Preserve historical model responses and frozen results.

## Predeclared conditional-corpus development study

Sources: Benidis, Feng and Palomar, [IEEE TSP 2018](https://doi.org/10.1109/TSP.2017.2762286),
the [author's package](https://github.com/dppalomar/sparseIndexTracking) at revision
73a8d6016588634ba91f7e6d1667f343034ec9b8, and [XY mixers](https://arxiv.org/abs/1904.09314).
The first source motivates joint selection/allocation and a real return corpus;
the latter motivates conserved-cardinality execution, not a speedup claim.

Use the source's 252 dated observations, first 126 for design/estimation and last
126 for a single frozen-weight diagnostic. This is opened development evidence,
not held-out model qualification or a continuous investment backtest. Families
are deterministic SHA256 order of source identifiers, N=10/K=3 and N=30/K=6.
No LLM selects assets. Include an additional N=10 scenario excluding the first
currently held asset. All costs are explicit 5-bp per-side assumptions. Policy
buckets are synthetic categories; they are not historical sectors.

Compare fixed, correlation-rule and random connected circuits (one seed=11),
uniform feasible draws with the same final sample count, allocation-aware swaps,
and joint SCIP (15-second solver limit). Every sampled method gets the same
32-query allocator. Use four finite-shot objective evaluations, 64 shots each,
and 64 final shots: a plumbing/scale test, not a well-optimized QAOA study.
Record all simulation support scoring and parameter-activity work; this additional
exact diagnostic access is not a hardware query protocol. Report the number of
non-negligible probability supports to expose limited exploration by shallow circuits.

Compute a continuous 386-asset tracking/cost relaxation as a source-universe lower
reference. It drops cardinality and minimum-position constraints and is a numerical
convex-solver reference, not a certified integer optimum. Gap to this relaxation
must not be called measured loss from restricting the universe.

Acceptance: exact source/date checks; no future return in design; no asset
prefilter inside a family; small full-state equivalence within 1e-9; all exports
and failed rows preserved; bounded state count <=2,000,000. Stop at a failed source
hash/schema/cap rather than substitute data. No quality superiority target is
imposed on this small development run. No new GPU inference is part of this study.
