"""Self-contained, bounded CPU table construction followed by a CUDA audit."""

from pathlib import Path
import io
import zipfile
import modal

app = modal.App("agqo-decision-audit")
results = modal.Volume.from_name("agqo-research-runs", create_if_missing=False)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("vllm==0.15.0", "jsonschema==4.26.0", "cvxpy==1.9.3",
        "scipy==1.18.1", "scikit-learn==1.9.1", "pandas==3.0.6",
        "qiskit==2.5.2", "qiskit-qasm3-import==0.6.0")
    .env({"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
    .add_local_python_source("agqo")
)


def checked_path(run_id, inputs):
    from agqo.research.decision_audit import RUN_ID
    from agqo.research.data import sha
    if run_id != RUN_ID:
        raise ValueError("Only the registered decision audit is admitted.")
    root = Path(__import__("agqo").__file__).resolve().parent.parent
    for name, expected in inputs["protocol"]["package_source_hashes"].items():
        if sha(root / name) != expected:
            raise ValueError(f"Prepared package differs: {name}")
    return Path("/runs") / run_id


@app.function(image=image, cpu=4, memory=16384, timeout=1800, startup_timeout=180,
              retries=0, max_containers=1, scaledown_window=2, volumes={"/runs": results})
def build_table(run_id, inputs):
    from agqo.research.decision_audit import build_tables
    from agqo.research.data import sha
    path = checked_path(run_id, inputs)
    try:
        summary = build_tables(path, inputs, results.commit)
        return {"summary": summary, "sha256_files": {str(p.relative_to(path)): sha(p) for p in path.rglob("*") if p.is_file()},
                "execution": "modal_cpu_financial_table_no_llm_or_gpu"}
    finally:
        results.commit()


@app.function(image=image, gpu=["H200", "A100-80GB"], cpu=4, memory=16384,
              timeout=600, startup_timeout=300, retries=0, max_containers=1,
              scaledown_window=2, volumes={"/runs": results})
def evaluate(run_id, inputs, table_receipt):
    from agqo.research.decision_audit import audit_gpu
    from agqo.research.data import sha
    path = checked_path(run_id, inputs)
    for name, expected in table_receipt["sha256_files"].items():
        if sha(path / name) != expected:
            raise ValueError("Completed financial table changed before GPU evaluation.")
    try:
        summary = audit_gpu(path, inputs, results.commit)
        source = Path(__import__("agqo").__file__).resolve().parent.parent
        for name in inputs["protocol"]["package_source_hashes"]:
            dest = path / "source_snapshot" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((source / name).read_bytes())
        files = sorted(p for p in path.rglob("*") if p.is_file())
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in files:
                archive.write(file, str(file.relative_to(path)))
        return {"summary": summary, "sha256_files": {str(p.relative_to(path)): sha(p) for p in files}, "archive": stream.getvalue()}
    finally:
        results.commit()
