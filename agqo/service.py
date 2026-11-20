"""One decision as a self-contained job: input dict in, JSON-safe result out.

Used by the Modal CPU function `decide_job` (app/modal_web.py) and by research runs. The result carries
everything the web page needs later (explanation evidence, OpenQASM), so the web container never simulates.
"""

from __future__ import annotations

import time

import numpy as np

from .mandate import Mandate

_DEMO = None


def demo():
    global _DEMO
    if _DEMO is None:
        from .demo import Demo

        _DEMO = Demo()
    return _DEMO


def clean(o):
    """JSON-safe copy: numpy scalars -> Python, NaN/inf -> None, drops private keys."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        o = o.item()
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o if isinstance(o, (str, int, float, bool, type(None))) else str(o)


def run_decision(payload: dict, progress=None) -> dict:
    """payload: {capital_million, mandate: dict, shots?, seed?, with_textbook?}."""
    t0 = time.time()
    say = progress or (lambda stage, **kw: None)
    say("load")
    d = demo()
    m = Mandate.from_dict(payload.get("mandate") or {})
    errs = m.validate(set(d.sector_of))
    if errs:
        return {"status": "invalid", "errors": errs}
    out = d.decide(float(payload["capital_million"]) * 1e6, m, shots=int(payload.get("shots", 512)),
                   seed=int(payload.get("seed", 0)), with_textbook=bool(payload.get("with_textbook", True)),
                   progress=say)
    res = clean(out)
    if out.get("_rec") is not None:
        say("evidence")
        try:
            res["evidence"] = clean(d.evidence(out))
        except Exception as e:                       # the decision stands without an explanation pack
            res["evidence_error"] = f"{type(e).__name__}: {e}"
        try:
            from .quantum.export import build_circuit, to_qasm

            inst, land, cp, spec, r = out["_rec"]
            res["qasm"] = to_qasm(build_circuit(cp, spec, r.angles))
        except Exception as e:                       # qiskit missing or export failure
            res["qasm_error"] = f"{type(e).__name__}: {e}"
    res["job_seconds"] = round(time.time() - t0, 2)
    say("done")
    return res
