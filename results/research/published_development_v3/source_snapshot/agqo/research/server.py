"""Local English decision application; live GPU inference is a separate bounded CLI."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json

PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AGQO · Portfolio Repair</title>
<style>*{box-sizing:border-box}body{font:15px system-ui;margin:0;background:#101825;color:#e3edf8}main{max-width:1180px;margin:auto;padding:38px 24px}h1{font-size:36px;letter-spacing:-1px;margin:8px 0;color:#7ce4c3}h2{font-size:20px}p{color:#a7b9cf;line-height:1.6}.badge{display:inline-block;background:#27364b;border-radius:20px;padding:6px 12px;font-size:12px}section{background:#19263a;padding:24px;margin:20px 0;border:1px solid #2c3a50;border-radius:14px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}label{display:block;color:#becce0;font-size:13px;margin:12px 0 5px}input,select,button{font:inherit;padding:10px 12px;border:1px solid #3a4a61;border-radius:7px;background:#101b2b;color:#e3edf8;width:100%}button{background:#7ce4c3;color:#0c2924;font-weight:700;cursor:pointer;margin-top:20px}button:disabled{opacity:.5}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#111c2e;padding:16px;border-radius:8px;max-height:420px;overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:12px 9px;text-align:left;border-bottom:1px solid #314259}.error{color:#ffba9c}details{margin-top:16px}a{color:#7ce4c3}.muted{color:#9db1cc}@media(max-width:750px){.grid{grid-template-columns:1fr}table{display:block;overflow:auto}}</style>
<main><span class="badge">Verified research workflow</span><h1>Repair the portfolio.<br>Inspect the evidence.</h1><p>Compare compliance, tracking and trading costs. Every proposed allocation and circuit is checked against the same financial specification.</p>
<div class="grid"><section><h2>1 · Investment requirements</h2><label>Dataset</label><select id="dataset"><option value="synthetic">Synthetic structural demo · software validation</option><option value="market">Historical US equity candidate · audit required</option></select><label>Number of holdings</label><input id="k" type="number" min="3" max="5" value="3"><label>Exclude a security</label><select id="exclude"><option value="">None</option><option>ASSET_00</option><option>ASSET_01</option><option>ASSET_02</option></select><label>Sector A maximum weight (%)</label><input id="cap" type="number" min="0" max="100" value="70"><label>One-way turnover maximum (%)</label><input id="turnover" type="number" min="0" max="100" value="100"><button id="run">Compare repair decisions</button><p id="message" aria-live="polite">The demo uses 6 synthetic assets and an existing 3-asset account. No GPU calls are made from this interface.</p></section>
<section><h2>2 · Dataset and existing holdings</h2><p id="audit">Loading audit status…</p><pre id="holdings">ASSET_00: 33.33%\nASSET_01: 33.33%\nASSET_02: 33.33%\nCash: 0.00%</pre><details><summary>Requirements and feasibility diagnosis</summary><pre id="mandate">Run a comparison to inspect the verified specification.</pre></details></section></div>
<section><h2>3 · Financial trade-offs</h2><p>Tracking RMSE is measured on the estimation window. It is not an out-of-sample return forecast. Costs use the stated 5 bp per-side assumption.</p><div id="comparison">No decision evaluated yet.</div></section>
<section><h2>4 · Trades, circuits and verification</h2><select id="choices"></select><pre id="decision">Choose an evaluated method to inspect its evidence.</pre></section>
<section><h2>Saved experiment · offline replay</h2><p>Replay reads saved measurements without additional inference. Failed and interrupted experiments remain visible.</p><pre id="results"></pre><details><summary>Protocol and cost accounting</summary><pre id="cost"></pre></details></section></main>
<script>const $=s=>document.querySelector(s);let records=[];const fmt=x=>x==null?'—':Number(x).toPrecision(5);fetch('/api/status').then(r=>r.json()).then(x=>{$('#audit').textContent=x.audit.status==='passed'?'Market data admission checks passed.':'Market evaluation blocked: '+x.audit.issues.slice(0,4).join(' ')});fetch('/evidence').then(r=>r.json()).then(x=>{$('#results').textContent=x.results;$('#cost').textContent=JSON.stringify({protocol:x.protocol,cost:x.cost},null,2)}).catch(e=>{$('#results').textContent='No complete saved experiment at this output path.'});$('#run').onclick=async()=>{let button=$('#run');button.disabled=true;$('#message').textContent='Checking the mandate and evaluating common references…';try{let r=await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dataset:$('#dataset').value,k:Number($('#k').value),exclude:$('#exclude').value,sector_cap:Number($('#cap').value)/100,turnover_cap:Number($('#turnover').value)/100})});let x=await r.json();if(!r.ok)throw Error(x.error);$('#mandate').textContent=JSON.stringify({mandate:x.mandate,diagnosis:x.diagnosis},null,2);if(x.status==='blocked'){$('#message').textContent=x.reason;$('#comparison').textContent='No market decision was generated.';return}records=x.methods;let table=document.createElement('table');let head=document.createElement('tr');['Method','Status','Tracking RMSE','Estimated cost / NAV','One-way turnover','CX'].forEach(v=>{let c=document.createElement('th');c.textContent=v;head.append(c)});table.append(head);records.forEach(row=>{let tr=document.createElement('tr');[row.method,row.status,fmt(row.tracking_rmse),fmt(row.transaction_cost),fmt(row.one_way_turnover),row.verification?.resources?.transpiled_cx??'—'].forEach(v=>{let td=document.createElement('td');td.textContent=v;tr.append(td)});table.append(tr)});$('#comparison').replaceChildren(table);$('#choices').replaceChildren();records.forEach((d,i)=>{let o=document.createElement('option');o.value=i;o.textContent=d.method;$('#choices').append(o)});$('#choices').onchange=()=>{$('#decision').textContent=JSON.stringify(records[$('#choices').value],null,2)};if(records.length)$('#choices').onchange();$('#message').textContent='Comparison complete. Inspect allocation feasibility and resource use before interpreting quality.'}catch(e){$('#message').textContent=e.message}finally{button.disabled=false}}</script></html>"""


