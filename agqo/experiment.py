"""End-to-end AGQO experiment. Training = 2023 only; every reported result is from 2024 onward.

Stage A  Training instances : first trading day of each 2023 month x 4 account sizes (48 problems);
                              budget penalty calibrated on them
Stage B  AI guidance        : every LR-QAOA schedule scored on every training problem; k-NN schedule
                              model over insight features, k by leave-one-month-out CV; controls:
                              textbook QAOA and random search over the whole design space (3 seeds)
Stage C  Walk-forward       : quarterly 2024-01 .. 2026-10, 100M VND, five strategies + three ETFs,
                              block-bootstrap intervals for tracking-error differences
Stage D  Quantum test       : on the same 12 quarters, AGQO's circuit vs warm start alone, textbook QAOA,
                              random search, the frozen schedule, an oracle schedule, simulated
                              annealing and exact enumeration; paired Wilcoxon tests
Stage E  Account sizes      : 20M .. 500M VND, AGQO vs practitioner rounding vs exact
Stage F  Personal mandates  : three investor instructions compiled by the LLM (or gold labels offline)
Stage G  Evidence           : per-quarter insight, design cards, explanation evidence, latest trades, QASM
"""

from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import (Account, active_returns, build_rounding_instance, daily_values, equal_weight_target,
                       etf_buy_and_hold, performance, practitioner_target)
from .classical import simulated_annealing
from .config import ExperimentConfig
from .data import MarketData, coverage_table
from .insight import hamiltonian_insight, market_insight
from .llm.tasks import DEMO
from .mandate import Mandate
from .portfolio import landscape
from .quantum.design import (ScheduleModel, cross_validate, design_card, design_features, polish_check,
                             schedule_grid, spec_of, success_table)
from .quantum.search import Evaluator, best, random_search
from .quantum.simulator import CompiledProblem, run_qaoa, uniform_reference, warm_start_only
from .quantum.spec import DEFAULT_SPEC
from .stats import block_bootstrap_te_diff, paired_test

AGQO = "AGQO: AI-guided QAOA rounding"
PRACT = "Practitioner: nearest-lot rounding"
EXACT = "Exact lot rounding (classical reference)"
TEXTBOOK = "Textbook QAOA rounding"
EQUAL = "Equal weight 1/N, whole lots"


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def _bits(idx: int, n: int) -> np.ndarray:
    return (idx >> np.arange(n)) & 1


class Guide:
    """The AI guidance: insight features -> schedule (k-NN) -> polished circuit."""

    def __init__(self, grid: pd.DataFrame, model: ScheduleModel, dc, use_polish: bool):
        self.grid, self.model, self.dc, self.use_polish = grid, model, dc, use_polish

    def row(self, cp: CompiledProblem) -> pd.Series:
        return self.grid.iloc[self.model.choose(design_features(cp))]

    def spec(self, cp: CompiledProblem, polish: bool | None = None):
        polish = self.use_polish if polish is None else polish
        return spec_of(self.row(cp), self.dc.polish_iters if polish else 0, self.dc.polish_cvar_alpha, "AGQO:")


def walk(md: MarketData, ec: ExperimentConfig, dates: list, capital: float, decide) -> tuple[pd.Series, list, Account]:
    """One account through the quarterly dates; `decide(date, k, account) -> (target shares, info)`."""
    acc, segs, rows = Account(cash=capital), [], []
    end = md.index.index[-1]
    for k, d in enumerate(dates):
        px = md.px.loc[d]
        nav = acc.value(px)
        target, info = decide(d, k, acc)
        fees0 = acc.fees_paid
        acc.rebalance(target, px, ec.rules)
        post = acc.value(px)
        rows.append({"date": str(d.date()), "nav_pre": nav, "fees": acc.fees_paid - fees0, "holdings": len(acc.shares),
                     "invested_pct": 100 * (1 - acc.cash / post),
                     "_weights": {t: s * px[t] / nav for t, s in acc.shares.items()}} | info)  # vs NAV at decision
        nxt = dates[k + 1] if k + 1 < len(dates) else end
        seg = daily_values(md, acc, d, nxt)
        segs.append(seg if k + 1 == len(dates) else seg.iloc[:-1])
    return pd.concat(segs), rows, acc


