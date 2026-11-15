"""End-to-end experiment: data insight -> insight-driven circuit -> walk-forward backtest.

Stage A  Data           : point-in-time universe per quarter, coverage, ETF availability
Stage B  Calibration    : budget penalty and the designed circuit's schedule, on the training quarters
                          only (2023); controls: textbook QAOA and random search (3 seeds)
Stage C  Walk-forward   : every strategy runs its own account with whole lots, fees and tax, against the
                          VN30 index and the investable VN30 ETFs
Stage D  Quantum test   : on every later quarter, the frozen circuits vs random guessing, warm start
                          alone, simulated annealing and exact enumeration; plus the data insight and
                          the data-to-circuit "design card" of each quarter
"""

from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import (Account, build_rounding_instance, daily_values, equal_weight_target, etf_buy_and_hold,
                       performance, qp_round_target)
from .classical import simulated_annealing
from .config import ExperimentConfig
from .data import MarketData, coverage_table
from .insight import hamiltonian_insight, market_insight
from .portfolio import landscape
from .quantum.design import calibrate, design_card, designed_spec
from .quantum.search import Evaluator, best, random_search
from .quantum.simulator import CompiledProblem, run_qaoa, uniform_reference, warm_start_only
from .quantum.spec import DEFAULT_SPEC

PRIMARY_ETF = "E1VFVN30"          # largest VN30 ETF; used for the "vs ETF" columns
RANDOM_SEEDS = (7, 8, 9)

# name -> optimiser:  "nearest" | "equal" | "exact" | "qaoa:<arm>"
STRATEGIES = {
    "QP + nearest-lot rounding (practitioner)": "nearest",
    "Equal weight 1/N, whole lots": "equal",
    "QP + exact lot rounding (classical reference)": "exact",
    "QP + textbook QAOA": "qaoa:textbook",
    "AGQO: QP + insight-designed QAOA": "qaoa:designed",
}
REFERENCE = "QP + exact lot rounding (classical reference)"
AGQO = "AGQO: QP + insight-designed QAOA"


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def _bits(idx: int, n: int) -> np.ndarray:
    return (idx >> np.arange(n)) & 1


def _calibrate_penalty(md, dates, universes, ec) -> tuple[float, list[dict]]:
    """Smallest budget penalty whose QUBO ground state is the affordable near-optimum on training quarters."""
    cfg, rows = ec.problem, []
    for lam in ec.design.penalty_grid:
        e = dataclasses.replace(ec, problem=dataclasses.replace(cfg, budget_penalty=lam))
        hits, gaps = 0, []
        for d in dates:
            inst = build_rounding_instance(md, d, universes[d], {}, Account(cash=cfg.capital_vnd), e)
            land = landscape(inst)
            g = float(land.gap()[int(np.argmin(land.energy))])
            gaps.append(g)
            hits += int(np.isfinite(g) and g <= cfg.success_gap)
        rows.append({"budget_penalty": lam, "ground_state_near_optimal": hits / len(dates),
                     "mean_ground_state_gap": float(np.mean(np.where(np.isfinite(gaps), gaps, 10)))})
    best_row = max(rows, key=lambda r: (r["ground_state_near_optimal"], -r["mean_ground_state_gap"], -r["budget_penalty"]))
    return best_row["budget_penalty"], rows


