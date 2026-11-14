"""End-to-end experiment: analysts -> circuit design search -> walk-forward backtest.

Stage A  Market analysis    : liquidity rule | greedy tracking-error rule | LLM analyst (views + basket)
Stage B  Circuit design     : default | random | classical evolution | LLM evolution  (train dates only,
                              on the lot-rounding problem)
Stage C  Walk-forward test  : every strategy runs its own 100M VND account with lots, fees and tax
Stage D  Quantum diagnostics: every frozen design re-scored on unseen dates against exact enumeration
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import (Account, build_rounding_instance, build_selection_instance, daily_values, performance,
                       qp_round_target, risk_inputs)
from .classical import greedy_te_shortlist, liquidity_shortlist, simulated_annealing
from .config import ExperimentConfig
from .data import MarketData, coverage_table
from .features import anonymise, benchmark_summary, feature_table
from .llm import analyst
from .llm.architect import Evaluator, best, problem_summary, search
from .llm.client import LLMClient, make_request
from .portfolio import landscape
from .quantum.simulator import CompiledProblem, run_qaoa, uniform_reference

# name -> (family, analyst, optimiser)
#   family   "full"   : hold any VN30 member; quantum decides integer-lot rounding of the continuous optimum
#            "basket" : concentrated 8-stock mandate; the analyst picks the register
#   analyst  "none" | "liquidity" | "greedy" | "llm"  (llm supplies views, and the basket in basket mode)
#   optimiser "nearest" | "exact" | "qaoa:<design arm>"
STRATEGIES = {
    "QP + nearest-lot rounding": ("full", "none", "nearest"),
    "QP + exact lot rounding": ("full", "none", "exact"),
    "QP + QAOA rounding (default circuit)": ("full", "none", "qaoa:default"),
    "QP + QAOA rounding (evolved circuit)": ("full", "none", "qaoa:evolve"),
    "LLM views + QP + exact rounding": ("full", "llm", "exact"),
    "AGQO: LLM views + QP + QAOA (LLM circuit)": ("full", "llm", "qaoa:llm"),
    "Basket: liquidity top-8": ("basket", "liquidity", "exact"),
    "Basket: greedy-TE top-8": ("basket", "greedy", "exact"),
    "Basket: LLM analyst top-8": ("basket", "llm", "exact"),
}
REFERENCE = "QP + exact lot rounding"


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def run(out: Path, llm: LLMClient | None, ec: ExperimentConfig = ExperimentConfig(),
        llm_samples: int = 1) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    cfg, sc = ec.problem, ec.search
    md = MarketData.load()
    dates = md.rebalance_dates(ec.first_rebalance, ec.last_rebalance)
    coverage_table(md, dates, cfg.lookback_days, cfg.min_history).to_csv(out / "coverage.csv", index=False)
    (out / "config.json").write_text(json.dumps(ec.to_dict(), indent=2))

    # ------------------------------------------------------------ Stage A: analysts
    _log(f"Stage A: market analysis on {len(dates)} rebalance dates")
    universes, requests, aliases = {}, [], {}
    decisions = {"none": {}, "liquidity": {}, "greedy": {}, "llm": {}}
    for k, d in enumerate(dates):
        uni, _ = md.universe(d, cfg.lookback_days, cfg.min_history)
        universes[d] = uni
        cov, cov_b, var_b = risk_inputs(md, d, uni, cfg)
        ft = feature_table(md, d, uni, cfg.lookback_days)
        g = [uni[i] for i in greedy_te_shortlist(cov, cov_b, var_b, cfg.n_candidates, cfg.invest_target)]
        liq = [uni[i] for i in liquidity_shortlist(ft.loc[uni, "liquidity_share_pct"].to_numpy(), cfg.n_candidates)]
        decisions["none"][d] = {"shortlist": uni, "views": {}}
        decisions["greedy"][d] = {"shortlist": g, "views": {}}
        decisions["liquidity"][d] = {"shortlist": liq, "views": {}}
        if llm is not None:
            table, alias = anonymise(ft, seed=1000 + k)
            aliases[d] = alias
            sys_prompt = analyst.SYSTEM.format(n=cfg.n_candidates, capital=cfg.capital_vnd / 1e6)
            payload = analyst.user_payload(table, benchmark_summary(md, d), cfg.n_candidates, cfg.capital_vnd / 1e6)
            for s in range(llm_samples):
                requests.append((d, make_request("market_analyst", sys_prompt, payload,
                                                 analyst.schema(list(alias), cfg.n_candidates),
                                                 seed=k * 10 + s, temperature=0.3, max_tokens=3072)))
    if llm is not None:
        recs = llm.generate([r for _, r in requests])
        by_date: dict = {}
        for (d, _), rec in zip(requests, recs):
            by_date.setdefault(d, []).append(rec)
        for d, rs in by_date.items():
            fallback = decisions["greedy"][d]["shortlist"] + universes[d]
            parsed = [analyst.parse(r["parsed"] if r["status"] == "ok" else None, aliases[d], cfg.n_candidates, fallback)
                      for r in rs]
            # self-consistency: majority vote over samples, view confidence scaled by agreement
            votes = pd.Series([t for p in parsed for t in p["shortlist"]]).value_counts()
            order = sorted(votes.index, key=lambda t: (-votes[t], fallback.index(t) if t in fallback else 99))
            views = {}
            for t in {t for p in parsed for t in p["views"]}:
                vs = [p["views"][t] for p in parsed if t in p["views"]]
                views[t] = (int(round(np.mean([v for v, _ in vs]))), float(np.mean([c for _, c in vs]) * len(vs) / len(parsed)))
            decisions["llm"][d] = {"shortlist": order[: cfg.n_candidates], "views": views,
                                   "regime": [p["regime"] for p in parsed], "rationale": parsed[0]["rationale"],
                                   "repairs": [p["repairs"] for p in parsed]}
    dump = {arm: {str(d.date()): v for d, v in dd.items()} for arm, dd in decisions.items()}
    (out / "analyst_decisions.json").write_text(json.dumps(dump, indent=1, ensure_ascii=False, default=str))

    # ------------------------------------------------------------ Stage B: circuit design search
    _log("Stage B: circuit-design search on training dates")
    train_dates = dates[: sc.train_dates]
    train_probs = []
    for d in train_dates:
        inst = build_rounding_instance(md, d, universes[d], {}, Account(cash=cfg.capital_vnd), ec)
        train_probs.append(CompiledProblem(inst, landscape(inst)))
    ev = Evaluator(train_probs, sc.cx_budget, cfg.success_gap, sc.shots, sc.seed)
    arms = ["default", "random", "evolve"] + (["llm"] if llm is not None else [])
    summary = problem_summary(train_probs, sc.cx_budget, cfg.success_gap)
    histories, best_specs = {}, {}
    for arm in arms:
        t0 = time.time()
        histories[arm] = search(arm, ev, sc.rounds, sc.proposals_per_round, sc.seed, llm, summary)
        best_specs[arm] = best(histories[arm])
        _log(f"  {arm:8s} designs={len(histories[arm]):3d} best success={best_specs[arm].fitness:.4f} "
             f"({time.time() - t0:.0f}s)")
    pd.DataFrame([h.row() | {"order": i} for arm in arms for i, h in enumerate(histories[arm])]).to_csv(
        out / "circuit_search.csv", index=False)
    (out / "best_specs.json").write_text(json.dumps(
        {a: {"spec": b.spec.to_dict(), "train_metrics": b.metrics} for a, b in best_specs.items()}, indent=2))
    (out / "problem_summary.json").write_text(json.dumps(summary, indent=2))

    # ------------------------------------------------------------ Stage C: walk-forward
    _log("Stage C: walk-forward backtest")
    strategies = {k: v for k, v in STRATEGIES.items() if v[1] != "llm" or llm is not None}
    end = md.index.index[-1]
    daily, rebal_rows, perf = {}, [], {}
    diag_instances = {}
    for name, (family, arm, opt) in strategies.items():
        acc = Account(cash=cfg.capital_vnd)
        segments = []
        for k, d in enumerate(dates):
            px = md.close.loc[d]
            info = {"strategy": name, "date": str(d.date()), "nav_pre": acc.value(px)}
            if opt == "nearest":
                target = qp_round_target(md, d, universes[d], acc, ec)
            else:
                dec = decisions[arm][d]
                if family == "full":
                    inst = build_rounding_instance(md, d, universes[d], dec["views"], acc, ec)
                else:
                    inst = build_selection_instance(md, d, dec["shortlist"], dec["views"], acc, ec)
                land = landscape(inst)
                if name == REFERENCE:
                    diag_instances[d] = (inst, land)
                if opt == "exact":
                    idx = land.opt_index
                else:
                    cp = CompiledProblem(inst, land)
                    res = run_qaoa(cp, best_specs[opt.split(":")[1]].spec, cfg.success_gap, sc.shots,
                                   np.random.default_rng(sc.seed + k))
                    idx = res.best_sample
                    info |= {"qaoa_success": res.success_prob, "qaoa_best_gap": res.best_sample_gap}
                if idx is None:
                    target = dict(acc.shares)
                    info["fallback"] = "no affordable sample: holdings kept"
                else:
                    x = (idx >> np.arange(inst.n_qubits)) & 1
                    target = dict(zip(inst.tickers, inst.shares(x)[0]))
                    info["gap_vs_exact"] = float(land.gap()[idx])
                    info["ex_ante_te_pct"] = float(100 * inst.tracking_error(inst.weights(x))[0])
            fees0 = acc.fees_paid
            acc.rebalance(target, px, ec.rules)
            info |= {"fees": acc.fees_paid - fees0, "holdings": len(acc.shares),
                     "invested_pct": 100 * (1 - acc.cash / acc.value(px))}
            rebal_rows.append(info)
            nxt = dates[k + 1] if k + 1 < len(dates) else end
            seg = daily_values(md, acc, d, nxt)
            segments.append(seg if k + 1 == len(dates) else seg.iloc[:-1])
        series = pd.concat(segments)
        daily[name] = series
        rows = [r for r in rebal_rows if r["strategy"] == name]
        perf[name] = performance(series, md.index) | {
            "family": family, "fees_vnd": acc.fees_paid, "turnover_x": acc.traded_value / cfg.capital_vnd,
            "avg_holdings": float(np.mean([r["holdings"] for r in rows])),
            "avg_invested_pct": float(np.mean([r["invested_pct"] for r in rows]))}
        _log(f"  {name:42s} TE={perf[name]['tracking_error_ann_pct']:.2f}%  active={perf[name]['active_return_ann_pct']:+.2f}%")
    vals = pd.DataFrame(daily)
    vals["VN30 index (scaled)"] = md.index.loc[vals.index] / md.index.loc[vals.index[0]] * cfg.capital_vnd
    vals.to_csv(out / "daily_values.csv")
    pd.DataFrame(rebal_rows).to_csv(out / "rebalances.csv", index=False)
    pd.DataFrame(perf).T.to_csv(out / "strategy_performance.csv")

    # ------------------------------------------------------------ Stage D: quantum diagnostics on unseen dates
    _log("Stage D: frozen designs on unseen dates")
    rows = []
    for k, d in enumerate(dates):
        if d in train_dates:
            continue
        inst, land = diag_instances[d]
        cp = CompiledProblem(inst, land)
        nb = inst.meta["nearest_bits"]
        near_idx = int((nb * (2 ** np.arange(len(nb)))).sum())
        base = {"date": str(d.date()), "n_qubits": cp.n, "uniform_success": uniform_reference(cp, cfg.success_gap),
                "nearest_rounding_gap": float(land.gap()[near_idx]),
                "floor_gap": float(land.gap()[0]),
                "te_exact_pct": float(100 * inst.tracking_error(inst.weights((land.opt_index >> np.arange(cp.n)) & 1))[0]),
                "te_nearest_pct": float(100 * inst.tracking_error(inst.weights(nb))[0]),
                "te_continuous_pct": float(100 * inst.tracking_error(inst.meta["continuous_weights"])[0])}
        sa_idx, sa_evals = simulated_annealing(inst, land, seed=k)
        base |= {"sa_gap": float(land.gap()[sa_idx]) if sa_idx is not None else np.inf, "sa_flips": sa_evals}
        for arm, b in best_specs.items():
            r = run_qaoa(cp, b.spec, cfg.success_gap, sc.shots, np.random.default_rng(sc.seed + 100 + k))
            rows.append(base | {"arm": arm, "success_prob": r.success_prob, "feasible_mass": r.feasible_mass,
                                "mean_gap": r.mean_gap, "best_sample_gap": r.best_sample_gap,
                                "p_hit_in_shots": 1 - (1 - r.success_prob) ** sc.shots,
                                "evaluations": r.evaluations, "two_qubit_gates": r.two_qubit_gates})
    pd.DataFrame(rows).to_csv(out / "quantum_test.csv", index=False)

    # latest recommendation (the decision a user would act on today)
    last = dates[-1]
    inst, land = diag_instances[last]
    _export_latest(out, inst, land, best_specs, sc, cfg)

    manifest = {"run_seconds": round(time.time() - t_start, 1), "dates": [str(d.date()) for d in dates],
                "train_dates": [str(d.date()) for d in train_dates], "design_arms": arms,
                "llm_backend": None if llm is None else llm.backend,
                "llm_model": None if llm is None else llm.model,
                "llm_calls": 0 if llm is None else sum(1 for _ in open(llm.log_path))}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    _log(f"done in {manifest['run_seconds']:.0f}s -> {out}")
    return manifest


def _export_latest(out: Path, inst, land, best_specs, sc, cfg) -> None:
    from .quantum.export import build_circuit, resource_report, to_qasm

    circ_dir = out / "circuits"
    circ_dir.mkdir(exist_ok=True)
    cp = CompiledProblem(inst, land)
    rep = {}
    for arm, b in best_specs.items():
        r = run_qaoa(cp, b.spec, cfg.success_gap, sc.shots, np.random.default_rng(sc.seed))
        try:
            qc = build_circuit(cp, b.spec, r.angles)
            (circ_dir / f"{arm}_{inst.date}.qasm").write_text(to_qasm(qc))
            rep[arm] = resource_report(qc) | {"spec": b.spec.to_dict(), "angles": r.angles.round(4).tolist()}
        except ImportError:
            rep[arm] = {"note": "qiskit not installed; circuit not exported"}
    (circ_dir / "resources.json").write_text(json.dumps(rep, indent=2))
    x = ((land.opt_index >> np.arange(inst.n_qubits)) & 1)
    sh = inst.shares(x)[0]
    pd.DataFrame({"ticker": inst.tickers, "price_vnd": inst.prices, "current_shares": inst.prev_shares,
                  "target_shares": sh, "trade_shares": sh - inst.prev_shares,
                  "target_value_vnd": sh * inst.prices}).to_csv(out / "latest_trades.csv", index=False)
