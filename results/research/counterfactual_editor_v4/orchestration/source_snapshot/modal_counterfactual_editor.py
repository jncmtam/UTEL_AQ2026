"""One new bounded live GPU study; old completed workers remain unchanged."""

from pathlib import Path
import io
import zipfile
import modal
cache = modal.Volume.from_name("agqo-gate-models", create_if_missing=False)
results = modal.Volume.from_name("agqo-research-runs", create_if_missing=False)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("vllm==0.15.0", "jsonschema==4.26.0", "cvxpy==1.9.3",
        "scipy==1.18.1", "scikit-learn==1.9.1", "pandas==3.0.6",
        "qiskit==2.5.2", "qiskit-qasm3-import==0.6.0")
    .env({"HF_HOME": "/model-cache/huggingface", "VLLM_LOGGING_LEVEL": "WARNING",
        "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
        "VLLM_WORKER_MULTIPROC_METHOD": "spawn"})
    .add_local_python_source("agqo")
)

app = modal.App("agqo-counterfactual-editor")


@app.function(image=image, gpu=["H200", "A100-80GB"], cpu=4, memory=98304,
              timeout=2400, startup_timeout=600, retries=0, max_containers=1,
              scaledown_window=2, volumes={"/model-cache": cache, "/runs": results})
def optimize(run_id, inputs):
    from agqo.research.counterfactual_editor import RUN_ID, run
    from agqo.research.cuda_simulation import TorchConservedBasis
    from agqo.research.data import write_json, sha
    from agqo.synthesis.gpu_runtime import generate_coder30

    if run_id != RUN_ID:
        raise ValueError("Only the new registered edit study is authorized here.")
    root = Path("/runs") / run_id
    if root.exists():
        raise ValueError("Existing paid run retained; retrieve rather than redispatch.")
    package_root = Path(__import__("agqo").__file__).resolve().parent.parent
    for name, expected in inputs["live_protocol"]["package_source_hashes"].items():
        if sha(package_root / name) != expected:
            raise ValueError(f"Source changed: {name}")
    try:
        summary = run(root, inputs, generate_coder30, TorchConservedBasis, results.commit)
        for name in inputs["live_protocol"]["package_source_hashes"]:
            target = root / "source_snapshot" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((package_root / name).read_bytes())
        files = sorted(p for p in root.rglob("*") if p.is_file())
        hashes = {str(p.relative_to(root)): sha(p) for p in files}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for p in files:
                archive.write(p, str(p.relative_to(root)))
        return {"summary": summary, "sha256_files": hashes, "archive": stream.getvalue()}
    except Exception as exc:
        write_json(root / "FAILED.json", {"reason": str(exc), "no_automatic_retry": True})
        raise
    finally:
        cache.commit()
        results.commit()


@app.function(image=image, cpu=2, memory=4096, timeout=300,
              startup_timeout=180, retries=0, max_containers=1, scaledown_window=2)
def import_preflight():
    from agqo.research.counterfactual_editor import RUN_ID
    from agqo.research.cuda_simulation import TorchConservedBasis
    from agqo.synthesis.gpu_runtime import generate_coder30
    return {"status": "imports_ready", "run_id": RUN_ID, "executor": TorchConservedBasis.__name__,
            "generator": generate_coder30.__name__, "gpu_requested": False, "model_loaded": False}
