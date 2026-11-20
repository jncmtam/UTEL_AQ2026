"""Regression tests for the product failure modes reproduced in agent.md (run on Modal CPU:
`pytest_suite` in modal_research.py). Several tests run the decision pipeline, which simulates a circuit."""

import json

import numpy as np
import pytest

from agqo.backtest import Account, build_rounding_instance
from agqo.config import RESULTS_DIR, ExperimentConfig
from agqo.data import MarketData
from agqo.llm.tasks import describe_evidence, verify_explanation
from agqo.mandate import Mandate, rule_clarification
from agqo.portfolio import all_bitstrings, landscape

EC = ExperimentConfig()


@pytest.fixture(scope="module")
def demo():
    from agqo.demo import Demo

    return Demo()


@pytest.fixture(scope="module")
def market():
    return MarketData.load()


def _post_fee_bank(out, md) -> float:
    nav = out["cash_after_vnd"] + sum(t["value_vnd"] for t in out["trades"])
    return sum(t["value_vnd"] for t in out["trades"] if md.sector(t["ticker"]) == "Banking") / nav


# ---------------------------------------------------------------- caps on the post-trade NAV
def test_every_state_obeys_caps_on_post_trade_nav(market):
    md = market
    d = md.rebalance_dates(EC.test_start, EC.test_end)[-1]
    uni, _ = md.universe(d, 250, 180)
    m = Mandate(sector_caps={"Banking": 0.25}, min_cash_pct=5.0)
    inst = build_rounding_instance(md, d, uni, Account(cash=200e6), EC, m)
    X = all_bitstrings(inst.n_qubits)
    W = inst.post_trade_weights(X)
    bank = np.array([md.sector(t) == "Banking" for t in inst.tickers])
    assert (W[:, bank].sum(1) <= 0.25 + 1e-12).all()             # cap-safe register, post-fee basis
    land = landscape(inst)
    assert land.feasible.any()
    # the cash floor is not cap-safe by construction (overspending states exist); it is checked exactly
    assert (W[land.feasible].sum(1) <= 0.95 + 1e-12).all() and (W.sum(1) > 0.95).any()
    nav_post = inst.post_trade_nav(X)
    assert np.allclose(nav_post, inst.nav - inst.fees(X))


def test_reported_200m_banking_cap_holds_after_fees(demo):
    m = Mandate(sector_caps={"Banking": 0.25})
    out = demo.decide(200e6, m, with_textbook=False)
    assert out["status"] == "ok" and out["all_checks_ok"]
    assert _post_fee_bank(out, demo.md) <= 0.25 + 1e-12
    row = next(c for c in out["checks"] if c["kind"] == "sector_cap")
    assert row["value_pct"] <= 25.0 + 1e-9


def test_independent_audit_agrees_with_app_checks(demo):
    from agqo.research.repro import audit

    for cap, m in [(20e6, Mandate(max_weight_per_stock=0.12)), (100e6, Mandate(min_cash_pct=10.0)),
                   (500e6, Mandate(sector_caps={"Banking": 0.25}, exclude_sectors=["Real estate"]))]:
        out = demo.decide(cap, m, with_textbook=False)
        assert out["status"] == "ok"
        assert out["all_checks_ok"] == audit(out, demo.md, m)["all_ok"] is True


# ---------------------------------------------------------------- edge cases and infeasible requests
@pytest.mark.parametrize("capital", [20e6, 100e6])
def test_hold_at_most_one_stock(demo, capital):
    out = demo.decide(capital, Mandate(max_holdings=1), with_textbook=False)
    assert out["status"] == "ok" and out["all_checks_ok"]
    assert len([t for t in out["trades"] if t["action"] == "buy"]) == 1
    assert out["quantum"]["ran"] is False and "exact search" in out["quantum"]["reason"]


def test_two_stocks_still_runs_the_circuit(demo):
    out = demo.decide(100e6, Mandate(max_holdings=2), with_textbook=False)
    assert out["status"] == "ok" and out["all_checks_ok"] and len(out["trades"]) <= 2
    assert out["quantum"]["ran"] is True and out["circuit"]["qubits"] == 2


@pytest.mark.parametrize("capital,m,code", [
    (20e6, Mandate(max_weight_per_stock=0.02), "per_stock_cap_below_one_lot"),
    (50e6, Mandate(exclude_sectors=["Aviation", "Banking", "Brokerage", "Consumer", "Energy", "Insurance",
                                    "Materials", "Real estate", "Technology"]), "empty_universe"),
    (5e6, Mandate(min_cash_pct=95.0), "no_affordable_lot"),
])
def test_infeasible_request_names_the_blocking_rule(demo, capital, m, code):
    out = demo.decide(capital, m, with_textbook=False)
    assert out["status"] == "infeasible" and out["trades"] == []
    codes = [r["code"] for r in out["feasibility"]["blocking"]]
    assert code in codes
    assert all(r["message_vi"] and r["message_en"] for r in out["feasibility"]["blocking"])


