"""Deploy the AGQO prototype on Modal: a web container plus a CPU job per decision.

    modal deploy app/modal_web.py                       # app "agqo-prototype", URL label "agqo-prototype"
    AGQO_WEB_APP=agqo-web AGQO_WEB_LABEL=agqo-demo modal deploy app/modal_web.py   # replace the Round-2 URL

The web container (FastAPI) serves the page, compiles instructions and starts jobs; it never simulates.
Each "Run" spawns `decide_job` in its own Modal CPU container: feasibility diagnosis, QUBO, k-NN schedule,
QAOA statevector simulation, exact enumeration, baselines, rule checks on post-trade NAV, explanation
evidence and OpenQASM. Progress goes to the Modal Dict `agqo-progress`, read by the page every second.
Live LLM calls go to the GPU app `agqo-llm` (modal_app.py); AGQO_LLM_PER_HOUR caps them per web container.
"""

import os
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
APP = os.environ.get("AGQO_WEB_APP", "agqo-prototype")
LABEL = os.environ.get("AGQO_WEB_LABEL", "agqo-prototype")
app = modal.App(APP)
progress = modal.Dict.from_name("agqo-progress", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("numpy>=1.26,<3", "scipy>=1.11", "pandas>=2.1", "fastapi[standard]>=0.115", "qiskit==2.5.2",
                    "modal>=1.0")
    .env({"AGQO_LIVE_LLM": "1", "AGQO_LLM_PER_HOUR": "40", "AGQO_WEB_APP": APP, "AGQO_COMPUTE": "modal"})
    .add_local_dir(ROOT / "data" / "vn30", "/root/data/vn30")
    .add_local_dir(ROOT / "results" / "final", "/root/results/final")
    .add_local_dir(ROOT / "results" / "app", "/root/results/app")
    .add_local_dir(ROOT / "app", "/root/app")
    .add_local_python_source("agqo")
)


@app.function(image=image, cpu=2, memory=4096, timeout=600, scaledown_window=600, max_containers=8)
def decide_job(payload: dict, key: str) -> dict:
    """One decision in its own CPU container; stage updates go to the progress Dict under `key`."""
    import sys

    sys.path.insert(0, "/root")
    from agqo.service import run_decision

    t0 = time.time()

    def say(stage, **kw):
        progress[key] = {"stage": stage, "t": round(time.time() - t0, 2),
                         "container": os.environ.get("MODAL_TASK_ID")}

    say("started")
    res = run_decision(payload, progress=say)
    res["execution"] = {"mode": "live_modal", "app": APP, "function": "decide_job",
                        "container": os.environ.get("MODAL_TASK_ID"), "seconds": round(time.time() - t0, 2)}
    return res


@app.function(image=image, cpu=1, memory=2048, scaledown_window=900, timeout=600, max_containers=1)
@modal.concurrent(max_inputs=32)
@modal.asgi_app(label=LABEL)
def web():
    import sys

    sys.path.insert(0, "/root")
    from app.server import api, startup

    startup()                                 # load data and presets once per container
    return api