def run(out: Path, ec: ExperimentConfig = ExperimentConfig()) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    md = MarketData.load()
    cfg, dc, sc = ec.problem, ec.design, ec.search
    _uni: dict = {}

    def uni(d):
        if d not in _uni:
            _uni[d] = md.universe(d, cfg.lookback_days, cfg.min_history)
        return _uni[d]

    train_dates = md.rebalance_dates(ec.train_start, ec.train_end, "MS")
    test_dates = md.rebalance_dates(ec.test_start, ec.test_end, "QS")
    coverage_table(md, test_dates, cfg.lookback_days, cfg.min_history).to_csv(out / "coverage.csv", index=False)

    # ------------------------------------------------------------ Stage A: training problems, budget penalty
    _log(f"Stage A: {len(train_dates)} training months x {len(dc.train_sizes)} account sizes")
    pen = []
    for lam in dc.penalty_grid:
        e = dataclasses.replace(ec, problem=dataclasses.replace(cfg, budget_penalty=lam))
        gaps = []
        for d in train_dates:
            for size in dc.train_sizes:
                land = landscape(build_rounding_instance(md, d, uni(d)[0], Account(cash=size), e))
                gaps.append(float(land.gap()[int(np.argmin(land.energy))]))
        g = np.array(gaps)
        pen.append({"budget_penalty": lam, "ground_state_near_optimal": float((g <= cfg.success_gap).mean()),
                    "mean_ground_state_gap": float(np.where(np.isfinite(g), g, 10).mean())})
    lam = max(pen, key=lambda r: (r["ground_state_near_optimal"], -r["mean_ground_state_gap"], r["budget_penalty"]))
    ec = dataclasses.replace(ec, problem=dataclasses.replace(cfg, budget_penalty=lam["budget_penalty"]))
    cfg = ec.problem
    pd.DataFrame(pen).to_csv(out / "penalty_calibration.csv", index=False)
    (out / "config.json").write_text(json.dumps(ec.to_dict(), indent=2))
    _log(f"  budget penalty = {cfg.budget_penalty}")
    train, meta = [], []
    for d in train_dates:
        for size in dc.train_sizes:
            inst = build_rounding_instance(md, d, uni(d)[0], Account(cash=size), ec)
            cp = CompiledProblem(inst, landscape(inst))
            train.append(cp)
            meta.append({"date": str(d.date()), "month": d.month, "capital_vnd": size} | design_features(cp))
    feats = pd.DataFrame(meta)

    # ------------------------------------------------------------ Stage B: AI guidance
    grid = schedule_grid(dc)
    t0 = time.time()
    table = success_table(train, grid, cfg.success_gap, dc.cx_budget, dc.workers)
    _log(f"  scored {len(grid)} schedules x {len(train)} problems ({time.time() - t0:.0f}s)")
    grid_out = grid.assign(train_success=table.clip(min=0).mean(0), over_budget=(table < 0).any(0))
    grid_out.to_csv(out / "schedule_grid.csv", index=False)
    feats.to_csv(out / "train_features.csv", index=False)
    cv = cross_validate(feats, table, feats.month.to_numpy(), dc.knn_grid)
    cv.to_csv(out / "schedule_cv.csv", index=False)
    best_k = int(cv.sort_values(["cv_success", "k"], ascending=[False, True]).iloc[0].k)
    frozen_cv = float(cv[cv.k == 0].cv_success.iloc[0])
    model = ScheduleModel.fit(feats, table, best_k)
    frozen = ScheduleModel.fit(feats, table, 0)
    frozen_row = grid.iloc[frozen.choose({})]
    _log(f"  schedule model: k={best_k or 'all'} (CV success {cv.cv_success.max():.4f} vs frozen {frozen_cv:.4f}); "
         f"frozen schedule {frozen_row.to_dict()}")
    polish = polish_check(train, frozen_row, dc, cfg.success_gap)
    (out / "polish_check.json").write_text(json.dumps(polish, indent=2))
    guide = Guide(grid, model, dc, polish["use_polish"])
    _log(f"  polish on training problems: {polish['train_success_plain']:.4f} -> {polish['train_success_polished']:.4f}"
         f" ({polish['polish_wins']}/{polish['n']} wins) -> use_polish={polish['use_polish']}")
    qtrain = [cp for cp, m in zip(train, meta) if m["capital_vnd"] == 100e6 and m["month"] in (1, 4, 7, 10)]
    ev = Evaluator(qtrain, dc.cx_budget, cfg.success_gap, sc.shots, sc.seed)
    history = [ev(DEFAULT_SPEC, "textbook", 0)]
    specs = {"textbook": DEFAULT_SPEC, "frozen": spec_of(frozen_row, label="frozen:")}
    for s in sc.seeds:
        h = random_search(ev, sc.designs, s, f"random_s{s}")
        history += h
        specs[f"random_s{s}"] = best(h).spec
        _log(f"  random search seed {s}: best training success {best(h).fitness:.4f}")
    pd.DataFrame([h.row() for h in history]).to_csv(out / "circuit_search.csv", index=False)
    (out / "specs.json").write_text(json.dumps({k: v.to_dict() for k, v in specs.items()}, indent=2))

    # ------------------------------------------------------------ strategies
    rng = lambda k, off=0: np.random.default_rng(sc.seed + 1000 * off + k)

    def qaoa_decider(spec_fn, mandate=None, record=None):
        def decide(d, k, acc):
            inst = build_rounding_instance(md, d, uni(d)[0], acc, ec, mandate)
            land = landscape(inst)
            cp = CompiledProblem(inst, land)
            spec = spec_fn(cp)
            r = run_qaoa(cp, spec, cfg.success_gap, sc.shots, rng(k))
            info = {"qaoa_success": r.success_prob, "qaoa_best_gap": r.best_sample_gap, "layers": spec.layers,
                    "cx": r.two_qubit_gates}
            if record is not None:
                record[d] = (inst, land, cp, spec, r)
            idx = r.best_sample
            if idx is None:                       # no sample passed the exact checks: floor rounding is always
                if not land.feasible[0]:          # inside every cap; keep holdings only if even that fails
                    return dict(acc.shares), info | {"fallback": "holdings kept"}
                idx, info = 0, info | {"fallback": "floor rounding"}
            x = _bits(idx, inst.n_qubits)
            return dict(zip(inst.tickers, inst.shares(x)[0])), info | {
                "gap_vs_exact": float(land.gap()[idx]),
                "ex_ante_te_pct": float(100 * inst.tracking_error(inst.weights(x))[0])}
        return decide

    def exact_decider(mandate=None, record=None):
        def decide(d, k, acc):
            inst = build_rounding_instance(md, d, uni(d)[0], acc, ec, mandate)
            land = landscape(inst)
            if record is not None:
                record[d] = (inst, land)
            x = _bits(land.opt_index, inst.n_qubits)
            return dict(zip(inst.tickers, inst.shares(x)[0])), {
                "ex_ante_te_pct": float(100 * inst.tracking_error(inst.weights(x))[0])}
        return decide

    pract = lambda mandate=None: (lambda d, k, acc: (practitioner_target(md, d, uni(d)[0], acc, ec, mandate), {}))
    equal = lambda d, k, acc: (equal_weight_target(md, d, uni(d)[0], acc, ec), {})

    # ------------------------------------------------------------ Stage C: walk-forward at 100M VND
    _log(f"Stage C: walk-forward {test_dates[0].date()} .. {md.index.index[-1].date()} at 100M VND")
    etf = md.etf_close[ec.primary_etf]
    agqo_rec, ref_rec = {}, {}
    deciders = {PRACT: pract(), EQUAL: equal, EXACT: exact_decider(record=ref_rec),
                TEXTBOOK: qaoa_decider(lambda cp: DEFAULT_SPEC), AGQO: qaoa_decider(guide.spec, record=agqo_rec)}
    daily, perf, rebal = {}, {}, []
    for name, dec in deciders.items():
        series, rows, acc = walk(md, ec, test_dates, cfg.capital_vnd, dec)
        daily[name] = series
        rebal += [r | {"strategy": name} for r in rows]
        perf[name] = performance(series, md.index, etf) | {
            "fees_vnd": acc.fees_paid, "turnover_x": acc.traded_value / cfg.capital_vnd,
            "avg_holdings": float(np.mean([r["holdings"] for r in rows])),
            "avg_invested_pct": float(np.mean([r["invested_pct"] for r in rows]))}
        _log(f"  {name:44s} TE {perf[name]['tracking_error_ann_pct']:.2f}%  "
             f"vs ETF {perf[name]['excess_return_vs_etf_ann_pct']:+.2f}%/yr")
    for t in md.etf_close.columns:
        series, fee = etf_buy_and_hold(md, t, test_dates[0], md.index.index[-1], ec)
        daily[f"ETF {t}"] = series
        perf[f"ETF {t}"] = performance(series, md.index, etf) | {"fees_vnd": fee, "avg_holdings": 1.0}
    vals = pd.DataFrame(daily)
    vals["VN30 index (scaled)"] = md.index.loc[vals.index] / md.index.loc[vals.index[0]] * cfg.capital_vnd
    vals.to_csv(out / "daily_values.csv")
    pd.DataFrame(rebal).drop(columns="_weights").to_csv(out / "rebalances.csv", index=False)
    pd.DataFrame(perf).T.to_csv(out / "strategy_performance.csv")
    act = {k: active_returns(v, md.index) for k, v in daily.items()}
    te_ci = {f"{a} vs {b}": block_bootstrap_te_diff(act[a], act[b])
             for a, b in [(AGQO, PRACT), (EXACT, PRACT), (AGQO, EXACT), (AGQO, TEXTBOOK), (AGQO, EQUAL)]}

    # ------------------------------------------------------------ Stage D: quantum test on the same quarters
    _log("Stage D: circuits on the 12 test quarters (reference account)")
    test_cps = [CompiledProblem(*ref_rec[d]) for d in test_dates]
    test_table = success_table(test_cps, grid, cfg.success_gap, dc.cx_budget, dc.workers)
    qrows, insights, cards = [], [], []
    for k, (d, cp) in enumerate(zip(test_dates, test_cps)):
        inst, land = cp.inst, cp.land
        inst.meta["relaxed"] = cp.relaxed
        f = design_features(cp)
        hi = hamiltonian_insight(cp, cfg.success_gap)
        mi = market_insight(md, inst, land, uni(d)[1], cfg.lookback_days)
        chosen = guide.row(cp)
        insights.append(mi.to_dict() | {"hamiltonian": hi.to_dict(), "features": f,
                                        "chosen_schedule": chosen.to_dict()})
        cards.append(design_card(cp, guide.spec(cp), f))
        arms = {"warm_start_only": warm_start_only(cp, float(chosen.epsilon), cfg.success_gap, sc.shots, rng(k, 2)),
                "textbook": run_qaoa(cp, DEFAULT_SPEC, cfg.success_gap, sc.shots, rng(k, 2)),
                "frozen": run_qaoa(cp, specs["frozen"], cfg.success_gap, sc.shots, rng(k, 2)),
                "agqo": run_qaoa(cp, guide.spec(cp), cfg.success_gap, sc.shots, rng(k, 2)),
                "polish_ablation": run_qaoa(cp, guide.spec(cp, polish=not guide.use_polish), cfg.success_gap,
                                            sc.shots, rng(k, 2)),
                "oracle": run_qaoa(cp, spec_of(grid.iloc[int(np.argmax(test_table[k]))]), cfg.success_gap,
                                   sc.shots, rng(k, 2))}
        for s in sc.seeds:
            arms[f"random_s{s}"] = run_qaoa(cp, specs[f"random_s{s}"], cfg.success_gap, sc.shots, rng(k, 2))
        sa_idx, sa_evals = simulated_annealing(inst, land, seed=k)
        base = {"date": str(d.date()), "uniform_success": uniform_reference(cp, cfg.success_gap),
                "near_optimal_states": hi.near_optimal_states, "nearest_rounding_gap": hi.nearest_rounding_gap,
                "sa_gap": float(land.gap()[sa_idx]) if sa_idx is not None else np.inf, "sa_flips": sa_evals}
        for arm, r in arms.items():
            qrows.append(base | {"arm": arm, "success_prob": r.success_prob, "better_than_rounding": r.better_than_ref,
                                 "feasible_mass": r.feasible_mass, "best_sample_gap": r.best_sample_gap,
                                 "p_hit_in_shots": 1 - (1 - r.success_prob) ** sc.shots,
                                 "evaluations": r.evaluations, "two_qubit_gates": r.two_qubit_gates,
                                 "layers": r.spec.layers if r.spec else 0})
    q = pd.DataFrame(qrows)
    q.to_csv(out / "quantum_test.csv", index=False)
    piv = q.pivot(index="date", columns="arm", values="success_prob")
    piv["random"] = piv[[f"random_s{s}" for s in sc.seeds]].mean(1)
    bpiv = q.pivot(index="date", columns="arm", values="better_than_rounding")
    bpiv["random"] = bpiv[[f"random_s{s}" for s in sc.seeds]].mean(1)
    qstats = {f"agqo vs {b}": paired_test(piv.agqo, piv[b]) for b in
              ["warm_start_only", "textbook", "random", "frozen", "polish_ablation"]}
    qstats["agqo vs uniform"] = paired_test(piv.agqo, q.groupby("date").uniform_success.first())
    qstats["better-than-rounding: agqo vs warm_start_only"] = paired_test(bpiv.agqo, bpiv.warm_start_only)
    (out / "quantum_stats.json").write_text(json.dumps(qstats, indent=2))
    (out / "insight.json").write_text(json.dumps(insights, indent=1, ensure_ascii=False, default=float))
    (out / "design_cards.json").write_text(json.dumps(cards, indent=1, ensure_ascii=False, default=float))

    # ------------------------------------------------------------ Stage E: account sizes
    _log("Stage E: account-size sweep")
    sweep, sweep_ci = [], {}
    for size in ec.sweep_sizes:
        ser = {}
        for name, dec in [(PRACT, pract()), (EXACT, exact_decider()), (AGQO, qaoa_decider(guide.spec))]:
            ser[name], rows, acc = walk(md, ec, test_dates, size, dec)
            sweep.append({"capital_vnd": size, "strategy": name, "fees_vnd": acc.fees_paid,
                          "avg_holdings": float(np.mean([r["holdings"] for r in rows])),
                          "avg_invested_pct": float(np.mean([r["invested_pct"] for r in rows]))}
                         | performance(ser[name], md.index, etf))
        sweep_ci[str(int(size))] = block_bootstrap_te_diff(active_returns(ser[AGQO], md.index),
                                                           active_returns(ser[PRACT], md.index))
        _log(f"  {size / 1e6:5.0f}M  TE agqo {sweep_ci[str(int(size))]['te_a']:.2f}%  "
             f"practitioner {sweep_ci[str(int(size))]['te_b']:.2f}%")
    pd.DataFrame(sweep).to_csv(out / "sweep.csv", index=False)

    # ------------------------------------------------------------ Stage F: personal mandates
    _log("Stage F: personal mandates")
    llm_file = out / "llm" / "mandate_eval.json"
    demo = []
    if llm_file.exists():
        rows = {r["instruction"]: r for r in json.loads(llm_file.read_text())["rows"]}
        for text, gold, _ in DEMO:
            r = rows.get(text)
            ok = r is not None and "llm" in r and not r["llm_errors"]
            demo.append((text, Mandate.from_dict(r["llm"]) if ok else gold, "LLM" if ok else "gold (LLM failed)"))
    else:
        demo = [(text, gold, "gold (LLM not run)") for text, gold, _ in DEMO]
    mand_rows = []
    base_te = perf[AGQO]["tracking_error_ann_pct"]
    for text, m, src in [("(none)", Mandate(), "-")] + demo:
        for name, dec in [(AGQO, qaoa_decider(guide.spec, m)), (PRACT, pract(m))]:
            series, rows, acc = walk(md, ec, test_dates, cfg.capital_vnd, dec)
            comp = _compliance(md, test_dates, series, rows, acc, m)
            p = performance(series, md.index, etf)
            mand_rows.append({"instruction": text, "source": src, "strategy": name, "mandate": json.dumps(m.to_dict(),
                              ensure_ascii=False), "te_cost_vs_unconstrained_pp": p["tracking_error_ann_pct"] - base_te,
                              "avg_holdings": float(np.mean([r["holdings"] for r in rows])),
                              "fallbacks": sum("fallback" in r for r in rows),
                              "qaoa_success_mean": float(np.mean([r.get("qaoa_success", np.nan) for r in rows]))}
                             | p | comp)
    pd.DataFrame(mand_rows).to_csv(out / "mandates.csv", index=False)

    # ------------------------------------------------------------ Stage G: evidence for the explainer, latest decision
    evidence = [_evidence(md, d, agqo_rec[d], md.index, cfg) for d in test_dates]
    (out / "evidence.json").write_text(json.dumps(evidence, indent=1, ensure_ascii=False))
    _export_latest(out, agqo_rec[test_dates[-1]])
    manifest = {"run_seconds": round(time.time() - t_start, 1), "train_dates": [str(d.date()) for d in train_dates],
                "test_dates": [str(d.date()) for d in test_dates], "budget_penalty": cfg.budget_penalty,
                "schedule_model_k": best_k, "frozen_schedule": frozen_row.to_dict(), "use_polish": guide.use_polish,
                "te_ci": te_ci,
                "sweep_ci": sweep_ci, "primary_etf": ec.primary_etf,
                "data_sha256": json.loads((Path(__file__).resolve().parent.parent / "data" / "vn30" /
                                           "manifest.json").read_text()).get("sha256")}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=float))
    _log(f"done in {manifest['run_seconds']:.0f}s -> {out}")
    return manifest


