"""Extra studies that answer the questions judges ask (python -m agqo extras, after `run`).

  distributions - where does each circuit put its probability? (mass by solution quality)
  hardware      - what happens on a real device? transpile to an IBM Heron model (FakeKingston),
                  count native two-qubit gates, estimate success with the ESP model and check it with
                  a full Aer noise simulation of the shallow circuit
  scaling       - 8..20 qubits: classical enumeration time, circuit size, and whether the frozen
                  2023 schedule still transfers (tests rule R4)
  robustness    - finance: commission level, monthly rebalancing, odd-lot execution with a premium
  examples      - one concrete decision (lot rounding at 20M VND), the coupling matrix, timings
  llm_usage     - token counts recomputed with the model's own tokenizer

Inputs are only what `run` saved (config, chosen schedules, polish decision); nothing is re-tuned.
Results go to results/final/extras/.
"""

from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import Account, active_returns, build_rounding_instance, continuous_target, daily_values, \
    performance, practitioner_target
from .classical import simulated_annealing
from .config import DesignConfig, ExperimentConfig, MarketRules, ProblemConfig, SearchConfig
from .data import MarketData
from .portfolio import landscape
from .quantum.design import designed_spec, spec_of
from .quantum.simulator import CompiledProblem, initial_angles, initial_state, run_qaoa, statevector, \
    uniform_reference
from .quantum.spec import DEFAULT_SPEC, CircuitSpec
from .stats import block_bootstrap_te_diff

BINS = [("optimal", 0, 1e-9), ("within 5%", 1e-9, 0.05), ("5–25%", 0.05, 0.25), ("25–100%", 0.25, 1.0),
        ("worse than typical", 1.0, np.inf)]


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def load_config(run: Path) -> ExperimentConfig:
    d = json.loads((run / "config.json").read_text())
    tup = lambda x: {k: tuple(v) if isinstance(v, list) else v for k, v in x.items()}
    return ExperimentConfig(problem=ProblemConfig(**d["problem"]), design=DesignConfig(**tup(d["design"])),
                            search=SearchConfig(**tup(d["search"])), rules=MarketRules(**d["rules"]),
                            **{k: tuple(v) if isinstance(v, list) else v for k, v in d.items()
                               if k not in ("problem", "design", "search", "rules")})


def reference_problems(md, ec, dates, capital=None):
    """Instances along the exact-rounding account (the same trajectory as the quantum test in `run`)."""
    acc, out = Account(cash=capital or ec.problem.capital_vnd), []
    for d in dates:
        uni, _ = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)
        inst = build_rounding_instance(md, d, uni, acc, ec)
        land = landscape(inst)
        out.append(CompiledProblem(inst, land))
        x = (land.opt_index >> np.arange(inst.n_qubits)) & 1
        acc.rebalance(dict(zip(inst.tickers, inst.shares(x)[0])), md.px.loc[d], ec.rules)
    return out


def _agqo_spec(row: dict, man: dict, dc) -> CircuitSpec:
    return spec_of(row, dc.polish_iters if man["use_polish"] else 0, dc.polish_cvar_alpha, "AGQO:")


def _masses(cp: CompiledProblem, probs: np.ndarray) -> dict:
    gap = cp.land.gap()
    p = probs / probs.sum()
    out = {name: float(p[np.isfinite(gap) & (gap >= lo) & (gap < hi) if lo > 0 else (gap <= hi)].sum())
           for name, lo, hi in BINS}
    out["over budget"] = float(p[~np.isfinite(gap)].sum())
    return out


# ------------------------------------------------------------------ 1. distributions
def distributions(cps, insight, man, ec) -> pd.DataFrame:
    rows = []
    for k, cp in enumerate(cps):
        row = insight[k]["chosen_schedule"]
        arms = {"random guessing": np.full(2 ** cp.n, 1.0),
                "warm start only": np.abs(initial_state(cp, CircuitSpec(initial_state="warm_start",
                                                                        warm_start_epsilon=row["epsilon"]))) ** 2,
                "textbook QAOA": run_qaoa(cp, DEFAULT_SPEC, ec.problem.success_gap, 64, np.random.default_rng(k)).probs,
                "AGQO": run_qaoa(cp, _agqo_spec(row, man, ec.design), ec.problem.success_gap, 64,
                                 np.random.default_rng(k)).probs}
        for arm, p in arms.items():
            rows.append({"date": cp.inst.date, "arm": arm} | _masses(cp, p))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 2. hardware
