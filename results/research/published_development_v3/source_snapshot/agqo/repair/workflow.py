"""One reusable decision workflow for CLI and UI; never sends orders."""
from __future__ import annotations

from dataclasses import replace
from time import perf_counter
import numpy as np

from .circuits import rule_spec, run_qaoa
from .data import make_window
from .llm import QwenClient
from .mandates import normalize_rules
from .model import heldout_metrics
from .solvers import anneal_solve, exact_solve, hold_result, milp_solve


def decide(data, text, client=None, normalizer="rules", n=8, k=4, evaluations=32, shots=256, export_circuit=False):
    start = perf_counter()
    client = client or QwenClient()
    base, future_r, future_b = make_window(data, n=n, k=k)
    tickers, sectors = base.tickers, tuple(sorted(set(base.sectors)))
    if normalizer == "qwen":
        mandate, trace = client.normalize(text, tickers, sectors)
    elif normalizer == "rules":
        mandate, trace = normalize_rules(text, tickers, sectors), {"status": "baseline_rules_not_llm"}
    else:
        raise ValueError("Normalizer phải là rules hoặc qwen.")
    if mandate is None or mandate.status != "ready":
        return {"status": "needs_clarification", "mandate": None if mandate is None else mandate.to_dict(), "llm_trace": trace, "results": []}
    p = replace(base, mandate=mandate)
    reference = exact_solve(p)
    records = [hold_result(p), reference, milp_solve(p), anneal_solve(p)]
    # A non-LLM circuit baseline is always present and labeled accordingly.
    q = run_qaoa(p, rule_spec(p), evaluations=evaluations, shots=shots, export_circuit=export_circuit)
    q["method"] = "qaoa_rule"; records.append(q)
    spec, circuit_trace = client.propose(p)
    if spec is not None:
        q = run_qaoa(p, spec, evaluations=evaluations, shots=shots, export_circuit=export_circuit)
        q.update(method="qwen_circuit", llm_trace=circuit_trace)
        q["elapsed_seconds"] += circuit_trace.get("elapsed_seconds", 0)
        records.append(q)
    else:
        records.append({"method": "qwen_circuit", "status": circuit_trace["status"], "llm_trace": circuit_trace, "feasible": False})
    for r in records:
        w = np.asarray(r["bits"]) / p.k if r.get("bits") is not None else np.asarray(r["weights"]) if "weights" in r else None
        if w is not None:
            r.update(heldout_metrics(p, w, future_r, future_b))
            r["trades"] = [{"ticker": ticker, "sector": p.sectors[i], "previous": float(p.previous_weights[i]),
                            "target": float(w[i]), "delta": float(w[i] - p.previous_weights[i]),
                            "cost": float(p.cost_rates[i] * abs(w[i] - p.previous_weights[i]))}
                           for i, ticker in enumerate(p.tickers)]
        if reference["status"] == "optimal" and r.get("feasible") and r.get("bits") is not None:
            r["objective_gap_absolute"] = r["objective"] - reference["objective"]
    candidates = [r for r in records if r.get("feasible") and r.get("objective") is not None]
    recommended = min(candidates, key=lambda r: r["objective"]) if candidates else None
    # Keep a feasible incumbent unless a target strictly improves the frozen objective.
    return {"status": "infeasible" if reference["status"] == "infeasible" and not candidates else "ready" if recommended else "unknown",
            "mandate": mandate.to_dict(), "normalization_trace": trace, "circuit_trace": circuit_trace,
            "problem_hash": p.fingerprint(), "cutoff": p.cutoff, "data_provenance": data.provenance,
            "tickers": list(p.tickers), "sectors": list(p.sectors), "previous_weights": p.previous_weights.tolist(),
            "cost_weight": p.effective_cost_weight, "two_way_turnover_definition": "sum(abs(target_weight - drifted_previous_weight)); range [0,2]",
            "results": records, "recommended_method": None if recommended is None else recommended["method"],
            "decision_basis": "Lowest in-sample frozen objective among feasible candidates, including hold. Future returns are diagnostic only and never used for selection.",
            "elapsed_seconds": perf_counter() - start,
            "claims": "Research decision support; synthetic/benchmark data, CPU simulation, no trading execution or quantum advantage claim."}