def _compliance(md: MarketData, dates, series, rows, acc, m: Mandate) -> dict:
    """Did every executed portfolio respect every rule of the mandate? Checked on post-trade weights."""
    viol = []
    for r in rows:
        w = r["_weights"]
        held = set(w)
        if held & set(m.exclude_tickers) or any(md.sector(t) in m.exclude_sectors for t in held):
            viol.append(f"{r['date']}: excluded name held")
        for s_, cap in m.sector_caps.items():
            tot = sum(v for t, v in w.items() if md.sector(t) == s_)
            if tot > cap + 1e-6:
                viol.append(f"{r['date']}: {s_} {tot:.3f} > {cap}")
        if m.max_weight_per_stock is not None and max(w.values(), default=0) > m.max_weight_per_stock + 1e-6:
            viol.append(f"{r['date']}: single stock above {m.max_weight_per_stock}")
        if m.max_holdings is not None and len(held) > m.max_holdings:
            viol.append(f"{r['date']}: {len(held)} holdings")
        if m.min_cash_pct is not None and sum(w.values()) > 1 - m.min_cash_pct / 100 + 1e-6:
            viol.append(f"{r['date']}: cash below {m.min_cash_pct}%")
    return {"rule_violations_at_rebalance": len(viol), "violations": "; ".join(viol[:5])}