def _esp(tqc, target) -> dict:
    """Estimated success probability: product of (1 - error) over every gate and measurement."""
    logf, n2, n1 = 0.0, 0, 0
    for inst in tqc.data:
        name = inst.operation.name
        if name in ("barrier", "delay"):
            continue
        qs = tuple(tqc.find_bit(q).index for q in inst.qubits)
        props = target[name].get(qs) if name in target.operation_names else None
        err = props.error if props is not None and props.error is not None else 0.0
        logf += np.log(max(1 - err, 1e-12))
        n2 += len(qs) == 2
        n1 += len(qs) == 1 and name != "measure"
    return {"esp": float(np.exp(logf)), "native_2q": n2, "native_1q": n1, "depth": tqc.depth()}


def hardware(cps, insight, man, grid: pd.DataFrame, ec, aer_quarters: int = 3, shots: int = 1000) -> pd.DataFrame:
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeKingston

    from .quantum.export import build_circuit

    backend = FakeKingston()
    noisy = AerSimulator.from_backend(backend)
    ok = grid[~grid.over_budget]
    shallow_row = ok[(ok.layers == 2) & (ok.coupling_mass == 0.75)].sort_values("train_success").iloc[-1].to_dict()
    rows = []
    picks = [0, len(cps) // 2, len(cps) - 1]
    for qi, k in enumerate(picks):
        cp = cps[k]
        row = insight[k]["chosen_schedule"]
        circuits = {"warm start only": CircuitSpec(layers=0, initial_state="warm_start", mixer="warm_x",
                                                   warm_start_epsilon=row["epsilon"], optimizer="none", max_iter=0),
                    "AGQO shallow (p=2, 75% couplings)": spec_of(shallow_row, label="shallow:"),
                    "AGQO (chosen schedule)": spec_of(row, label="AGQO:"),
                    "textbook QAOA": DEFAULT_SPEC}
        gap = cp.land.gap()
        good = np.isfinite(gap) & (gap <= ec.problem.success_gap)
        ref = cp.reference_index()
        better = np.isfinite(gap) & (cp.land.objective < cp.land.objective[ref]) if np.isfinite(gap[ref]) \
            else np.isfinite(gap)
        unif = uniform_reference(cp, ec.problem.success_gap)
        for name, spec in circuits.items():
            if spec.layers == 0:
                angles = np.array([])
                probs = np.abs(initial_state(cp, spec)) ** 2
            else:
                r = run_qaoa(cp, spec, ec.problem.success_gap, 64, np.random.default_rng(k))
                angles, probs = r.angles, r.probs
            qc = build_circuit(cp, spec, angles) if spec.layers else _warm_only_circuit(cp, spec)
            tqc = transpile(qc, backend, optimization_level=3, seed_transpiler=7)
            e = _esp(tqc, backend.target)
            ideal = float(probs[good].sum())
            row_out = {"date": cp.inst.date, "circuit": name, "logical_2q": int(qc.count_ops().get("rzz", 0) * 2),
                       "ideal_success": ideal, "uniform_success": unif,
                       "esp_model_success": e["esp"] * ideal + (1 - e["esp"]) * unif,
                       "ideal_better_than_rounding": float(probs[better].sum())} | e
            if qi < aer_quarters and name in ("warm start only", "AGQO shallow (p=2, 75% couplings)"):
                t0 = time.time()
                counts = noisy.run(tqc, shots=shots, seed_simulator=7).result().get_counts()
                idx = np.array([int(b.replace(" ", ""), 2) for b in counts])
                c = np.array(list(counts.values()), float)
                row_out |= {"aer_noisy_success": float(c[good[idx]].sum() / c.sum()),
                            "aer_noisy_better_than_rounding": float(c[better[idx]].sum() / c.sum()),
                            "aer_seconds": round(time.time() - t0, 1)}
            rows.append(row_out)
            _log(f"  hardware {cp.inst.date} {name:34s} 2q={e['native_2q']:5d} depth={e['depth']:5d} "
                 f"ESP={e['esp']:.3g} ideal={ideal:.3f} {row_out.get('aer_noisy_success', '')}")
    return pd.DataFrame(rows)


def _warm_only_circuit(cp, spec):
    from qiskit import QuantumCircuit

    from .quantum.simulator import warm_angles
    qc = QuantumCircuit(cp.n)
    for q, t in enumerate(warm_angles(cp, spec.warm_start_epsilon)):
        qc.ry(float(t), q)
    qc.measure_all()
    return qc


# ------------------------------------------------------------------ 3. scaling
def scaling(md, ec, dates, man, sizes=(8, 12, 16, 20)) -> pd.DataFrame:
    frozen = man["frozen_schedule"]
    rows = []
    for n in sizes:
        e = dataclasses.replace(ec, problem=dataclasses.replace(ec.problem, register_size=n))
        for k, d in enumerate(dates):
            uni, _ = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)
            inst = build_rounding_instance(md, d, uni, Account(cash=ec.problem.capital_vnd), e)
            t0 = time.time()
            land = landscape(inst)
            t_enum = time.time() - t0
            cp = CompiledProblem(inst, land)
            spec = spec_of(frozen)
            t0 = time.time()
            probs = np.abs(statevector(cp, spec, initial_angles(spec))) ** 2
            t_sv = time.time() - t0
            gap = land.gap()
            good = np.isfinite(gap) & (gap <= ec.problem.success_gap)
            warm = np.abs(initial_state(cp, CircuitSpec(initial_state="warm_start",
                                                         warm_start_epsilon=frozen["epsilon"]))) ** 2
            t0 = time.time()
            sa_idx, sa_flips = simulated_annealing(inst, land, seed=k)
            t_sa = time.time() - t0
            rows.append({"qubits": inst.n_qubits, "date": inst.date, "states": 2 ** inst.n_qubits,
                         "enumeration_s": t_enum, "statevector_s": t_sv, "sa_s": t_sa, "sa_flips": sa_flips,
                         "sa_gap": float(gap[sa_idx]) if sa_idx is not None else np.inf,
                         "cx_logical": 2 * len(cp.phase_terms(spec)[1]) * spec.layers,
                         "uniform_success": float(good.mean()), "warm_success": float(warm[good].sum()),
                         "frozen_success": float(probs[good].sum() / probs.sum())})
        _log(f"  scaling n={n}: frozen success {np.mean([r['frozen_success'] for r in rows if r['qubits'] == n]):.3f}")
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 4. finance robustness
def greedy_target(md, d, universe, acc, ec) -> dict:
    """Strong classical heuristic: floor lots of the QP target, then add the single lot that lowers
    TE^2 + turnover the most, while cash (after fees) allows; stop when no lot helps."""
    from .backtest import risk_inputs

    tk, w, target, _ = continuous_target(md, d, universe, acc, ec)
    px = md.px.loc[d, tk].to_numpy()
    nav = acc.value(md.px.loc[d])
    lot = ec.rules.lot_size
    cov, cov_b, var_b = risk_inputs(md, d, tk, ec.problem)
    prev = np.array([acc.shares.get(t, 0.0) for t in tk]) * px / nav
    lots = np.floor(w * nav / (lot * px) + 1e-9)
    a = lot * px / nav
    obj = lambda wv: 252 * (wv @ cov @ wv - 2 * wv @ cov_b + var_b) + ec.problem.turnover_weight * ((wv - prev) ** 2).sum()
    budget = nav * (1 - 2 * ec.rules.commission) * min(0.985, target + 0.005)
    while True:
        wv = lots * a
        base = obj(wv)
        best, gain = None, 0.0
        spend = (lots * lot * px).sum()
        for j in range(len(tk)):
            if spend + lot * px[j] > budget:
                continue
            wv[j] += a[j]
            g = base - obj(wv)
            wv[j] -= a[j]
            if g > gain:
                best, gain = j, g
        if best is None:
            break
        lots[best] += 1
    return dict(zip(tk, lots * lot))



