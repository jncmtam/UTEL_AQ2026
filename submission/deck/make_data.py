"""Chart data for the semifinal deck and report: one CSV per chart + SOURCES.json (source, metric, scope).

    python submission/deck/make_data.py

Reads saved evidence only (results/final for the main study, results/runs/<run_id> for follow-up runs) and the price snapshot for
the lot-cost chart. Nothing is simulated here. Edit a number by rerunning the run that produced it, then this.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent / "data"
R = ROOT / "results" / "final"
RUNS = ROOT / "results" / "runs"
PITCH = RUNS / "20261120-083954-df815a9-pitch"
SIZES = RUNS / "20261120-084148-39544db-account-sizes"
KNN = RUNS / "20261120-073008-ab60365-knn-study"
LLM32 = RUNS / "20261120-073653-2291b6a-llm-mandates"
CIRC32 = RUNS / "20261120-074358-ef91bb6-llm-circuits"
SOURCES: dict = {}


def save(name: str, df: pd.DataFrame, source: list[str], metric: str, scope: str) -> None:
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / f"{name}.csv", index=False)
    SOURCES[name] = {"source": source, "metric": metric, "scope": scope}


def main() -> None:
    from agqo.data import MarketData
    from agqo.extras import load_config

    md, ec = MarketData.load(), load_config(R)
    d = md.rebalance_dates(ec.test_start, ec.test_end)[-1]
    uni, _ = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)
    px = md.px.loc[d, uni]
    lot = pd.DataFrame({"ticker": uni, "sector": [md.sector(t) for t in uni], "price_vnd": px.values,
                        "lot_vnd": 100 * px.values})
    lot["lot_pct_of_20m"] = 100 * lot.lot_vnd / 20e6
    save("c1_lot_cost", lot.sort_values("lot_vnd", ascending=False),
         ["data/vn30/ohlcv_daily.csv (SHA-256 7f076128…3042)", "VN30 membership 2026-10-01"],
         "price of one board lot (100 shares) as % of a 20M VND account", f"close of {d.date()}, 30 usable VN30 members")

    # ---- options: ETF, odd lots, board lots (12 quarters, realised annualised TE)
    sp = pd.read_csv(R / "strategy_performance.csv", index_col=0)
    rb = pd.read_csv(R / "extras" / "robustness.csv")
    odd = rb[(rb.capital_vnd == 20e6) & (rb.scenario == "odd-lot execution, premium 0.0%")].te_odd_lot.iloc[0]
    pw = pd.read_csv(PITCH / "pitch_walks.csv").set_index("label").te_pct
    opts = pd.DataFrame([
        {"option": "ETF E1VFVN30 (buy and hold)", "te_daily_pct": sp.loc["ETF E1VFVN30", "tracking_error_ann_pct"],
         "te_weekly_pct": sp.loc["ETF E1VFVN30", "tracking_error_weekly_ann_pct"], "rules_possible": False,
         "note": "market price vs VN30 price index; ETF includes distributions and fund costs"},
        {"option": "Odd lots, modelled fills", "te_daily_pct": odd, "te_weekly_pct": None, "rules_possible": True,
         "note": "simulated execution at the close, no extra odd-lot premium; liquidity not modelled"},
        {"option": "Board lots, nearest-lot rounding, no rules", "te_daily_pct": pw["none|practitioner"], "te_weekly_pct": None,
         "rules_possible": True, "note": "20M VND"},
        {"option": "Board lots, AGQO, no rules", "te_daily_pct": pw["none|agqo"], "te_weekly_pct": None, "rules_possible": True,
         "note": "20M VND"},
        {"option": "Board lots, AGQO, no real estate + banking <= 30%", "te_daily_pct": pw["rules|agqo"], "te_weekly_pct": None,
         "rules_possible": True, "note": "20M VND"}])
    save("c2_options", opts, [str(R / "strategy_performance.csv"), str(R / "extras/robustness.csv"), PITCH.name],
         "annualised tracking error vs the VN30 price index, daily returns × √252", "12 quarterly rebalances 2024-01-02 … 2026-10-01, held to 2026-11-13")

    # ---- pitch decision (one decision, estimated TE)
    dec = json.loads((PITCH / "pitch_decision.json").read_text())["decision"]
    tick = dec["tickers"]
    rows = []
    for k, label in (("nearest-lot rounding", "Nearest-lot rounding"), ("greedy lot filling", "Greedy lot filling"),
                     ("AGQO", "AGQO"), ("ideal (fractional shares)", "Ideal (fractional shares)")):
        p = dec["portfolios"][k]
        for t, w in zip(tick, p["weights"]):
            rows.append({"method": label, "ticker": t, "weight_pct": 100 * w})
    wdf = pd.DataFrame(rows)
    save("c3_pitch_weights", wdf, [PITCH.name + "/pitch_decision.json"], "portfolio weight, % of pre-trade NAV",
         f"one decision on {dec['date']}, 20M VND, no real estate, banking ≤ 30%")
    kp = []
    for k, label in (("nearest-lot rounding", "Nearest-lot rounding"), ("greedy lot filling", "Greedy lot filling"),
                     ("AGQO", "AGQO"), ("ideal (fractional shares)", "Ideal (fractional shares)")):
        p = dec["portfolios"][k]
        kp.append({"method": label, "estimated_te_pct": p["te_pct"], "invested_pct": p["invested_pct"], "holdings": p["holdings"]})
    kp = pd.DataFrame(kp)
    save("c3_pitch_kpis", kp, [PITCH.name + "/pitch_decision.json"],
         "estimated tracking error (250-day covariance before the date, annualised); invested % of pre-trade NAV",
         f"one decision on {dec['date']}")
    agqo_trades = pd.DataFrame(dec["trades"])
    save("c3_pitch_trades", agqo_trades[["ticker", "sector", "lots", "price_vnd", "value_vnd", "fee_vnd"]],
         [PITCH.name + "/pitch_decision.json"], "AGQO buy orders", f"{dec['date']}; cash after fees "
         f"{dec['cash_after_vnd']:.0f} VND; post-trade NAV {dec['post_trade_nav_vnd']:.0f} VND")
    SOURCES["c3_pitch_trades"]["cash_after_fees_vnd"] = dec["cash_after_vnd"]
    SOURCES["c3_pitch_trades"]["fees_vnd"] = dec["fees_vnd"]
    SOURCES["c3_pitch_trades"]["post_trade_nav_vnd"] = dec["post_trade_nav_vnd"]
    SOURCES["c3_pitch_trades"]["checks"] = dec["checks"]

    # ---- persistence over 12 quarters, all account sizes, four methods
    ab = pd.DataFrame(json.loads((SIZES / "account_benchmark.json").read_text())["rows"])
    tab = ab.pivot(index="capital_vnd", columns="strategy", values="te_pct").reset_index()
    tests = pd.DataFrame(json.loads((SIZES / "account_benchmark.json").read_text())["tests"])
    save("c4_accounts", tab, [SIZES.name], "realised annualised tracking error vs VN30, %",
         "12 quarterly rebalances 2024–2026, fresh cash account per size, no rules")
    save("c4_accounts_ci", tests[["capital_vnd", "comparison", "te_a", "te_b", "diff_pp", "ci_low", "ci_high"]], [SIZES.name],
         "difference in annualised TE (pp) with 95% moving-block bootstrap CI", "12 quarters")
    pt = pd.read_csv(PITCH / "pitch_tests.csv")
    save("c4_pitch_rules", pd.concat([pw.rename("te_pct").reset_index(), ]), [PITCH.name], "realised annualised TE, %",
         "20M VND, 12 quarters, with and without the two rules")
    save("c4_pitch_ci", pt[["mandate", "comparison", "te_a", "te_b", "diff_pp", "ci_low", "ci_high"]], [PITCH.name],
         "difference in annualised TE (pp), 95% block-bootstrap CI", "20M VND, 12 quarters")

    # ---- one-stock mapping example (the pitch decision's register)
    ideal = dict(zip(tick, dec["portfolios"]["ideal (fractional shares)"]["weights"]))
    price = {s["ticker"]: s["price_vnd"] for s in dec["stocks"]}
    reg = pd.DataFrame(dec["register"])
    reg["continuous_lots"] = [ideal[t] * dec["capital_vnd"] / (100 * price[t]) for t in reg.ticker]
    reg["fixed_lots"] = reg.continuous_lots.astype(int)
    save("c5_register", reg[["qubit", "ticker", "sector", "lot_pct", "continuous_lots", "fixed_lots", "relaxed", "agqo_bit",
                             "optimal_bit", "nearest_bit"]], [PITCH.name + "/pitch_decision.json"],
         "per qubit: continuous lots from the fractional optimum, fixed lots, warm-start probability, chosen bit",
         f"{dec['date']}, 16 qubits")

    # ---- circuit comparison (main study, 12 quarters, 100M trajectory account)
    q = pd.read_csv(R / "quantum_test.csv")
    q["arm2"] = q.arm.str.replace(r"^random_s\d+$", "random_search", regex=True)
    g = q.groupby("arm2").agg(success_pct=("success_prob", lambda s: 100 * s.mean()), evaluations=("evaluations", "mean"),
                              two_qubit_gates=("two_qubit_gates", "mean"), layers=("layers", "mean")).reset_index()
    names = {"textbook": "Textbook QAOA", "warm_start_only": "Warm-start baseline", "random_search": "Random circuit search",
             "agqo": "AGQO circuit (k-NN + polish)", "frozen": "Frozen schedule", "polish_ablation": "k-NN, no polish",
             "oracle": "Oracle schedule (uses test answer)"}
    g["label"] = g.arm2.map(names)
    st = json.loads((R / "quantum_stats.json").read_text())
    save("c6_circuits", g, [str(R / "quantum_test.csv"), str(R / "quantum_stats.json")],
         "near-optimal solution probability per shot (%): feasible and normalised gap ≤ 5%",
         "12 quarters 2024–2026, 100M VND account, 16 qubits, exact noiseless statevector, 512 shots")
    SOURCES["c6_circuits"]["ratios"] = {k: v["ratio"] for k, v in st.items()}

    # ---- appendix
    sc = pd.read_csv(R / "extras" / "scaling.csv").groupby("qubits")[["warm_success", "frozen_success", "enumeration_s",
                                                                        "statevector_s"]].mean().reset_index()
    sc["ratio"] = sc.frozen_success / sc.warm_success
    save("a_scaling", sc, [str(R / "extras/scaling.csv")], "near-optimal probability per shot; enumeration and statevector seconds",
         "frozen schedule from 2023, 8–20 qubits, noiseless")
    ha = pd.read_csv(R / "extras" / "hardware_aware.csv")
    ha["ratio"] = ha.esp_model_success / ha.warm_esp_model
    save("a_noise", ha[["date", "logical_2q", "native_2q", "esp_model_success", "warm_esp_model", "ratio", "aer_noisy_success"]],
         [str(R / "extras/hardware_aware.csv")], "success under the ESP noise model (estimate), Aer noisy simulation where run",
         "noise-aware shallow circuit chosen on 2023, IBM Heron model (FakeKingston); no hardware run")
    me = json.loads((R / "llm" / "mandate_eval.json").read_text())["score"]
    ev_file = next(f for f in (LLM32 / "mandate_eval.json", LLM32 / "mandate_eval_v2.json") if f.exists())  # older runs used _v2
    v32 = json.loads(ev_file.read_text())["score"]
    save("a_llm", pd.DataFrame([
        {"set": "Set A (35 instructions)", "metric": "effective constraints correct", "llm": f"{round(me['llm_effective_pct'] * .35)}/35",
         "keyword": f"{round(me['rule_effective_pct'] * .35)}/35"},
        {"set": "Set A (35 instructions)", "metric": "strict JSON match", "llm": f"{round(me['llm_exact_pct'] * .35)}/35", "keyword": ""},
        {"set": "Set B (50 new instructions)", "metric": "end-to-end correct outcome", "llm": "49/50", "keyword": "33/50"}]),
        [str(R / "llm/mandate_eval.json"), LLM32.name], "team-written evaluation sets", "Qwen3.8-27B-FP8, temperature 0")
    kn = json.loads((KNN / "holdout_results.json").read_text())["holdout"]["arms"]
    save("a_knn", pd.DataFrame([{"arm": k, "success_pct": 100 * v["mean_success"]} for k, v in kn.items()]), [KNN.name],
         "near-optimal probability per shot (%)", "Holdout: 22 months × 5 sizes × 3 rule types, fresh accounts")
    (OUT / "SOURCES.json").write_text(json.dumps(SOURCES, indent=1, ensure_ascii=False, default=str))
    print(f"wrote {len(SOURCES)} tables to {OUT}")


if __name__ == "__main__":
    main()
