"""Reproduce the product failure modes reported against V3.1 and probe nearby edge cases.

Each case runs the real decision pipeline (`Demo.decide`) and then re-checks the result with an
independent post-trade audit written here, so the audit does not share code with the checks it tests:

  post-trade NAV  = cash after fees + market value of the new holdings  (= NAV - fees)
  weight_i        = value_i / post-trade NAV
  a cap holds     if the summed weight is <= cap (no tolerance beyond float rounding, 1e-12)

Run on Modal CPU:  modal run modal_research.py::reproduce
"""

from __future__ import annotations

import json
import traceback

import numpy as np

from ..config import RESULTS_DIR
from ..mandate import Mandate


def audit(out: dict, md, m: Mandate) -> dict:
    """Independent post-trade compliance audit of one decision."""
    trades = out["trades"]
    value = {t["ticker"]: t["value_vnd"] for t in trades}
    post_nav = out["cash_after_vnd"] + sum(value.values())
    w = {t: v / post_nav for t, v in value.items()}
    rows = []
    for sec, cap in m.sector_caps.items():
        tot = sum(v for t, v in w.items() if md.sector(t) == sec)
        rows.append({"rule": f"{sec} <= {cap:.2%}", "post_fee_weight": tot, "ok": tot <= cap + 1e-12})
    if m.max_weight_per_stock is not None:
        mx = max(w.values(), default=0.0)
        rows.append({"rule": f"each stock <= {m.max_weight_per_stock:.2%}", "post_fee_weight": mx,
                     "ok": mx <= m.max_weight_per_stock + 1e-12})
    if m.min_cash_pct is not None:
        cash_w = out["cash_after_vnd"] / post_nav
        rows.append({"rule": f"cash >= {m.min_cash_pct}%", "post_fee_weight": cash_w,
                     "ok": cash_w >= m.min_cash_pct / 100 - 1e-12})
    if m.max_holdings is not None:
        rows.append({"rule": f"holdings <= {m.max_holdings}", "post_fee_weight": None, "ok": len(w) <= m.max_holdings})
    bad = [t for t in w if t in m.exclude_tickers or md.sector(t) in m.exclude_sectors]
    rows.append({"rule": "no excluded names", "post_fee_weight": None, "ok": not bad})
    rows.append({"rule": "cash >= 0", "post_fee_weight": None, "ok": out["cash_after_vnd"] >= 0})
    return {"post_trade_nav_vnd": post_nav, "fees_vnd": out["fees_vnd"], "rules": rows,
            "all_ok": all(r["ok"] for r in rows)}


def _case(d, name: str, capital: float, m: Mandate) -> dict:
    rec = {"case": name, "capital_vnd": capital, "mandate": m.to_dict()}
    try:
        out = d.decide(capital, m, with_textbook=False)
    except Exception as e:                                   # the failure itself is the evidence
        return rec | {"outcome": "exception", "error": f"{type(e).__name__}: {e}",
                      "traceback": traceback.format_exc()[-2500:]}
    a = audit(out, d.md, m)
    app_ok = all(c["ok"] for c in out["checks"])
    status = out.get("status", "ok")
    rec |= {"outcome": "decision", "status": status, "app_checks": out["checks"], "app_all_ok": app_ok,
            "audit": a, "holdings": len(out["trades"]), "cash_after_vnd": out["cash_after_vnd"],
            "fees_vnd": out["fees_vnd"],
            "app_says_ok_but_audit_fails": bool(app_ok and not a["all_ok"]),
            "infeasibility": out.get("infeasibility")}
    return rec


EDGE_CASES = [
    ("reported: 200M, banking <= 25%", 200e6, Mandate(sector_caps={"Banking": 0.25})),
    ("reported: hold at most one stock (20M)", 20e6, Mandate(max_holdings=1)),
    ("hold at most one stock (100M)", 100e6, Mandate(max_holdings=1)),
    ("hold at most two stocks (100M)", 100e6, Mandate(max_holdings=2)),
    ("20M, banking <= 25%", 20e6, Mandate(sector_caps={"Banking": 0.25})),
    ("500M, banking <= 25%", 500e6, Mandate(sector_caps={"Banking": 0.25})),
    ("100M, each stock <= 10%", 100e6, Mandate(max_weight_per_stock=0.10)),
    ("20M, each stock <= 2% (below one lot of every stock)", 20e6, Mandate(max_weight_per_stock=0.02)),
    ("100M, keep 10% cash", 100e6, Mandate(min_cash_pct=10.0)),
    ("50M, exclude every sector", 50e6, Mandate(exclude_sectors=["Aviation", "Banking", "Brokerage", "Consumer",
                                                                 "Energy", "Insurance", "Materials",
                                                                 "Real estate", "Technology"])),
    ("5M, no rules (smallest allowed account)", 5e6, Mandate()),
    ("review: 20M, <= 12 holdings, <= 10% each, >= 5% cash", 20e6,
     Mandate(max_holdings=12, max_weight_per_stock=0.10, min_cash_pct=5.0)),
    ("review: 100M, >= 1.30% cash", 100e6, Mandate(min_cash_pct=1.30)),
    ("review: 100M, >= 1.30% cash, banking <= 30%", 100e6, Mandate(min_cash_pct=1.30, sector_caps={"Banking": 0.30})),
    ("pitch: 20M, no real estate, banking <= 30%", 20e6,
     Mandate(exclude_sectors=["Real estate"], sector_caps={"Banking": 0.30})),
]


