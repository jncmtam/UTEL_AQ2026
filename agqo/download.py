"""Keyless daily data download from the DNSE (Entrade) chart API.

Downloads every stock that was ever a VN30 member in the membership history
(so the backtest is point-in-time, not survivor-biased), the VN30 and VN-Index
levels, and the VN30 ETFs a retail investor could buy instead of AGQO.

What the series is (measured, see `price_adjustment_check` in the manifest):
the provider back-adjusts equity prices for stock dividends and splits. Returns
are therefore usable, but historical price *levels* are not the prices traded at
the time. ETF prices come from the same endpoint and include each fund's costs.

    python -m agqo download                  # writes data/vn30/ohlcv_daily.csv + manifest.json
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .config import DATA_DIR

ENDPOINT = "https://services.entrade.com.vn/chart-api/v2/ohlcs"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://banggia.dnse.com.vn",
    "referer": "https://banggia.dnse.com.vn/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 Chrome/124 Safari/537.36",
}
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
INDICES = ("VN30", "VNINDEX")
# VN30-tracking ETFs listed on HOSE (fund manager in brackets).
ETFS = {"E1VFVN30": "DCVFM VN30 ETF", "FUESSV30": "SSIAM VN30 ETF", "FUEKIV30": "KIM Growth VN30 ETF"}
HOSE_DAILY_LIMIT = 0.07


def _epoch(d: str, next_day: bool = False) -> int:
    day = pd.Timestamp(d).date() + (timedelta(days=1) if next_day else timedelta())
    return int(datetime.combine(day, datetime.min.time(), tzinfo=VN_TZ).timestamp())


def fetch(symbol: str, kind: str, start: str, end: str) -> pd.DataFrame:
    """Daily OHLCV for one symbol. kind: 'stock' (stocks and ETFs) or 'index'."""
    params = {"from": _epoch(start), "to": _epoch(end, next_day=True), "symbol": symbol, "resolution": "1D"}
    r = requests.get(f"{ENDPOINT}/{kind}", params=params, headers=HEADERS, timeout=45)
    r.raise_for_status()
    j = r.json()
    if not isinstance(j, dict) or not j.get("t"):
        raise ValueError(f"no data for {symbol}")
    f = pd.DataFrame({k: j[k] for k in ("t", "o", "h", "l", "c", "v")})
    f["date"] = pd.to_datetime(f["t"], unit="s", utc=True).dt.tz_convert(VN_TZ).dt.strftime("%Y-%m-%d")
    f = f.groupby("date", as_index=False).agg(open=("o", "first"), high=("h", "max"), low=("l", "min"),
                                              close=("c", "last"), volume=("v", "sum"))
    scale = 1000.0 if kind == "stock" else 1.0        # shares/ETF units are quoted in thousand VND
    for c in ("open", "high", "low", "close"):
        f[c] = pd.to_numeric(f[c]) * scale
    return f


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def adjustment_check(stocks: pd.DataFrame) -> dict:
    """Evidence that the provider series is back-adjusted.

    Unadjusted HOSE prices cannot move more than the +-7% daily limit, so an ex-date
    for a stock dividend or split would show as a larger overnight drop. Adjusted
    series show no such gaps and drift off the HOSE price-tick grid.
    """
    s = stocks.sort_values(["ticker", "date"]).copy()
    s["ret"] = s.groupby("ticker")["close"].pct_change()
    beyond = s[s.ret.abs() > HOSE_DAILY_LIMIT + 0.005]
    return {"stock_days": int(s.ret.notna().sum()),
            "moves_beyond_hose_daily_limit": int(len(beyond)),
            "tickers_with_such_moves": sorted(beyond.ticker.unique().tolist()),
            "share_of_closes_off_10_vnd_grid": round(float((s.close % 10 != 0).mean()), 4),
            "conclusion": ("Large moves are rare (listed above). Without back-adjustment every stock dividend or "
                           "split ex-date across these stocks would appear as a drop beyond the daily limit, so the "
                           "series is treated as back-adjusted. Listed moves still need individual review "
                           "(UPCoM periods, first day after a halt, or a missed adjustment).")}


def download(out_dir: Path = DATA_DIR, start: str = "2022-01-01", end: str | None = None,
             pause: float = 3.0) -> dict:
    end = end or date.today().isoformat()
    mem = pd.read_csv(out_dir / "vn30_membership_history.csv")
    tickers = sorted(mem.ticker.unique())
    jobs = ([(t, "stock", "stock") for t in tickers] + [(t, "index", "index") for t in INDICES]
            + [(t, "stock", "etf") for t in ETFS])
    frames, failures = [], []
    for i, (sym, kind, itype) in enumerate(jobs, 1):
        print(f"[{i}/{len(jobs)}] {sym} ({itype})", flush=True)
        try:
            f = fetch(sym, kind, start, end)
            f["ticker"], f["instrument_type"] = sym, itype
            frames.append(f)
        except Exception as exc:                          # provider hiccups are reported, never hidden
            failures.append({"ticker": sym, "error": repr(exc)})
        time.sleep(pause)
    if failures:
        raise SystemExit(f"download failed for {failures}; nothing written")
    data = pd.concat(frames, ignore_index=True)[["date", "ticker", "instrument_type", "open", "high", "low",
                                                 "close", "volume"]]
    data = data.sort_values(["instrument_type", "ticker", "date"]).reset_index(drop=True)
    if data.duplicated(["ticker", "date"]).any() or (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise SystemExit("duplicate rows or non-positive prices; nothing written")
    path = out_dir / "ohlcv_daily.csv"
    data.to_csv(path, index=False)
    cov = data.groupby(["instrument_type", "ticker"]).date.agg(["min", "max", "count"]).reset_index()
    manifest = {
        "dataset": "VN30 point-in-time members, indices and VN30 ETFs, daily",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "endpoint": ENDPOINT, "requested": [start, end], "rows": int(len(data)), "sha256": _sha(path),
        "stocks": tickers, "indices": list(INDICES), "etfs": ETFS,
        "coverage": cov.rename(columns={"min": "first", "max": "last", "count": "days"}).to_dict("records"),
        "units": "stocks and ETFs in VND per share/unit; indices in points",
        "price_adjustment_check": adjustment_check(data[data.instrument_type == "stock"]),
        "limits": ["Historical equity price levels are provider back-adjusted, so historical lot costs are "
                   "understated relative to the prices traded at the time; returns are unaffected.",
                   "Cash-dividend treatment by the provider is not documented and not independently verified.",
                   "VN30 and VN-Index are price indices (no dividends); the ETFs include distributions and fund costs.",
                   "The connector does not convey redistribution rights; the OHLCV file is not committed."],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(json.dumps({k: manifest[k] for k in ("rows", "sha256", "price_adjustment_check")}, indent=2))
    return manifest


if __name__ == "__main__":
    download()
