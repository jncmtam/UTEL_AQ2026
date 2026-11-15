"""Point-in-time VN30 data: prices, benchmark, membership and rebalance calendar."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA_DIR, SECTOR_EN


@dataclass
class MarketData:
    close: pd.DataFrame          # date x ticker, adjusted close (stocks only)
    volume: pd.DataFrame         # date x ticker
    index: pd.Series             # VN30 index level
    membership: pd.DataFrame     # ticker, valid_from, valid_to, sector
    etf_close: pd.DataFrame      # date x VN30 ETF, unit price in VND (investable benchmark)

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "MarketData":
        raw = pd.read_csv(data_dir / "ohlcv_daily.csv", parse_dates=["date"])
        stocks = raw[raw.instrument_type == "stock"]
        etfs = raw[raw.instrument_type == "etf"]
        close = stocks.pivot(index="date", columns="ticker", values="close").sort_index()
        volume = stocks.pivot(index="date", columns="ticker", values="volume").sort_index()
        idx = raw[raw.ticker == "VN30"].set_index("date")["close"].sort_index()
        close = close.reindex(idx.index)
        volume = volume.reindex(idx.index)
        etf = (etfs.pivot(index="date", columns="ticker", values="close").sort_index().reindex(idx.index)
               if len(etfs) else pd.DataFrame(index=idx.index))
        mem = pd.read_csv(data_dir / "vn30_membership_history.csv",
                          parse_dates=["valid_from", "valid_to"])
        mem["sector"] = mem["group"].map(SECTOR_EN).fillna(mem["group"])
        return cls(close=close.astype(float), volume=volume.astype(float),
                   index=idx.astype(float), membership=mem, etf_close=etf.astype(float))

    @cached_property
    def px(self) -> pd.DataFrame:
        """Prices for valuation and execution: last traded price carried over days without a trade."""
        return self.close.ffill()

    @cached_property
    def returns(self) -> pd.DataFrame:
        return self.close.pct_change(fill_method=None)

    @cached_property
    def index_returns(self) -> pd.Series:
        return self.index.pct_change()

    def members(self, date: pd.Timestamp) -> list[str]:
        m = self.membership
        live = m[(m.valid_from <= date) & (m.valid_to >= date)]
        return sorted(live.ticker.unique())

    def sector(self, ticker: str) -> str:
        rows = self.membership[self.membership.ticker == ticker]
        return rows.sector.iloc[-1] if len(rows) else "Other"

    def universe(self, date: pd.Timestamp, lookback: int, min_history: int) -> tuple[list[str], list[str]]:
        """Members at `date` that have enough price history strictly before `date`.

        Returns (usable, excluded). Excluded members are reported, never silently hidden.
        """
        hist = self.close.loc[:date].iloc[:-1].tail(lookback)
        usable, excluded = [], []
        for t in self.members(date):
            if t in hist.columns and hist[t].notna().sum() >= min_history:
                usable.append(t)
            else:
                excluded.append(t)
        return usable, excluded

    def trading_day_on_or_after(self, date: pd.Timestamp) -> pd.Timestamp:
        pos = self.index.index.searchsorted(date)
        return self.index.index[min(pos, len(self.index) - 1)]

    def rebalance_dates(self, first: str, last: str, freq: str = "QS") -> list[pd.Timestamp]:
        """First trading day of each calendar quarter ("QS") or month ("MS") in [first, last]."""
        starts = pd.date_range(first, last, freq=freq)
        days = [self.trading_day_on_or_after(d) for d in starts]
        return sorted(set(d for d in days if d <= pd.Timestamp(last)))


def history_window(md: MarketData, date: pd.Timestamp, tickers: list[str], lookback: int):
    """Returns (asset returns T x n, benchmark returns T) using data strictly before `date`."""
    r = md.returns.loc[:date].iloc[:-1].tail(lookback)[tickers]
    b = md.index_returns.loc[r.index]
    mask = r.notna().all(axis=1) & b.notna()
    return r[mask].to_numpy(), b[mask].to_numpy()


def coverage_table(md: MarketData, dates: list[pd.Timestamp], lookback: int, min_history: int) -> pd.DataFrame:
    rows = []
    for d in dates:
        usable, excluded = md.universe(d, lookback, min_history)
        rows.append({"date": d.date().isoformat(), "members": len(usable) + len(excluded),
                     "usable": len(usable), "excluded": ",".join(excluded)})
    return pd.DataFrame(rows)


def shrunk_covariance(r: np.ndarray, shrink: float) -> np.ndarray:
    """Convex blend of the sample covariance and its diagonal (stays PSD)."""
    s = np.cov(r, rowvar=False)
    return (1 - shrink) * s + shrink * np.diag(np.diag(s))
