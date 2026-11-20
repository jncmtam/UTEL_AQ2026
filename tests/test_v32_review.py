"""Regressions for the semifinal review findings (run on Modal CPU: several tests simulate a circuit)."""

import json

import pytest
from fastapi import HTTPException

from agqo.config import RESULTS_DIR
from agqo.mandate import Mandate, rule_clarification, rule_parse, ticker_intents

TK = {"VIC", "VHM", "VRE", "HPG", "GAS", "FPT", "SSI", "VJC"}


@pytest.fixture(scope="module")
def demo():
    from agqo.demo import Demo

    return Demo()


# ---------------------------------------------------------------- keyword parser: negation and vagueness
@pytest.mark.parametrize("text,excluded", [
    ("Đừng bỏ VIC", []), ("Không loại VIC", []), ("Giữ VIC, bỏ VRE", ["VRE"]), ("Bỏ VIC", ["VIC"]),
    ("Không mua VIC, VHM, VRE", ["VHM", "VIC", "VRE"]), ("Không nắm giữ HPG và GAS", ["GAS", "HPG"]),
])
def test_negated_exclusion_is_preserved(text, excluded):
    assert rule_parse(text, TK).exclude_tickers == excluded


def test_negated_sector_exclusion_and_unclear_ticker():
    assert rule_parse("Không bỏ ngân hàng, chỉ bỏ VRE", TK).exclude_sectors == []
    assert ticker_intents("Tôi thích VIC", TK) == {"VIC": "unclear"}
    q, text = rule_clarification("Tôi thích VIC", TK)
    assert q and "VIC" in text


def test_vague_risk_request_asks():
    q, text = rule_clarification("Tôi muốn ít rủi ro hơn", TK)
    assert q and text.endswith("?")
    assert rule_parse("Tôi muốn ít rủi ro hơn", TK).is_empty()


# ---------------------------------------------------------------- decisions on the reviewed cases
def test_small_account_with_tight_limits_is_explained(demo):
    m = Mandate(max_holdings=12, max_weight_per_stock=0.10, min_cash_pct=5.0)
    out = demo.decide(20e6, m, with_textbook=False)
    assert out["status"] == "ok" and out["all_checks_ok"]
    buys = [t for t in out["trades"] if t["action"] == "buy"]
    notes = [n["code"] for n in out["feasibility"]["notes"]]
    assert buys or "no_lot_fits" in notes                 # never a silent all-cash result
    assert all(t["value_vnd"] / out["post_trade_nav_vnd"] <= 0.10 + 1e-12 for t in buys)


def test_cash_floor_uses_one_nav_definition(demo):
    from agqo.research.repro import audit

    m = Mandate(min_cash_pct=1.30)
    out = demo.decide(100e6, m, with_textbook=False)
    row = next(c for c in out["checks"] if c["kind"] == "min_cash_pct")
    a = next(r for r in audit(out, demo.md, m)["rules"] if r["rule"].startswith("cash >="))
    assert abs(row["value_pct"] - 100 * a["post_fee_weight"]) < 1e-3   # page check = independent audit
    assert row["ok"] == a["ok"] is True and a["post_fee_weight"] >= 0.013


def test_constrained_greedy_obeys_the_same_rules(demo):
    m = Mandate(exclude_sectors=["Real estate"], sector_caps={"Banking": 0.30})
    out = demo.decide(20e6, m, with_textbook=False)
    g = out["portfolios"]["greedy lot filling"]
    w = dict(zip(out["tickers"], g["weights"]))
    assert sum(v for t, v in w.items() if demo.md.sector(t) == "Banking") <= 0.30 + 1e-9
    assert not any(demo.md.sector(t) == "Real estate" and v > 0 for t, v in w.items())


# ---------------------------------------------------------------- explanations
def test_published_example_with_false_market_claim_is_rejected_and_replaced():
    from agqo.llm.fallback import deterministic_explanation
    from agqo.llm.tasks import describe_evidence, verify_explanation

    ex = json.loads((RESULTS_DIR / "llm" / "explanations.json").read_text())["rows"][-1]
    ev = describe_evidence({e["date"]: e for e in json.loads((RESULTS_DIR / "evidence.json").read_text())}[ex["date"]])
    check = verify_explanation(ex["explanation"], ev)
    assert not check["ok"] and check["claim_issues"]
    for e in json.loads((RESULTS_DIR / "evidence.json").read_text()):
        e = describe_evidence(e)
        assert verify_explanation(deterministic_explanation(e), e)["ok"]


# ---------------------------------------------------------------- confirmation gate
def test_text_derived_rules_need_confirmation(monkeypatch):
    import app.server as S

    monkeypatch.setattr(S, "COMPUTE", "replay")
    with pytest.raises(HTTPException) as e:
        S.run(S.RunIn(capital_million=20, mandate={"exclude_tickers": ["HPG"]}, sources={"exclude_tickers": "text"},
                      constraints_confirmed=False))
    assert e.value.status_code == 409
