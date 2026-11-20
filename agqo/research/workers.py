"""Worker bodies that Modal containers run (imported inside modal_research.py functions).

They simulate circuits, so they must only be called from a Modal container.
"""

from __future__ import annotations

import time

import numpy as np

from .instances import build, extended_features, load_v3_config

_STATE: dict = {}


def _ctx():
    if not _STATE:
        from ..data import MarketData
        from ..quantum.design import schedule_grid

        ec = load_v3_config()
        _STATE.update(md=MarketData.load(), ec=ec, grid=schedule_grid(ec.design), uni={})
    return _STATE


def schedule_rows(specs: list[dict]) -> list[dict]:
    """Success of every grid schedule (no optimiser) on each instance + features + cheap baselines."""
    from ..quantum.design import _row_success
    from ..quantum.simulator import CompiledProblem, uniform_reference, warm_start_only

    c = _ctx()
    ec, grid = c["ec"], c["grid"]
    out = []
    for s in specs:
        t0 = time.time()
        try:
            inst, land = build(c["md"], ec, s, c["uni"])
            if inst.n_qubits < 2:
                out.append(s | {"error": f"{inst.n_qubits} qubits"})
                continue
            cp = CompiledProblem(inst, land)
            t1 = time.time()
            row = _row_success((cp, grid, ec.problem.success_gap, ec.design.cx_budget))
            t_sim = time.time() - t1
            gap = land.gap()
            warm = {eps: warm_start_only(cp, eps, ec.problem.success_gap, 64, np.random.default_rng(0)).success_prob
                    for eps in sorted(set(grid.epsilon))}
            cx = [2 * len(cp.phase_terms(_spec(r))[1]) * int(r["layers"]) for r in grid.to_dict("records")]
            out.append(s | {"features": extended_features(cp, s), "success": row.tolist(), "cx": cx,
                            "n_qubits": int(cp.n), "uniform_success": uniform_reference(cp, ec.problem.success_gap),
                            "warm_success": {str(k): v for k, v in warm.items()},
                            "near_optimal_states": int((np.isfinite(gap) & (gap <= ec.problem.success_gap)).sum()),
                            "feasible_fraction": float(land.feasible.mean()), "sim_seconds": t_sim,
                            "seconds": time.time() - t0})
        except Exception as e:                                # recorded, never hidden
            out.append(s | {"error": f"{type(e).__name__}: {e}"})
    return out


def _spec(row):
    from ..quantum.design import spec_of

    return spec_of(row)


def evaluate_specs(job: dict) -> list[dict]:
    """Run each CircuitSpec (dict) on each instance spec: QAOA with the spec's own optimiser and budget."""
    from ..quantum.simulator import CompiledProblem, run_qaoa
    from ..quantum.spec import CircuitSpec, verify

    c = _ctx()
    ec = c["ec"]
    out = []
    for s in job["instances"]:
        try:
            inst, land = build(c["md"], ec, s, c["uni"])
            cp = CompiledProblem(inst, land)
        except Exception as e:
            out.append(s | {"error": f"{type(e).__name__}: {e}"})
            continue
        for name, sd in job["specs"].items():
            spec = CircuitSpec.from_dict(sd)
            errs = verify(spec, cp.n, ec.design.cx_budget)
            if not errs and 2 * len(cp.phase_terms(spec)[1]) * spec.layers > ec.design.cx_budget:
                errs = [f"compiled two-qubit gates exceed {ec.design.cx_budget}"]
            if errs:
                out.append(s | {"spec": name, "errors": errs})
                continue
            t0 = time.time()
            r = run_qaoa(cp, spec, ec.problem.success_gap, job.get("shots", 512),
                         np.random.default_rng(job.get("seed", 7)))
            out.append(s | {"spec": name, "errors": [], "success_prob": r.success_prob, "feasible_mass": r.feasible_mass,
                            "best_sample_gap": r.best_sample_gap if np.isfinite(r.best_sample_gap) else None,
                            "evaluations": r.evaluations, "two_qubit_gates": r.two_qubit_gates,
                            "seconds": time.time() - t0})
    return out


def decide_items(jobs: list[dict]) -> list[dict]:
    """End-to-end outcome of parsed mandates: the deterministic decision, audited against the gold mandate.

    job = {item, arm, capital_million, mandate (parsed), gold (mandate)}"""
    from ..mandate import Mandate
    from ..service import demo
    from .repro import audit

    d = demo()
    out = []
    for j in jobs:
        rec = {k: j[k] for k in ("item", "arm")}
        try:
            m, gold = Mandate.from_dict(j["mandate"]), Mandate.from_dict(j["gold"])
            errs = m.validate(set(d.sector_of))
            if errs:
                out.append(rec | {"outcome": "invalid", "errors": errs})
                continue
            res = d.decide(j["capital_million"] * 1e6, m, with_textbook=False)
            if res["status"] == "infeasible":
                out.append(rec | {"outcome": "infeasible",
                                  "blocking": [b["code"] for b in res["feasibility"]["blocking"]]})
                continue
            a_gold, a_own = audit(res, d.md, gold), audit(res, d.md, m)
            out.append(rec | {"outcome": "decision", "own_rules_ok": a_own["all_ok"], "gold_rules_ok": a_gold["all_ok"],
                              "gold_failures": [r["rule"] for r in a_gold["rules"] if not r["ok"]],
                              "holdings": len(res["trades"]), "quantum_ran": res["quantum"]["ran"],
                              "te_pct": res["portfolios"]["AGQO"]["te_pct"]})
        except Exception as e:
            out.append(rec | {"outcome": "error", "errors": [f"{type(e).__name__}: {e}"]})
    return out


