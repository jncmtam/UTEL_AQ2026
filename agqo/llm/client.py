"""LLM backends with a single interface and a complete transparency log.

Backends
  modal   - Qwen3 served by vLLM on a Modal GPU (see modal_app.py); JSON-schema constrained.
  openai  - any OpenAI-compatible endpoint (base URL + key from env vars).
  replay  - re-reads responses from an earlier run's llm_log.jsonl (zero cost, exact replay).
  mock    - deterministic stand-in used ONLY by unit tests; every record is tagged "mock".

Every call is appended to <run>/llm_log.jsonl: request hash, prompts, raw text,
parsed JSON, status, token usage, model id and wall time. Nothing is filtered.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


def request_hash(req: dict) -> str:
    body = json.dumps({k: req[k] for k in ("agent", "system", "user", "schema", "seed", "temperature")},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def make_request(agent: str, system: str, user: dict | str, schema: dict, seed: int = 0,
                 temperature: float = 0.6, max_tokens: int = 2048) -> dict:
    req = {"agent": agent, "system": system,
           "user": user if isinstance(user, str) else json.dumps(user, ensure_ascii=False),
           "schema": schema, "seed": seed, "temperature": temperature, "max_tokens": max_tokens}
    req["hash"] = request_hash(req)
    return req


@dataclass
class LLMClient:
    backend: str
    log_path: Path
    model: str = "coder30"
    replay_from: Path | None = None
    mock_fn: Callable[[dict], dict] | None = None

    def __post_init__(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._replay = {}
        if self.backend == "replay":
            for line in Path(self.replay_from).read_text().splitlines():
                rec = json.loads(line)
                self._replay[rec["hash"]] = rec

    @property
    def is_live(self) -> bool:
        return self.backend in ("modal", "openai")

    def generate(self, requests: list[dict]) -> list[dict]:
        t0 = time.time()
        if self.backend == "modal":
            out = self._modal(requests)
        elif self.backend == "openai":
            out = [self._openai(r) for r in requests]
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
                rec = {"hash": r["hash"], "agent": r["agent"], "seed": r["seed"],
                       "temperature": r["temperature"], "system": r["system"], "user": r["user"],
                       "raw_text": o["raw_text"], "parsed": parsed, "status": status,
                       "finish_reason": o.get("finish_reason"), "usage": o.get("usage", {}),
                       "model": o.get("model"), "revision": o.get("revision"),
                       "execution": o.get("execution", self.backend), "batch_wall_s": round(wall, 2)}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                records.append(rec)
        return records

    # ---------------------------------------------------------------- backends
    def _modal(self, requests: list[dict]) -> list[dict]:
        import modal

        app = os.environ.get("AGQO_MODAL_APP", "agqo-llm-core")
        Engine = modal.Cls.from_name(app, "Engine")
        payload = [{k: r[k] for k in ("system", "user", "schema", "seed", "temperature", "max_tokens")}
                   for r in requests]
        return Engine(model_key=self.model).generate.remote(payload)

    def _openai(self, r: dict) -> dict:
        base = os.environ["AGQO_OPENAI_BASE_URL"].rstrip("/")
        key = os.environ.get("AGQO_OPENAI_API_KEY", "none")
        body = {"model": self.model, "temperature": r["temperature"], "max_tokens": r["max_tokens"],
                "seed": r["seed"],
                "messages": [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["user"]}],
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": r["agent"], "schema": r["schema"], "strict": True}}}
        req = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read())
        ch = data["choices"][0]
        return {"raw_text": ch["message"]["content"], "finish_reason": ch.get("finish_reason"),
                "usage": data.get("usage", {}), "model": data.get("model"), "execution": "live_openai_compatible"}