def decision(payload, directory):
    from dataclasses import replace
    from .runner import cases
    from .workflow import solve_decision
    from .finance import diagnose, Account
    from .data import audit

    if payload.get("dataset", "synthetic") == "market":
        mp = Path("data/us_equities/dataset_manifest.json")
        m = json.loads(mp.read_text()) if mp.exists() else {}
        result = audit(m, mp.parent)
        return {
            "status": "blocked",
            "mandate": payload,
            "diagnosis": result,
            "reason": "Market data needs the source-backed audit and aligned prices. Use the CLI trajectory command after admission.",
        }
    if payload.get("dataset", "synthetic") != "synthetic":
        raise ValueError("Unknown dataset.")
    _, spec = cases()[0]
    k = payload.get("k", 3)
    if type(k) is not int or not 3 <= k <= 5:
        raise ValueError("Demo cardinality must be an integer between 3 and 5.")
    exclude = payload.get("exclude", "")
    if exclude and exclude not in spec.tickers:
        raise ValueError("Unknown security.")
    spec = replace(
        spec,
        k=k,
        exclude=(exclude,) if exclude else (),
        sector_count_caps={},
        sector_weight_caps={"Sector_A": payload.get("sector_cap", 0.7)},
        turnover_cap=payload.get("turnover_cap", 1),
    )
    methods = []
    for method in ("hold", "joint_scip", "allocation_swap", "qaoa_fixed", "qaoa_rules"):
        row = solve_decision(spec, method, evaluations=12, shots=128)
        if row.get("feasible"):
            account = Account(100000 * spec.previous_weights.copy())
            row["order"] = account.rebalance(row["weights"], spec.cost_rate)
            row["trade_rows"] = [
                {"asset": t, "dollars": v}
                for t, v in zip(spec.tickers, row["order"]["trade_dollars"])
                if abs(v) > 1e-5
            ]
        methods.append(row)
    saved = Path("results/research/quasar_interface_v1/records.json")
    if saved.exists():
        records = json.loads(saved.read_text())
        record = next(
            (
                r
                for r in records
                if r.get("task") == "gate_ir_transfer_n6" and r.get("valid")
            ),
            None,
        )
        if record:
            row = solve_decision(
                spec, "qaoa_reuse", program=record["program"], evaluations=12, shots=128
            )
            row["method"] = "quasar4_saved_design"
            row["design_origin"] = {
                "source": str(saved),
                "revision": record["inference"]["revision"],
                "execution": "saved_design_revalidated_no_new_inference",
            }
            methods.append(row)
    result = {
        "status": "completed",
        "mandate": {
            k: v for k, v in spec.to_dict().items() if k not in ("returns", "benchmark")
        },
        "diagnosis": diagnose(spec),
        "methods": methods,
        "execution": "synthetic_local_simulation_no_live_inference",
    }
    from .data import write_json
    from agqo.synthesis.profile import digest

    write_json(Path(directory) / "interactive" / f"{digest(payload)}.json", result)
    return result


def serve(directory, port=8765):
    path = Path(directory)

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, value, mime="application/json"):
            body = (
                value.encode()
                if isinstance(value, str)
                else json.dumps(value, allow_nan=False).encode()
            )
            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.respond(200, PAGE, "text/html")
                return
            if self.path == "/api/status":
                from .data import audit

                mp = Path("data/us_equities/dataset_manifest.json")
                m = json.loads(mp.read_text()) if mp.exists() else {}
                self.respond(200, {"audit": audit(m, mp.parent)})
                return
            if self.path == "/evidence":
                try:
                    value = {
                        "protocol": json.loads((path / "protocol.json").read_text()),
                        "decisions": [
                            json.loads(s)
                            for s in (path / "decisions.jsonl").read_text().splitlines()
                        ],
                        "results": (path / "RESULTS.md").read_text(),
                        "cost": json.loads((path / "cost_report.json").read_text()),
                    }
                except (FileNotFoundError, ValueError):
                    self.respond(
                        503, {"error": "Complete saved artifacts are required."}
                    )
                    return
                self.respond(200, value)
                return
            self.send_error(404)

        def do_POST(self):
            if self.path != "/api/decision":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ValueError("Request body exceeds the supported size.")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Expected an object.")
                self.respond(200, decision(payload, path))
            except (ValueError, TypeError, KeyError) as exc:
                self.respond(400, {"error": str(exc)})

    print(f"AGQO portfolio repair: http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
