"""Preset evaluation (protocol §6) and the small-account benchmark with the price-level bound (protocol §5).

Walks and decisions run on Modal CPU (functions passed in); this module assembles and tests the results.
"""

from __future__ import annotations

import pandas as pd

from ..backtest import active_returns, performance
from ..data import MarketData
from ..stats import block_bootstrap_te_diff


def _series(r: dict) -> pd.Series:
    return pd.Series(r["values"], index=pd.to_datetime(r["dates"]))


def run_presets(run, preset_fn, walk_fn) -> dict:
    from ..demo import compile_mandate
    from ..presets import PRESETS, public

    md = MarketData.load()
    etf = md.etf_close["E1VFVN30"]
    runnable = [public(p) for p in PRESETS if p["expect"] != "clarification"]
    decisions = {r["id"]: r for r in preset_fn(runnable)}
    run.step("latest_decisions", presets=len(decisions))
    # 12-quarter walks: each feasible preset with AGQO and practitioner rounding, plus unconstrained AGQO per capital
    jobs = []
    for p in runnable:
        if decisions[p["id"]]["measured"]["status"] != "ok":
            continue
        for s in ("agqo", "practitioner"):
            jobs.append({"label": f"{p['id']}|{s}", "capital_vnd": p["capital_million"] * 1e6, "strategy": s,
                         "mandate": p["mandate"]})
    for cap in sorted({p["capital_million"] for p in runnable}):
        jobs.append({"label": f"unconstrained_{cap:g}|agqo", "capital_vnd": cap * 1e6, "strategy": "agqo", "mandate": {}})
    walks = {r["label"]: r for r in walk_fn(jobs)}
    run.step("walks", jobs=len(jobs), errors=sum("error" in r for r in walks.values()))

    out = []
    for p in [public(x) for x in PRESETS]:
        rec = {"id": p["id"], "title_vi": p["title_vi"], "capital_million": p["capital_million"], "mandate": p["mandate"],
               "expect": p["expect"]}
        if p["expect"] == "clarification":
            sector_of = {t: md.sector(t) for t in md.close.columns}
            res = compile_mandate(p["instruction_vi"], sector_of, backend="none")
            rec["measured"] = {"status": "needs_clarification" if res["needs_clarification"] else "ok",
                               "question": res.get("question"), "source": res["source"]}
            rec["outcome"] = "clarification" if res["needs_clarification"] else "parsed without a question"
            out.append(rec)
            continue
        dec = decisions[p["id"]]
        rec["measured"] = dict(dec["measured"])
        rec["decision"] = dec["decision"]
        if dec["measured"]["status"] != "ok":
            rec["outcome"] = "infeasible"
            out.append(rec)
            continue
        a, b = walks.get(f"{p['id']}|agqo"), walks.get(f"{p['id']}|practitioner")
        u = walks.get(f"unconstrained_{p['capital_million']:g}|agqo")
        if a and b and "error" not in a and "error" not in b:
            sa, sb = _series(a), _series(b)
            pa, pb = performance(sa, md.index, etf), performance(sb, md.index, etf)
            ci = block_bootstrap_te_diff(active_returns(sa, md.index), active_returns(sb, md.index))
            rec["measured"] |= {"realised_te_agqo_pct": pa["tracking_error_ann_pct"],
                                "realised_te_rounding_pct": pb["tracking_error_ann_pct"],
                                "realised_diff_pp": ci["diff_pp"], "realised_ci_pp": [ci["ci_low"], ci["ci_high"]],
                                "rule_violations_12q": a["rule_violations_at_rebalance"], "avg_holdings_12q": a["avg_holdings"]}
            if u and "error" not in u:
                pu = performance(_series(u), md.index, etf)
                rec["measured"]["rule_cost_pp"] = pa["tracking_error_ann_pct"] - pu["tracking_error_ann_pct"]
            better = ci["ci_high"] < 0
            rec["outcome"] = "favourable" if better else ("unfavourable" if ci["ci_low"] > 0 else "no clear difference")
        else:
            rec["outcome"] = "walk failed"
            rec["walk_errors"] = [w.get("error") for w in (a, b) if w and "error" in w]
        out.append(rec)
    res = {"run_id": run.run_id, "presets": out}
    run.save("presets.json", res)
    run.save("presets_summary.csv", pd.DataFrame([{"id": r["id"], "expect": r["expect"], "outcome": r["outcome"]}
                                                  | {k: v for k, v in r["measured"].items() if not isinstance(v, list)}
                                                  for r in out]))
    return res


def run_account_benchmark(run, walk_fn, capitals=(20e6, 18.18e6, 16e6, 13.33e6),
                          strategies=("practitioner", "greedy", "exact", "agqo")) -> dict:
    md = MarketData.load()
    etf = md.etf_close["E1VFVN30"]
    jobs = [{"label": f"{c:.0f}|{s}", "capital_vnd": c, "strategy": s, "mandate": {}} for c in capitals for s in strategies]
    walks = {r["label"]: r for r in walk_fn(jobs)}
    rows, tests = [], []
    for c in capitals:
        ser = {}
        for s in strategies:
            r = walks[f"{c:.0f}|{s}"]
            if "error" in r:
                rows.append({"capital_vnd": c, "strategy": s, "error": r["error"]})
                continue
            ser[s] = _series(r)
            pf = performance(ser[s], md.index, etf)
            rows.append({"capital_vnd": c, "price_factor_equivalent": 20e6 / c, "strategy": s,
                         "te_pct": pf["tracking_error_ann_pct"], "return_ann_pct": pf["return_ann_pct"],
                         "fees_vnd": r["fees_vnd"], "avg_holdings": r["avg_holdings"],
                         "avg_invested_pct": r["avg_invested_pct"]})
        for a, b in (("agqo", "practitioner"), ("agqo", "greedy"), ("exact", "practitioner"), ("agqo", "exact")):
            if a in ser and b in ser:
                ci = block_bootstrap_te_diff(active_returns(ser[a], md.index), active_returns(ser[b], md.index))
                tests.append({"capital_vnd": c, "comparison": f"{a} vs {b}", **ci})
    res = {"run_id": run.run_id, "rows": rows, "tests": tests,
           "note": "Uniformly understated historical prices by a factor f are equivalent to an account of 20M / f."}
    run.save("account_benchmark.json", res)
    run.save("account_benchmark.csv", pd.DataFrame(rows))
    run.save("account_benchmark_tests.csv", pd.DataFrame(tests))
    return res
