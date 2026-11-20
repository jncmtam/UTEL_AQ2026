"""Web API: run gating, replay labelling and errors (no Modal call is made: compute mode replay)."""

import json

import pytest
from fastapi import HTTPException

import app.server as S

J = lambda r: json.loads(r.body)


@pytest.fixture(autouse=True)
def replay_mode(monkeypatch):
    monkeypatch.setattr(S, "COMPUTE", "replay")
    monkeypatch.setattr(S, "ALLOW_LOCAL", False)


def test_meta_lists_presets_with_measurements():
    m = J(S.meta())
    ids = {p["id"] for p in m["presets"]}
    assert {"small20", "bank25_200", "cap2_20", "vague_bank"} <= ids
    assert m["fees"]["commission_pct"] > 0 and len(m["sectors"]) == 9


def test_pending_clarification_blocks_the_run():
    with pytest.raises(HTTPException) as e:
        S.run(S.RunIn(capital_million=50, clarification_pending=True))
    assert e.value.status_code == 409


def test_invalid_rules_are_rejected():
    with pytest.raises(HTTPException) as e:
        S.run(S.RunIn(capital_million=50, mandate={"max_holdings": 0}))
    assert e.value.status_code == 400


def test_preset_replay_is_labelled_and_complete():
    if not (S.APP_DATA / "presets.json").exists():
        pytest.skip("no saved preset run")
    r = J(S.run(S.RunIn(capital_million=200, mandate={"sector_caps": {"Banking": 0.25}}, preset_id="bank25_200")))
    assert r["mode"] == "replay" and r["status"] == "done"
    s = J(S.run_status(r["id"]))
    res = s["result"]
    assert res["execution"]["mode"] == "replay" and res["execution"]["run_id"]
    assert res["status"] == "ok" and res["all_checks_ok"] and res["trades"]


def test_non_preset_without_modal_is_an_error_not_a_silent_fallback():
    with pytest.raises(HTTPException) as e:
        S.run(S.RunIn(capital_million=33))
    assert e.value.status_code == 503
