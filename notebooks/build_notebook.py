"""Generate notebooks/AGQO_V3_2_Research_Modal.ipynb from the cells below (keeps the notebook reviewable).

    python notebooks/build_notebook.py

Execute (from the repository root; the notebook only submits work, Modal runs it):
    papermill notebooks/AGQO_V3_2_Research_Modal.ipynb results/runs/notebook_<date>.ipynb -p TASKS '["reproduce"]'
or open it in Jupyter / Modal Notebooks and run the cells in order.
"""

from pathlib import Path

import nbformat as nbf

MD, CODE = "markdown", "code"
CELLS = [
    (MD, """# AGQO V3.2 research runs on Modal

This notebook is the entry point for every quantum simulation, benchmark rerun and live LLM experiment of
V3.2. It submits work to Modal and keeps a local copy of each run directory under `results/runs/`.
No circuit is simulated in this kernel: the functions live in `modal_research.py` (Modal CPU) and
`modal_app.py` (Qwen3.8-27B on a Modal H100).

Prerequisites: `modal token new` once (credentials stay in `~/.modal.toml`), the price snapshot at
`data/vn30/ohlcv_daily.csv`, and for LLM tasks the deployed `agqo-llm` app. Vietnamese guide:
`docs/vi/NGHIEN_CUU_MODAL.md`.

Set `TASKS` in the next cell (papermill parameter) to choose what runs."""),
    (CODE, """# Parameters (papermill)
TASKS = ["smoke"]          # any of: smoke, reproduce, pytest, knn_table, knn_refine, presets, account_benchmark, llm_mandates,
                           #         llm_circuits, knn_table, knn_study
PYTEST_ARGS = []
LLM_MODEL_APP = "agqo-llm"
RUN_TAG = \"\""""),
    (CODE, """import json, os, sys, time
from pathlib import Path

ROOT = Path.cwd()
while not (ROOT / "modal_research.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import modal
import modal_research as mr
from agqo.research.orchestrate import keep, revision, show

REV = revision()
print("revision", REV)
kept = {}"""),
    (MD, "## Smoke test: image, data snapshot and Volume"),
    (CODE, """if "smoke" in TASKS:
    with mr.app.run():
        res = mr.smoke.remote(REV)
    kept["smoke"] = keep(res); show(kept["smoke"])"""),
    (MD, """## Product failure reproduction

Runs the decision pipeline on the edge cases reported against V3.1 and audits every result on the
post-trade NAV (cash after fees + holdings). Output: `product_failures.json`."""),
    (CODE, """if "reproduce" in TASKS:
    with mr.app.run():
        res = mr.reproduce.remote(REV)
    kept["reproduce"] = keep(res); show(kept["reproduce"])
    pf = json.loads((kept["reproduce"] / "product_failures.json").read_text())
    for c in pf["cases"]:
        a = c.get("audit", {})
        print(f"{c['case'][:58]:58s} {c['outcome']:9s} status={c.get('status')} app_ok={c.get('app_all_ok')} audit_ok={a.get('all_ok')}")
    print("verifier accepts swapped numbers:", pf["verifier_swap"]["swapped"]["check"]["ok"])"""),
    (MD, "## Test suite (including the circuit-simulating tests) on Modal CPU"),
    (CODE, """if "pytest" in TASKS:
    with mr.app.run():
        res = mr.pytest_suite.remote(REV, PYTEST_ARGS)
    kept["pytest"] = keep(res); show(kept["pytest"])
    print((kept["pytest"] / "pytest.txt").read_text()[-3000:])"""),
    (MD, """## k-NN study: success table (protocol §4)

Builds every calibration, validation, holdout and V3-test instance (5 account sizes × 3 constraint types) in
Modal containers and scores all 1,080 grid schedules on each with an exact statevector. The caller only
collects rows. Output: `meta.csv` (spec, features, baselines), `success_table.npz` (success, two-qubit gates)."""),
    (CODE, """if "knn_table" in TASKS:
    import numpy as np, pandas as pd
    from agqo.data import MarketData
    from agqo.research.instances import specs
    from agqo.research.orchestrate import local_run, push
    md = MarketData.load()
    sp = specs(md) + specs(md, splits=("v3_test",))
    run = local_run("knn-table", {"n_specs": len(sp), "grid": "V3 DesignConfig (1080 schedules)", "batch": 3,
                                  "account": "fresh cash", "sizes": sorted({s["capital_vnd"] for s in sp})})
    batches = [sp[i:i + 3] for i in range(0, len(sp), 3)]
    from agqo.research.orchestrate import fanout
    with mr.app.run():
        parts = fanout(mr.schedule_rows, batches,
                       on_item=lambda i, r: i % 30 == 0 and run.log(f"{3 * i}/{len(sp)} instances"))
        rows = [r for part in parts for r in part]
        ok = [r for r in rows if "error" not in r]
        bad = [r for r in rows if "error" in r]
        for r in bad:
            run.manifest["errors"].append({"where": f"{r['split']} {r['date']} {r['capital_vnd']:.0f} {r['constraint']}",
                                           "error": r["error"], "traceback": ""})
        key = lambda r: (r["split"], r["date"], r["capital_vnd"], r["constraint"])
        ok.sort(key=key)
        meta = pd.DataFrame([{k: v for k, v in r.items() if k not in ("features", "success", "cx", "warm_success")}
                             | {f"f_{k}": v for k, v in r["features"].items()}
                             | {f"warm_{k}": v for k, v in r["warm_success"].items()} for r in ok])
        run.save("meta.csv", meta)
        np.savez_compressed(run.dir / "success_table.npz", success=np.array([r["success"] for r in ok], dtype=np.float32),
                            cx=np.array([r["cx"] for r in ok], dtype=np.int32))
        run.step("table", instances=len(ok), errors=len(bad), cpu_seconds=float(meta.seconds.sum()))
        run.finish(instances=len(ok), errors=len(bad), cpu_hours=round(float(meta.seconds.sum()) / 3600, 2))
        push(run, mr.archive)
    kept["knn_table"] = run.dir; show(run.dir)"""),
    (MD, "## Summary of this notebook execution"),
    (CODE, """print(json.dumps({k: str(v) for k, v in kept.items()}, indent=1))"""),
]


def build(path: Path = Path(__file__).with_name("AGQO_V3_2_Research_Modal.ipynb")) -> Path:
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    for kind, src in CELLS:
        cell = nbf.v4.new_markdown_cell(src) if kind == MD else nbf.v4.new_code_cell(src)
        if kind == CODE and src.startswith("# Parameters"):
            cell.metadata["tags"] = ["parameters"]
        nb.cells.append(cell)
    nbf.write(nb, path)
    return path


if __name__ == "__main__":
    print(build())