def _evidence(md: MarketData, d, rec, index, cfg) -> dict:
    """Code-built facts the LLM explainer may use; every number is pre-rounded."""
    inst, land, cp, spec, r = rec
    x = _bits(r.best_sample if r.best_sample is not None else land.opt_index, inst.n_qubits)
    new = inst.shares(x)[0]
    trades = []
    for t, p, a, b in zip(inst.tickers, inst.prices, inst.prev_shares, new):
        if b != a:
            trades.append({"ticker": t, "action": "mua" if b > a else "bán", "lots": int(abs(b - a) // 100),
                           "value_million_vnd": round(abs(b - a) * p / 1e6, 2)})
    trades = sorted(trades, key=lambda z: -z["value_million_vnd"])[:8]
    w = inst.weights(x)[0]
    sectors: dict[str, float] = {}
    for t, wi in zip(inst.tickers, w):
        sectors[md.sector(t)] = sectors.get(md.sector(t), 0) + wi
    nb = inst.meta["nearest_bits"]
    mi = market_insight(md, inst, land, [], cfg.lookback_days)
    return {"date": inst.date, "account_value_million_vnd": round(inst.nav / 1e6, 2),
            "stocks_held_after_trade": int((new > 0).sum()), "trades": trades,
            "tracking_error_pct": {"agqo_choice": round(float(100 * inst.tracking_error(w)[0]), 2),
                                   "nearest_lot_rounding": round(float(100 * inst.tracking_error(inst.weights(nb))[0]), 2),
                                   "ideal_fractional_shares": round(mi.te_continuous_pct, 2)},
            "sector_weights_pct": {k: round(100 * v, 1) for k, v in sorted(sectors.items(), key=lambda z: -z[1])[:4]},
            "quantum": {"qubits": inst.n_qubits, "layers": spec.layers, "two_qubit_gates": r.two_qubit_gates,
                        "near_optimal_share_of_shots_pct": round(100 * r.success_prob, 1),
                        "normalised_gap_to_exact_optimum_pct": round(100 * float(land.gap()[r.best_sample]), 2)
                        if r.best_sample is not None else None,
                        "checked_by": "exact enumeration of all 65536 lot choices"},
            "market": {"effective_independent_bets": round(mi.effective_bets, 1),
                       "market_factor_share_pct": round(100 * mi.market_factor_share, 1)}}


def _export_latest(out: Path, rec) -> None:
    """The decision a user would act on today (AGQO account) and its hardware-ready circuit."""
    from .quantum.export import build_circuit, resource_report, to_qasm

    inst, land, cp, spec, r = rec
    circ = out / "circuits"
    circ.mkdir(exist_ok=True)
    try:
        qc = build_circuit(cp, spec, r.angles)
        (circ / f"agqo_{inst.date}.qasm").write_text(to_qasm(qc))
        (circ / "resources.json").write_text(json.dumps(resource_report(qc) | {"spec": spec.to_dict(),
                                                        "angles": r.angles.round(4).tolist()}, indent=2))
    except ImportError:
        (circ / "resources.json").write_text(json.dumps({"note": "qiskit not installed"}))
    x = _bits(r.best_sample if r.best_sample is not None else land.opt_index, inst.n_qubits)
    sh = inst.shares(x)[0]
    pd.DataFrame({"ticker": inst.tickers, "price_vnd": inst.prices, "current_shares": inst.prev_shares,
                  "target_shares": sh, "trade_shares": sh - inst.prev_shares,
                  "target_value_vnd": sh * inst.prices}).to_csv(out / "latest_trades.csv", index=False)
