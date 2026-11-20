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
TASKS = ["smoke"]          # any of: smoke, reproduce, pytest, presets, account_benchmark, llm_mandates,
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
    with modal.enable_output(), mr.app.run():
        res = mr.smoke.remote(REV)
    kept["smoke"] = keep(res); show(kept["smoke"])"""),
    (MD, """## Product failure reproduction

Runs the decision pipeline on the edge cases reported against V3.1 and audits every result on the
post-trade NAV (cash after fees + holdings). Output: `product_failures.json`."""),
    (CODE, """if "reproduce" in TASKS:
    with modal.enable_output(), mr.app.run():
        res = mr.reproduce.remote(REV)
    kept["reproduce"] = keep(res); show(kept["reproduce"])
    pf = json.loads((kept["reproduce"] / "product_failures.json").read_text())
    for c in pf["cases"]:
        a = c.get("audit", {})
        print(f"{c['case'][:58]:58s} {c['outcome']:9s} status={c.get('status')} app_ok={c.get('app_all_ok')} audit_ok={a.get('all_ok')}")
    print("verifier accepts swapped numbers:", pf["verifier_swap"]["swapped"]["check"]["ok"])"""),
    (MD, "## Test suite (including the circuit-simulating tests) on Modal CPU"),
    (CODE, """if "pytest" in TASKS:
    with modal.enable_output(), mr.app.run():
        res = mr.pytest_suite.remote(REV, PYTEST_ARGS)
    kept["pytest"] = keep(res); show(kept["pytest"])
    print((kept["pytest"] / "pytest.txt").read_text()[-3000:])"""),
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
