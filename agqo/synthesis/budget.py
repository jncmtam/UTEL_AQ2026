"""Process-safe reservation ledger; fail closed when billing cannot be read.

Reservations are conservative upper bounds, not provider invoices. A failed or
interrupted remote job consumes the reservation until explicitly reconciled.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import math
import os
import uuid


MODELS = {
    "next80": {"model": "Qwen/Qwen3-Coder-Next-FP8", "revision": "da6e2ed27304dd39abadd9c82ef50e8de67bdd4c", "gpu": "H200",
               "rate_key": "gpu_hour_cost_h200", "dtype": "auto", "ram_gib": 128, "cpu": 4},
    "coder30": {"model": "Qwen/Qwen3-Coder-30B-A3B-Instruct", "revision": "b2cff646eb4bb1d68355c01b18ae02e7cf42d120", "gpu": "A100-80GB",
                "rate_key": "gpu_hour_cost_a100_80gb", "dtype": "bfloat16", "ram_gib": 96, "cpu": 4},
}

# Legacy MODELS stays immutable so preregistered v1/v2 protocols can replay.
LARGE_MODELS = {
    'coder480': {'model':'Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8',
                 'revision':'003f183a92fbe5b9a8325aaa8b2ae797c91dd90f',
                 'gpu':'H200:4','gpu_count':4,'tensor_parallel_size':4,
                 'rate_key':'gpu_hour_cost_h200','dtype':'auto','ram_gib':384,'cpu':16,
                 'timeout':1800,'startup_timeout':900,'vllm_version':'0.15.0'},
    'qwen397': {'model':'Qwen/Qwen3.5-397B-A17B-FP8',
                'revision':'ea5b4f81096f3901c91dea97f81324302495781d',
                'gpu':'H200:4','gpu_count':4,'tensor_parallel_size':4,
                'rate_key':'gpu_hour_cost_h200','dtype':'auto','ram_gib':384,'cpu':16,
                'timeout':1800,'startup_timeout':900,'vllm_version':'0.17.1'},
}
MODEL_CATALOG = {**MODELS, **LARGE_MODELS}


def billing_snapshot():
    import modal
    workspace = modal.Workspace.from_context()
    summary = workspace.billing.summary(cycle="this month")
    rates = dict(workspace.billing.rates())
    return {"checked_utc": datetime.now(timezone.utc).isoformat(), "metered_cost": float(summary.metered_cost),
            "billed_cost": float(summary.billed_cost), "adjustments": {k: str(v) for k, v in summary.adjustments.items()},
            "rates": {k: float(v) for k, v in rates.items() if k in {"gpu_hour_cost_h200", "gpu_hour_cost_a100_80gb", "cpu_hour_cost", "mem_gib_hour_cost"}},
            "allowance_basis": "User-confirmed Starter USD30 monthly allowance; API exposes metered/billed costs, not a standalone available-credit balance."}


def job_reservation(model, snapshot, timeout=None, startup_timeout=None):
    config = MODEL_CATALOG[model]; rates = snapshot["rates"]
    timeout=config.get('timeout',900) if timeout is None else timeout
    startup_timeout=config.get('startup_timeout',600) if startup_timeout is None else startup_timeout
    hourly = rates[config["rate_key"]] * config.get('gpu_count',1) + rates["cpu_hour_cost"] * config["cpu"] + rates["mem_gib_hour_cost"] * config["ram_gib"]
    # Include startup, timeout, scaledown and a buffer. Idle containers are terminated.
    return math.ceil(hourly * (timeout + startup_timeout + 30) / 3600 * 1.25 * 100) / 100


class BudgetLedger:
    def __init__(self, path, limit=25.0, monthly_allowance=30.0, authorization=None):
        expanded = bool(authorization and isinstance(authorization,str) and len(authorization)>=20)
        if not math.isfinite(limit) or limit<=0 or (not expanded and limit>25) or (monthly_allowance is None and not expanded) or (monthly_allowance is not None and (not math.isfinite(monthly_allowance) or monthly_allowance<=0 or (not expanded and monthly_allowance>30))):
            raise ValueError("Budget must be within the authorized USD25 batch and USD30 monthly envelope.")
        self.path, self.limit, self.allowance = Path(path), limit, monthly_allowance
        self.authorization=authorization

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(self.path.read_text()) if self.path.exists() else {"version": "budget-v1", "limit_usd": self.limit, "jobs": [],
                "authorization":self.authorization,"monthly_allowance":self.allowance}
            # Reopening a ledger cannot increase its authorized cap.
            data["limit_usd"] = min(data["limit_usd"], self.limit)
            yield data
            tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_text(json.dumps(data, indent=2, allow_nan=False)); tmp.replace(self.path)

    def reserve(self, amount, label, snapshot, resource="gpu"):
        if resource not in {"gpu", "cpu"}:
            raise ValueError("Unknown reservation resource.")
        if not math.isfinite(amount) or amount <= 0 or not snapshot or not math.isfinite(snapshot.get("metered_cost", math.nan)):
            raise ValueError("Missing verified billing or invalid reservation.")
        from datetime import timedelta
        checked = datetime.fromisoformat(snapshot["checked_utc"])
        if checked.tzinfo is None or datetime.now(timezone.utc) - checked > timedelta(minutes=5):
            raise ValueError("Billing snapshot is stale; refresh before dispatch.")
        with self.locked() as data:
            if resource == "gpu" and any(job["status"] == "running" and job.get("resource", "gpu") == "gpu" for job in data["jobs"]):
                raise ValueError("One GPU job is already reserved; sequential execution required.")
            used = sum(job["reserved_usd"] for job in data["jobs"])
            # Conservatively count all metered costs, even waived storage/egress.
            available = data['limit_usd']-used
            if self.allowance is not None:
                available = min(available,self.allowance-snapshot['metered_cost']-2.0)
            if amount > available + 1e-9:
                raise ValueError(f"Budget blocked: reservation {amount:.2f} exceeds conservative remaining {max(0, available):.2f} USD.")
            job = {"id": uuid.uuid4().hex, "label": label, "resource": resource, "reserved_usd": amount, "status": "running", "billing": snapshot}
            data["jobs"].append(job)
            return job["id"]

    def finish(self, job_id, status, metadata=None):
        with self.locked() as data:
            job = next(j for j in data["jobs"] if j["id"] == job_id)
            job.update(status=status, metadata=metadata or {})

    def state(self):
        with self.locked() as data:
            return json.loads(json.dumps(data))
