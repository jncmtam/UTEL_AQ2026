"""Fail-closed reliability qualification and immutable final-test configuration.

These utilities cannot turn a blocked data audit or an unrun model into evidence.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
from scipy.stats import beta
from agqo.synthesis.profile import digest
from .data import audit, sha, write_json


def reliability(records, planned=72, required=0.95, confidence=0.95):
    if (
        type(planned) is not int
        or planned < 1
        or not 0 < required < 1
        or not 0 < confidence < 1
    ):
        raise ValueError("Invalid reliability protocol.")
    ids = [r.get("problem_hash") for r in records]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError(
            "Confirmation requires unique problem identities; repeated seeds are not new tasks."
        )
    if len(records) > planned:
        raise ValueError("Do not extend the frozen confirmation set until it passes.")
    if any(r.get("split") != "confirmation" for r in records):
        raise ValueError(
            "Development/pilot cases cannot qualify confirmation reliability."
        )
    attempted = [r for r in records if r.get("execution_status") == "executed"]
    success = sum(r.get("first_pass_valid") is True for r in attempted)
    n = len(attempted)
    alpha = 1 - confidence
    low = float(beta.ppf(alpha / 2, success, n - success + 1)) if success else 0.0
    high = (
        float(beta.ppf(1 - alpha / 2, success + 1, n - success)) if success < n else 1.0
    )
    complete = len(records) == planned and n == planned
    return {
        "planned_cases": planned,
        "received_records": len(records),
        "attempted": n,
        "successes": success,
        "not_executed": len(records) - n,
        "missing_records": planned - len(records),
        "observed_first_pass_rate": success / n if n else None,
        "exact_binomial_interval": [low, high],
        "confidence": confidence,
        "required_lower_bound": required,
        "status": "qualified_for_declared_task_distribution"
        if complete and low >= required
        else "failed_threshold"
        if complete
        else "incomplete",
        "financial_value_established": False,
        "assumption": "Independent draws from the frozen confirmation task distribution; different seeds alone do not justify independence.",
    }


def freeze_final_test(
    directory, data_directory, model_record, configuration, formulation_review
):
    """Write the lock only after its prerequisites; never evaluate returns here."""
    path = Path(directory)
    if (path / "test_lock.json").exists() or (path / "BLOCKED.json").exists():
        raise ValueError("Final-test lock already exists; never silently overwrite.")
    data = Path(data_directory)
    manifest = json.loads((data / "dataset_manifest.json").read_text())
    gate = audit(manifest, data)
    reasons = []
    if not gate["financial_evaluation_allowed"]:
        reasons.append("Historical market-data admission has not passed.")
    if model_record.get("status") != "qualified_for_declared_task_distribution":
        reasons.append("Model reliability is not confirmed.")
    if (
        not model_record.get("model")
        or not model_record.get("revision")
        or not model_record.get("confirmation_artifact_sha256")
    ):
        reasons.append(
            "Model checkpoint and confirmation artifact identity are incomplete."
        )
    if (
        formulation_review.get("status")
        != "accepted_for_continuous_financial_objective"
    ):
        reasons.append(
            "Primary continuous-allocation formulation fidelity is unresolved."
        )
    if not formulation_review.get("evidence_sha256"):
        reasons.append("Missing formulation evidence hash.")
    required = (
        "development_end",
        "validation_end",
        "test_start",
        "test_end",
        "prompt_hash",
        "grammar_version",
        "optimizer",
        "candidate_pooling",
        "total_budget",
        "financial_estimand",
        "comparators",
        "uncertainty_method",
    )
    if any(not configuration.get(k) for k in required):
        reasons.append("Frozen evaluation configuration is incomplete.")
    else:
        import pandas as pd

        try:
            d, v, s, e = [
                pd.Timestamp(configuration[k])
                for k in ("development_end", "validation_end", "test_start", "test_end")
            ]
            if not d < v < s <= e:
                reasons.append(
                    "Development/validation/test periods overlap or are unordered."
                )
        except ValueError:
            reasons.append("Invalid split dates.")
    if reasons:
        blocked = {
            "status": "blocked",
            "reasons": reasons,
            "data_audit": gate,
            "test_outcomes_opened": False,
            "new_inference_calls": 0,
        }
        write_json(path / "BLOCKED.json", blocked)
        return blocked
    lock = {
        "version": "final-financial-test-lock-v1",
        "status": "sealed_not_evaluated",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": model_record,
        "configuration": configuration,
        "formulation_review": formulation_review,
        "dataset_manifest_sha256": sha(data / "dataset_manifest.json"),
        "files": manifest["files"],
        "processed_prices": manifest["processed_prices"],
        "historical_test_is_not_proven_outside_llm_pretraining": True,
    }
    lock["lock_hash"] = digest(lock)
    write_json(path / "test_lock.json", lock)
    return lock


def verify_lock(lock, data_directory):
    data = Path(data_directory)
    body = {k: v for k, v in lock.items() if k != "lock_hash"}
    if lock.get("status") != "sealed_not_evaluated" or digest(body) != lock.get(
        "lock_hash"
    ):
        raise ValueError("Invalid or altered test lock.")
    if sha(data / "dataset_manifest.json") != lock["dataset_manifest_sha256"]:
        raise ValueError("Dataset changed after final-test freeze.")
    for entry in [*lock["files"], lock["processed_prices"]]:
        p = (data / entry["path"]).resolve()
        if (
            not p.is_relative_to(data.resolve())
            or not p.is_file()
            or sha(p) != entry["sha256"]
        ):
            raise ValueError("Final-test source data changed after freeze.")
    return True
