"""Reserve, dispatch, checkpoint and download the bounded cloud integration run."""

import argparse
from pathlib import Path
import io
import json
import zipfile
import modal

from agqo.research.data import sha, write_json
from agqo.synthesis.budget import configured_budget, billing_snapshot
from agqo.synthesis.client import SynthesisClient


def unpack_verified(payload, directory):
    """Validate paths and every file before writing any archive member."""
    root = Path(directory).resolve()
    with zipfile.ZipFile(io.BytesIO(payload["archive"])) as archive:
        files = {
            member.filename: member
            for member in archive.infolist()
            if not member.is_dir()
        }
        if set(files) != set(payload["sha256_files"]):
            raise ValueError("Archive and manifest file sets disagree.")
        import hashlib

        contents = {}
        for name in files:
            target = (root / name).resolve()
            if not target.is_relative_to(root):
                raise ValueError("Unsafe archive path.")
            content = archive.read(files[name])
            if hashlib.sha256(content).hexdigest() != payload["sha256_files"][name]:
                raise ValueError("Cloud artifact checksum mismatch.")
            if target.exists() and target.read_bytes() != content:
                raise ValueError("Local artifact differs; refusing overwrite.")
            contents[target] = content
        for target, content in contents.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="modal_e2e_v1")
    parser.add_argument("--cost-aware", action="store_true")
    args = parser.parse_args()
    path = Path("results/research") / args.run_id
    orchestration = path / "orchestration"
    orchestration.mkdir(parents=True, exist_ok=True)
    if (orchestration / "completed.json").exists():
        previous = json.loads((orchestration / "prepare.json").read_text())
        if previous["protocol"].get("cost_aware", False) != args.cost_aware:
            raise ValueError(
                "Completed settings differ; use a new frozen protocol and run ID."
            )
        print("Completed run already downloaded; no paid jobs relaunched.")
        return
    ledger = configured_budget(ledger_path=str(orchestration / "budget.json"))

    def cpu_call(stage, function, *inputs):
        checkpoint = orchestration / (stage + ".json")
        if checkpoint.exists():
            return json.loads(checkpoint.read_text())
        dispatch = orchestration / (stage + "_dispatch.json")
        if dispatch.exists():
            saved = json.loads(dispatch.read_text())
            if saved.get("failed"):
                raise ValueError("Failed call retained; no automatic paid retry.")
            job = saved["job_id"]
            call_id = saved["call_id"]
            call = modal.FunctionCall.from_id(call_id)
        else:
            snapshot = billing_snapshot()
            rates = snapshot["rates"]
            reservation = (
                (4 * rates["cpu_hour_cost"] + 8 * rates["mem_gib_hour_cost"])
                * 1110
                / 3600
                * 1.25
            )
            job = ledger.reserve(reservation, stage, snapshot, resource="cpu")
            call = modal.Function.from_name("agqo-research-pipeline", function).spawn(
                args.run_id, *inputs
            )
            call_id = call.object_id
            write_json(
                dispatch,
                {"call_id": call.object_id, "job_id": job, "reserved_usd": reservation},
            )
        print("Waiting for", stage, call_id, flush=True)
        try:
            response = call.get(timeout=1110)
            if stage == "finish":
                unpack_verified(response, path)
                write_json(
                    orchestration / "download_manifest.json", response["sha256_files"]
                )
                response = response["summary"]
            write_json(checkpoint, response)
            ledger.finish(job, "completed", {"function_call_id": call_id})
            return response
        except Exception as exc:
            try:
                call.cancel(terminate_containers=True)
            except Exception:
                pass
            ledger.finish(job, "failed_reservation_charged", {"reason": str(exc)})
            write_json(
                dispatch,
                {
                    "job_id": job,
                    "call_id": call_id,
                    "failed": True,
                    "reason": str(exc),
                },
            )
            raise

    write_json(orchestration / "billing_before.json", billing_snapshot())
    prepared = cpu_call("prepare", "prepare_run", args.cost_aware)
    client = SynthesisClient(
        "coder30", "modal", orchestration / "inference", ledger=ledger, prefetch=True
    )
    answers = client.batch(prepared["requests"])
    write_json(orchestration / "answers.json", answers)
    result = cpu_call(
        "finish",
        "finish_run",
        answers,
        prepared["prepared_hash"],
        {
            "ledger_at_finish_dispatch": ledger.state(),
            "reservation_is_not_invoice": True,
        },
    )
    write_json(orchestration / "billing_after.json", billing_snapshot())
    write_json(
        orchestration / "cost_report.json",
        {
            "ledger": ledger.state(),
            "reserved_usd_total": sum(
                j["reserved_usd"] for j in ledger.state()["jobs"]
            ),
            "reservation_is_not_invoice": True,
            "measured_monthly_billing_delta_is_not_isolated_job_bill": True,
            "input_tokens": sum(
                a.get("usage", {}).get("input_tokens", 0) for a in answers
            ),
            "output_tokens": sum(
                a.get("usage", {}).get("output_tokens", 0) for a in answers
            ),
            "download_manifest_sha256": sha(orchestration / "download_manifest.json"),
        },
    )
    write_json(orchestration / "completed.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
