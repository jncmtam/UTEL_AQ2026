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
    """Return {mandate, status, needs_clarification, question, conflicts, source, errors, raw}. Never raises.

    Order: logged live V3.2 answer for this exact text -> logged live V3 answer -> live Qwen with the V3.2 prompt
    (backend "auto"/"modal") -> keyword rules. status is ok | needs_clarification | conflict."""
    from .llm import v32
    from .llm.tasks import parse_mandate

    tickers = set(sector_of)
    hit = v32.logged(text)
    if hit is not None:
        res = v32.parse(hit["parsed"], tickers)
        return res | {"source": "Qwen3.8-27B, V3.2 prompt (logged live answer)", "raw": hit["parsed"],
                      "needs_clarification": res["status"] != "ok"}
    if log.exists():                                     # same instruction answered live in V3 (latest answer)
        hit = None
        for line in log.read_text().splitlines():
            rec = json.loads(line)
            if rec["agent"] == "mandate_compiler" and rec["user"].strip() == text.strip() and rec.get("parsed"):
                hit = rec
        if hit is not None:
            m, clar, errs = parse_mandate(hit["parsed"], tickers)
            return {"mandate": m.to_dict(), "source": "Qwen3.8-27B, V3 prompt (logged live answer)",
                    "status": "needs_clarification" if clar else "ok", "needs_clarification": clar, "conflicts": [],
                    "question": hit["parsed"].get("clarification_question_vi"), "errors": errs, "raw": hit["parsed"]}
    if backend in ("auto", "modal"):
        try:
            import modal

            req = v32.request(text, sector_of)
            engine = modal.Cls.from_name("agqo-llm", "Engine")()
            payload = [{k: req[k] for k in ("system", "user", "schema", "seed", "temperature", "max_tokens")}]
            out = engine.generate.remote(payload)[0]
            parsed = json.loads(out["raw_text"])
            res = v32.parse(parsed, tickers)
            return res | {"source": "Qwen3.8-27B, V3.2 prompt (live, Modal H100)", "raw": parsed,
                          "needs_clarification": res["status"] != "ok"}
        except Exception as e:                           # no Modal credentials, cold start failure, ...
            fallback_reason = f"{type(e).__name__}: {e}"[:200]
    else:
        fallback_reason = "LLM disabled"
    from .mandate import rule_clarification

    m = rule_parse(text, tickers)
    clar, question = rule_clarification(text)
    return {"mandate": m.to_dict(), "source": "keyword rules (fallback)", "needs_clarification": clar,
            "status": "needs_clarification" if clar else "ok", "conflicts": [],
            "question": question, "errors": [], "raw": None, "fallback_reason": fallback_reason}


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

    # -------------------------------------------------------------- deterministic accounting
    def _execution(self, inst, new: np.ndarray, m: Mandate) -> dict:
        """Trades, fees, cash and every rule check, all on the post-trade NAV (cash after fees + holdings)."""
        md, rules = self.md, self.ec.rules
        delta = new - inst.prev_shares
        trades, fee_total = [], 0.0
        for tk, p, s, dv in zip(inst.tickers, inst.prices, new, delta):
            if dv != 0:
                v = abs(dv) * p
                fee = rules.commission * v + (rules.sell_tax * v if dv < 0 else 0.0)
                fee_total += fee
                trades.append({"ticker": tk, "sector": md.sector(tk), "action": "buy" if dv > 0 else "sell",
                               "lots": int(abs(dv) // rules.lot_size), "shares": int(s), "price_vnd": float(p),
                               "value_vnd": float(v), "fee_vnd": float(fee)})
        if inst.other_value:                                # holdings outside the universe are sold
            fee_total += (rules.commission + rules.sell_tax) * inst.other_value
        trades.sort(key=lambda z: -z["value_vnd"])
        held_value = new * inst.prices
        cash_after = float(inst.cash + inst.other_value + (inst.prev_shares * inst.prices).sum()
                           - held_value.sum() - fee_total)
        post_nav = cash_after + float(held_value.sum())
        w = held_value / post_nav
        sec = np.array([md.sector(t) for t in inst.tickers])
        checks = []
        for s, cap in m.sector_caps.items():
            if s in m.exclude_sectors:
                continue
            v = float(w[sec == s].sum())
            checks.append({"kind": "sector_cap", "sector": s, "rule": f"{s} <= {100 * cap:.1f}%",
                           "limit_pct": 100 * cap, "value_pct": round(100 * v, 3), "ok": v <= cap + 1e-12})
        if m.max_weight_per_stock is not None:
            j = int(np.argmax(w)) if len(w) else 0
            v = float(w[j]) if len(w) else 0.0
            checks.append({"kind": "max_weight_per_stock", "ticker": inst.tickers[j] if len(w) else None,
                           "rule": f"largest single stock <= {100 * m.max_weight_per_stock:.1f}%",
                           "limit_pct": 100 * m.max_weight_per_stock, "value_pct": round(100 * v, 3),
                           "ok": v <= m.max_weight_per_stock + 1e-12})
        if m.min_cash_pct is not None:
            v = cash_after / post_nav
            checks.append({"kind": "min_cash_pct", "rule": f"cash >= {m.min_cash_pct:g}%", "limit_pct": m.min_cash_pct,
                           "value_pct": round(100 * v, 3), "ok": v >= m.min_cash_pct / 100 - 1e-12})
        held = [tk for tk, s in zip(inst.tickers, new) if s > 0]
        if m.max_holdings is not None:
            checks.append({"kind": "max_holdings", "rule": f"at most {m.max_holdings} stocks", "limit": m.max_holdings,
                           "value": len(held), "ok": len(held) <= m.max_holdings})
        if m.exclude_tickers or m.exclude_sectors:
            bad = [tk for tk in held if tk in m.exclude_tickers or md.sector(tk) in m.exclude_sectors]
            checks.append({"kind": "exclusions", "rule": "no excluded stock or sector held", "held": bad, "ok": not bad})
        checks.append({"kind": "cash", "rule": "cash never negative after fees", "value_vnd": cash_after,
                       "ok": cash_after >= 0})
        return {"trades": trades, "fees_vnd": fee_total, "cash_after_vnd": cash_after, "post_trade_nav_vnd": post_nav,
                "invested_pct_post_fee": round(100 * float(w.sum()), 3), "checks": checks,
                "all_checks_ok": all(c["ok"] for c in checks),
                "fee_rules": {"commission_pct": 100 * rules.commission, "sell_tax_pct": 100 * rules.sell_tax,
                              "lot_size": rules.lot_size,
                              "basis": "rules are checked on post-trade NAV = cash after fees + holdings"}}

    def _infeasible(self, base: dict, diag: dict) -> dict:
        return base | {"status": "infeasible", "feasibility": diag, "trades": [], "checks": [], "fees_vnd": 0.0,
                       "cash_after_vnd": base["capital_vnd"], "portfolios": {}, "quantum": {"ran": False,
                       "reason": "no feasible whole-lot portfolio"}, "_rec": None}

    # -------------------------------------------------------------- the pipeline
    def decide(self, capital: float, mandate: Mandate | None = None, shots: int = 512, seed: int = 0,
               with_textbook: bool = True, progress=None) -> dict:
        """One decision. Returns status "ok" (trades verified) or "infeasible" (with the blocking rules)."""
        from .feasibility import diagnose
        from .portfolio import NoFeasiblePortfolio

        md, ec, d = self.md, self.ec, self.date
        m = mandate or Mandate()
        say = progress or (lambda stage, **kw: None)
        t = {}
        acc = Account(cash=float(capital))
        base = {"date": str(d.date()), "capital_vnd": float(capital), "mandate": m.to_dict(),
                "universe": len(self.universe)}

        say("feasibility")
        diag = diagnose(md, d, self.universe, acc, m, ec)
        if not diag["feasible"]:
            return self._infeasible(base, diag)
        say("build_qubo")
        t0 = time.time()
        try:
            inst = build_rounding_instance(md, d, self.universe, acc, ec, m)
            t["build_qubo"] = time.time() - t0
            say("enumerate")
            t0 = time.time()
            land = landscape(inst)
            t["enumerate_all"] = time.time() - t0
        except NoFeasiblePortfolio as e:
            diag = diag | {"feasible": False, "blocking": diag["blocking"] + [{
                "code": "no_feasible_lot_combination", "rule": "combination",
                "message_en": f"No whole-lot portfolio satisfies cash and every rule ({e}).",
                "message_vi": "Không có tổ hợp lô chẵn nào vừa đủ tiền vừa thỏa mọi quy tắc.", "detail": {}}]}
            return self._infeasible(base, diag)
        n = inst.n_qubits
        excluded = [x for x in self.universe if x not in inst.tickers]
        tickers = inst.tickers
        rules = ec.rules

        # baselines for the same account (deterministic)
        say("baselines")
        prac = practitioner_target(md, d, self.universe, acc, ec, m)
        greedy = greedy_target(md, d, self.universe, acc, ec) if m.is_empty() else None
        w_cont = inst.meta["continuous_weights"]
        opt_x = _bits(land.opt_index, n)

        if n < 2:
            # Too few lot decisions for a circuit: the exact search over 2^n choices is the decision.
            x = opt_x
            new = inst.shares(x)[0]
            ex = self._execution(inst, new, m)
            ports = {"ideal (fractional shares)": self._ideal(inst, w_cont),
                     "nearest-lot rounding": self._portfolio(inst, tickers, prac),
                     "AGQO": self._portfolio(inst, tickers, dict(zip(tickers, new)))}
            mi = market_insight(md, inst, land, excluded, ec.problem.lookback_days)
            return base | ex | {
                "status": "ok", "feasibility": diag, "excluded_by_mandate": excluded,
                "market": self._market(mi), "stocks": self._stocks(inst), "register": [],
                "quantum": {"ran": False, "qubits": int(n),
                            "reason": f"only {n} lot decision(s) remain after the rules; exact search over "
                                      f"{2 ** n} choice(s) decides directly, no circuit is run",
                            "reason_vi": f"sau khi áp quy tắc chỉ còn {n} quyết định lô; tìm kiếm chính xác trên "
                                         f"{2 ** n} lựa chọn quyết định ngay, không cần chạy mạch"},
                "hamiltonian": None, "ai": None, "circuit": None,
                "result": {"found_exact_optimum": True, "states_total": int(2 ** n),
                           "states_affordable": int(land.feasible.sum())},
                "portfolios": ports, "tickers": tickers, "seconds": {k: round(v, 3) for k, v in t.items()},
                "_rec": None}

        cp = CompiledProblem(inst, land)
        mi = market_insight(md, inst, land, excluded, ec.problem.lookback_days)

        # AI guidance (k-NN over insight features -> schedule)
        say("schedule")
        f = design_features(cp)
        row = self.grid.iloc[self.model.choose(f)]
        spec = spec_of(row, ec.design.polish_iters if self.use_polish else 0, ec.design.polish_cvar_alpha, "AGQO:")

        say("qaoa")
        t0 = time.time()
        r = run_qaoa(cp, spec, ec.problem.success_gap, shots, np.random.default_rng(seed))
        t["qaoa"] = time.time() - t0
        rng = np.random.default_rng(seed + 1)
        samples = rng.choice(len(r.probs), size=shots, p=r.probs / r.probs.sum())

        gap = land.gap()
        warm = warm_start_only(cp, float(row["epsilon"]), ec.problem.success_gap, shots, np.random.default_rng(seed))
        arms = {"AGQO": r.probs, "warm start only": warm.probs, "random guessing": np.full(2 ** n, 2.0 ** -n)}
        if with_textbook:
            say("textbook")
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
        say("verify")
        best = r.best_sample if r.best_sample is not None else land.opt_index
        x = _bits(best, n)
        new = inst.shares(x)[0]
        ex = self._execution(inst, new, m)
        ports = {"ideal (fractional shares)": self._ideal(inst, w_cont),
                 "nearest-lot rounding": self._portfolio(inst, tickers, prac),
                 "AGQO": self._portfolio(inst, tickers, dict(zip(tickers, new)))}
        if greedy is not None:
            ports["greedy lot filling"] = self._portfolio(inst, tickers, greedy)

        # circuit description for drawing
        diag_terms, sel, scale = cp.phase_terms(spec)
        reg = inst.register
        angles = r.angles if len(r.angles) else initial_angles(spec)
        p = spec.layers
        top = np.argsort(-r.probs)[:12]
        e_samples = land.energy[samples]
        ok = np.isfinite(gap)
        return base | ex | {
            "status": "ok", "feasibility": diag, "excluded_by_mandate": excluded,
            "quantum": {"ran": True, "qubits": int(n)},
            "market": self._market(mi), "stocks": self._stocks(inst),
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
            "seconds": {k: round(v, 3) for k, v in t.items()}, "_rec": (inst, land, cp, spec, r),
        }

    def _ideal(self, inst, w_cont) -> dict:
        return {"weights": np.round(w_cont, 5).tolist(), "te_pct": round(float(100 * inst.tracking_error(w_cont)[0]), 3),
                "invested_pct": round(float(100 * w_cont.sum()), 2), "holdings": int((w_cont > 1e-4).sum())}

    @staticmethod
    def _market(mi) -> dict:
        nan = lambda v, k=3: None if not np.isfinite(v) else round(float(v), k)
        return {"avg_correlation": nan(mi.avg_correlation), "market_factor_share_pct": nan(100 * mi.market_factor_share, 1),
                "effective_bets": nan(mi.effective_bets, 1), "clusters": mi.clusters,
                "lot_cost_pct_median": nan(mi.lot_cost_pct_median, 2), "lot_cost_pct_max": nan(mi.lot_cost_pct_max, 2)}

    def _stocks(self, inst) -> list[dict]:
        return [{"ticker": tk, "sector": self.md.sector(tk), "price_vnd": float(pp),
                 "lot_pct": round(float(100 * self.ec.rules.lot_size * pp / inst.nav), 2)}
                for tk, pp in zip(inst.tickers, inst.prices)]

    def evidence(self, out: dict) -> dict | None:
        """Fact sheet for the explainer; None when no circuit ran (infeasible or too few lot decisions)."""
        from .experiment import _evidence

        if out.get("_rec") is None:
            return None
        return _evidence(self.md, self.date, out["_rec"], None, self.ec.problem)


if __name__ == "__main__":
    t = time.time()
    tab = build_schedule_table()
    print(f"schedule table {tab.shape} in {time.time() - t:.0f}s")
