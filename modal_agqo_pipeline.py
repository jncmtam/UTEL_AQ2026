"""Chạy toàn bộ pipeline AGQO trên Modal: walk-forward, phép thử đuôi, biểu đồ và báo cáo.

Container CPU chạy mô phỏng QAOA và đánh giá tài chính; mỗi quyết định LLM được gọi sang
lớp Qwen3.8-27B đã triển khai (modal_qwen38_agqo.py). Kết quả được nén và tải về results/final.

    modal run modal_agqo_pipeline.py                        # walkforward + tail
    modal run modal_agqo_pipeline.py --steps walkforward    # chỉ walk-forward
    modal run modal_agqo_pipeline.py --llm-guide none       # không gọi LLM
    modal run modal_agqo_pipeline.py --data data/vn30_provisional_raw_20261114/ohlcv_daily.csv \
        --results results/provisional_raw_20261114 --provisional   # chạy thử bằng giá thô
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

import modal


ROOT = Path(__file__).resolve().parent
REMOTE_ROOT = "/root/agqo-project"
DATA_REL = "data/vn30_snapshot_20261002/ohlcv_daily.csv"
RESULTS_REL = "results/final"
PROVISIONAL_BANNER = (
    "> **KẾT QUẢ TẠM — MỘT CHUỖI GIÁ DNSE DÙNG CHO CẢ HAI VAI TRÒ.** Lượt chạy này dùng chuỗi giá DNSE chart API "
    "cho cả cột giá thô lẫn cột `*_adjusted`. Kiểm tra dữ liệu cho thấy chuỗi này đã được nhà cung cấp điều chỉnh lùi "
    "theo cổ tức cổ phiếu/chia tách (không có khoảng trống ngày không hưởng quyền vượt biên độ; giá lệch bước giá HOSE), "
    "nên lợi suất dùng được. Tuy nhiên mức giá lịch sử, giá khớp giả định và đại diện thanh khoản `close × volume` "
    "không phải giá giao dịch thực tại thời điểm đó; việc điều chỉnh cổ tức tiền mặt chưa được xác minh và chưa đối soát "
    "với nguồn thứ hai.\n\n"
)
STEPS = ("walkforward", "tail")

app = modal.App(os.environ.get("AGQO_PIPELINE_MODAL_APP", "agqo-pipeline"))

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "numpy==2.5.4",
        "scipy==1.18.1",
        "pandas==3.0.6",
        "scikit-learn==1.9.1",
        "matplotlib==3.11.2",
        "modal==1.6.2",
    )
    .env({"PYTHONPATH": REMOTE_ROOT, "MPLBACKEND": "Agg", "PYTHONUNBUFFERED": "1"})
    # Dữ liệu giá không theo dõi bởi Git vẫn được gửi lên container (chỉ trong phiên chạy).
    .add_local_dir(ROOT / "agqo", f"{REMOTE_ROOT}/agqo", ignore=["**/__pycache__/**"])
    .add_local_dir(ROOT / "scripts", f"{REMOTE_ROOT}/scripts", ignore=["**/__pycache__/**"])
    .add_local_dir(ROOT / "data", f"{REMOTE_ROOT}/data", ignore=["**/modal_upload.zip"])
    .add_local_dir(ROOT / "results", f"{REMOTE_ROOT}/results")
)


def _run(command: list[str], log: list[str]) -> None:
    started = time.time()
    header = f"$ {' '.join(command)}"
    print(header, flush=True)
    log.append(header)
    process = subprocess.Popen(
        command, cwd=REMOTE_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        log.append(line.rstrip("\n"))
    code = process.wait()
    footer = f"[exit {code} after {time.time() - started:.0f}s]"
    print(footer, flush=True)
    log.append(footer)
    if code != 0:
        raise RuntimeError(f"Bước thất bại ({code}): {' '.join(command)}")


@app.function(image=image, cpu=8, memory=32768, timeout=6 * 60 * 60, retries=0)
def run_pipeline(
    steps: list[str], llm_guide: str, data_rel: str, results_rel: str, provisional: bool
) -> dict:
    """Chạy các bước đã chọn; luôn trả log và kết quả đã có, kể cả khi một bước lỗi."""
    log: list[str] = []
    error = None
    results = f"{REMOTE_ROOT}/{results_rel}"
    data = f"{REMOTE_ROOT}/{data_rel}"
    os.makedirs(results, exist_ok=True)
    os.environ["AGQO_RESULTS_DIR"] = results
    os.environ["AGQO_OHLCV_PATH"] = data
    try:
        if "walkforward" in steps:
            _run(
                [
                    "python", "scripts/run_ai_qaoa_walkforward.py",
                    "--llm-guide", llm_guide,
                    "--data", data,
                    "--json", f"{results}/agqo_final_walkforward.json",
                    "--report", f"{results}/BAO_CAO_AGQO_CUOI_CUNG.md",
                    "--figures", f"{results}/figures",
                    "--guide-cache", f"{results}/qwen38_decisions.json",
                ],
                log,
            )
        if "tail" in steps:
            _run(["python", "scripts/run_tail_probe.py"], log)
    except Exception as exc:  # trả về phần đã chạy được để kiểm tra
        error = f"{type(exc).__name__}: {exc}"
    if provisional:
        for name in os.listdir(results):
            if name.endswith(".md"):
                path = os.path.join(results, name)
                with open(path, encoding="utf-8") as stream:
                    text = stream.read()
                if text.startswith(PROVISIONAL_BANNER):
                    continue
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(PROVISIONAL_BANNER + text)
    manifest = os.path.join(os.path.dirname(data), "manifest.json")
    if os.path.exists(manifest):
        with open(manifest, encoding="utf-8") as stream:
            dataset_manifest = json.load(stream)
        with open(os.path.join(results, "dataset_manifest.json"), "w", encoding="utf-8") as stream:
            json.dump(dataset_manifest, stream, ensure_ascii=False, indent=2)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        archive.add(results, arcname=results_rel)
    return {"archive": buffer.getvalue(), "log": "\n".join(log), "error": error}


def _preflight(data_rel: str, provisional: bool) -> None:
    """Không tốn GPU nếu dữ liệu chưa đủ cột giá điều chỉnh theo yêu cầu của walk-forward."""
    path = ROOT / data_rel
    if not path.exists():
        raise SystemExit(f"Thiếu {data_rel}. Chạy scripts/download_vn30_dataset.py trước.")
    manifest_path = path.parent / "manifest.json"
    is_provisional = manifest_path.exists() and "PROVISIONAL_WARNING" in json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    if is_provisional and not provisional:
        raise SystemExit(f"{data_rel} là dữ liệu tạm bằng giá thô; thêm --provisional để chạy và gắn nhãn.")
    header = path.open(encoding="utf-8").readline().strip().split(",")
    required = {f"{column}_adjusted" for column in ("open", "high", "low", "close")}
    missing = sorted(required - set(header))
    if missing:
        raise SystemExit(f"{data_rel} thiếu cột {missing}; tải lại bằng scripts/download_vn30_dataset.py.")


@app.local_entrypoint()
def main(
    steps: str = ",".join(STEPS),
    llm_guide: str = "modal-qwen38",
    data: str = DATA_REL,
    results: str = RESULTS_REL,
    provisional: bool = False,
) -> None:
    selected = [step.strip() for step in steps.split(",") if step.strip()]
    unknown = sorted(set(selected) - set(STEPS))
    if unknown:
        raise SystemExit(f"Bước không hợp lệ: {unknown}; chọn trong {list(STEPS)}.")
    if provisional and results == RESULTS_REL:
        raise SystemExit("Lượt chạy tạm phải ghi vào --results riêng, không đè results/final.")
    _preflight(data, provisional)
    outcome = run_pipeline.remote(selected, llm_guide, data, results, provisional)
    log_path = ROOT / results / "modal_pipeline_run.log"
    with tarfile.open(fileobj=io.BytesIO(outcome["archive"]), mode="r:gz") as archive:
        archive.extractall(ROOT, filter="data")
    log_path.write_text(outcome["log"] + "\n", encoding="utf-8")
    print(f"Đã tải kết quả về {ROOT / results}; log: {log_path}")
    if outcome["error"]:
        raise SystemExit(f"Pipeline dừng với lỗi: {outcome['error']}")
