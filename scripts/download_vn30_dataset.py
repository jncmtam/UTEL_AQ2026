"""Tải snapshot OHLCV ngày cho rổ VN30 và hai chỉ số tham chiếu."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data" / "vn30_snapshot_20261002"
MEMBERS_URL = "https://www.hodl.vn/bai-hoc/vn30-gom-nhung-ma-nao"
SOURCE_REPOSITORY = "https://github.com/nguyenthdat/vnstock-data"
SOURCE_COMMIT = "d6bafb23dd02f3f63273f12b1f3e3949877b2242"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default="2022-01-01")
    parser.add_argument("--end-date", default="2026-10-19")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--pause-seconds", type=float, default=0.5)
    args = parser.parse_args()
    if args.end_date < args.start_date:
        parser.error("Ngày kết thúc phải sau ngày bắt đầu.")
    if args.pause_seconds < 0:
        parser.error("Thời gian nghỉ giữa các truy vấn không được âm.")

    try:
        from vnstock import stock_historical_data
    except ImportError as exc:
        raise SystemExit(
            "Thiếu bộ kết nối vnstock. Cài bằng: "
            "python -m pip install -r requirements-data.txt"
        ) from exc

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    members_path = output_dir / "members.csv"
    if not members_path.exists():
        raise SystemExit(f"Không tìm thấy danh sách mã đóng băng: {members_path}")
    members = pd.read_csv(members_path)
    if len(members) != 30 or members["ticker"].duplicated().any():
        raise SystemExit("Danh sách rổ đầu vào phải có đúng 30 mã duy nhất.")

    requests = [(ticker, "stock") for ticker in members["ticker"]]
    requests.extend((("VN30", "index"), ("VNINDEX", "index")))
    chunks = []
    failures = []
    for number, (ticker, kind) in enumerate(requests, start=1):
        print(f"[{number}/{len(requests)}] Đang lấy {ticker} ({kind})", flush=True)
        for attempt in range(3):
            try:
                frame = stock_historical_data(
                    ticker, args.start_date, args.end_date, "1D", kind
                )
                required = {"time", "open", "high", "low", "close", "volume"}
                if frame.empty or not required.issubset(frame.columns):
                    raise ValueError(
                        f"Nguồn trả bảng rỗng hoặc sai cấu trúc: {list(frame.columns)}"
                    )
                frame = frame.rename(columns={"time": "date"})
                frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
                frame["ticker"] = ticker
                frame["instrument_type"] = kind
                # API có thể trả nhiều phân đoạn nến trong cùng ngày; quy về một nến ngày.
                frame = (
                    frame.sort_values("date")
                    .groupby("date", as_index=False)
                    .agg(
                        open=("open", "first"),
                        high=("high", "max"),
                        low=("low", "min"),
                        close=("close", "last"),
                        volume=("volume", "sum"),
                    )
                )
                frame["ticker"] = ticker
                frame["instrument_type"] = kind
                chunks.append(
                    frame[
                        [
                            "date",
                            "ticker",
                            "instrument_type",
                            "open",
                            "high",
                            "low",
                            "close",
                            "volume",
                        ]
                    ]
                )
                break
            except Exception as exc:  # nguồn công khai có thể chập chờn
                if attempt == 2:
                    failures.append({"ticker": ticker, "error": repr(exc)})
                else:
                    time.sleep(2 ** attempt)
        time.sleep(args.pause_seconds)

    if failures:
        (output_dir / "download_failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        raise SystemExit(
            "Không tải đủ dữ liệu; xem download_failures.json. "
            "Không ghi snapshot một phần thành bộ dữ liệu hoàn chỉnh."
        )

    data = pd.concat(chunks, ignore_index=True)
    data = data.sort_values(["ticker", "date"]).reset_index(drop=True)
    if data.duplicated(["ticker", "date"]).any():
        raise SystemExit("Nguồn trả ngày giao dịch trùng lặp trong cùng một mã.")
    for column in ("open", "high", "low", "close", "volume"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise SystemExit("Phát hiện giá không dương.")
    if (data["volume"] < 0).any():
        raise SystemExit("Phát hiện khối lượng âm.")

    data_path = output_dir / "ohlcv_daily.csv"
    data.to_csv(data_path, index=False, encoding="utf-8")
    coverage = (
        data.groupby(["instrument_type", "ticker"], as_index=False)
        .agg(
            first_date=("date", "min"),
            last_date=("date", "max"),
            sessions=("date", "count"),
        )
        .to_dict("records")
    )
    manifest = {
        "dataset_name": "vn30_current_members_and_indices_daily",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_start_date": args.start_date,
        "requested_end_date": args.end_date,
        "source_library": SOURCE_REPOSITORY,
        "source_library_commit": SOURCE_COMMIT,
        "market_data_endpoint": "https://services.entrade.com.vn/chart-api/v2/ohlcs",
        "member_snapshot_date": "2026-10-02",
        "member_snapshot_source": MEMBERS_URL,
        "member_count": int(len(members)),
        "index_tickers": ["VN30", "VNINDEX"],
        "rows": int(len(data)),
        "ohlcv_sha256": sha256(data_path),
        "members_sha256": sha256(members_path),
        "coverage": coverage,
        "price_unit": "VND per share/index points as returned by the source connector",
        "price_adjustment": "The connector provides OHLCV only; adjusted-close/total-return status is not asserted.",
        "daily_bar_aggregation": "Duplicate records for the same ticker and date are combined as first open, maximum high, minimum low, last close, and summed volume.",
        "membership_limitation": "The present-day VN30 membership snapshot is used for all historical rows; this is not point-in-time constituent history and creates survivorship bias in historical portfolio backtests.",
        "data_rights": "The connector software license does not establish redistribution rights for source market data. Retain locally for research and verify source terms before publishing or redistributing.",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"data_file": str(data_path), "manifest": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
