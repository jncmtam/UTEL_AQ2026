"""AGQO V3.2 prototype web server (FastAPI). The page: choose a preset or type requirements, review the
structured constraints, click Run, follow a real Modal job, read the result.

Run locally (the page still sends every decision to Modal):
    modal deploy app/modal_web.py                      # once: deploys decide_job (and the public page)
    AGQO_LIVE_LLM=0 uvicorn app.server:api --port 8000

Compute modes (env AGQO_COMPUTE)
  modal   (default) each Run spawns `decide_job` in the deployed app AGQO_WEB_APP (default agqo-web-v32)
  replay  only presets, answered from the saved Modal preset run (results/v32/presets.json)
If a live job cannot start, a preset falls back to its replay; anything else returns an error with a retry.
AGQO_ALLOW_LOCAL_COMPUTE=1 additionally allows an in-process run (development only, labelled "fallback").

Endpoints
  GET  /                      the page (app/static/index.html)
  GET  /api/meta              date, universe, sectors, presets (with measured numbers), compute mode
  GET  /api/story             saved V3 evidence for the results section
  POST /api/mandate           instruction -> structured constraints + status (ok | needs_clarification)
  POST /api/run               start a decision job (refused while a clarification is pending)
  GET  /api/run/{id}          job status: queued | running (stage) | done (result) | failed (error)
  POST /api/explain           start the LLM explainer for a finished run
  GET  /api/job/{id}          poll a live LLM job (mandate or explanation)
  GET  /api/qasm/{id}         the run's circuit as OpenQASM 2
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agqo.config import RESULTS_DIR, ROOT, SECTOR_EN
from agqo.demo import compile_mandate
from agqo.llm import v32
from agqo.llm.tasks import explain_request, verify_explanation
from agqo.mandate import Mandate
from agqo.presets import PRESETS, public
from agqo.service import clean

STATIC = Path(__file__).resolve().parent / "static"
V32 = ROOT / "results" / "v32"
LIVE_LLM = os.environ.get("AGQO_LIVE_LLM", "1") == "1"          # set 0 to never start the GPU
LLM_PER_HOUR = int(os.environ.get("AGQO_LLM_PER_HOUR", "40"))    # cost guard for a public URL
COMPUTE = os.environ.get("AGQO_COMPUTE", "modal")
WEB_APP = os.environ.get("AGQO_WEB_APP", "agqo-web-v32")
ALLOW_LOCAL = os.environ.get("AGQO_ALLOW_LOCAL_COMPUTE", "0") == "1"

api = FastAPI(title="AGQO prototype")
api.mount("/static", StaticFiles(directory=STATIC), name="static")

_ctx: dict = {}
_lock = threading.Lock()
_runs: OrderedDict[str, dict] = OrderedDict()
_jobs: dict[str, dict] = {}
_llm_calls: list[float] = []


def startup() -> dict:
    """Light context for the page: prices, universe, sectors, presets. No optimiser state is loaded."""
    with _lock:
        if not _ctx:
            from agqo.data import MarketData
            from agqo.extras import load_config

            ec = load_config(RESULTS_DIR)
            md = MarketData.load()
            date = md.rebalance_dates(ec.test_start, ec.test_end)[-1]
            uni, _ = md.universe(date, ec.problem.lookback_days, ec.problem.min_history)
            replay = json.loads((V32 / "presets.json").read_text()) if (V32 / "presets.json").exists() else None
            _ctx.update(md=md, ec=ec, date=date, universe=uni, sector_of={t: md.sector(t) for t in md.close.columns},
                        replay=replay)
    return _ctx


def _json(obj) -> JSONResponse:
    return JSONResponse(clean(obj))


def _llm_budget_ok() -> bool:
    now = time.time()
    _llm_calls[:] = [t for t in _llm_calls if now - t < 3600]
    return len(_llm_calls) < LLM_PER_HOUR


def _spawn_llm(requests: list[dict]):
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
    c = startup()
    md, date = c["md"], c["date"]
    ev = json.loads((RESULTS_DIR / "llm" / "mandate_eval.json").read_text())
    px = md.px.loc[date]
    stocks = sorted(({"ticker": t, "sector": md.sector(t), "price_vnd": float(px[t]), "lot_vnd": float(100 * px[t])}
                     for t in c["universe"]), key=lambda z: -z["lot_vnd"])
    measured = {p["id"]: p for p in (c["replay"] or {}).get("presets", [])}
    presets = [public(p) | {"measured": measured.get(p["id"], {}).get("measured", {}) | {"outcome": measured.get(p["id"], {}).get("outcome")},
                            "replay_available": "decision" in measured.get(p["id"], {})} for p in PRESETS]
    rules = c["ec"].rules
    return _json({"date": str(date.date()), "universe": c["universe"], "stocks": stocks,
                  "sectors": [{"en": en, "vi": vi} for vi, en in SECTOR_EN.items()],
                  "presets": presets, "replay_run": (c["replay"] or {}).get("run_id"),
                  "live_llm": LIVE_LLM, "llm_score": ev["score"], "compute": COMPUTE, "web_app": WEB_APP,
                  "fees": {"commission_pct": 100 * rules.commission, "sell_tax_pct": 100 * rules.sell_tax,
                           "lot_size": rules.lot_size}})


@api.get("/api/story")
def story():
    run = RESULTS_DIR
    dv = pd.read_csv(run / "daily_values.csv", parse_dates=["date"]).set_index("date")
    keep = {"AGQO: AI-guided QAOA rounding": "AGQO", "Practitioner: nearest-lot rounding": "Làm tròn lô gần nhất",
            "VN30 index (scaled)": "Chỉ số VN30", "ETF E1VFVN30": "ETF E1VFVN30"}
    wk = dv[list(keep)].resample("W-FRI").last().dropna()
    q = pd.read_csv(run / "quantum_test.csv")
    q["arm"] = q.arm.str.replace(r"^random_s\d+$", "random_search", regex=True)
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
    example = expl["rows"][-1]
    ev_last = {e["date"]: e for e in json.loads((run / "evidence.json").read_text())}.get(example["date"])
    if ev_last is not None:                       # re-check the saved example with the V3.2 verifier
        from agqo.llm.fallback import deterministic_explanation
        from agqo.llm.tasks import describe_evidence

        ev_last = describe_evidence(ev_last)
        recheck = verify_explanation(example["explanation"], ev_last)
        example = example | {"check_v32": recheck}
        if not recheck["ok"]:
            example["fallback"] = deterministic_explanation(ev_last)
    v32 = json.loads((V32 / "summary.json").read_text()) if (V32 / "summary.json").exists() else None
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
        "explanation_example": example,
        "v32": v32,
    })


# ------------------------------------------------------------------ instruction -> constraints
class MandateIn(BaseModel):
    text: str = Field(max_length=800)
    live: bool = True


@api.post("/api/mandate")
def mandate(body: MandateIn):
    c = startup()
    text = body.text.strip()
    if not text:
        return _json({"mandate": Mandate().to_dict(), "source": "no instruction", "status": "ok", "conflicts": [],
                      "job": None})
    res = compile_mandate(text, c["sector_of"], backend="none")     # logged live answer, else keyword rules
    res["job"] = None
    if res["source"].startswith("keyword") and body.live and LIVE_LLM:
        if not _llm_budget_ok():
            res["llm_note"] = "live LLM budget for this hour is used up; keyword rules shown"
        else:
            try:
                req = v32.request(text, c["sector_of"])
                fc = _spawn_llm([req])
                jid = uuid.uuid4().hex[:12]
                _jobs[jid] = {"kind": "mandate", "fc": fc.object_id, "req": req, "t0": time.time()}
                res["job"] = jid
            except Exception as e:
                res["llm_note"] = f"live LLM unavailable ({type(e).__name__}); keyword rules shown"
    res.pop("fallback_reason", None)
    return _json(res)


# ------------------------------------------------------------------ decision jobs
class RunIn(BaseModel):
    capital_million: float = Field(ge=5, le=2000)
    mandate: dict = {}
    sources: dict = {}                   # field -> "user" | "preset" | "text" | "unset" (shown back, logged)
    preset_id: str | None = None
    clarification_pending: bool = False
    constraints_confirmed: bool = True      # the page sends false until the user confirms text-derived rules
    with_textbook: bool = True


def _replay(preset_id: str | None, capital: float, mandate: dict) -> dict | None:
    rp = (startup()["replay"] or {})
    for p in rp.get("presets", []):
        if p["id"] == preset_id and "decision" in p and abs(p["capital_million"] - capital) < 1e-9 \
                and Mandate.from_dict(p["mandate"]) == Mandate.from_dict(mandate):
            return p["decision"] | {"execution": {"mode": "replay", "run_id": rp.get("run_id"),
                                                   "note": "saved result of a Modal run; no new computation"}}
    return None


def _store(rid: str, rec: dict) -> None:
    _runs[rid] = rec
    while len(_runs) > 60:
        _runs.popitem(last=False)


@api.post("/api/run")
def run(body: RunIn):
    c = startup()
    if body.clarification_pending:
        raise HTTPException(409, "Hãy trả lời câu hỏi làm rõ trước khi chạy danh mục cá nhân hóa.")
    if not body.constraints_confirmed and "text" in (body.sources or {}).values():
        raise HTTPException(409, "Hãy xác nhận các ràng buộc được diễn giải từ câu của bạn trước khi chạy.")
    m = Mandate.from_dict(body.mandate or {})
    errs = m.validate(set(c["sector_of"]))
    if errs:
        raise HTTPException(400, "; ".join(errs))
    payload = {"capital_million": body.capital_million, "mandate": m.to_dict(), "with_textbook": body.with_textbook}
    rid = uuid.uuid4().hex[:12]
    rec = {"t0": time.time(), "payload": payload, "sources": body.sources, "preset_id": body.preset_id}
    if COMPUTE == "modal":
        try:
            import modal

            fn = modal.Function.from_name(WEB_APP, "decide_job")
            key = f"run-{rid}"
            fc = fn.spawn(payload, key)
            _store(rid, rec | {"mode": "live_modal", "fc": fc.object_id, "key": key})
            return _json({"id": rid, "mode": "live_modal", "status": "queued", "function_call": fc.object_id})
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"[:300]
    else:
        reason = f"compute mode {COMPUTE}"
    rep = _replay(body.preset_id, body.capital_million, m.to_dict())
    if rep is not None:
        _store(rid, rec | {"mode": "replay", "result": rep | {"execution": rep["execution"] | {"why": reason}}})
        return _json({"id": rid, "mode": "replay", "status": "done", "note": reason})
    if ALLOW_LOCAL:
        from agqo.service import run_decision

        _store(rid, rec | {"mode": "fallback_inprocess", "stage": "started"})

        def work():
            def say(stage, **kw):
                _runs[rid]["stage"] = stage
            try:
                res = run_decision(payload, progress=say)
                _runs[rid]["result"] = res | {"execution": {"mode": "fallback_inprocess", "why": reason}}
            except Exception as e:
                _runs[rid]["error"] = f"{type(e).__name__}: {e}"
        threading.Thread(target=work, daemon=True).start()
        return _json({"id": rid, "mode": "fallback_inprocess", "status": "queued", "note": reason})
    raise HTTPException(503, f"Không khởi động được job trên Modal ({reason}). Hãy thử lại sau ít phút.")


@api.get("/api/run/{rid}")
def run_status(rid: str):
    rec = _runs.get(rid)
    if rec is None:
        raise HTTPException(404, "Không tìm thấy lần chạy này (máy chủ có thể đã khởi động lại). Hãy bấm chạy lại.")
    t = round(time.time() - rec["t0"], 1)
    if "result" in rec:
        return _json({"id": rid, "status": "done", "seconds": t, "mode": rec["mode"], "result": rec["result"],
                      "sources": rec["sources"]})
    if "error" in rec:
        return _json({"id": rid, "status": "failed", "seconds": t, "mode": rec["mode"], "error": rec["error"]})
    if rec["mode"] == "fallback_inprocess":
        return _json({"id": rid, "status": "running", "stage": rec.get("stage"), "seconds": t, "mode": rec["mode"]})
    import modal

    try:
        out = modal.FunctionCall.from_id(rec["fc"]).get(timeout=0)
    except TimeoutError:
        stage = None
        try:
            stage = modal.Dict.from_name("agqo-v32-progress").get(rec["key"])
        except Exception:
            pass
        return _json({"id": rid, "status": "running" if stage else "queued", "stage": stage, "seconds": t,
                      "mode": rec["mode"], "function_call": rec["fc"]})
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"[:500]
        return _json({"id": rid, "status": "failed", "seconds": t, "mode": rec["mode"], "error": rec["error"]})
    if out.get("status") == "invalid":
        rec["error"] = "; ".join(out.get("errors", []))
        return _json({"id": rid, "status": "failed", "seconds": t, "mode": rec["mode"], "error": rec["error"]})
    rec["result"] = out
    return _json({"id": rid, "status": "done", "seconds": t, "mode": rec["mode"], "result": out,
                  "sources": rec["sources"]})


@api.get("/api/qasm/{rid}")
def qasm(rid: str):
    rec = _runs.get(rid)
    q = (rec or {}).get("result", {}).get("qasm")
    if not q:
        raise HTTPException(404, "no circuit for this run")
    return PlainTextResponse(q, media_type="text/plain",
                             headers={"Content-Disposition": f"attachment; filename=agqo_{rec['result']['date']}.qasm"})


# ------------------------------------------------------------------ LLM: explanation
class ExplainIn(BaseModel):
    id: str


@api.post("/api/explain")
def explain(body: ExplainIn):
    rec = _runs.get(body.id)
    ev = (rec or {}).get("result", {}).get("evidence")
    if not ev:
        raise HTTPException(404, "Lần chạy này không có bằng chứng để giải thích (không chạy mạch hoặc đã hết hạn).")
    if not LIVE_LLM:
        return _json({"job": None, "evidence": ev, "note": "live LLM disabled on this server"})
    if not _llm_budget_ok():
        return _json({"job": None, "evidence": ev, "note": "live LLM budget for this hour is used up"})
    try:
        req = explain_request(ev)
        fc = _spawn_llm([req])
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
        c = startup()
        pr = v32.parse(parsed, set(c["sector_of"]))
        mstatus = pr.pop("status")                   # keep "status" for the job state (done), not the parse state
        res |= pr | {"mandate_status": mstatus, "needs_clarification": mstatus != "ok",
                     "source": "Qwen3.8-27B, V3.2 prompt (live, Modal H100)", "raw": parsed}
    else:
        check = verify_explanation(parsed, j["ev"])
        res |= {"explanation": parsed, "check": check}
        if not check["ok"]:                       # never show an unchecked sentence as the explanation
            from agqo.llm.fallback import deterministic_explanation

            det = deterministic_explanation(j["ev"])
            res |= {"fallback": det, "fallback_check": verify_explanation(det, j["ev"])}
    j["result"] = res
    return _json(res)
