"""Deploy the AGQO prototype as a public web app on Modal (CPU container, scales to zero).

    modal deploy app/modal_web.py          # prints the public URL  https://<workspace>--agqo-web-web.modal.run

The container holds the `agqo` package, the VN30 data and the frozen results (≈ 15 MB). Every
decision runs live on CPU (QAOA statevector simulation, exact enumeration, ~2-4 s). Live LLM calls go
to the separately deployed GPU app `agqo-llm` (modal_app.py); a cold GPU takes about 6 minutes, so the
page shows the keyword-rule result at once and swaps in Qwen3.8's answer when it arrives.
Cost guard: AGQO_LLM_PER_HOUR caps live LLM calls per hour per web container.
"""

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
app = modal.App("agqo-web")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("numpy>=1.26,<3", "scipy>=1.11", "pandas>=2.1", "fastapi[standard]>=0.115", "qiskit==2.5.2",
                    "modal>=1.0")
    .env({"AGQO_LIVE_LLM": "1", "AGQO_LLM_PER_HOUR": "40"})
    .add_local_dir(ROOT / "data" / "vn30", "/root/data/vn30")
    .add_local_dir(ROOT / "results" / "final", "/root/results/final")
    .add_local_dir(ROOT / "app", "/root/app")
    .add_local_python_source("agqo")
)


@app.function(image=image, cpu=2, memory=4096, scaledown_window=900, timeout=600, max_containers=1)
@modal.concurrent(max_inputs=16)
@modal.asgi_app(label="agqo-demo")
def web():
    import sys

    sys.path.insert(0, "/root")
    from app.server import api, demo

    demo()                                   # load data and the schedule model once per container
    return api
