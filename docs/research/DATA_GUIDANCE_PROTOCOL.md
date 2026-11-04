# Data features to circuit decisions

Date: 2026-11-04. Recorded before implementation. Offline development only;
no new Modal dispatch, model selection, held-out scoring or advantage claim.

The existing designer receives correlations, objective terms and constraints but
only a generic instruction to use them. The three saved live proposals all use a
path and two layers. This does not establish data adaptation. The previous CPU
study also shows that correlation trees alone do not beat informed local search.
The next correction is an explicit, auditable design procedure, not a bigger LLM.

## Evidence and alternatives

- [Hadfield et al., alternating operator ansatz, v2](https://arxiv.org/abs/1709.03489v2)
  establishes the constrained-mixing design framework. Connected XY exchanges
  motivate a cardinality-preserving domain; connectivity does not prove low-depth
  performance or preservation of all financial inequalities.
- [Zhu et al., ADAPT-QAOA, v3](https://arxiv.org/abs/2005.10258v3) reports adaptive
  operator selection on MaxCut. It motivates testing problem-specific operators,
  but its gradient-selected algorithm is not replicated by an LLM reading data.
- [Stopfer and Wagner, portfolio benchmark, v3](https://arxiv.org/abs/2509.17876v3)
  supports retaining strong classical references. Its variance objective differs
  from our allocated tracking/cost task; its numerical conclusions do not transfer.

Alternatives: keep a fixed circuit; use a deterministic feature rule; use an
ADAPT-like measured operator pool with its additional evaluations counted. A new
LLM must beat these alternatives under a matched total budget to justify itself.

## Exact descriptor and its limits

Write the immutable *selection proxy* as
`B(x) = c + sum(l_i*x_i) + sum(i<j, J_ij*x_i*x_j)`.
For a permitted exchange `x_i=1,x_j=0 -> x_i=0,x_j=1`,

`delta_ij = l_j-l_i + sum(t != i,j, (J_jt-J_it)*x_t)`.

Fix mandatory bits. Among the other free bits, condition on uniform choice of
`s = remaining_cardinality-1` out of `L = free_count-2`. With `a_t=J_jt-J_it`,
the exact mean is the fixed-bit contribution plus `(s/L)*sum(a_t)`. The variance
is `s*(L-s)/(L*(L-1))*sum((a_t-mean(a))**2)` for `L>1`, and zero otherwise.
The RMS difference is `sqrt(mean_delta**2 + variance_delta)`.

This polynomial descriptor uses no sampled portfolios, optimizer shots, allocation
queries, future observations or solver optimum. It measures sensitivity of B to
an exchange, **not** a favorable direction, a quantum gradient, a transition
probability, or improvement in the continuous allocated objective F. The neutral
reference conditions only on cardinality/include/exclude, not other inequalities.
Large RMS can overemphasize costly channels; near-degenerate channels can also
matter. No monotonic performance theorem is assumed.

Correlation and half-window changes are supplementary descriptors. Identical
correlations can coexist with different benchmark exposures and cost terms; they
cannot determine the mixer alone. Numerical code computes all values.

## Explicit LLM procedure and contract

1. Inspect frozen bits and remaining cardinality. Keep every admitted security.
2. Compare allowed parent edges using exchange sensitivity, correlation stability
   and existing positions. Explain the tradeoff; do not automatically maximize RMS
   or absolute correlation. Every chosen parent must cite its actual pair ID.
3. Use connected exchanges; account for overlapping-edge conflicts when ordering
   gates. Reordering overlapping exchanges changes the circuit and needs refitting.
4. Choose one or two shared beta groups. Additional flexibility must earn its
   optimization cost. Give a falsifiable justification for ordering and sharing.
5. Keep common compiler-owned preparation, one layer, exact cost and measured
   resource caps. Do not replace the problem by dropping weak cost terms.
6. Return typed evidence links. An independent adapter checks links against the
   actual chosen gates before existing quantum/resource admission. Evidence links
   prove traceability only; natural-language explanations are not correctness proof.

Provide compact per-parent numeric rows for *all* allowed pairs, with declared
rounding and scale. This is not security filtering. The full descriptor hash and
problem/Hamiltonian identities accompany each request. This initial request
contract is capped at 20 free assets until context costs are measured. Legacy
request paths and completed source snapshots remain unchanged.

## Offline scope, data suitability and acceptance

Use the same eight development cases from improvement_v1, the first126 rows of
the pinned 2010 US corpus. Artificial policy buckets are not historical sectors.
Full-year membership conditioning persists: this is an algorithm diagnostic,
not investable historical evidence. No independent test set is consumed here.

Verify exact mean/RMS against exhaustive small supports, frozen-bit behavior,
constant objectives, consistent asset permutations, benchmark changes with fixed
asset correlations, immutable cost hashes, missing/wrong evidence links, and
separation of explanation admission from quantum/resource admission. Produce
eight inspectable request artifacts and a feature visualization. A deterministic
response fixture may exercise the contract but must never be called LLM output.

Budget: local CPU only, no paid inference or new portfolio-quality search. Stop
after these software/descriptor checks. Do not report a new circuit-quality win.

## Future experiment, not executed or qualified here

Freeze one identical model, common preparation/coordinates, compiler and total
architecture/angle/allocation budget. Compare unguided context, explicit guidance,
feature-rule proposals, random proposals and adaptive classical structure search;
retain conditioned uniform and allocation-aware swap. Use held-out families and
mandate combinations, with permutation and descriptor-ablation interventions.
Shuffling descriptors alone leaves the cost Hamiltonian as another data channel;
it cannot establish that *all* data dependence was removed.

Success requires validity and resource admission, useful allocated-F quality by
budget against the strongest reference, and a real guidance effect beyond a rule
baseline. Different gates or plausible citations alone are insufficient. Include
descriptor construction, explanation tokens and all failed trials in costs. Size
that independent study from a preregistered effect/uncertainty target; do not
recycle the opened cases as confirmation. If no useful frontier appears, stop
LLM scaling. The historical market-data gate remains separate and closed.