def _walk(md, ec, dates, capital, decide, odd_premium=0.0):
    acc, segs = Account(cash=capital), []
    end = md.index.index[-1]
    for k, d in enumerate(dates):
        px = md.px.loc[d]
        target = decide(d, acc)
        if odd_premium:
            extra = sum(odd_premium * (abs(target.get(t, 0) - acc.shares.get(t, 0)) % 100) * px[t]
                        for t in set(target) | set(acc.shares))
        acc.rebalance(target, px, ec.rules)
        if odd_premium:
            acc.cash -= extra
            acc.fees_paid += extra
        nxt = dates[k + 1] if k + 1 < len(dates) else end
        seg = daily_values(md, acc, d, nxt)
        segs.append(seg if k + 1 == len(dates) else seg.iloc[:-1])
    return pd.concat(segs), acc


def robustness(md, ec, man) -> pd.DataFrame:
    """Exact whole-lot rounding stands in for AGQO here: AGQO returned the exact optimum in 12/12 quarters."""
    uni = lambda d: md.universe(d, ec.problem.lookback_days, ec.problem.min_history)[0]

    def exact(e):
        def f(d, acc):
            inst = build_rounding_instance(md, d, uni(d), acc, e)
            land = landscape(inst)
            x = (land.opt_index >> np.arange(inst.n_qubits)) & 1
            return dict(zip(inst.tickers, inst.shares(x)[0]))
        return f

    def odd(e):
        def f(d, acc):
            tk, w, _, _ = continuous_target(md, d, uni(d), acc, e)
            nav = acc.value(md.px.loc[d])
            return dict(zip(tk, np.floor(w * nav / md.px.loc[d, tk].to_numpy())))
        return f

    pract = lambda e: (lambda d, acc: practitioner_target(md, d, uni(d), acc, e))
    greedy = lambda e: (lambda d, acc: greedy_target(md, d, uni(d), acc, e))
    q = md.rebalance_dates(ec.test_start, ec.test_end, "QS")
    m = md.rebalance_dates(ec.test_start, ec.test_end, "MS")
    etf = md.etf_close[ec.primary_etf]
    rows = []
    for cap in (20e6, 100e6):
        scen = [("base (0.15% commission, quarterly)", ec, q, 0.0),
                ("commission 0.10%", dataclasses.replace(ec, rules=dataclasses.replace(ec.rules, commission=0.001)), q, 0.0),
                ("commission 0.25%", dataclasses.replace(ec, rules=dataclasses.replace(ec.rules, commission=0.0025)), q, 0.0),
                ("monthly rebalancing", ec, m, 0.0)]
        for label, e, dates, _ in scen:
            sp, ap = _walk(md, e, dates, cap, pract(e))
            sx, ax = _walk(md, e, dates, cap, exact(e))
            sg, ag = _walk(md, e, dates, cap, greedy(e))
            ci = block_bootstrap_te_diff(active_returns(sx, md.index), active_returns(sp, md.index))
            cg = block_bootstrap_te_diff(active_returns(sx, md.index), active_returns(sg, md.index))
            pp, px_, pg = performance(sp, md.index, etf), performance(sx, md.index, etf), performance(sg, md.index, etf)
            rows.append({"capital_vnd": cap, "scenario": label, "te_practitioner": pp["tracking_error_ann_pct"],
                         "te_whole_lot_optimum": px_["tracking_error_ann_pct"], "diff_pp": ci["diff_pp"],
                         "ci_low": ci["ci_low"], "ci_high": ci["ci_high"],
                         "return_practitioner": pp["return_ann_pct"], "return_whole_lot_optimum": px_["return_ann_pct"],
                         "fees_whole_lot_optimum": ax.fees_paid, "te_greedy": pg["tracking_error_ann_pct"],
                         "return_greedy": pg["return_ann_pct"], "diff_vs_greedy_pp": cg["diff_pp"],
                         "greedy_ci_low": cg["ci_low"], "greedy_ci_high": cg["ci_high"]})
            _log(f"  robustness {cap / 1e6:.0f}M {label:36s} {ci['diff_pp']:+.2f} pp")
        for prem in (0.0, 0.005, 0.01, 0.02):
            so, ao = _walk(md, ec, q, cap, odd(ec), odd_premium=prem)
            po = performance(so, md.index, etf)
            rows.append({"capital_vnd": cap, "scenario": f"odd-lot execution, premium {100 * prem:.1f}%",
                         "te_odd_lot": po["tracking_error_ann_pct"], "return_odd_lot": po["return_ann_pct"],
                         "fees_odd_lot": ao.fees_paid})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 5. examples
