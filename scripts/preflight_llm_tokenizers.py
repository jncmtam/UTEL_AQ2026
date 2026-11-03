"""Bounded, sequential Modal CPU tokenizer checks. No model weights/inference."""

from pathlib import Path
import json
import modal
from agqo.research.data import write_json
from agqo.synthesis.budget import BudgetLedger, billing_snapshot, MODEL_CATALOG


def main():
    path = Path("results/research/tokenizer_preflight_v1")
    if (path / "records.json").exists():
        raise ValueError("Completed preflight must not be relaunched.")
    write_json(
        path / "protocol.json",
        {
            "version": "cpu-tokenizer-preflight-v1",
            "evidence": "docs/research/QUALIFICATION_PROTOCOL.md#cpu-only-runtime-preflight-addendum",
            "models": ["coder30", "mistral24q", "quasar4"],
            "gpu": False,
            "model_weights": False,
            "cpu": 2,
            "ram_gib": 4,
            "timeout_seconds": 300,
            "startup_timeout_seconds": 180,
            "max_reservation_per_job_usd": 1,
            "max_total_reservation_usd": 3,
            "runtime_scope": "Shared modern vLLM0.17.1 image; not complete GPU-worker/weight equivalence.",
        },
    )
    ledger = BudgetLedger(
        path / "budget.json",
        limit=3,
        monthly_allowance=None,
        authorization="User-authorized bounded Modal CPU tokenizer preflight, no weights or inference.",
    )
    rows = []
    for key in ["coder30", "mistral24q", "quasar4"]:
        target = path / (key + "_receipt.json")
        if target.exists():
            rows.append(json.loads(target.read_text()))
            continue
        row = {
            "key": key,
            "model": MODEL_CATALOG[key]["model"],
            "revision": MODEL_CATALOG[key]["revision"],
        }
        call = None
        job = None
        try:
            snapshot = billing_snapshot()
            rates = snapshot["rates"]
            reservation = (
                (2 * rates["cpu_hour_cost"] + 4 * rates["mem_gib_hour_cost"])
                * 600
                / 3600
                * 1.25
            )
            if reservation > 1:
                raise ValueError(
                    "CPU reservation exceeds the registered per-job ceiling."
                )
            job = ledger.reserve(
                reservation, "tokenizer:" + key, snapshot, resource="cpu"
            )
            call = modal.Function.from_name(
                "agqo-gate-synthesis", "tokenizer_preflight"
            ).spawn(key)
            write_json(
                path / (key + "_dispatch.json"),
                {
                    "job_id": job,
                    "call_id": call.object_id,
                    "reserved_usd": reservation,
                    "billing_before": snapshot,
                },
            )
            result = call.get(timeout=510)
            if (
                result.get("model") != row["model"]
                or result.get("revision") != row["revision"]
            ):
                raise ValueError("Tokenizer checkpoint identity mismatch.")
            row.update(result)
            row["reserved_usd"] = reservation
            ledger.finish(job, "completed", row)
        except Exception as exc:
            if call is not None:
                try:
                    call.cancel(terminate_containers=True)
                except Exception:
                    pass
            row.update(
                status="failed" if call else "blocked",
                reason=f"{type(exc).__name__}: {exc}",
            )
            if job:
                ledger.finish(job, "failed_reservation_charged", row)
        write_json(target, row)
        rows.append(row)
        print(key, row["status"], flush=True)
    write_json(path / "records.json", rows)
    try:
        write_json(path / "billing_after.json", billing_snapshot())
    except Exception as exc:
        write_json(
            path / "billing_after.json", {"status": "unavailable", "reason": str(exc)}
        )
    (path / "RESULTS.md").write_text(
        "# CPU tokenizer preflight\n\n"
        + "\n".join(f"- {r['key']}: {r['status']}" for r in rows)
        + "\n\nNo model weights, GPU inference, circuit correctness or financial qualification is established. Reservations are not invoices.\n"
    )


if __name__ == "__main__":
    main()