def verifier_swap_case() -> dict:
    """The explanation check must reject two correct numbers attached to the wrong strategies."""
    from ..llm.tasks import describe_evidence, verify_explanation

    ev = describe_evidence(json.loads((RESULTS_DIR / "evidence.json").read_text())[-1])
    te = ev["tracking_error_vs_vn30_index_pct"]
    a, b = te["agqo_whole_lot_portfolio"], te["nearest_lot_rounding_portfolio"]
    fmt = lambda v: f"{v:.2f}".replace(".", ",")
    good = (f"Sai số bám so với chỉ số VN30 của danh mục lô chẵn AGQO là {fmt(a)}%, "
            f"còn cách làm tròn từng mã về lô gần nhất là {fmt(b)}%.")
    swapped = (f"Sai số bám so với chỉ số VN30 của danh mục lô chẵn AGQO là {fmt(b)}%, "
               f"còn cách làm tròn từng mã về lô gần nhất là {fmt(a)}%.")
    unit = f"Sai số bám so với chỉ số VN30 của danh mục lô chẵn AGQO là {fmt(a)} lô."
    mk = lambda s: {"summary_vi": s, "trade_notes": [], "risk_notes_vi": ["Giá có thể biến động."]}
    return {"evidence_date": ev["date"], "agqo_te": a, "rounding_te": b,
            "correct": {"text": good, "check": verify_explanation(mk(good), ev)},
            "swapped": {"text": swapped, "check": verify_explanation(mk(swapped), ev)},
            "wrong_unit": {"text": unit, "check": verify_explanation(mk(unit), ev)}}


def parser_cases(d) -> list[dict]:
    """Keyword-fallback behaviour on negations and vague instructions (the LLM path is tested in llm runs)."""
    from ..mandate import rule_clarification, rule_parse

    tk = set(d.sector_of)
    out = []
    for text in ("Đừng bỏ VIC", "Không bỏ ngân hàng, chỉ bỏ VRE", "Tôi muốn ít rủi ro hơn", "Bỏ VIC"):
        m = rule_parse(text, tk)
        try:
            q = rule_clarification(text, tk)
        except TypeError:
            q = rule_clarification(text)
        out.append({"text": text, "mandate": m.to_dict(), "needs_clarification": q[0], "question": q[1]})
    return out


def clarification_case(d) -> dict:
    """What the V3.1 flow does with a vague instruction: the logged Qwen answer and the app path."""
    from ..demo import compile_mandate

    text = "Đừng mua quá nhiều cổ phiếu ngân hàng"
    res = compile_mandate(text, d.sector_of, backend="none")
    return {"instruction": text, "source": res["source"], "needs_clarification": res["needs_clarification"],
            "question": res.get("question"), "mandate": res["mandate"],
            "v31_frontend": "app/static/app.js run(): renderMandate(mres); await decideAndShow(capital, mres.mandate) "
                            "runs unconditionally, so the trade list of the unconstrained portfolio is shown "
                            "while the question is pending."}


def reproduce(run) -> dict:
    from ..demo import Demo

    d = Demo()
    run.log(f"demo loaded: date {d.date.date()}, {len(d.universe)} usable members")
    cases = []
    for name, cap, m in EDGE_CASES:
        c = _case(d, name, cap, m)
        cases.append(c)
        tag = c["outcome"] if c["outcome"] == "exception" else (
            "APP OK / AUDIT FAIL" if c["app_says_ok_but_audit_fails"] else f"status={c['status']} audit_ok={c['audit']['all_ok']}")
        run.log(f"  {name}: {tag}")
    out = {"cases": cases, "verifier_swap": verifier_swap_case(), "clarification": clarification_case(d),
           "parser": parser_cases(d)}
    run.save("product_failures.json", out)
    n_exc = sum(c["outcome"] == "exception" for c in cases)
    n_silent = sum(c.get("app_says_ok_but_audit_fails", False) for c in cases)
    sw = out["verifier_swap"]["swapped"]["check"]["ok"]
    run.step("reproduce", exceptions=n_exc, silent_cap_breaches=n_silent, verifier_accepts_swap=sw)
    return {"exceptions": n_exc, "silent_cap_breaches": n_silent, "verifier_accepts_swap": sw,
            "infeasible_with_reason": sum(c.get("status") == "infeasible" for c in cases)}


def _np(o):
    return o.item() if isinstance(o, np.generic) else o