def examples(md, ec, man, insight) -> dict:
    d = md.rebalance_dates(ec.test_start, ec.test_end)[-1]
    uni, _ = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)
    out = {}
    for cap in (20e6, 100e6):
        acc = Account(cash=cap)
        t0 = time.time()
        inst = build_rounding_instance(md, d, uni, acc, ec)
        t_build = time.time() - t0
        t0 = time.time()
        land = landscape(inst)
        t_enum = time.time() - t0
        cp = CompiledProblem(inst, land)
        spec = _agqo_spec(insight[-1]["chosen_schedule"], man, ec.design)
        t0 = time.time()
        r = run_qaoa(cp, spec, ec.problem.success_gap, 512, np.random.default_rng(0))
        t_qaoa = time.time() - t0
        prac = practitioner_target(md, d, uni, acc, ec)
        gr = greedy_target(md, d, uni, acc, ec)
        w_g = np.array([gr.get(t, 0) for t in inst.tickers]) * inst.prices / inst.nav
        x = (land.opt_index >> np.arange(inst.n_qubits)) & 1
        w_c = inst.meta["continuous_weights"]
        w_x = inst.weights(x)[0]
        w_p = np.array([prac.get(t, 0) for t in inst.tickers]) * inst.prices / inst.nav
        out[str(int(cap))] = {
            "date": inst.date, "tickers": inst.tickers, "sector": [md.sector(t) for t in inst.tickers],
            "continuous": w_c.tolist(), "practitioner": w_p.tolist(), "greedy": w_g.tolist(), "agqo": w_x.tolist(),
            "register": inst.register, "lot_pct": (100 * inst.rules.lot_size * inst.prices / inst.nav).tolist(),
            "te": {"continuous": float(100 * inst.tracking_error(w_c)[0]),
                   "practitioner": float(100 * inst.tracking_error(w_p)[0]),
                   "greedy": float(100 * inst.tracking_error(w_g)[0]),
                   "agqo": float(100 * inst.tracking_error(w_x)[0])},
            "J": cp.J.tolist(), "h": cp.hz.tolist(), "relaxed": cp.relaxed.tolist(),
            "agqo_success": r.success_prob, "agqo_best_gap": r.best_sample_gap,
            "seconds": {"build_problem": t_build, "enumerate_65536": t_enum, "qaoa_simulate_and_polish": t_qaoa}}
    return out


