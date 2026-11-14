"""Point-in-time market features handed to the LLM market analyst.

Code computes every number; the LLM only reads them. Tickers and dates are
anonymised (S01, S02, ...) so the model cannot recall what happened next to a
named stock -- a guard against look-ahead through pre-training memory.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import MarketData


def feature_table(md: MarketData, date: pd.Timestamp, tickers: list[str], lookback: int) -> pd.DataFrame:
    close = md.close.loc[:date].iloc[:-1]
    vol = md.volume.loc[:date].iloc[:-1]
    r = md.returns.loc[close.index].tail(lookback)
    b = md.index_returns.loc[r.index]
    rows = []
    traded = (close[tickers] * vol[tickers]).tail(60).mean()
    liq_share = traded / traded.sum()
    for t in tickers:
        x = r[t].dropna()
        bb = b.loc[x.index]
        cov = np.cov(x, bb)
        beta = cov[0, 1] / cov[1, 1]
        corr = np.corrcoef(x, bb)[0, 1]
        px = close[t].dropna()
        p60 = px.tail(60)
        rows.append({
            "ticker": t,
            "sector": md.sector(t),
            "liquidity_share_pct": 100 * liq_share[t],
            "beta": beta,
            "corr_to_index": corr,
            "vol_60d_ann_pct": 100 * x.tail(60).std() * np.sqrt(252),
            "ret_20d_pct": 100 * (px.iloc[-1] / px.iloc[-21] - 1),
            "ret_60d_pct": 100 * (px.iloc[-1] / px.iloc[-61] - 1),
            "ret_250d_pct": 100 * (px.iloc[-1] / px.iloc[max(-len(px), -250)] - 1),
            "max_drawdown_60d_pct": 100 * (p60 / p60.cummax() - 1).min(),
            "rel_strength_60d_pct": 100 * ((1 + x.tail(60)).prod() - (1 + bb.tail(60)).prod()),
            "lot_value_mvnd": close[t].iloc[-1] * 100 / 1e6,
        })
    return pd.DataFrame(rows).set_index("ticker")


def benchmark_summary(md: MarketData, date: pd.Timestamp) -> dict:
    lvl = md.index.loc[:date].iloc[:-1]
    r = lvl.pct_change().dropna()
    return {
        "index_ret_20d_pct": round(100 * (lvl.iloc[-1] / lvl.iloc[-21] - 1), 2),
        "index_ret_60d_pct": round(100 * (lvl.iloc[-1] / lvl.iloc[-61] - 1), 2),
        "index_ret_250d_pct": round(100 * (lvl.iloc[-1] / lvl.iloc[max(-len(lvl), -250)] - 1), 2),
        "index_vol_20d_ann_pct": round(100 * r.tail(20).std() * np.sqrt(252), 2),
        "index_vol_250d_ann_pct": round(100 * r.tail(250).std() * np.sqrt(252), 2),
        "index_drawdown_from_250d_high_pct": round(100 * (lvl.iloc[-1] / lvl.tail(250).max() - 1), 2),
    }


def anonymise(table: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, dict[str, str]]:
    """Shuffle rows and replace tickers by S01..Snn. Returns (table, alias->ticker)."""
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(table))
    t = table.iloc[order].copy()
    alias = {f"S{i + 1:02d}": tk for i, tk in enumerate(t.index)}
    t.index = list(alias)
    t.index.name = "id"
    return t, alias
