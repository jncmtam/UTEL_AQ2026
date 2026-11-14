import json

from agqo.guide import (
    POLICIES,
    PROMPT_CACHE_VERSION,
    CachedGuide,
    create_guide_prompt,
    decision_json_schema,
    controller_system_prompt,
    repair_guidance,
    validate_guidance,
)
from agqo.insights import insight_code_rules
from agqo.knowledge import CORPUS_VERSION
from agqo.walkforward import _supervise_policy_proposal


def _payload():
    return {
        "as_of_date": "2026-08-31",
        "market": {
            "ai_high_volatility_probability": 0.72,
            "mean_pairwise_correlation_252d": 0.61,
            "volatility_ratio_20d_to_120d": 1.4,
            "cross_sectional_20d_return_dispersion": 0.06,
            "bank_fraction_of_eligible_stocks": 0.30,
            "candidate_median_daily_traded_value_proxy_vnd": 1_000_000_000,
        },
        "submodels": {
            "regime_classifier": {
                "reliability_to_date": {
                    "matured_monthly_signals": 8,
                    "brier_skill_vs_training_prevalence": 0.04,
                }
            }
        },
        "eligible_policy_ids": ["n12_balanced_xy_ring_p1"],
        "policy_candidates": [
            {"id": "n12_balanced_xy_ring_p1", "n": 12, "mixer": "XY", "layout": "ring", "p": 1}
        ],
        "insight_code_rules": insight_code_rules(333_333_333.33),
        "evidence_ids": ["MKT:VOLATILITY", "MKT:CROSS_SECTION", "MKT:LIQUIDITY"],
        "evidence": {
            "MKT:VOLATILITY": {"p_high_volatility": 0.72},
            "MKT:CROSS_SECTION": {"mean_correlation": 0.61},
            "MKT:LIQUIDITY": {"median_daily_value_vnd": 1_000_000_000},
        },
    }


def test_prompt_is_english_grounded_and_has_per_signal_allowlists():
    payload = _payload()
    prompt = controller_system_prompt() + create_guide_prompt(payload)
    enriched = json.loads(create_guide_prompt(payload))
    assert "not a financial analyst" in prompt
    assert "Sharpe" in prompt and "normalized objective regret" in prompt
    assert "n12_balanced_xy_ring_p1" in prompt
    assert "logical two-qubit gates" in prompt
    assert enriched["local_knowledge_base_version"] == CORPUS_VERSION
    assert enriched["response_schema"]["properties"]["policy_id"]["enum"] == [
        "n12_balanced_xy_ring_p1"
    ]
    assert set(enriched["allowed_insight_codes"]) == {
        "high_volatility", "volatility_rising", "high_correlation", "high_dispersion"
    }
    note_ids = {note["id"] for note in enriched["method_notes"]}
    assert len(note_ids) == 7
    assert {
        "AGQO-METRICS-01",
        "AGQO-DATA-01",
        "AGQO-FEATURES-01",
        "AGQO-REGIME-01",
        "AGQO-BENCHMARK-01",
        "AGQO-QAOA-01",
        "AGQO-OBJECTIVE-01",
    }.issubset(note_ids)
    assert all(note["id"] in prompt for note in enriched["method_notes"])
    assert not any(char in prompt for char in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")


def test_schema_and_validator_enforce_policy_insight_and_evidence_allowlists():
    payload = _payload()
    enriched = json.loads(create_guide_prompt(payload))
    schema = decision_json_schema(
        set(enriched["eligible_policy_ids"]),
        set(enriched["evidence_ids"]),
        set(enriched["allowed_insight_codes"]),
    )
    assert schema["properties"]["policy_id"]["enum"] == ["n12_balanced_xy_ring_p1"]
    decision = validate_guidance(
        {
            "policy_id": "n12_balanced_xy_ring_p1",
            "insight_codes": ["high_volatility", "high_correlation"],
            "evidence_ids": ["MKT:VOLATILITY", "MKT:CROSS_SECTION"],
        },
        set(enriched["evidence_ids"]),
        set(enriched["eligible_policy_ids"]),
        set(enriched["allowed_insight_codes"]),
    )
    assert decision["policy_id"] == "n12_balanced_xy_ring_p1"
    try:
        validate_guidance(
            {
                **decision,
                "policy_id": sorted(set(POLICIES) - {"n12_balanced_xy_ring_p1"})[0],
            },
            set(enriched["evidence_ids"]),
            set(enriched["eligible_policy_ids"]),
            set(enriched["allowed_insight_codes"]),
        )
    except ValueError as exc:
        assert "không được phép" in str(exc)
    else:
        raise AssertionError("A policy outside the per-signal allow-list was accepted.")


def test_malformed_llm_fields_are_removed_and_safe_defaults_are_used():
    repaired, fields = repair_guidance(
        {
            "policy_id": "made_up_policy",
            "insight_codes": ["high_volatility", "unknown_insight"],
            "risk_flags": ["high_correlation", "unknown_flag"],
            "evidence_ids": ["MKT:NOT_REAL"],
            "rationale": "An ungrounded explanation.",
        },
        {"MKT:VOLATILITY"},
        {"n12_balanced_xy_ring_p1"},
        {"mixed_signals"},
    )
    assert repaired["policy_id"] == "n12_balanced_xy_ring_p1"
    assert repaired["insight_codes"] == ["mixed_signals"]
    assert repaired["evidence_ids"] == ["MKT:VOLATILITY"]
    assert "risk_flags" not in repaired and "rationale" not in repaired
    assert {
        "policy_id_to_warmup_default",
        "unsupported_free_text_fields_removed",
        "unknown_insight_codes_removed",
        "evidence_id_defaulted",
    }.issubset(fields)

    grounded, repairs = repair_guidance(
        {
            "policy_id": "n12_balanced_xy_ring_p1",
            "insight_codes": ["unsupported_code"],
            "evidence_ids": ["MKT:VOLATILITY"],
        },
        {"MKT:VOLATILITY"},
        {"n12_balanced_xy_ring_p1"},
        {"volatility_rising"},
    )
    assert grounded["insight_codes"] == ["volatility_rising"]
    assert "insight_codes_defaulted" in repairs


def test_policy_supervisor_uses_warmup_baseline_with_insufficient_history():
    policy_ids = list(POLICIES)
    chosen, reason, evidence = _supervise_policy_proposal(
        policy_ids[0], "n12_balanced_xy_ring_p1", {}, []
    )
    assert chosen == "n12_balanced_xy_ring_p1"
    assert reason is not None and "fewer than 6" in reason
    assert evidence["proposed"]["completed_periods"] == 0


def test_guide_cache_discards_entries_from_older_prompt_versions(tmp_path):
    cache_path = tmp_path / "decisions.json"
    cache_path.write_text(
        json.dumps({
            "old": {"prompt_version": "agqo-prompt-v8-en-rag-submodel-allowlisted-structured"},
            "current": {"prompt_version": PROMPT_CACHE_VERSION},
        }),
        encoding="utf-8",
    )
    guide = CachedGuide(lambda _: {}, cache_path)
    assert list(guide.cache) == ["current"]
