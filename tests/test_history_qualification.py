from copy import deepcopy
import json
import pandas as pd
import pytest
from agqo.research.history_audit import inspect_chart
from agqo.research.qualification import reliability, freeze_final_test, verify_lock
from agqo.research.data import candidate, sha
from agqo.synthesis.profile import digest
from agqo.synthesis.budget import MODEL_CATALOG


def chart():
    dates = pd.DatetimeIndex(["2018-01-02", "2018-01-03", "2018-01-04"])
    stamps = [
        int((d.tz_localize("America/New_York") + pd.Timedelta(hours=16)).timestamp())
        for d in dates
    ]
    close = [100.0, 99.0, 100.0]
    return {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "A"},
                    "timestamp": stamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": list(close),
                                "high": [101.0, 100.0, 101.0],
                                "low": [99.0, 98.0, 99.0],
                                "close": list(close),
                                "volume": [1000, 1000, 1000],
                            }
                        ],
                        "adjclose": [{"adjclose": [99.0, 99.0, 100.0]}],
                    },
                    "events": {"dividends": {"x": {"date": stamps[1], "amount": 1.0}}},
                }
            ]
        }
    }, dates


def test_cash_adjustment_and_noninteger_label_are_not_entitlement_certification():
    payload, sessions = chart()
    report = inspect_chart(payload, "A", sessions)
    assert report["unexplained_adjustment_changes"] == 0
    assert report["cash_adjustment_checks"] == 1
    assert report["cash_adjustment_residual_above_5e_minus_5"] == 0
    assert not report["identity_verified"] and not report["entitlements_verified"]
    source = payload["chart"]["result"][0]
    source["events"]["splits"] = {
        "x": {"date": source["timestamp"][1], "numerator": 1196, "denominator": 1000}
    }
    reviewed = inspect_chart(payload, "A", sessions)
    assert reviewed["status"] == "review_required"
    assert len(reviewed["unclassified_noninteger_split_labels"]) == 1


def test_audit_detects_missing_session_bad_ohlc_and_symbol():
    payload, sessions = chart()
    source = payload["chart"]["result"][0]
    source["meta"]["symbol"] = "OTHER"
    source["indicators"]["quote"][0]["high"][0] = 90
    report = inspect_chart(payload, "A", sessions)
    assert report["ohlc_violations"] == 1
    assert any("symbol" in x for x in report["issues"])
    extra = sessions.union(pd.DatetimeIndex(["2018-01-05"]))
    # Missing edge days are exposed by period coverage even outside observed span.
    report = inspect_chart(payload, "A", extra)
    assert report["period_coverage"]["development"]["missing_sessions"] == 1


@pytest.mark.parametrize(
    "payload", [None, [], {"chart": None}, {"chart": {"result": [None]}}]
)
def test_malformed_provider_objects_fail_closed(payload):
    report = inspect_chart(payload, "A", pd.DatetimeIndex(["2018-01-02"]))
    assert report["status"] == "invalid"
    assert report["issues"]


def test_future_price_shape_never_enters_development_diagnostics():
    payload, sessions = chart()
    source = payload["chart"]["result"][0]
    future = pd.Timestamp("2022-01-03 16:00", tz="America/New_York")
    source["timestamp"].append(int(future.timestamp()))
    q = source["indicators"]["quote"][0]
    for k in ["open", "close"]:
        q[k].append(1000.0)
    q["high"].append(1001.0)
    q["low"].append(999.0)
    q["volume"].append(1000)
    source["indicators"]["adjclose"][0]["adjclose"].append(1000.0)
    report = inspect_chart(
        payload, "A", sessions.union(pd.DatetimeIndex(["2022-01-03"]))
    )
    assert report["development_return_observations"] == 2
    assert report["development_abs_daily_return_above_25pct"] == 0
    assert report["period_coverage"]["test"]["exposure"].startswith("hygiene_only")


def confirmations(n):
    return [
        {
            "problem_hash": f"case-{i}",
            "split": "confirmation",
            "execution_status": "executed",
            "first_pass_valid": True,
        }
        for i in range(n)
    ]


def test_exact_confirmation_threshold_and_no_adaptive_sample_extension():
    report = reliability(confirmations(72))
    assert report["exact_binomial_interval"][0] > 0.95
    assert report["status"] == "qualified_for_declared_task_distribution"
    assert not report["financial_value_established"]
    failed = confirmations(72)
    failed[0]["first_pass_valid"] = False
    assert reliability(failed)["status"] == "failed_threshold"
    assert reliability(confirmations(71))["status"] == "incomplete"
    with pytest.raises(ValueError):
        reliability(confirmations(73))
    with pytest.raises(ValueError):
        reliability([*confirmations(71), confirmations(1)[0]])
    records = confirmations(72)
    records[0]["execution_status"] = "not_dispatched"
    assert reliability(records)["status"] == "incomplete"


def test_final_test_remains_blocked_without_data_model_and_faithfulness(tmp_path):
    data = tmp_path / "data"
    candidate(data)
    result = freeze_final_test(tmp_path / "lock", data, {}, {}, {})
    assert result["status"] == "blocked" and not result["test_outcomes_opened"]
    assert not (tmp_path / "lock/test_lock.json").exists()
    assert any("formulation" in x for x in result["reasons"])


def test_data_and_lock_changes_are_detected(tmp_path):
    # Integrity mechanism fixture only; not a qualified financial/model result.
    data = tmp_path / "data"
    data.mkdir()
    file = data / "source.json"
    file.write_text("{}")
    manifest = data / "dataset_manifest.json"
    manifest.write_text("{}")
    entry = {"path": "source.json", "sha256": sha(file)}
    lock = {
        "status": "sealed_not_evaluated",
        "dataset_manifest_sha256": sha(manifest),
        "files": [entry],
        "processed_prices": entry,
    }
    lock["lock_hash"] = digest(lock)
    assert verify_lock(lock, data)
    file.write_text('{"changed":true}')
    with pytest.raises(ValueError):
        verify_lock(lock, data)
    bad = deepcopy(lock)
    bad["status"] = "completed"
    with pytest.raises(ValueError):
        verify_lock(bad, data)


def test_qiskit_checkpoint_uses_hf_layout_compatible_backend():
    metadata = json.load(open("results/research/model_artifact_audit_v1.json"))
    model = next(m for m in metadata["models"] if m["key"] == "mistral24q")
    assert "config.json" in model["files"] and "params.json" in model["files"]
    assert "tekken.json" in model["files"]
    assert any(
        name.startswith("model-") and name.endswith(".safetensors")
        for name in model["files"]
    )
    assert not any(
        name.startswith("consolidated") and name.endswith(".safetensors")
        for name in model["files"]
    )
    assert "tokenizer.json" in model["files"]
    config = MODEL_CATALOG["mistral24q"]["engine_kwargs"]
    assert config["config_format"] == "hf" and config["tokenizer_mode"] == "hf"
