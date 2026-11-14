"""Deterministic schema-valid stand-in for unit tests and dry runs.

It is NOT a language model and its outputs are never reported as LLM results:
every log record it produces carries execution="mock".
"""

from __future__ import annotations

import json

import numpy as np


def mock_response(req: dict) -> dict:
    rng = np.random.default_rng(req["seed"])
    if req["agent"] == "market_analyst":
        payload = json.loads(req["user"])
        cols = payload["columns"]
        rows = payload["rows"]
        ci, li = cols.index("corr_to_index"), cols.index("liquidity_share_pct")
        ranked = sorted(rows, key=lambda r: -(r[ci] + 0.02 * r[li]))
        n = int(payload["task"].split()[1])
        return {"regime": "neutral", "shortlist": [r[0] for r in ranked[:n]],
                "views": [{"id": r[0], "view": int(np.sign(r[cols.index("rel_strength_60d_pct")])),
                           "confidence": 0.3} for r in ranked[:n]],
                "rationale": "mock: rank by correlation and liquidity"}
    if req["agent"] == "circuit_architect":
        m = json.loads(req["user"])["designs_requested"]
        props = []
        for _ in range(m):
            p = int(rng.integers(1, 5))
            props.append({"layers": p, "initial_state": "warm_start", "mixer": "warm_x",
                          "warm_start_epsilon": float(rng.uniform(0.02, 0.3)), "coupling_keep_fraction": 1.0,
                          "angle_init": "linear_ramp", "ramp_dt": float(rng.uniform(0.3, 1.2)),
                          "optimizer": "cobyla", "max_iter": 60, "cvar_alpha": 0.2,
                          "rationale": "mock: aligned warm start"})
        return {"analysis": "mock", "proposals": props}
    return {"answer": 6, "why": "mock"}
