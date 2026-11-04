"""One bounded CPU dispatch; no model inference or automatic paid retry."""

from pathlib import Path
import argparse
import json
import modal
from agqo.research.improvement import prepare_inputs
from agqo.research.data import write_json
from agqo.synthesis.budget import configured_budget, billing_snapshot

try:
    from scripts.run_modal_pipeline import unpack_verified
except ModuleNotFoundError:
    from run_modal_pipeline import unpack_verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    run_id = "improvement_v1"
    path = Path("results/research") / run_id
    orchestration = path / "orchestration"
    if (orchestration / "completed.json").exists():
        print("Completed study retained; no new dispatch.")
        return
    if (orchestration / "dispatch.json").exists():
        raise ValueError(
            "Existing call retained; resume/download by call ID, never automatically redispatch."
        )
    inputs = prepare_inputs()
    write_json(
        orchestration / "input_identity.json",
        {
            "inputs_hash": inputs["inputs_hash"],
            "source_cutoff": inputs["source_cutoff"],
            "private_return_matrices_not_published": True,
            "cases": [
                {k: c[k] for k in ("id", "family", "source_columns", "hash")}
                for c in inputs["cases"]
            ],
        },
    )
    if args.prepare_only:
        print("Frozen inputs prepared; no cloud dispatch or billing call.")
        return
    ledger = configured_budget(ledger_path=str(orchestration / "budget.json"))
    before = billing_snapshot()
    write_json(orchestration / "billing_before.json", before)
    rates = before["rates"]
    amount = (
        (4 * rates["cpu_hour_cost"] + 16 * rates["mem_gib_hour_cost"])
        * 2010
        / 3600
        * 1.25
    )
    job = ledger.reserve(amount, "improvement_cpu", before, resource="cpu")
    call = None
    write_json(
        orchestration / "dispatch.json",
        {"job_id": job, "status": "dispatching", "reserved_usd": amount},
    )
    try:
        call = modal.Function.from_name(
            "agqo-research-pipeline", "improvement_run"
        ).spawn(run_id, inputs)
        write_json(
            orchestration / "dispatch.json",
            {"job_id": job, "call_id": call.object_id, "reserved_usd": amount},
        )
        print("Waiting for CPU study", call.object_id, flush=True)
        payload = call.get(timeout=2010)
        unpack_verified(payload, path)
        write_json(orchestration / "download_manifest.json", payload["sha256_files"])
        ledger.finish(job, "completed", payload["summary"])
        write_json(orchestration / "billing_after.json", billing_snapshot())
        write_json(orchestration / "completed.json", payload["summary"])
        print(json.dumps(payload["summary"], indent=2), flush=True)
    except Exception as exc:
        if call:
            try:
                call.cancel(terminate_containers=True)
            except Exception:
                pass
        ledger.finish(job, "failed_reservation_charged", {"reason": str(exc)})
        write_json(
            orchestration / "failure.json",
            {"reason": str(exc), "call_id": call.object_id if call else None},
        )
        raise


if __name__ == "__main__":
    main()
