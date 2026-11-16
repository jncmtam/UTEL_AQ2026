"""Prototype backend: one live AGQO decision for a new account, step by step.

The web prototype (`app/`) calls three functions here:

  compile_mandate(text)      Vietnamese instruction -> checked constraints
                             (Qwen3.8 on Modal when reachable; replay of a logged live call;
                             keyword rules as the always-available fallback)
  Demo.decide(capital, m)    the full Phase 1a -> 2 -> verify pipeline on the latest rebalance date:
                             market insight, cap-safe 16-qubit QUBO, AI-chosen schedule (k-NN model
                             trained on 2023), QAOA statevector simulation with 512 shots, exact
                             enumeration of all 2^16 lot choices, baselines and the trade list
  Demo.evidence(...)         the code-built fact sheet the LLM explainer may use

The schedule model needs the 2023 training success table; `python -m agqo.demo` rebuilds it
once (results/final/schedule_table.npy, a few minutes on CPU) from the saved configuration.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import Account, build_rounding_instance, practitioner_target
from .config import RESULTS_DIR
from .data import MarketData
from .extras import BINS, greedy_target, load_config
from .insight import market_insight
from .mandate import Mandate, rule_parse
from .portfolio import landscape
from .quantum.design import FEATURES, ScheduleModel, design_features, schedule_grid, spec_of, success_table
from .quantum.simulator import CompiledProblem, initial_angles, initial_state, run_qaoa, warm_start_only
from .quantum.spec import DEFAULT_SPEC, CircuitSpec

TABLE_FILE = "schedule_table.npy"


# ------------------------------------------------------------------ schedule model
def build_schedule_table(run: Path = RESULTS_DIR) -> np.ndarray:
    """Re-score every schedule on the 48 training problems (identical to Stage B of `run`)."""
    ec = load_config(run)
    md = MarketData.load()
    feats = pd.read_csv(run / "train_features.csv")
    cps = []
    for d, size in zip(pd.to_datetime(feats.date), feats.capital_vnd):
        uni, _ = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)
        inst = build_rounding_instance(md, d, uni, Account(cash=float(size)), ec)
        cps.append(CompiledProblem(inst, landscape(inst)))
    table = success_table(cps, schedule_grid(ec.design), ec.problem.success_gap, ec.design.cx_budget,
                          ec.design.workers)
    np.save(run / TABLE_FILE, table)
    return table


def _bits(idx: int, n: int) -> np.ndarray:
    return (idx >> np.arange(n)) & 1


def _bitstring(idx: int, n: int) -> str:
    return "".join(str(b) for b in _bits(idx, n))          # qubit 0 first, as in the register list


# ------------------------------------------------------------------ mandate compiler
def compile_mandate(text: str, sector_of: dict[str, str], backend: str = "auto",
                    log: Path = RESULTS_DIR / "llm" / "llm_log.jsonl") -> dict:
    """Return {mandate, source, needs_clarification, errors, raw}. Never raises on LLM failure."""
    from .llm.tasks import mandate_request, parse_mandate

    req = mandate_request(text, sector_of)
    tickers = set(sector_of)
    if log.exists():                                     # same instruction already answered live (latest answer)
        hit = None
        for line in log.read_text().splitlines():
            rec = json.loads(line)
            if rec["agent"] == "mandate_compiler" and rec["user"].strip() == text.strip() and rec.get("parsed"):
                hit = rec
        if hit is not None:
            m, clar, errs = parse_mandate(hit["parsed"], tickers)
            return {"mandate": m.to_dict(), "source": "Qwen3.8-27B (logged live answer)",
                    "needs_clarification": clar, "question": hit["parsed"].get("clarification_question_vi"),
                    "errors": errs, "raw": hit["parsed"]}
    if backend in ("auto", "modal"):
        try:
            import modal

            engine = modal.Cls.from_name("agqo-llm", "Engine")()
            payload = [{k: req[k] for k in ("system", "user", "schema", "seed", "temperature", "max_tokens")}]
            out = engine.generate.remote(payload)[0]
            parsed = json.loads(out["raw_text"])
            m, clar, errs = parse_mandate(parsed, tickers)
            return {"mandate": m.to_dict(), "source": "Qwen3.8-27B (live, Modal H100)", "needs_clarification": clar,
                    "question": parsed.get("clarification_question_vi"), "errors": errs, "raw": parsed}
        except Exception as e:                           # no Modal credentials, cold start failure, ...
            fallback_reason = f"{type(e).__name__}: {e}"[:200]
    else:
        fallback_reason = "LLM disabled"
    m = rule_parse(text, tickers)
    return {"mandate": m.to_dict(), "source": "keyword rules (fallback)", "needs_clarification": False,
            "question": None, "errors": [], "raw": None, "fallback_reason": fallback_reason}


# ------------------------------------------------------------------ one decision
class Demo:
    def __init__(self, run: Path = RESULTS_DIR):
        self.run = run
        self.ec = load_config(run)
        self.md = MarketData.load()
        self.date = self.md.rebalance_dates(self.ec.test_start, self.ec.test_end)[-1]
        self.universe, self.dropped = self.md.universe(self.date, self.ec.problem.lookback_days,
                                                       self.ec.problem.min_history)
        manifest = json.loads((run / "run_manifest.json").read_text())
        self.use_polish = bool(manifest["use_polish"])
        self.grid = schedule_grid(self.ec.design)
        self.feats = pd.read_csv(run / "train_features.csv")
        table = np.load(run / TABLE_FILE) if (run / TABLE_FILE).exists() else build_schedule_table(run)
        self.model = ScheduleModel.fit(self.feats, table, int(manifest["schedule_model_k"]))
        self.sector_of = {t: self.md.sector(t) for t in self.md.close.columns}   # as in the 35-item evaluation

    # -------------------------------------------------------------- helpers
    def _neighbours(self, f: dict) -> list[dict]:
        z = (np.array([f[c] for c in FEATURES]) - self.model.mean) / self.model.std
        d = ((self.model.X - z) ** 2).sum(1)
        nn = np.argsort(d)[: self.model.k]
        return [{"date": self.feats.date.iloc[i], "capital_vnd": float(self.feats.capital_vnd.iloc[i]),
                 "distance": round(float(np.sqrt(d[i])), 3), "z": np.round(self.model.X[i], 3).tolist()} for i in nn]

    def _portfolio(self, inst, tickers, shares: dict) -> dict:
        w = np.array([shares.get(t, 0.0) for t in tickers]) * inst.prices / inst.nav
        return {"weights": w.round(5).tolist(), "te_pct": round(float(100 * inst.tracking_error(w)[0]), 3),
                "invested_pct": round(float(100 * w.sum()), 2), "holdings": int((w > 0).sum())}

    # -------------------------------------------------------------- the pipeline
    def decide(self, capital: float, mandate: Mandate | None = None, shots: int = 512, seed: int = 0,
               with_textbook: bool = True) -> dict:
        md, ec, d = self.md, self.ec, self.date
        m = mandate or Mandate()
        t = {}
        acc = Account(cash=float(capital))

        t0 = time.time()
        inst = build_rounding_instance(md, d, self.universe, acc, ec, m)
        t["build_qubo"] = time.time() - t0
        t0 = time.time()
        land = landscape(inst)
        t["enumerate_all"] = time.time() - t0
        cp = CompiledProblem(inst, land)
        n = inst.n_qubits

        # Phase 1a: market insight (statistics)
        excluded = [x for x in self.universe if x not in inst.tickers]
        mi = market_insight(md, inst, land, excluded, ec.problem.lookback_days)

        # Phase 2b: AI guidance (k-NN over insight features -> schedule)
        f = design_features(cp)
        row = self.grid.iloc[self.model.choose(f)]
        spec = spec_of(row, ec.design.polish_iters if self.use_polish else 0, ec.design.polish_cvar_alpha, "AGQO:")

        # Quantum: statevector simulation of the designed circuit, then 512 measurement shots
        t0 = time.time()
        r = run_qaoa(cp, spec, ec.problem.success_gap, shots, np.random.default_rng(seed))
        t["qaoa"] = time.time() - t0
        rng = np.random.default_rng(seed + 1)
        samples = rng.choice(len(r.probs), size=shots, p=r.probs / r.probs.sum())

        gap = land.gap()
        warm = warm_start_only(cp, float(row["epsilon"]), ec.problem.success_gap, shots, np.random.default_rng(seed))
        arms = {"AGQO": r.probs, "warm start only": warm.probs, "random guessing": np.full(2 ** n, 2.0 ** -n)}
        if with_textbook:
            t0 = time.time()
            tb = run_qaoa(cp, DEFAULT_SPEC, ec.problem.success_gap, shots, np.random.default_rng(seed))
            t["textbook_qaoa"] = time.time() - t0
            arms["textbook QAOA"] = tb.probs

        def masses(p):
            p = p / p.sum()
            out = {name: float(p[np.isfinite(gap) & (gap >= lo) & (gap < hi) if lo > 0 else (gap <= hi)].sum())
                   for name, lo, hi in BINS}
            out["over budget"] = float(p[~np.isfinite(gap)].sum())
            return out

        # decision = best affordable sample (verified exactly)
        best = r.best_sample if r.best_sample is not None else land.opt_index
        x = _bits(best, n)
        new = inst.shares(x)[0]
        opt_x = _bits(land.opt_index, n)

        # baselines for the same account
        prac = practitioner_target(md, d, self.universe, acc, ec, m)
        greedy = greedy_target(md, d, self.universe, acc, ec) if m.is_empty() else None
        tickers = inst.tickers
        w_cont = inst.meta["continuous_weights"]
        ports = {"ideal (fractional shares)": {"weights": np.round(w_cont, 5).tolist(),
                                              "te_pct": round(float(100 * inst.tracking_error(w_cont)[0]), 3),
                                              "invested_pct": round(float(100 * w_cont.sum()), 2),
                                              "holdings": int((w_cont > 1e-4).sum())},
                 "nearest-lot rounding": self._portfolio(inst, tickers, prac),
                 "AGQO": self._portfolio(inst, tickers, dict(zip(tickers, new)))}
        if greedy is not None:
            ports["greedy lot filling"] = self._portfolio(inst, tickers, greedy)

        trades, fee_total = [], 0.0
        rules = ec.rules
        for tk, p, s in zip(tickers, inst.prices, new):
            if s > 0:
                v = s * p
                fee = rules.commission * v
                fee_total += fee
                trades.append({"ticker": tk, "sector": md.sector(tk), "lots": int(s // rules.lot_size),
                               "shares": int(s), "price_vnd": float(p), "value_vnd": float(v), "fee_vnd": float(fee)})
        trades.sort(key=lambda z: -z["value_vnd"])
        cash_after = float(inst.cash_after(x[None, :])[0])

        # compliance with every rule of the mandate (post-trade weights)
        w_new = new * inst.prices / inst.nav
        checks = []
        for mask, cap in inst.caps:
            names = [tk for tk, k in zip(tickers, mask) if k]
            label = "invested share" if mask.all() else (names[0] if mask.sum() == 1 else md.sector(names[0]))
            checks.append({"rule": f"{label} <= {100 * cap:.1f}%", "value_pct": round(float(100 * w_new[mask].sum()), 2),
                           "ok": bool(w_new[mask].sum() <= cap + 1e-9)})
        held = {tk for tk, s in zip(tickers, new) if s > 0}
        if m.exclude_tickers or m.exclude_sectors:
            bad = [tk for tk in held if tk in m.exclude_tickers or md.sector(tk) in m.exclude_sectors]
            checks.append({"rule": "no excluded stock or sector held", "value_pct": None, "ok": not bad})
        if m.max_holdings is not None:
            checks.append({"rule": f"at most {m.max_holdings} stocks", "value_pct": None, "ok": len(held) <= m.max_holdings})
        checks.append({"rule": "cash never negative after fees", "value_pct": None, "ok": cash_after >= 0})

        # circuit description for drawing
        diag, sel, scale = cp.phase_terms(spec)
        reg = inst.register
        angles = r.angles if len(r.angles) else initial_angles(spec)
        p = spec.layers
        top = np.argsort(-r.probs)[:12]
        e_samples = land.energy[samples]
        ok = np.isfinite(gap)
        return {
            "date": inst.date, "capital_vnd": float(capital), "mandate": m.to_dict(),
            "universe": len(self.universe), "excluded_by_mandate": excluded,
            "market": {"avg_correlation": round(mi.avg_correlation, 3),
                       "market_factor_share_pct": round(100 * mi.market_factor_share, 1),
                       "effective_bets": round(mi.effective_bets, 1), "clusters": mi.clusters,
                       "lot_cost_pct_median": round(mi.lot_cost_pct_median, 2),
                       "lot_cost_pct_max": round(mi.lot_cost_pct_max, 2)},
            "stocks": [{"ticker": tk, "sector": md.sector(tk), "price_vnd": float(pp),
                        "lot_pct": round(float(100 * rules.lot_size * pp / inst.nav), 2)}
                       for tk, pp in zip(tickers, inst.prices)],
            "register": [{"qubit": q, "ticker": reg[q], "sector": md.sector(reg[q]),
                          "lot_pct": round(float(100 * rules.lot_size * inst.prices[inst.bit_stock[q]] / inst.nav), 2),
                          "relaxed": round(float(cp.relaxed[q]), 3), "h": round(float(cp.hz[q]), 6),
                          "agqo_bit": int(x[q]), "optimal_bit": int(opt_x[q]),
                          "nearest_bit": int(inst.meta["nearest_bits"][q])} for q in range(n)],
            "hamiltonian": {"J": np.round(cp.J, 7).tolist(), "h": np.round(cp.hz, 7).tolist(),
                            "pairs_total": int(len(cp.pair_w)), "pairs_kept": int(len(sel)), "scale": scale,
                            "kept": [{"a": int(i), "b": int(j), "w": float(w)}
                                     for (i, j), w in zip(cp.pairs[sel], cp.pair_w[sel])]},
            "ai": {"features": {k: round(float(v), 4) for k, v in f.items()}, "feature_names": FEATURES,
                   "features_z": np.round((np.array([f[c] for c in FEATURES]) - self.model.mean) / self.model.std, 3).tolist(),
                   "neighbours": self._neighbours(f), "k": self.model.k,
                   "schedule": {k: float(v) for k, v in row.items()}, "polish": self.use_polish,
                   "schedules_considered": int(len(self.grid))},
            "circuit": {"qubits": n, "layers": p, "two_qubit_gates": int(r.two_qubit_gates),
                        "gammas": np.round(angles[:p], 4).tolist(), "betas": np.round(angles[p:], 4).tolist(),
                        "warm_theta": np.round(2 * np.arcsin(np.sqrt(np.clip(cp.relaxed, spec.warm_start_epsilon,
                                                                                1 - spec.warm_start_epsilon))), 4).tolist(),
                        "evaluations": int(r.evaluations), "rationale": spec.rationale},
            "result": {"success_pct": round(100 * r.success_prob, 2),
                       "warm_success_pct": round(100 * warm.success_prob, 2),
                       "random_success_pct": round(100 * float((ok & (gap <= ec.problem.success_gap)).mean()), 3),
                       "textbook_success_pct": round(100 * tb.success_prob, 2) if with_textbook else None,
                       "best_sample_gap_pct": round(100 * float(gap[best]), 3),
                       "found_exact_optimum": bool(best == land.opt_index),
                       "masses": {k: masses(v) for k, v in arms.items()},
                       "top_states": [{"bits": _bitstring(int(i), n), "prob": float(r.probs[i]),
                                       "gap_pct": None if not np.isfinite(gap[i]) else round(100 * float(gap[i]), 3),
                                       "optimal": bool(i == land.opt_index)} for i in top],
                       "sample_energy": {"agqo": np.round(e_samples, 6).tolist(),
                                         "landscape_quantiles": np.round(np.quantile(land.energy[ok], np.linspace(0, 1, 41)), 6).tolist(),
                                         "optimum": float(land.energy[land.opt_index])},
                       "states_total": int(2 ** n), "states_affordable": int(ok.sum())},
            "portfolios": ports, "tickers": tickers,
            "trades": trades, "fees_vnd": fee_total, "cash_after_vnd": cash_after, "checks": checks,
            "seconds": {k: round(v, 3) for k, v in t.items()}, "_rec": (inst, land, cp, spec, r),
        }

    def evidence(self, out: dict) -> dict:
        from .experiment import _evidence

        return _evidence(self.md, self.date, out["_rec"], None, self.ec.problem)


if __name__ == "__main__":
    t = time.time()
    tab = build_schedule_table()
    print(f"schedule table {tab.shape} in {time.time() - t:.0f}s")