def llm_usage(run: Path) -> dict:
    """Recount prompt tokens with Qwen3.8's tokenizer (the live log recorded a wrong input count)."""
    log = [json.loads(x) for x in (run / "llm" / "llm_log.jsonl").read_text().splitlines()]
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.8-27B-FP8", revision="c3a462cc3d38cf351f3b26cbd763469eeb74ef81")
    except Exception as exc:                                    # offline: report output tokens only
        tok, err = None, repr(exc)[:200]
    out = {}
    for agent in sorted({r["agent"] for r in log}):
        rs = [r for r in log if r["agent"] == agent]
        k = len(rs)                                             # the latest batch: trailing records of one call
        while k > 0 and rs[k - 1]["batch_wall_s"] == rs[-1]["batch_wall_s"]:
            k -= 1
        rs = rs[k:]
        n_in = None
        if tok is not None:
            n_in = 0
            for r in rs:
                ids = tok.apply_chat_template([{"role": "system", "content": r["system"]},
                                               {"role": "user", "content": r["user"]}], add_generation_prompt=True,
                                              tokenize=True, enable_thinking=False)
                n_in += len(ids["input_ids"] if isinstance(ids, dict) or hasattr(ids, "keys") else ids)
        out[agent] = {"requests": len(rs), "input_tokens": n_in, "output_tokens": sum(r["usage"].get("output_tokens", 0)
                                                                                         for r in rs),
                      "batch_wall_seconds_incl_cold_start": rs[0]["batch_wall_s"],
                      "model_load_s": rs[0].get("model_load_s"), "generate_s": rs[0].get("batch_generate_s"),
                      "model": rs[0]["model"],
                      "gpu": rs[0].get("gpu")}
    if tok is None:
        out["note"] = "tokenizer unavailable: " + err
    return out


