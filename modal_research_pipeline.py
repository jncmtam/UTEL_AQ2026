"""Cloud CPU stages; live model inference uses the existing bounded GPU app."""

from pathlib import Path
import io
import re
import zipfile
import modal

app = modal.App("agqo-research-pipeline")
results = modal.Volume.from_name(
    "agqo-research-runs", create_if_missing=True, version=2
)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "numpy==2.5.4",
        "scipy==1.18.1",
        "pandas==3.0.6",
        "scikit-learn==1.9.1",
        "matplotlib==3.11.2",
        "jsonschema==4.26.0",
        "cvxpy==1.9.3",
        "pyscipopt==6.3.0",
        "qiskit==2.5.2",
        "qiskit-aer==0.17.2",
        "qiskit-qasm3-import==0.6.0",
        "requests==2.34.2",
    )
    .env({"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MPLBACKEND": "Agg"})
    .add_local_python_source("agqo")
    .add_local_dir("docs/research", "/root/docs/research")
    .add_local_file("pyproject.toml", "/root/pyproject.toml")
    .add_local_file("requirements-lock.txt", "/root/requirements-lock.txt")
    .add_local_file(
        "data/us_equities/dataset_manifest.json",
        "/root/data/us_equities/dataset_manifest.json",
    )
)


def run_path(run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-z0-9_]{1,80}", run_id):
        raise ValueError("Invalid run ID.")
    return Path("/runs") / run_id


@app.function(
    image=image,
    cpu=4,
    memory=8192,
    timeout=900,
    startup_timeout=180,
    retries=0,
    max_containers=1,
    scaledown_window=2,
    volumes={"/runs": results},
)
def prepare_run(run_id, cost_aware=False):
    from agqo.research.cloud_pipeline import prepare

    path = run_path(run_id)
    try:
        return prepare(path, "/root/data/us_equities", cost_aware=cost_aware)
    finally:
        results.commit()


@app.function(
    image=image,
    cpu=4,
    memory=8192,
    timeout=900,
    startup_timeout=180,
    retries=0,
    max_containers=1,
    scaledown_window=2,
    volumes={"/runs": results},
)
def finish_run(run_id, answers, prepared_hash, cost_context):
    from agqo.research.cloud_pipeline import finish
    from agqo.research.data import sha

    path = run_path(run_id)
    try:
        summary = finish(path, answers, prepared_hash, cost_context)
        files = sorted(p for p in path.rglob("*") if p.is_file())
        manifest = {str(p.relative_to(path)): sha(p) for p in files}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for p in files:
                archive.write(p, str(p.relative_to(path)))
        return {
            "summary": summary,
            "sha256_files": manifest,
            "archive": stream.getvalue(),
        }
    finally:
        results.commit()


@app.function(
    image=image,
    cpu=4,
    memory=16384,
    timeout=1800,
    startup_timeout=180,
    retries=0,
    max_containers=1,
    scaledown_window=2,
    volumes={"/runs": results},
)
def improvement_run(run_id, inputs):
    from agqo.research.improvement import run
    from agqo.research.data import sha

    path = run_path(run_id)
    try:
        summary = run(path, inputs)
        files = sorted(p for p in path.rglob("*") if p.is_file())
        hashes = {str(p.relative_to(path)): sha(p) for p in files}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for p in files:
                archive.write(p, str(p.relative_to(path)))
        return {
            "summary": summary,
            "sha256_files": hashes,
            "archive": stream.getvalue(),
        }
    finally:
        results.commit()
