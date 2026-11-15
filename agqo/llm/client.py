"""LLM backends with one interface and a complete transparency log.

Backends
  modal   - Qwen3.8-27B served by vLLM on a Modal H100 (modal_app.py); JSON-schema constrained.
  replay  - re-reads responses from an earlier run's llm_log.jsonl (zero cost, exact replay).
  mock    - deterministic stand-in used ONLY by unit tests; every record is tagged "mock".

Every call is appended to the log: request hash, prompts, raw text, parsed JSON, status,
token usage, model id and wall time. Nothing is filtered.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


def request_hash(req: dict) -> str:
    body = json.dumps({k: req[k] for k in ("agent", "system", "user", "schema", "seed", "temperature")},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def make_request(agent: str, system: str, user: dict | str, schema: dict, seed: int = 0,
                 temperature: float = 0.2, max_tokens: int = 1024) -> dict:
    req = {"agent": agent, "system": system,
           "user": user if isinstance(user, str) else json.dumps(user, ensure_ascii=False),
           "schema": schema, "seed": seed, "temperature": temperature, "max_tokens": max_tokens}
    req["hash"] = request_hash(req)
    return req


@dataclass
class LLMClient:
    backend: str
    log_path: Path
    replay_from: Path | None = None
    mock_fn: Callable[[dict], dict] | None = None
    app_name: str = "agqo-llm"

    def __post_init__(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._replay = {}
        if self.backend == "replay":
            for line in Path(self.replay_from).read_text().splitlines():
                rec = json.loads(line)
                self._replay[rec["hash"]] = rec

    def generate(self, requests: list[dict]) -> list[dict]:
        t0 = time.time()
        if self.backend == "modal":
            import modal

            engine = modal.Cls.from_name(self.app_name, "Engine")()
            payload = [{k: r[k] for k in ("system", "user", "schema", "seed", "temperature", "max_tokens")}
                       for r in requests]
            out = engine.generate.remote(payload)
        elif self.backend == "replay":
            out = [dict(self._replay[r["hash"]], execution="replay") for r in requests]
        elif self.backend == "mock":
            out = [{"raw_text": json.dumps(self.mock_fn(r)), "finish_reason": "stop",
                    "usage": {}, "model": "mock", "execution": "mock"} for r in requests]
        else:
            raise ValueError(f"unknown backend {self.backend}")
        wall = time.time() - t0
        records = []
        with self.log_path.open("a") as f:
            for r, o in zip(requests, out, strict=True):
                try:
                    parsed = json.loads(o["raw_text"])
                    status = "ok" if o.get("finish_reason", "stop") == "stop" else "truncated"
                except (json.JSONDecodeError, TypeError):
                    parsed, status = None, "invalid_json"
                rec = {"hash": r["hash"], "agent": r["agent"], "seed": r["seed"], "temperature": r["temperature"],
                       "system": r["system"], "user": r["user"], "raw_text": o["raw_text"], "parsed": parsed,
                       "status": status, "finish_reason": o.get("finish_reason"), "usage": o.get("usage", {}),
                       "model": o.get("model"), "revision": o.get("revision"), "gpu": o.get("gpu"),
                       "execution": o.get("execution", self.backend), "batch_wall_s": round(wall, 2)}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                records.append(rec)
        return records
