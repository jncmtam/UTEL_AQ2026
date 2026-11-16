"""AGQO prototype web server (FastAPI).

Run locally:   uvicorn app.server:api --port 8000        (from the repository root)
Deploy:        modal deploy app/modal_web.py              (public URL, scales to zero)

Endpoints
  GET  /                      the single-page prototype (app/static/index.html)
  GET  /api/meta              date, universe, example instructions, LLM availability
  GET  /api/story             pre-computed evidence for the "Kết quả" section (backtest, 12 quarters, board)
  POST /api/mandate           Vietnamese instruction -> constraints (logged live answer | live Qwen job | keyword rules)
  POST /api/decide            one live AGQO decision for a new account (QAOA simulation + exact verification)
  POST /api/explain           start the LLM explainer for a decision (returns a job id)
  GET  /api/job/{id}          poll a live LLM job (mandate or explanation)
  GET  /api/qasm/{id}         the decision's circuit as OpenQASM 2 (hardware-ready)
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agqo.config import RESULTS_DIR
from agqo.demo import Demo, compile_mandate
from agqo.llm.tasks import explain_request, mandate_request, parse_mandate, verify_explanation
from agqo.mandate import Mandate, rule_parse

STATIC = Path(__file__).resolve().parent / "static"
LIVE_LLM = os.environ.get("AGQO_LIVE_LLM", "1") == "1"         # set 0 to never start the GPU
LLM_PER_HOUR = int(os.environ.get("AGQO_LLM_PER_HOUR", "40"))   # cost guard for a public URL

api = FastAPI(title="AGQO prototype")
api.mount("/static", StaticFiles(directory=STATIC), name="static")

_demo: Demo | None = None
_lock = threading.Lock()
_decisions: OrderedDict[str, dict] = OrderedDict()
_jobs: dict[str, dict] = {}
_llm_calls: list[float] = []


def demo() -> Demo:
    global _demo
    with _lock:
        if _demo is None:
            _demo = Demo()
    return _demo


def _clean(o):
    """JSON-safe copy: numpy scalars -> Python, NaN/inf -> null."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        o = o.item()
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o if isinstance(o, (str, int, float, bool, type(None))) else str(o)


def _json(obj) -> JSONResponse:
    return JSONResponse(_clean(obj))


def _llm_budget_ok() -> bool:
    now = time.time()
    _llm_calls[:] = [t for t in _llm_calls if now - t < 3600]
    return len(_llm_calls) < LLM_PER_HOUR


def _spawn(requests: list[dict]):
    """Start a Qwen3.8 batch on the deployed Modal GPU app; returns the FunctionCall (non-blocking)."""
    import modal

    engine = modal.Cls.from_name("agqo-llm", "Engine")()
    payload = [{k: r[k] for k in ("system", "user", "schema", "seed", "temperature", "max_tokens")} for r in requests]
    _llm_calls.append(time.time())
    return engine.generate.spawn(payload)


# ------------------------------------------------------------------ pages
@api.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@api.get("/api/meta")
def meta():
    d = demo()
    ev = json.loads((RESULTS_DIR / "llm" / "mandate_eval.json").read_text())
    examples = [r["instruction"] for r in ev["rows"] if r.get("llm_effective")]
    px = d.md.px.loc[d.date]
    stocks = sorted(({"ticker": t, "sector": d.md.sector(t), "price_vnd": float(px[t]),
                      "lot_vnd": float(100 * px[t])} for t in d.universe), key=lambda z: -z["lot_vnd"])
    return _json({"date": str(d.date.date()), "universe": d.universe, "stocks": stocks, "examples": examples,
                  "live_llm": LIVE_LLM, "llm_score": ev["score"],
                  "schedules": len(d.grid), "k": d.model.k, "polish": d.use_polish})


@api.get("/api/story")
def story():
    run = RESULTS_DIR
    dv = pd.read_csv(run / "daily_values.csv", parse_dates=["date"]).set_index("date")
    keep = {"AGQO: AI-guided QAOA rounding": "AGQO", "Practitioner: nearest-lot rounding": "Làm tròn lô gần nhất",
            "VN30 index (scaled)": "Chỉ số VN30", "ETF E1VFVN30": "ETF E1VFVN30"}
    wk = dv[list(keep)].resample("W-FRI").last().dropna()
    q = pd.read_csv(run / "quantum_test.csv")
    q["arm"] = q.arm.str.replace(r"^random_s\d+$", "random_search", regex=True)   # mean of the three seeds
    arms = {"agqo": "AGQO", "warm_start_only": "Khởi động ấm (cổ điển)", "textbook": "QAOA sách giáo khoa",
            "random_search": "Tìm kiếm ngẫu nhiên"}
    qt = (q[q.arm.isin(arms)].pivot_table(index="date", columns="arm", values="success_prob").rename(columns=arms))
    stats = json.loads((run / "quantum_stats.json").read_text())
    rb = pd.read_csv(run / "extras" / "robustness.csv")
    base = rb[rb.scenario.str.startswith("base")]
    hw = pd.read_csv(run / "extras" / "hardware_aware.csv") if (run / "extras" / "hardware_aware.csv").exists() else None
    sc = pd.read_csv(run / "extras" / "scaling.csv")
    man = pd.read_csv(run / "mandates.csv")
    man = man[man.strategy.str.startswith("AGQO")][["instruction", "tracking_error_ann_pct", "te_cost_vs_unconstrained_pp",
                                                     "avg_holdings", "rule_violations_at_rebalance"]]
    expl = json.loads((run / "llm" / "explanations.json").read_text())
    return _json({
        "backtest": {"dates": [str(x.date()) for x in wk.index],
                     "series": {keep[c]: (wk[c] / 1e6).round(3).tolist() for c in keep}},
        "quarters": {"dates": qt.index.tolist(), "series": {c: (100 * qt[c]).round(2).tolist() for c in qt.columns}},
        "stats": stats,
        "accounts": base[["capital_vnd", "te_practitioner", "te_whole_lot_optimum", "te_greedy", "ci_low", "ci_high",
                          "return_practitioner", "return_whole_lot_optimum"]].to_dict("records"),
        "scaling": sc.to_dict("records"),
        "hardware": hw.to_dict("records") if hw is not None else [],
        "mandates": man.to_dict("records"),
        "explainer_score": expl["score"],
        "explanation_example": expl["rows"][-1],
    })


