"""Run one source-frozen allocation-table stage and one GPU distribution audit."""

from pathlib import Path
import argparse
import json
import math
import modal
from agqo.research.decision_audit import prepare, RUN_ID
from agqo.research.data import sha, write_json
from agqo.synthesis.profile import digest
from agqo.synthesis.budget import configured_budget, billing_snapshot

try:
    from scripts.run_modal_pipeline import unpack_verified
except ModuleNotFoundError:
    from run_modal_pipeline import unpack_verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    path = Path("results/research") / RUN_ID
    controller = path / "orchestration"
    if (controller / "completed.json").exists():
        print("Completed decision audit retained; no paid dispatch.")
        return
    inputs = prepare()
    files = sorted(Path("agqo").rglob("*.py"))
    extra = [Path("modal_decision_audit.py"), Path(__file__).resolve(), Path("docs/research/DECISION_AUDIT_PROTOCOL.md")]
    protocol = {"run_id": RUN_ID, "input_hash": inputs["input_hash"],
        "package_source_hashes": {str(p): sha(p) for p in files},
        "controller_hashes": {str(p.relative_to(Path.cwd()) if p.is_absolute() else p): sha(p) for p in extra},
        "new_model_calls": 0, "angle_optimizations": 0, "reservation_cap_usd": 8,
        "source_cases": [{"case_id": c["id"], "spec_hash": c["hash"]} for c in inputs["cases"]]}
    inputs["protocol"] = protocol
    frozen = controller / "prepared.json"
    payload = {"protocol": protocol, "prepared_hash": digest(inputs), "cache_counts": inputs["cache_counts"]}
    if frozen.exists() and json.loads(frozen.read_text()) != payload:
        raise ValueError("Prepared source/cache/financial identity changed.")
    write_json(frozen, payload)
    for source in files+extra:
        relative = source.relative_to(Path.cwd()) if source.is_absolute() else source
        dest = controller / "source_snapshot" / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.read_bytes() != source.read_bytes():
            raise ValueError("Source snapshot changed.")
        dest.write_bytes(source.read_bytes())
    if args.prepare_only:
        print(json.dumps({"status": "prepared_no_dispatch", **inputs["cache_counts"]}))
        return
    ledger = configured_budget(ledger_path=str(controller / "budget.json"))
    ledger.limit = min(ledger.limit, 8)

    def stage(name, function, seconds, memory, gpu=False, *values):
        receipt, dispatch = controller / f"{name}.json", controller / f"{name}_dispatch.json"
        if receipt.exists():
            return json.loads(receipt.read_text())
        if dispatch.exists():
            saved = json.loads(dispatch.read_text())
            if saved.get("failed") or not saved.get("call_id"):
                raise ValueError("Failed or uncertain dispatch retained; no automatic retry.")
            call, job = modal.FunctionCall.from_id(saved["call_id"]), saved["job_id"]
        else:
            snapshot = billing_snapshot()
            if not (controller / "billing_before.json").exists():
                write_json(controller / "billing_before.json", snapshot)
            rates = snapshot["rates"]
            hourly = 4*rates["cpu_hour_cost"] + memory*rates["mem_gib_hour_cost"]
            if gpu:
                hourly += max(rates["gpu_hour_cost_h200"], rates["gpu_hour_cost_a100_80gb"])
            reserve = math.ceil(hourly*seconds/3600*1.25*100)/100
            job = ledger.reserve(reserve, name, snapshot, resource="gpu" if gpu else "cpu")
            write_json(dispatch, {"job_id": job, "reserved_usd": reserve, "status": "dispatching"})
            call = modal.Function.from_name("agqo-decision-audit", function).spawn(RUN_ID, inputs, *values)
            write_json(dispatch, {"call_id": call.object_id, "job_id": job, "reserved_usd": reserve})
        print(name, call.object_id, flush=True)
        try:
            result = call.get(timeout=seconds+30)
            if gpu:
                unpack_verified(result, path / "evaluation")
                write_json(controller / "download_manifest.json", result["sha256_files"])
                result = result["summary"]
            write_json(receipt, result)
            ledger.finish(job, "completed", {"call_id": call.object_id})
            return result
        except Exception as exc:
            call.cancel(terminate_containers=True)
            ledger.finish(job, "failed_reservation_charged", {"call_id": call.object_id, "reason": str(exc)})
            saved = json.loads(dispatch.read_text())
            write_json(dispatch, {**saved, "failed": True, "reason": str(exc)})
            raise

    table = stage("table", "build_table", 2010, 16)
    result = stage("gpu", "evaluate", 930, 16, True, table)
    write_json(controller / "billing_after.json", billing_snapshot())
    write_json(controller / "cost_report.json", {"ledger": ledger.state(), "reserved_usd_total": sum(j["reserved_usd"] for j in ledger.state()["jobs"]), "reservation_is_not_invoice": True, "new_model_calls": 0})
    write_json(controller / "completed.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
