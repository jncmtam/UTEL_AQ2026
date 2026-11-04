"""One diagnosed CPU recovery; reuses original GPU outputs without new inference."""

from pathlib import Path
import json
import modal
from agqo.research.live_guidance import prepare
from agqo.research.improvement import decode
from agqo.research.quantum import compile_cost
from agqo.research.frozen_numerics import freeze, bind
from agqo.research.data import write_json, sha
from agqo.research.sources import relative_sources
from agqo.synthesis.profile import digest
from agqo.synthesis.budget import configured_budget, billing_snapshot

try:
    from scripts.run_modal_pipeline import unpack_verified
except ModuleNotFoundError:
    from run_modal_pipeline import unpack_verified


def main():
    path = Path("results/research/live_guidance_v1")
    orchestration = path / "orchestration"
    recovery = orchestration / "recovery_v2"
    if (orchestration / "completed.json").exists():
        print("Completed live study retained; no CPU or GPU dispatch.")
        return
    old = json.loads((orchestration / "protocol.json").read_text())
    inputs = prepare()
    if (
        inputs["inputs_hash"] != old["inputs_hash"]
        or digest(inputs["requests"]) != old["requests_hash"]
    ):
        raise ValueError("Original financial data or exact model requests changed.")
    answers = json.loads((orchestration / "answers.json").read_text())
    for case in inputs["cases"]:
        spec = decode(case["spec"])
        h = compile_cost(spec, True)
        if h["hamiltonian_hash"] != case["hamiltonian_hash"]:
            raise ValueError(
                "Original local Hamiltonian no longer reconstructs exactly."
            )
        case["frozen_numerics"] = freeze(spec, h)
        bind(spec, case["frozen_numerics"])
        write_json(
            recovery / "canonical" / f"{case['id']}.json", case["frozen_numerics"]
        )
    inputs["inputs_hash"] = digest(inputs["cases"])
    protected = sorted(Path("agqo").rglob("*.py")) + [
        Path(__file__),
        Path("modal_research_pipeline.py"),
        Path("docs/research/LIVE_GUIDANCE_RECOVERY.md"),
    ]
    protected = relative_sources(Path.cwd(), protected)
    protocol = {
        "version": "manual-canonical-numerics-cpu-recovery-v2",
        "inputs_hash": inputs["inputs_hash"],
        "original_request_hash": old["requests_hash"],
        "original_answers_sha256": sha(orchestration / "answers.json"),
        "source_hashes": {str(p): sha(p) for p in protected},
        "new_model_calls": 0,
        "remote_run_id": "live_guidance_v1_eval2",
    }
    file = recovery / "protocol.json"
    if file.exists() and json.loads(file.read_text()) != protocol:
        raise ValueError("Recovery source/input identity changed.")
    write_json(file, protocol)
    for p in protected:
        target = recovery / "source_snapshot" / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    ledger = configured_budget(ledger_path=str(orchestration / "budget.json"))
    ledger.limit = min(ledger.limit, 10)
    dispatch = recovery / "dispatch.json"
    if dispatch.exists():
        saved = json.loads(dispatch.read_text())
        if saved.get("failed"):
            raise ValueError("Failed recovery retained; no further paid retry.")
        job, call_id = saved["job_id"], saved["call_id"]
        call = modal.FunctionCall.from_id(call_id)
    else:
        snapshot = billing_snapshot()
        write_json(recovery / "billing_before.json", snapshot)
        reserve = (
            (
                4 * snapshot["rates"]["cpu_hour_cost"]
                + 16 * snapshot["rates"]["mem_gib_hour_cost"]
            )
            * 2010
            / 3600
            * 1.25
        )
        job = ledger.reserve(
            reserve, "diagnosed_cpu_recovery_v2", snapshot, resource="cpu"
        )
        write_json(
            dispatch, {"job_id": job, "status": "dispatching", "reserved_usd": reserve}
        )
        call = modal.Function.from_name(
            "agqo-research-pipeline", "guided_study_run"
        ).spawn("live_guidance_v1_eval2", inputs, answers)
        call_id = call.object_id
        write_json(
            dispatch, {"job_id": job, "call_id": call_id, "reserved_usd": reserve}
        )
    print("Recovering CPU evaluation only", call_id, flush=True)
    try:
        response = call.get(timeout=2010)
        unpack_verified(response, path / "evaluation")
        write_json(orchestration / "download_manifest.json", response["sha256_files"])
        write_json(recovery / "receipt.json", response["summary"])
        ledger.finish(job, "completed", response["summary"])
    except Exception as exc:
        call.cancel(terminate_containers=True)
        ledger.finish(job, "failed_reservation_charged", {"reason": str(exc)})
        write_json(
            dispatch,
            {"job_id": job, "call_id": call_id, "failed": True, "reason": str(exc)},
        )
        raise
    write_json(orchestration / "billing_after.json", billing_snapshot())
    write_json(
        orchestration / "cost_report.json",
        {
            "ledger": ledger.state(),
            "reserved_usd_total": sum(
                j["reserved_usd"] for j in ledger.state()["jobs"]
            ),
            "reservation_is_not_invoice": True,
            "billing_delta_is_not_isolated_job_bill": True,
            "includes_failed_original_cpu_reservation": True,
            "new_model_calls_in_recovery": 0,
            "input_tokens": sum(
                a.get("usage", {}).get("input_tokens", 0) for a in answers
            ),
            "output_tokens": sum(
                a.get("usage", {}).get("output_tokens", 0) for a in answers
            ),
        },
    )
    write_json(orchestration / "completed.json", response["summary"])
    print(json.dumps(response["summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
