"""Modal CPU app for every V3.2 quantum simulation, test run and benchmark rerun.

Nothing in this file simulates a circuit on the caller's machine: each function runs in a Modal
container, writes its run directory to the Volume `agqo-v32-runs` and returns the files so the caller
can keep a local copy under results/runs/<run_id>/. The notebook
`notebooks/AGQO_V3_2_Research_Modal.ipynb` is the entry point; it calls these functions.

    modal run modal_research.py::smoke        # check the image and the data snapshot
    (all research tasks: run the notebook, see docs/vi/NGHIEN_CUU_MODAL.md)

The LLM stays in the GPU app `agqo-llm` (modal_app.py); research functions that need it call the
deployed Engine, so a CPU container never holds a GPU.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
APP_NAME = "agqo-research"
RUNS = "/runs"

app = modal.App(APP_NAME)
runs_volume = modal.Volume.from_name("agqo-v32-runs", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("numpy>=1.26,<3", "scipy>=1.11", "pandas>=2.1", "matplotlib>=3.8", "requests>=2.31",
                    "qiskit==2.5.2", "pytest>=8", "fastapi>=0.115", "httpx>=0.27", "modal>=1.0")
    .env({"AGQO_LIVE_LLM": "0", "PYTHONPATH": "/root"})
    .add_local_dir(ROOT / "data" / "vn30", "/root/data/vn30")
    .add_local_dir(ROOT / "results" / "final", "/root/results/final")
    .add_local_dir(ROOT / "tests", "/root/tests")
    .add_local_dir(ROOT / "app", "/root/app")
    .add_local_file(ROOT / "pyproject.toml", "/root/pyproject.toml")
    .add_local_python_source("agqo")
)

CPU = dict(image=image, volumes={RUNS: runs_volume}, timeout=3 * 3600)


def _start(kind: str, rev: dict, config: dict | None = None, run_id: str | None = None):
    os.environ["AGQO_GIT_REVISION"] = json.dumps(rev)
    from agqo.research.runlog import Run

    return Run(kind, base=Path(RUNS), config=config or {}, run_id=run_id)


def _files(run) -> dict[str, str]:
    """Every text file of the run directory (returned to the caller for its local copy)."""
    runs_volume.commit()
    out = {}
    for p in sorted(run.dir.rglob("*")):
        if p.is_file() and p.stat().st_size < 60_000_000:
            try:
                out[str(p.relative_to(run.dir))] = p.read_text()
            except UnicodeDecodeError:
                pass
    return out


@app.function(cpu=2, memory=4096, **CPU)
def smoke(rev: dict) -> dict:
    run = _start("smoke", rev)
    from agqo.data import MarketData, verify_price_snapshot

    digest = verify_price_snapshot()
    md = MarketData.load()
    run.log(f"data {digest[:12]} ok, {md.close.shape[1]} stocks, last day {md.index.index[-1].date()}")
    run.finish(data_sha256=digest)
    return {"run_id": run.run_id, "files": _files(run)}


@app.function(cpu=8, memory=16384, **CPU)
def reproduce(rev: dict, run_id: str | None = None) -> dict:
    """Product failure modes (fees vs caps, one-stock mandates, clarification, verifier) on Modal CPU."""
    run = _start("product-failures", rev, run_id=run_id)
    from agqo.research.repro import reproduce as go

    try:
        summary = go(run)
        run.finish(**summary)
    except Exception as e:
        run.error("reproduce", e)
        run.finish("failed")
    return {"run_id": run.run_id, "files": _files(run)}


@app.function(cpu=8, memory=16384, **CPU)
def pytest_suite(rev: dict, args: list[str] | None = None) -> dict:
    """The full test suite, including the tests that simulate circuits, on Modal CPU."""
    import subprocess

    run = _start("pytest", rev, {"args": args or []})
    p = subprocess.run(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *(args or [])], cwd="/root",
                       capture_output=True, text=True)
    (run.dir / "pytest.txt").write_text(p.stdout + "\n" + p.stderr)
    tail = (p.stdout.strip().splitlines() or [""])[-1]
    run.log(tail)
    run.finish("ok" if p.returncode == 0 else "failed", returncode=p.returncode, tail=tail)
    return {"run_id": run.run_id, "files": _files(run)}