def run_extras(run: Path) -> None:
    out = run / "extras"
    out.mkdir(exist_ok=True)
    ec = load_config(run)
    man = json.loads((run / "run_manifest.json").read_text())
    insight = json.loads((run / "insight.json").read_text())
    grid = pd.read_csv(run / "schedule_grid.csv")
    md = MarketData.load()
    dates = md.rebalance_dates(ec.test_start, ec.test_end, "QS")
    _log("extras: reference problems")
    cps = reference_problems(md, ec, dates)
    _log("extras: distributions")
    distributions(cps, insight, man, ec).to_csv(out / "distributions.csv", index=False)
    _log("extras: examples")
    (out / "examples.json").write_text(json.dumps(examples(md, ec, man, insight), indent=1))
    _log("extras: LLM usage")
    (out / "llm_usage.json").write_text(json.dumps(llm_usage(run), indent=2))
    _log("extras: finance robustness")
    robustness(md, ec, man).to_csv(out / "robustness.csv", index=False)
    _log("extras: scaling")
    scaling(md, ec, dates, man).to_csv(out / "scaling.csv", index=False)
    _log("extras: hardware")
    hw = hardware(cps, insight, man, grid, ec)
    hw.to_csv(out / "hardware.csv", index=False)
    _log("extras: noise-aware guidance")
    ha, summ = hardware_aware(md, ec, man, cps, hw)
    ha.to_csv(out / "hardware_aware.csv", index=False)
    (out / "hardware_aware.json").write_text(json.dumps(summ, indent=2, default=float))
    _log("extras: done")


def run_hardware_aware(run: Path) -> None:
    """Re-run only the noise-aware study from saved hardware results."""
    out = run / "extras"
    ec = load_config(run)
    man = json.loads((run / "run_manifest.json").read_text())
    md = MarketData.load()
    cps = reference_problems(md, ec, md.rebalance_dates(ec.test_start, ec.test_end, "QS"))
    ha, summ = hardware_aware(md, ec, man, cps, pd.read_csv(out / "hardware.csv"))
    ha.to_csv(out / "hardware_aware.csv", index=False)
    (out / "hardware_aware.json").write_text(json.dumps(summ, indent=2, default=float))