# ------------------------------------------------------------------ LLM: mandate
class MandateIn(BaseModel):
    text: str = Field(max_length=600)
    live: bool = True


@api.post("/api/mandate")
def mandate(body: MandateIn):
    d = demo()
    text = body.text.strip()
    if not text:
        return _json({"mandate": Mandate().to_dict(), "source": "no instruction", "job": None})
    res = compile_mandate(text, d.sector_of, backend="none")     # logged live answer, else keyword rules
    res["job"] = None
    if res["source"].startswith("keyword") and body.live and LIVE_LLM:
        if not _llm_budget_ok():
            res["llm_note"] = "live LLM budget for this hour is used up; keyword rules shown"
        else:
            try:
                req = mandate_request(text, d.sector_of)
                fc = _spawn([req])
                jid = uuid.uuid4().hex[:12]
                _jobs[jid] = {"kind": "mandate", "fc": fc.object_id, "req": req, "t0": time.time()}
                res["job"] = jid
            except Exception as e:                                  # Modal not reachable: keep the fallback
                res["llm_note"] = f"live LLM unavailable ({type(e).__name__}); keyword rules shown"
    res.pop("fallback_reason", None)
    return _json(res)


# ------------------------------------------------------------------ the decision
class DecideIn(BaseModel):
    capital_million: float = Field(ge=5, le=2000)
    mandate: dict = {}


@api.post("/api/decide")
def decide(body: DecideIn):
    d = demo()
    m = Mandate.from_dict(body.mandate or {})
    errs = m.validate(set(d.sector_of))
    if errs:
        raise HTTPException(400, "; ".join(errs))
    try:
        out = d.decide(body.capital_million * 1e6, m)
    except Exception as e:
        raise HTTPException(422, f"no feasible whole-lot portfolio for these rules ({type(e).__name__}: {e})")
    did = uuid.uuid4().hex[:12]
    _decisions[did] = out
    while len(_decisions) > 40:
        _decisions.popitem(last=False)
    res = {k: v for k, v in out.items() if not k.startswith("_")}
    res["id"] = did
    return _json(res)


@api.get("/api/qasm/{did}")
def qasm(did: str):
    out = _decisions.get(did)
    if out is None:
        raise HTTPException(404, "decision expired; run it again")
    from agqo.quantum.export import build_circuit, to_qasm

    inst, land, cp, spec, r = out["_rec"]
    return PlainTextResponse(to_qasm(build_circuit(cp, spec, r.angles)), media_type="text/plain",
                             headers={"Content-Disposition": f"attachment; filename=agqo_{inst.date}.qasm"})


# ------------------------------------------------------------------ LLM: explanation
class ExplainIn(BaseModel):
    id: str


@api.post("/api/explain")
def explain(body: ExplainIn):
    out = _decisions.get(body.id)
    if out is None:
        raise HTTPException(404, "decision expired; run it again")
    ev = demo().evidence(out)
    if not LIVE_LLM:
        return _json({"job": None, "evidence": ev, "note": "live LLM disabled on this server"})
    if not _llm_budget_ok():
        return _json({"job": None, "evidence": ev, "note": "live LLM budget for this hour is used up"})
    try:
        req = explain_request(ev)
        fc = _spawn([req])
    except Exception as e:
        return _json({"job": None, "evidence": ev, "note": f"live LLM unavailable ({type(e).__name__})"})
    jid = uuid.uuid4().hex[:12]
    _jobs[jid] = {"kind": "explain", "fc": fc.object_id, "req": req, "ev": ev, "t0": time.time()}
    return _json({"job": jid, "evidence": ev})


@api.get("/api/job/{jid}")
def job(jid: str):
    j = _jobs.get(jid)
    if j is None:
        raise HTTPException(404, "unknown job")
    if "result" in j:
        return _json(j["result"])
    import modal

    try:
        out = modal.FunctionCall.from_id(j["fc"]).get(timeout=0)[0]
    except TimeoutError:
        return _json({"status": "running", "seconds": round(time.time() - j["t0"])})
    except Exception as e:
        j["result"] = {"status": "failed", "error": f"{type(e).__name__}: {e}"[:300]}
        return _json(j["result"])
    try:
        parsed = json.loads(out["raw_text"])
    except (json.JSONDecodeError, TypeError):
        parsed = None
    res = {"status": "done", "seconds": round(time.time() - j["t0"]), "model": out.get("model"),
           "usage": out.get("usage"), "gpu": out.get("gpu"), "model_load_s": out.get("model_load_s")}
    if j["kind"] == "mandate":
        d = demo()
        m, clar, errs = parse_mandate(parsed, set(d.sector_of))
        res |= {"mandate": m.to_dict(), "needs_clarification": clar, "errors": errs,
                "question": (parsed or {}).get("clarification_question_vi"), "source": "Qwen3.8-27B (live, Modal H100)",
                "raw": parsed}
    else:
        res |= {"explanation": parsed, "check": verify_explanation(parsed, j["ev"])}
    j["result"] = res
    return _json(res)