def walk_job(job: dict) -> dict:
    """One account through the 12 test quarters with one strategy (protocol §5 and §6).

    job = {capital_vnd, strategy: practitioner | greedy | exact | agqo, mandate: dict, label}
    Returns daily account values, per-rebalance rows (post-trade weights) and the mandate audit."""
    from ..backtest import build_rounding_instance, practitioner_target
    from ..experiment import _compliance, walk
    from ..extras import greedy_target
    from ..mandate import Mandate
    from ..portfolio import landscape
    from ..quantum.design import design_features, spec_of
    from ..quantum.simulator import CompiledProblem, run_qaoa
    from ..service import demo

    c = _ctx()
    md, ec = c["md"], c["ec"]
    dm = demo()
    m = Mandate.from_dict(job.get("mandate") or {})
    dates = md.rebalance_dates(ec.test_start, ec.test_end, "QS")
    uni = lambda d: c["uni"].setdefault(("u", d), md.universe(d, ec.problem.lookback_days, ec.problem.min_history)[0])
    t0 = time.time()

    def decide(d, k, acc):
        s = job["strategy"]
        if s == "practitioner":
            return practitioner_target(md, d, uni(d), acc, ec, m), {}
        if s == "greedy":
            return greedy_target(md, d, uni(d), acc, ec, m), {}
        inst = build_rounding_instance(md, d, uni(d), acc, ec, m)
        land = landscape(inst)
        if s == "exact" or inst.n_qubits < 2:
            x = (land.opt_index >> np.arange(inst.n_qubits)) & 1
            return dict(zip(inst.tickers, inst.shares(x)[0])), {"qubits": inst.n_qubits}
        cp = CompiledProblem(inst, land)
        row = dm.grid.iloc[dm.model.choose(design_features(cp))]
        spec = spec_of(row, ec.design.polish_iters if dm.use_polish else 0, ec.design.polish_cvar_alpha)
        r = run_qaoa(cp, spec, ec.problem.success_gap, 512, np.random.default_rng(ec.search.seed + k))
        idx = r.best_sample if r.best_sample is not None else land.opt_index
        x = (idx >> np.arange(inst.n_qubits)) & 1
        return dict(zip(inst.tickers, inst.shares(x)[0])), {"qaoa_success": r.success_prob,
                                                            "gap_vs_exact": float(land.gap()[idx])}

    try:
        series, rows, acc = walk(md, ec, dates, job["capital_vnd"], decide)
    except Exception as e:
        return job | {"error": f"{type(e).__name__}: {e}"}
    comp = _compliance(md, dates, series, rows, acc, m)
    return job | {"dates": [str(x.date()) for x in series.index], "values": series.round(2).tolist(),
                  "fees_vnd": acc.fees_paid, "avg_holdings": float(np.mean([r["holdings"] for r in rows])),
                  "avg_invested_pct": float(np.mean([r["invested_pct"] for r in rows])), **comp,
                  "rows": [{k: v for k, v in r.items() if k != "_weights"} for r in rows], "seconds": time.time() - t0}


def preset_job(p: dict) -> dict:
    """Latest-date decision of one preset (kept for the app's replay) plus its measured summary."""
    from ..service import run_decision

    res = run_decision({"capital_million": p["capital_million"], "mandate": p["mandate"], "with_textbook": True})
    ports = res.get("portfolios") or {}
    meas = {"status": res["status"], "capital_million": p["capital_million"]}
    if res["status"] == "ok":
        meas |= {"te_pct": ports["AGQO"]["te_pct"], "te_rounding_pct": ports["nearest-lot rounding"]["te_pct"],
                 "te_greedy_pct": (ports.get("greedy lot filling") or {}).get("te_pct"),
                 "te_ideal_pct": ports["ideal (fractional shares)"]["te_pct"], "holdings": len(res["trades"]),
                 "fees_vnd": res["fees_vnd"], "cash_after_vnd": res["cash_after_vnd"],
                 "all_checks_ok": res["all_checks_ok"], "quantum_ran": res["quantum"]["ran"]}
    else:
        meas |= {"blocking": "; ".join(b["message_vi"] for b in res["feasibility"]["blocking"])}
    res["execution"] = {"mode": "modal_research", "function": "preset_job"}
    return {"id": p["id"], "measured": meas, "decision": res}