# ------------------------------------------------------------------ 6. noise-aware guidance
def hardware_aware(md, ec, man, cps, hw: pd.DataFrame, shots: int = 1000) -> tuple[pd.DataFrame, dict]:
    """Choose the schedule that maximises *expected noisy* success on the 2023 training problems.

    Noise model fitted on this run's transpiles to IBM Heron (FakeKingston): log ESP = a + b * logical CX.
    Noisy success = ESP * ideal + (1 - ESP) * random guessing (global depolarising approximation, checked
    against a full Aer noise simulation in `hardware`).
    """
    import itertools

    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeKingston

    from .quantum.design import success_table
    from .quantum.export import build_circuit

    fit = hw[hw.esp > 0]
    b, a = np.polyfit(fit.logical_2q, np.log(fit.esp), 1)
    esp = lambda cx: float(np.exp(a + b * cx))
    dc = ec.design
    grid = pd.DataFrame(itertools.product((1, 2), (0.02, 0.05, 0.10), (0.25, 0.5, 0.75, 1.0), dc.dgamma_grid,
                                          dc.dbeta_grid), columns=["layers", "epsilon", "coupling_mass", "dgamma", "dbeta"])
    train = []
    for d in md.rebalance_dates(ec.train_start, ec.train_end, "MS"):
        uni, _ = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)
        for size in dc.train_sizes:
            inst = build_rounding_instance(md, d, uni, Account(cash=size), ec)
            train.append(CompiledProblem(inst, landscape(inst)))
    table = success_table(train, grid, ec.problem.success_gap, 10_000, dc.workers)
    cx = np.array([[2 * len(cp.phase_terms(spec_of(r))[1]) * int(r["layers"]) for r in grid.to_dict("records")]
                   for cp in train])
    uni_tr = np.array([uniform_reference(cp, ec.problem.success_gap) for cp in train])[:, None]
    e = np.exp(a + b * cx)
    noisy = e * table + (1 - e) * uni_tr
    best = int(np.argmax(noisy.mean(0)))
    row = grid.iloc[best].to_dict()
    eps_best = float(row["epsilon"])
    warm_tr = np.mean([float((np.abs(initial_state(cp, CircuitSpec(initial_state="warm_start",
                                                                       warm_start_epsilon=eps_best))) ** 2)[
        np.isfinite(cp.land.gap()) & (cp.land.gap() <= ec.problem.success_gap)].sum()) for cp in train])
    backend = FakeKingston()
    sim = AerSimulator.from_backend(backend)
    rows = []
    for k, cp in enumerate(cps):
        spec = spec_of(row, label="noise-aware:")
        r = run_qaoa(cp, spec, ec.problem.success_gap, 64, np.random.default_rng(k))
        gap = cp.land.gap()
        good = np.isfinite(gap) & (gap <= ec.problem.success_gap)
        unif = uniform_reference(cp, ec.problem.success_gap)
        warm = float((np.abs(initial_state(cp, CircuitSpec(initial_state="warm_start", warm_start_epsilon=eps_best))) ** 2)[good].sum())
        out = {"date": cp.inst.date, "ideal_success": r.success_prob, "logical_2q": r.two_qubit_gates,
               "esp_fit": esp(r.two_qubit_gates), "warm_ideal": warm, "uniform": unif}
        out["esp_model_success"] = out["esp_fit"] * r.success_prob + (1 - out["esp_fit"]) * unif
        out["warm_esp_model"] = esp(0) * warm + (1 - esp(0)) * unif
        if k in (0, len(cps) // 2, len(cps) - 1):
            tqc = transpile(build_circuit(cp, spec, r.angles), backend, optimization_level=3, seed_transpiler=7)
            e_t = _esp(tqc, backend.target)
            counts = sim.run(tqc, shots=shots, seed_simulator=7).result().get_counts()
            idx = np.array([int(bs.replace(" ", ""), 2) for bs in counts])
            c = np.array(list(counts.values()), float)
            out |= {"native_2q": e_t["native_2q"], "esp_transpiled": e_t["esp"],
                    "aer_noisy_success": float(c[good[idx]].sum() / c.sum())}
        rows.append(out)
    summary = {"fit_log_esp_intercept": a, "fit_log_esp_per_logical_cx": b,
               "two_qubit_error_implied": float(1 - np.exp(b)), "schedule": row,
               "train_expected_noisy_success": float(noisy.mean(0)[best]),
               "train_warm_start_noisy_success": float(esp(0) * warm_tr + (1 - esp(0)) * uni_tr.mean()),
               "train_ideal_success": float(table[:, best].mean()),
               "cx_for_esp_half_at_p6": None}
    # How good must hardware get for the full p=6 AGQO circuit to keep half its noiseless advantage?
    deep = hw[hw.circuit == "AGQO (chosen schedule)"]
    if len(deep):
        n2 = float(deep.native_2q.mean())
        summary["deep_native_2q"] = n2
        summary["two_qubit_error_needed_for_esp_0.5"] = float(1 - 0.5 ** (1 / n2))
        summary["median_cz_error_today"] = float(np.median([backend.target["cz"][q].error for q in backend.target["cz"]
                                                            if backend.target["cz"][q] and backend.target["cz"][q].error]))
    _log(f"  noise-aware schedule {row} train noisy {summary['train_expected_noisy_success']:.4f} "
         f"vs warm {summary['train_warm_start_noisy_success']:.4f}")
    return pd.DataFrame(rows), summary


def run_update(run: Path) -> None:
    """Re-run the robustness and hardware studies (after adding baselines) and the noise-aware study."""
    out = run / "extras"
    ec = load_config(run)
    man = json.loads((run / "run_manifest.json").read_text())
    insight = json.loads((run / "insight.json").read_text())
    md = MarketData.load()
    cps = reference_problems(md, ec, md.rebalance_dates(ec.test_start, ec.test_end, "QS"))
    _log("robustness")
    robustness(md, ec, man).to_csv(out / "robustness.csv", index=False)
    _log("hardware")
    hw = hardware(cps, insight, man, pd.read_csv(run / "schedule_grid.csv"), ec)
    hw.to_csv(out / "hardware.csv", index=False)
    _log("noise-aware")
    ha, summ = hardware_aware(md, ec, man, cps, hw)
    ha.to_csv(out / "hardware_aware.csv", index=False)
    (out / "hardware_aware.json").write_text(json.dumps(summ, indent=2, default=float))
