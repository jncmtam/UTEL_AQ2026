"""Freeze, reserve, dispatch once, and retrieve the live GPU optimization study."""

from pathlib import Path
import argparse
import json
import modal
from agqo.research.data import sha, write_json
from agqo.research.edge_program import prepare
from agqo.research.gpu_optimization import VERSION, RUN_ID
from agqo.synthesis.profile import digest
from agqo.synthesis.budget import billing_snapshot, configured_budget, job_reservation

try:
    from scripts.run_modal_pipeline import unpack_verified
except ModuleNotFoundError:
    from run_modal_pipeline import unpack_verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    path = Path("results/research") / RUN_ID
    orchestration = path / "orchestration"
    if (orchestration / "completed.json").exists():
        print("Completed live GPU result retained; no new paid dispatch.")
        return
    files = sorted(Path("agqo").rglob("*.py"))
    protocol = {
        "version": VERSION, "run_id": RUN_ID, "model_key": "coder30",
        "evidence": "docs/research/LIVE_GPU_OPTIMIZATION_PROTOCOL.md",
        "package_source_hashes": {str(p): sha(p) for p in files},
        "controller_hashes": {str(p): sha(p) for p in [Path(__file__).resolve(), Path("modal_live_optimizer.py"), Path("docs/research/LIVE_GPU_OPTIMIZATION_PROTOCOL.md")]},
        "rounds": 3, "requests_per_round": 4, "selection_seed": 11,
        "evaluation_seeds": [23, 47], "reservation_limit_usd": 15,
        "financial_qualification": False, "gpu_simulation_required": True,
    }
    inputs = prepare()
    inputs["requests"] = []  # New prompts are generated live from measured feedback.
    inputs["live_protocol"] = protocol
    inputs["dataset_manifest"] = {
        "source": json.loads(Path("data/published_us/dataset_manifest.json").read_text()),
        "case_source_columns": {c["id"]: c["source_columns"] for c in inputs["cases"]},
        "case_hashes": {c["id"]: c["hash"] for c in inputs["cases"]},
        "scope": "126 estimation rows, conditional membership and artificial policy buckets; opened development cases, not investable market evaluation",
    }
    prepared = orchestration / "prepared.json"
    identity = digest(inputs)
    if prepared.exists() and json.loads(prepared.read_text())["prepared_hash"] != identity:
        raise ValueError("Prepared source/protocol/data changed; never overwrite a frozen run.")
    write_json(prepared, {"prepared_hash": identity, "protocol": protocol, "inputs_hash": inputs["inputs_hash"]})
    for source in files + [Path("modal_live_optimizer.py"), Path("scripts/run_gpu_optimization.py"), Path("docs/research/LIVE_GPU_OPTIMIZATION_PROTOCOL.md")]:
        target = orchestration / "source_snapshot" / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    if args.prepare_only:
        print("New protocol and source frozen; no inference or paid dispatch.")
        return
    ledger = configured_budget(ledger_path=str(orchestration / "budget.json"))
    ledger.limit = min(ledger.limit, 15)
    dispatch = orchestration / "gpu_dispatch.json"
    if dispatch.exists():
        saved = json.loads(dispatch.read_text())
        if saved.get("failed") or not saved.get("call_id"):
            raise ValueError("Failed/uncertain dispatch retained; no automatic paid retry.")
        job = saved["job_id"]
        call = modal.FunctionCall.from_id(saved["call_id"])
    else:
        snapshot = billing_snapshot()
        write_json(orchestration / "billing_before.json", snapshot)
        reserve = job_reservation("coder30", snapshot, timeout=2400, startup_timeout=600)
        job = ledger.reserve(reserve, RUN_ID, snapshot)
        write_json(dispatch, {"job_id": job, "status": "dispatching", "reserved_usd": reserve})
        call = modal.Function.from_name("agqo-live-optimizer", "optimize").spawn(RUN_ID, inputs)
        write_json(dispatch, {"job_id": job, "call_id": call.object_id, "reserved_usd": reserve})
    print("Live GPU optimization call:", call.object_id, flush=True)
    try:
        response = call.get(timeout=3040)
        unpack_verified(response, path / "evaluation")
        write_json(orchestration / "download_manifest.json", response["sha256_files"])
        write_json(orchestration / "completed.json", response["summary"])
        ledger.finish(job, "completed", {"call_id": call.object_id})
        write_json(orchestration / "billing_after.json", billing_snapshot())
        write_json(orchestration / "cost_report.json", {"ledger": ledger.state(), "reserved_usd_total": sum(j["reserved_usd"] for j in ledger.state()["jobs"]), "reservation_is_not_invoice": True, "monthly_billing_delta_is_not_isolated_job_bill": True})
        print(json.dumps(response["summary"], indent=2), flush=True)
    except Exception as exc:
        try:
            call.cancel(terminate_containers=True)
        finally:
            ledger.finish(job, "failed_reservation_charged", {"call_id": call.object_id, "reason": str(exc)})
            saved = json.loads(dispatch.read_text())
            write_json(dispatch, {**saved, "failed": True, "reason": str(exc)})
        raise


if __name__ == "__main__":
    main()