def run(out: Path, ec: ExperimentConfig = ExperimentConfig()) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    md = MarketData.load()
    cfg, sc, dc = ec.problem, ec.search, ec.design
    dates = md.rebalance_dates(ec.first_rebalance, ec.last_rebalance)
    universes, excluded = {}, {}
    for d in dates:
        universes[d], excluded[d] = md.universe(d, cfg.lookback_days, cfg.min_history)
    coverage_table(md, dates, cfg.lookback_days, cfg.min_history).to_csv(out / "coverage.csv", index=False)
    train_dates = dates[: sc.train_dates]

    # ------------------------------------------------------------ Stage B: calibration on training quarters
    _log(f"Stage B: calibration on {len(train_dates)} training quarters "
         f"({train_dates[0].date()}..{train_dates[-1].date()})")
    lam, pen_rows = _calibrate_penalty(md, train_dates, universes, ec)
    ec = dataclasses.replace(ec, problem=dataclasses.replace(cfg, budget_penalty=lam))
    cfg = ec.problem
    (out / "config.json").write_text(json.dumps(ec.to_dict(), indent=2))
    pd.DataFrame(pen_rows).to_csv(out / "penalty_calibration.csv", index=False)
    _log(f"  budget penalty = {lam}")
    train = []
    for d in train_dates:
        inst = build_rounding_instance(md, d, universes[d], {}, Account(cash=cfg.capital_vnd), ec)
        train.append(CompiledProblem(inst, landscape(inst)))
    t0 = time.time()
    designed, grid = calibrate(train, dc, cfg.success_gap, sc.cx_budget)
    grid.to_csv(out / "design_calibration.csv", index=False)
    refined = designed_spec(designed.layers, designed.warm_start_epsilon, designed.ramp_dt, designed.ramp_dbeta,
                            dc.coupling_mass, dc.refine_iters, dc.refine_cvar_alpha)
    _log(f"  designed circuit: p={designed.layers} eps={designed.warm_start_epsilon} dgamma={designed.ramp_dt} "
         f"dbeta={designed.ramp_dbeta} ({len(grid)} schedules, {time.time() - t0:.0f}s)")
    ev = Evaluator(train, sc.cx_budget, cfg.success_gap, sc.shots, sc.seed)
    history = [ev(DEFAULT_SPEC, "textbook", 0)]
    specs = {"textbook": DEFAULT_SPEC, "designed": designed, "designed_refined": refined}
    for s in RANDOM_SEEDS:
        t0 = time.time()
        h = random_search(ev, sc.rounds * sc.proposals_per_round, seed=s, arm=f"random_s{s}")
        history += h
        specs[f"random_s{s}"] = best(h).spec
        _log(f"  random search seed {s}: best train success {best(h).fitness:.4f} ({time.time() - t0:.0f}s)")
    pd.DataFrame([h.row() for h in history]).to_csv(out / "circuit_search.csv", index=False)
    (out / "specs.json").write_text(json.dumps({k: v.to_dict() for k, v in specs.items()}, indent=2))

    # ------------------------------------------------------------ Stage C: walk-forward
    _log("Stage C: walk-forward backtest")
    end = md.index.index[-1]
    etf = md.etf_close[PRIMARY_ETF] if PRIMARY_ETF in md.etf_close else None
    daily, rebal_rows, perf, ref_inst, agqo_inst = {}, [], {}, {}, {}
    for name, opt in STRATEGIES.items():
        acc = Account(cash=cfg.capital_vnd)
        segments = []
        for k, d in enumerate(dates):
            px = md.px.loc[d]
            info = {"strategy": name, "date": str(d.date()), "nav_pre": acc.value(px)}
            if opt == "nearest":
                target = qp_round_target(md, d, universes[d], acc, ec)
            elif opt == "equal":
                target = equal_weight_target(md, d, universes[d], acc, ec)
            else:
                inst = build_rounding_instance(md, d, universes[d], {}, acc, ec)
                land = landscape(inst)
                if opt == "exact":
                    idx = land.opt_index
                    ref_inst[d] = (inst, land)
                else:
                    cp = CompiledProblem(inst, land)
                    res = run_qaoa(cp, specs[opt.split(":")[1]], cfg.success_gap, sc.shots,
                                   np.random.default_rng(sc.seed + k))
                    idx = res.best_sample
                    info |= {"qaoa_success": res.success_prob, "qaoa_best_gap": res.best_sample_gap}
                    if name == AGQO:
                        agqo_inst[d] = (inst, land, idx)
                if idx is None:
                    target = dict(acc.shares)
                    info["fallback"] = "no affordable sample: holdings kept"
                else:
                    x = _bits(idx, inst.n_qubits)
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
        perf[name] = performance(series, md.index, etf) | {
            "fees_vnd": acc.fees_paid, "turnover_x": acc.traded_value / cfg.capital_vnd,
            "avg_holdings": float(np.mean([r["holdings"] for r in rows])),
            "avg_invested_pct": float(np.mean([r["invested_pct"] for r in rows]))}
        _log(f"  {name:46s} TE={perf[name]['tracking_error_ann_pct']:.2f}%  "
             f"vs ETF {perf[name].get('excess_return_vs_etf_ann_pct', float('nan')):+.2f}%/yr")
    for t in md.etf_close.columns:
        series, fee = etf_buy_and_hold(md, t, dates[0], end, ec)
        name = f"ETF buy-and-hold: {t}"
        daily[name] = series
        perf[name] = performance(series, md.index, etf) | {"fees_vnd": fee, "turnover_x": np.nan,
                                                           "avg_holdings": 1.0, "avg_invested_pct": np.nan}
        _log(f"  {name:46s} TE={perf[name]['tracking_error_ann_pct']:.2f}%")
    vals = pd.DataFrame(daily)
    vals["VN30 index (scaled)"] = md.index.loc[vals.index] / md.index.loc[vals.index[0]] * cfg.capital_vnd
    vals.to_csv(out / "daily_values.csv")
    pd.DataFrame(rebal_rows).to_csv(out / "rebalances.csv", index=False)
    pd.DataFrame(perf).T.to_csv(out / "strategy_performance.csv")

    # ------------------------------------------------------------ Stage D: quantum test + insight on unseen quarters
    _log("Stage D: frozen circuits on unseen quarters")
    rows, insights, cards = [], [], []
    for k, d in enumerate(dates):
        inst, land = ref_inst[d]
        cp = CompiledProblem(inst, land)
        inst.meta["relaxed"] = cp.relaxed
        hi = hamiltonian_insight(cp, cfg.success_gap)
        mi = market_insight(md, inst, land, excluded[d], cfg.lookback_days)
        insights.append({"split": "train" if d in train_dates else "test"} | mi.to_dict() | {"hamiltonian": hi.to_dict()})
        cards.append(design_card(cp, designed, hi))
        if d in train_dates:
            continue
        rng = lambda off: np.random.default_rng(sc.seed + 100 + k + off)
        base = {"date": str(d.date()), "n_qubits": cp.n, "uniform_success": uniform_reference(cp, cfg.success_gap),
                "nearest_rounding_gap": hi.nearest_rounding_gap, "near_optimal_states": hi.near_optimal_states,
                "te_exact_pct": mi.te_exact_pct, "te_nearest_pct": mi.te_nearest_pct,
                "te_continuous_pct": mi.te_continuous_pct}
        sa_idx, sa_evals = simulated_annealing(inst, land, seed=k)
        base |= {"sa_gap": float(land.gap()[sa_idx]) if sa_idx is not None else np.inf, "sa_flips": sa_evals}
        results = {"warm_start_only": warm_start_only(cp, designed.warm_start_epsilon, cfg.success_gap, sc.shots, rng(0))}
        for arm, spec in specs.items():
            results[arm] = run_qaoa(cp, spec, cfg.success_gap, sc.shots, rng(1))
        for arm, r in results.items():
            rows.append(base | {"arm": arm, "success_prob": r.success_prob, "better_than_rounding": r.better_than_ref,
                                "feasible_mass": r.feasible_mass, "mean_gap": r.mean_gap,
                                "best_sample_gap": r.best_sample_gap,
                                "p_hit_in_shots": 1 - (1 - r.success_prob) ** sc.shots,
                                "evaluations": r.evaluations, "two_qubit_gates": r.two_qubit_gates})
    pd.DataFrame(rows).to_csv(out / "quantum_test.csv", index=False)
    (out / "insight.json").write_text(json.dumps(insights, indent=1, ensure_ascii=False, default=float))
    (out / "design_cards.json").write_text(json.dumps(cards, indent=1, ensure_ascii=False, default=float))

    _export_latest(out, *agqo_inst[dates[-1]], specs, sc, cfg)
    manifest = {"run_seconds": round(time.time() - t_start, 1), "dates": [str(d.date()) for d in dates],
                "train_dates": [str(d.date()) for d in train_dates], "budget_penalty": lam,
                "designed_spec": designed.to_dict(), "primary_etf": PRIMARY_ETF,
                "data_manifest_sha256": json.loads((Path(__file__).resolve().parent.parent / "data" / "vn30" /
                                                    "manifest.json").read_text()).get("sha256")}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    _log(f"done in {manifest['run_seconds']:.0f}s -> {out}")
    return manifest