def test_conflicting_rules_are_reported_not_fatal(demo):
    m = Mandate(exclude_sectors=["Banking"], sector_caps={"Banking": 0.3})
    out = demo.decide(100e6, m, with_textbook=False)
    assert out["status"] == "ok"
    assert "exclusion_overrides_cap" in [n["code"] for n in out["feasibility"]["notes"]]
    assert not any(demo.md.sector(t["ticker"]) == "Banking" for t in out["trades"])


# ---------------------------------------------------------------- clarification
def test_keyword_fallback_does_not_read_banking_as_aviation():
    from agqo.mandate import rule_parse

    m = rule_parse("bỏ HPG, ngân hàng không quá 28% và giữ 7% tiền mặt", {"HPG", "VJC"})
    assert m.exclude_sectors == [] and m.sector_caps == {"Banking": 0.28} and m.exclude_tickers == ["HPG"]
    assert rule_parse("Tránh hàng không", {"VJC"}).exclude_sectors == ["Aviation"]


def test_keyword_fallback_asks_instead_of_guessing():
    q, text = rule_clarification("Đừng mua quá nhiều cổ phiếu ngân hàng")
    assert q and "ngân hàng" in text and text.endswith("?")
    assert rule_clarification("Ngân hàng tối đa 30%") == (False, None)
    assert rule_clarification("Tôi muốn ít rủi ro hơn")[0]


# ---------------------------------------------------------------- explanation attribution
def _evidence():
    return describe_evidence(json.loads((RESULTS_DIR / "evidence.json").read_text())[-1])


def _note(s):
    return {"summary_vi": s, "trade_notes": [], "risk_notes_vi": ["Giá cổ phiếu có thể biến động."]}


def test_verifier_rejects_swapped_strategy_numbers():
    ev = _evidence()
    te = ev["tracking_error_vs_vn30_index_pct"]
    a, b = (f"{te[k]:.2f}".replace(".", ",") for k in ("agqo_whole_lot_portfolio", "nearest_lot_rounding_portfolio"))
    good = f"Sai số bám so với chỉ số VN30 của danh mục AGQO là {a}%, còn cách làm tròn lô gần nhất là {b}%."
    swap = f"Sai số bám so với chỉ số VN30 của danh mục AGQO là {b}%, còn cách làm tròn lô gần nhất là {a}%."
    compact = f"So với chỉ số VN30, AGQO có sai số bám {b}% so với {a}% của cách làm tròn lô gần nhất."
    assert verify_explanation(_note(good), ev)["ok"]
    for bad in (swap, compact):
        r = verify_explanation(_note(bad), ev)
        assert not r["ok"] and {i["type"] for i in r["attribution_issues"]} == {"misattributed"}


def test_verifier_rejects_wrong_and_missing_units():
    ev = _evidence()
    a = f"{ev['tracking_error_vs_vn30_index_pct']['agqo_whole_lot_portfolio']:.2f}".replace(".", ",")
    r = verify_explanation(_note(f"Sai số bám so với chỉ số VN30 của danh mục AGQO là {a} lô."), ev)
    assert not r["ok"] and r["attribution_issues"][0]["type"] == "wrong_unit"
    r = verify_explanation(_note(f"Sai số bám so với chỉ số VN30 của danh mục AGQO là {a}."), ev)
    assert not r["ok"] and r["attribution_issues"][0]["type"] == "missing_unit"


def test_verifier_keeps_accepting_the_archived_explanations():
    """No new false alarms from the attribution check on the 12 live Qwen explanations of the main study. The only new
    rejections are the three that state the market forbids odd lots (a false claim, now caught)."""
    ex = json.loads((RESULTS_DIR / "llm" / "explanations.json").read_text())
    evs = {e["date"]: describe_evidence(e) for e in json.loads((RESULTS_DIR / "evidence.json").read_text())}
    newly = []
    for row in ex["rows"]:
        c = verify_explanation(row["explanation"], evs[row["date"]])
        assert not c["attribution_issues"]
        if c["ok"] != row["check"]["ok"]:
            assert c["claim_issues"] and row["check"]["ok"]
            newly.append(row["date"])
    assert newly == ["2024-07-01", "2025-01-02", "2026-10-01"]
