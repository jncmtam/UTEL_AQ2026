"""Bounded Modal LLM/QAOA ablation; exact prompts and call IDs are retained."""

from pathlib import Path
import argparse
import json
import modal

from agqo.research.live_guidance import prepare
from agqo.research.data import write_json, sha
from agqo.synthesis.profile import digest
from agqo.synthesis.budget import configured_budget, billing_snapshot
from agqo.synthesis.client import SynthesisClient

try:
    from scripts.run_modal_pipeline import unpack_verified
except ModuleNotFoundError:
    from run_modal_pipeline import unpack_verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--interface", choices=("v1", "edge_v2"), default="v1")
    args = parser.parse_args()
    edge_v2 = args.interface == "edge_v2"
    run_id = "live_edge_v2" if edge_v2 else "live_guidance_v1"
    path = Path("results/research") / run_id
    orchestration = path / "orchestration"
    if (orchestration / "completed.json").exists():
        print("Completed live study retained; no new dispatch.")
        return
    if edge_v2:
        from agqo.research.edge_program import prepare as prepare_edges

        inputs = prepare_edges()
    else:
        inputs = prepare()
    protected = sorted(Path("agqo").rglob("*.py")) + [
        Path("modal_gate_synthesis.py"),
        Path("modal_research_pipeline.py"),
        Path(__file__),
        Path("docs/research/LIVE_GUIDANCE_PROTOCOL.md"),
        Path("docs/research/EDGE_PROGRAM_PROTOCOL.md"),
    ]
    protocol = {
        "version": "live-guidance-v1",
        "inputs_hash": inputs["inputs_hash"],
        "requests_hash": digest(inputs["requests"]),
        "cases": [
            {"id": c["id"], "hash": c["hash"], "resource_budget": c["resource_budget"]}
            for c in inputs["cases"]
        ],
        "source_hashes": {str(p): sha(p) for p in protected},
        "max_total_reservation_usd": 10,
        "request_count": 8,
        "investment_universe_approved": False,
        "interface": args.interface,
    }
    target = orchestration / "protocol.json"
    if target.exists() and json.loads(target.read_text()) != protocol:
        raise ValueError("Frozen source, request or private input identity changed.")
    write_json(target, protocol)
    write_json(orchestration / "prepared_requests.json", inputs["requests"])
    for p in protected:
        dest = orchestration / "source_snapshot" / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.read_bytes() != p.read_bytes():
            raise ValueError("Source snapshot changed.")
        dest.write_bytes(p.read_bytes())
    if args.prepare_only:
        print(
            "Eight matched requests prepared; no billing, deployment or inference call."
        )
        return
    ledger = configured_budget(ledger_path=str(orchestration / "budget.json"))
    ledger.limit = min(ledger.limit, 10)
    original_reserved = 0.0
    if edge_v2:
        original = json.loads(
            Path(
                "results/research/live_guidance_v1/orchestration/cost_report.json"
            ).read_text()
        )
        original_reserved = original["reserved_usd_total"]
        ledger.limit = min(ledger.limit, 10 - original_reserved)
    if not (orchestration / "billing_before.json").exists():
        write_json(orchestration / "billing_before.json", billing_snapshot())

    def cpu(stage, function, seconds, memory, *values):
        receipt, dispatch = (
            orchestration / f"{stage}.json",
            orchestration / f"{stage}_dispatch.json",
        )
        if receipt.exists():
            return json.loads(receipt.read_text())
        if dispatch.exists():
            saved = json.loads(dispatch.read_text())
            if saved.get("failed"):
                raise ValueError("Failed CPU dispatch retained; no paid retry.")
            job, call_id = saved["job_id"], saved["call_id"]
            call = modal.FunctionCall.from_id(call_id)
        else:
            snapshot = billing_snapshot()
            cores = 2 if stage == "tokenizer" else 4
            reserve = (
                (
                    cores * snapshot["rates"]["cpu_hour_cost"]
                    + memory * snapshot["rates"]["mem_gib_hour_cost"]
                )
                * seconds
                / 3600
                * 1.25
            )
            job = ledger.reserve(reserve, stage, snapshot, resource="cpu")
            write_json(
                dispatch,
                {"job_id": job, "status": "dispatching", "reserved_usd": reserve},
            )
            call = modal.Function.from_name(
                "agqo-gate-synthesis"
                if stage == "tokenizer"
                else "agqo-research-pipeline",
                function,
            ).spawn(*values)
            call_id = call.object_id
            write_json(
                dispatch, {"job_id": job, "call_id": call_id, "reserved_usd": reserve}
            )
        print("Waiting for", stage, call_id, flush=True)
        try:
            response = call.get(timeout=seconds)
            if stage == "evaluation":
                unpack_verified(response, path / "evaluation")
                write_json(
                    orchestration / "download_manifest.json", response["sha256_files"]
                )
                response = response["summary"]
            write_json(receipt, response)
            ledger.finish(job, "completed", {"call_id": call_id})
            return response
        except Exception as exc:
            call.cancel(terminate_containers=True)
            ledger.finish(job, "failed_reservation_charged", {"reason": str(exc)})
            write_json(
                dispatch,
                {"job_id": job, "call_id": call_id, "failed": True, "reason": str(exc)},
            )
            raise

    requests = [r["request"] for r in inputs["requests"]]
    tokenized = cpu("tokenizer", "tokenizer_requests", 510, 4, "coder30", requests)
    if tokenized["status"] != "ready":
        raise ValueError("Real prompts exceed context allowance; GPU not dispatched.")
    answer_file = orchestration / "answers.json"
    if answer_file.exists():
        answers = json.loads(answer_file.read_text())
    else:
        inference = orchestration / "inference"
        if list(inference.glob("*_dispatch.json")):
            raise ValueError(
                "Existing model dispatch retained; recover by call ID, no duplicate GPU dispatch."
            )
        answers = SynthesisClient(
            "coder30", "modal", inference, ledger=ledger, prefetch=not edge_v2
        ).batch(requests)
        write_json(answer_file, answers)
    if not any(a.get("status") == "ok" for a in answers):
        raise ValueError(
            "No usable live response; stop without further paid evaluation."
        )
    result = cpu("evaluation", "guided_study_run", 2010, 16, run_id, inputs, answers)
    write_json(orchestration / "billing_after.json", billing_snapshot())
    write_json(
        orchestration / "cost_report.json",
        {
            "ledger": ledger.state(),
            "reserved_usd_total": sum(
                j["reserved_usd"] for j in ledger.state()["jobs"]
            ),
            "original_v1_reservations_usd": original_reserved,
            "combined_v1_v2_reserved_usd": original_reserved
            + sum(j["reserved_usd"] for j in ledger.state()["jobs"]),
            "reservation_is_not_invoice": True,
            "billing_delta_is_not_isolated_job_bill": True,
            "input_tokens": sum(
                a.get("usage", {}).get("input_tokens", 0) for a in answers
            ),
            "output_tokens": sum(
                a.get("usage", {}).get("output_tokens", 0) for a in answers
            ),
        },
    )
    write_json(orchestration / "completed.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