def _export_latest(out: Path, inst, land, idx, specs, sc, cfg) -> None:
    """The decision a user would act on today (AGQO account), plus hardware-ready circuits."""
    from .quantum.export import build_circuit, resource_report, to_qasm

    circ_dir = out / "circuits"
    circ_dir.mkdir(exist_ok=True)
    cp = CompiledProblem(inst, land)
    rep = {}
    for arm in ("textbook", "designed"):
        r = run_qaoa(cp, specs[arm], cfg.success_gap, sc.shots, np.random.default_rng(sc.seed))
        try:
            qc = build_circuit(cp, specs[arm], r.angles)
            (circ_dir / f"{arm}_{inst.date}.qasm").write_text(to_qasm(qc))
            rep[arm] = resource_report(qc) | {"spec": specs[arm].to_dict(), "angles": r.angles.round(4).tolist()}
        except ImportError:
            rep[arm] = {"note": "qiskit not installed; circuit not exported"}
    (circ_dir / "resources.json").write_text(json.dumps(rep, indent=2))
    x = _bits(idx if idx is not None else land.opt_index, inst.n_qubits)
    sh = inst.shares(x)[0]
    pd.DataFrame({"ticker": inst.tickers, "price_vnd": inst.prices, "current_shares": inst.prev_shares,
                  "target_shares": sh, "trade_shares": sh - inst.prev_shares,
                  "target_value_vnd": sh * inst.prices}).to_csv(out / "latest_trades.csv", index=False)
