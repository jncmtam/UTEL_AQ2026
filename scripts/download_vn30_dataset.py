"""Download point-in-time VN30 coverage with raw and rights-adjusted OHLCV."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, time as day_time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from agqo.universe import load_membership_history


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data" / "vn30_snapshot_20261002"
DEFAULT_MEMBERSHIP = DEFAULT_DIR / "vn30_membership_history.csv"
RAW_ENDPOINT = "https://services.entrade.com.vn/chart-api/v2/ohlcs"
VNSTOCK_VERSION = "5.1.0"
ADJUSTMENT_SOURCE = "vci"
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
RAW_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://banggia.dnse.com.vn",
    "referer": "https://banggia.dnse.com.vn/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 Chrome/124 Safari/537.36",
}
RAW_FIELDS = ("open", "high", "low", "close")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _date_epoch(value: str, *, next_day: bool = False) -> int:
    date = pd.Timestamp(value).date()
    if next_day:
        date += timedelta(days=1)
    return int(datetime.combine(date, day_time.min, tzinfo=VN_TZ).timestamp())


def _download_raw(symbol: str, kind: str, start: str, end: str) -> pd.DataFrame:
    params = {
        "from": _date_epoch(start),
        "to": _date_epoch(end, next_day=True),
        "symbol": symbol,
        "resolution": "1D",
    }
    response = requests.get(
        f"{RAW_ENDPOINT}/{kind}", params=params, headers=RAW_HEADERS, timeout=45
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, (list, dict)) or not payload:
        raise ValueError(f"DNSE không trả dữ liệu OHLCV thô cho {symbol}.")
    frame = pd.DataFrame(payload)
    required = {"t", "o", "h", "l", "c", "v"}
    if not required.issubset(frame.columns):
        raise ValueError(f"DNSE trả cấu trúc không nhận diện được cho {symbol}: {frame.columns.tolist()}")
    frame["date"] = (
        pd.to_datetime(frame["t"], unit="s", utc=True)
        .dt.tz_convert(VN_TZ)
        .dt.strftime("%Y-%m-%d")
    )
    frame = frame.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    frame = frame.groupby("date", as_index=False).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"),
    )
    # DNSE's native OHLC values are in thousands of VND for shares, but index
    # levels are already points. Standardize shares to VND/share.
    scale = 1000.0 if kind == "stock" else 1.0
    for column in RAW_FIELDS:
        frame[column] = pd.to_numeric(frame[column], errors="raise") * scale
    frame["volume"] = pd.to_numeric(frame["volume"], errors="raise")
    return frame[["date", *RAW_FIELDS, "volume"]]


def _download_adjusted(market, symbol: str, start: str, end: str) -> tuple[pd.DataFrame, dict]:
    response = market.equity(symbol).ohlcv(
        start=start, end=end, interval="1D", source=ADJUSTMENT_SOURCE, floating=None
    )
    if response.empty or not {"time", *RAW_FIELDS, "volume"}.issubset(response.columns):
        raise ValueError(f"VCI không trả OHLC điều chỉnh đủ cột cho {symbol}.")
    frame = response.copy()
    time_values = pd.to_datetime(frame["time"], errors="raise")
    if time_values.dt.tz is None:
        time_values = time_values.dt.tz_localize(VN_TZ)
    frame["date"] = time_values.dt.tz_convert(VN_TZ).dt.strftime("%Y-%m-%d")
    frame = frame.rename(columns={f: f"{f}_adjusted" for f in RAW_FIELDS})
    for column in [f"{f}_adjusted" for f in RAW_FIELDS]:
        # Vnstock VCI equity OHLC is returned in thousand VND per share.
        frame[column] = pd.to_numeric(frame[column], errors="raise") * 1000.0
    frame["adjusted_volume"] = pd.to_numeric(frame["volume"], errors="raise")
    metadata = {
        "source": response.attrs.get("source", ADJUSTMENT_SOURCE),
        "source_name": response.attrs.get("source_name", "Vietcap (VCI)"),
        "terms_url": response.attrs.get("terms_url", "https://www.vietcap.com.vn/dieu-khoan-su-dung-chinh-sach-bao-mat"),
        "requested_at": response.attrs.get("requested_at"),
        "returned_rows": int(len(frame)),
        "date_start": str(frame["date"].min()),
        "date_end": str(frame["date"].max()),
    }
    return frame[["date", *[f"{f}_adjusted" for f in RAW_FIELDS], "adjusted_volume"]], metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default="2022-01-01")
    parser.add_argument("--end-date", default="2026-10-19")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--membership-history", type=Path, default=DEFAULT_MEMBERSHIP)
    parser.add_argument("--pause-seconds", type=float, default=3.5)
    args = parser.parse_args()
    if args.end_date < args.start_date:
        parser.error("Ngày kết thúc phải sau ngày bắt đầu.")
    if args.pause_seconds < 3:
        parser.error("Khoảng nghỉ tối thiểu là 3 giây để tôn trọng giới hạn truy vấn cộng đồng.")

    try:
        from vnstock import Market
    except ImportError as exc:
        raise SystemExit(
            "Thiếu Vnstock 5.1.0. Cài bằng: python -m pip install -r requirements-data.txt"
        ) from exc

    membership_path = args.membership_history.resolve()
    if not membership_path.exists():
        raise SystemExit(
            f"Không có lịch thành phần {membership_path}; chạy scripts/build_vn30_membership_history.py trước."
        )
    history = load_membership_history(membership_path)
    stock_tickers = sorted(history["ticker"].unique())
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    market = Market()
    chunks = []
    failures = []
    provider_rows = []
    requests_to_make = [(ticker, "stock") for ticker in stock_tickers]
    requests_to_make += [(symbol, "index") for symbol in ("VN30", "VNINDEX")]
    for number, (ticker, kind) in enumerate(requests_to_make, start=1):
        print(f"[{number}/{len(requests_to_make)}] {ticker} ({kind})", flush=True)
        try:
            raw = _download_raw(ticker, kind, args.start_date, args.end_date)
            if kind == "stock":
                adjusted, metadata = _download_adjusted(
                    market, ticker, args.start_date, args.end_date
                )
                raw_first = pd.Timestamp(raw["date"].min())
                adjusted_first = pd.Timestamp(adjusted["date"].min())
                if adjusted_first - raw_first > pd.Timedelta(days=365):
                    raise SystemExit(
                        "Vnstock đang chạy ở quyền Khách và chỉ trả khoảng 365 ngày giá điều chỉnh. "
                        "Đăng ký miễn phí Cộng đồng bằng `vnstock register`, kiểm tra `vnstock status`, "
                        "rồi chạy lại để lấy đủ lịch sử từ ngày yêu cầu. Không dùng chuỗi chỉ có một năm "
                        "để thay thế phần lịch sử còn thiếu."
                    )
                merged = raw.merge(adjusted, how="outer", on="date", validate="one_to_one")
                merged["adjusted_volume"] = merged["adjusted_volume"].fillna(merged["volume"])
                provider_rows.append({"ticker": ticker, "instrument_type": kind, **metadata})
                merged["price_adjustment_status"] = "rights_adjusted_by_vci; event coverage not independently reconciled"
                merged["raw_price_source"] = "DNSE chart API"
                merged["adjusted_price_source"] = ADJUSTMENT_SOURCE
            else:
                merged = raw.copy()
                for column in RAW_FIELDS:
                    merged[f"{column}_adjusted"] = merged[column]
                merged["adjusted_volume"] = merged["volume"]
                merged["price_adjustment_status"] = "not_applicable_index"
                merged["raw_price_source"] = "DNSE chart API"
                merged["adjusted_price_source"] = "not_applicable_index"
            merged["ticker"] = ticker
            merged["instrument_type"] = kind
            chunks.append(merged)
        except Exception as exc:  # external providers can fail intermittently
            failures.append({"ticker": ticker, "instrument_type": kind, "error": repr(exc)})
        time.sleep(args.pause_seconds)

    if failures:
        failure_path = output_dir / "download_failures.json"
        failure_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit(
            f"Tải chưa đủ dữ liệu cho {len(failures)} mã; xem {failure_path}. "
            "Không ghi tập một phần thành bộ dữ liệu hoàn chỉnh."
        )
    data = pd.concat(chunks, ignore_index=True)
    data["date"] = pd.to_datetime(data["date"], errors="raise").dt.strftime("%Y-%m-%d")
    data = data.sort_values(["ticker", "date"]).reset_index(drop=True)
    if data.duplicated(["ticker", "date"]).any():
        raise SystemExit("Dữ liệu có trùng ngày/mã sau khi hợp nhất.")
    required_price_columns = [
        *RAW_FIELDS,
        "volume",
        *[f"{field}_adjusted" for field in RAW_FIELDS],
    ]
    if data[required_price_columns].isna().any().any():
        raise SystemExit("Dữ liệu giá thô hoặc điều chỉnh còn thiếu phiên/cột sau khi hợp nhất.")
    if data.loc[data.instrument_type == "stock", [f"{f}_adjusted" for f in RAW_FIELDS]].isna().any().any():
        raise SystemExit("VCI thiếu OHLC điều chỉnh ở một số phiên; không công bố tập đầy đủ.")
    if (data[[*RAW_FIELDS] + [f"{f}_adjusted" for f in RAW_FIELDS]].dropna() <= 0).any().any():
        raise SystemExit("Dữ liệu giá có giá trị không dương.")

    data_path = output_dir / "ohlcv_daily.csv"
    data.to_csv(data_path, index=False, encoding="utf-8")
    coverage = data.groupby(["instrument_type", "ticker"], as_index=False).agg(
        first_date=("date", "min"), last_date=("date", "max"), sessions=("date", "count")
    ).to_dict("records")
    adjustment_ratios = (
        data.loc[data.instrument_type == "stock"]
        .assign(adjustment_factor=lambda x: x.close_adjusted / x.close)
        .groupby("ticker")["adjustment_factor"]
        .agg(min_factor="min", max_factor="max", distinct_factors="nunique")
        .reset_index().to_dict("records")
    )
    manifest = {
        "dataset_name": "vn30_point_in_time_members_raw_and_rights_adjusted_daily",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_start_date": args.start_date,
        "requested_end_date": args.end_date,
        "membership_history_file": membership_path.name,
        "membership_history_sha256": sha256(membership_path),
        "membership_history_coverage": ["2022-01-01", "2026-10-19"],
        "membership_count_per_effective_snapshot": 30,
        "stock_ticker_count": len(stock_tickers),
        "stock_tickers": stock_tickers,
        "index_tickers": ["VN30", "VNINDEX"],
        "rows": int(len(data)),
        "ohlcv_sha256": sha256(data_path),
        "coverage": coverage,
        "raw_price_source": {
            "provider": "DNSE chart API",
            "endpoint": RAW_ENDPOINT,
            "use": "actual historical OHLC for execution-price assumptions and close×volume liquidity proxy",
            "price_unit": "VND per share for equities; index points for indices",
        },
        "adjusted_price_source": {
            "connector": f"vnstock=={VNSTOCK_VERSION}",
            "provider": "Vietcap (VCI)",
            "provider_price_adjustment": "VCI ohlcv prices are adjusted for entitlement events; use the adjusted columns for return estimation.",
            "provider_terms_url": "https://www.vietcap.com.vn/dieu-khoan-su-dung-chinh-sach-bao-mat",
            "price_unit": "VND per share for equities; index points for indices",
            "adjustment_factor_diagnostics": adjustment_ratios,
            "independent_corporate_action_reconciliation": "not completed; adjusted provider series is documented, but completeness of each dividend, split, bonus issue and rights event is not independently certified",
        },
        "liquidity_measure": "raw close × raw volume; a turnover proxy, not confirmed matched value or executable capacity",
        "membership_method": "Use only the 30 constituents effective on the signal date. History is reconstructed from published HOSE review changes and anchored to the Jan-2026 HOSE membership list; see vn30_membership_events.csv and per-period source URLs.",
        "membership_research_limit": "Review announcements were found for the changes listed, but this is a curated reconstruction rather than a licensed exchange constituents database; use source links to audit each interval.",
        "data_rights": "Vnstock is a connector, not the market-data owner. The connector license does not convey redistribution rights for DNSE/VCI source data. The generated OHLCV file is excluded from Git; check each provider's terms before publication or redistribution.",
        "provider_requests": provider_rows,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"data_file": str(data_path), "rows": len(data), "tickers": len(stock_tickers), "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
