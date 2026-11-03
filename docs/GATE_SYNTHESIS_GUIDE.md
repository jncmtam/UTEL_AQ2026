# Verified gate synthesis

Use the maintained `agqo-research` CLI described in [USER_GUIDE.md](USER_GUIDE.md).
Read [the evidence review](research/EVIDENCE_REVIEW.md) before selecting a model.

The LLM designs exchange connectivity, gate schedule, initialization and parameter
sharing. A compiler locks financial coefficients and expands COST to RZ/RZZ gates.
The verifier checks source identity, schema, invariants, gate semantics, independent
execution and resources before angle fitting. Original financial feasibility is
checked again after measurement and continuous allocation.

Run `baseline` for non-LLM controls, `probe` for bounded native/IR specialist tests,
`smoke` for structural comparisons, and `replay` for saved evidence. Inspect
GateIR, QASM, QPY, source maps and verification reports in `circuits/`.

Legacy free-GateIR/v2 commands remain available for reproducing their frozen
protocols. Their original explanations are under `docs/legacy/`.
