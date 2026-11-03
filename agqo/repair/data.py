"""Versioned synthetic fixtures, strict OR-Library price adapter and window construction."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from urllib.request import urlopen
import numpy as np

from .mandates import normalize_rules
from .model import ProblemInstance

OR_URL = "https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/indtrack1.txt"


@dataclass
class MarketData:
    tickers: tuple[str, ...]
    sectors: tuple[str, ...]
    returns: np.ndarray
    benchmark: np.ndarray
    provenance: dict


def synthetic_data(seed=20261031, n=8, periods=240):
    if not 3 <= n <= 12 or periods < 100:
        raise ValueError("Synthetic fixture requires 3<=N<=12 and at least 100 periods.")
    rng = np.random.default_rng(seed)
    market = rng.normal(0.0002, 0.008, periods)
    factors = rng.normal(0, 0.004, (periods, 3))
    r = np.column_stack([market * (0.7 + 0.6 * i / n) + factors[:, i % 3] + rng.normal(0, 0.005, periods) for i in range(n)])
    benchmark = r @ (np.arange(1, n + 1) / np.arange(1, n + 1).sum())
    return MarketData(tuple(f"S{i:02}" for i in range(n)), tuple(("Banks", "Industry", "Services")[i % 3] for i in range(n)),
                      r, benchmark, {"kind": "synthetic", "generator": "repair-factor-v1", "seed": seed,
                                     "periods_per_year": None, "benchmark": "synthetic_weighted_basket", "sector_source": "synthetic"})


def fetch_or_library(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    path = directory / "indtrack1.txt"
    if not path.exists():
        with urlopen(OR_URL, timeout=30) as response:
            content = response.read(2_000_000)
        # Validate before persisting, including expected source dimensions.
        parse_or_prices(content.decode(), expected_n=31)
        path.write_bytes(content)
    data = parse_or_prices(path.read_text(), expected_n=31)
    manifest = {**data.provenance, "url": OR_URL, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "raw_file": path.name, "rights": "Public research source; redistribution permission not asserted. Raw file excluded from Git."}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def parse_or_prices(text, expected_n=None):
    tokens = text.split()
    try:
        n, t = int(tokens[0]), int(tokens[1])
        values = np.asarray([float(x) for x in tokens[2:]], dtype=float)
    except (ValueError, IndexError) as exc:
        raise ValueError("Invalid OR-Library header or value.") from exc
    if n < 1 or t < 2 or values.size != (n + 1) * (t + 1) or (expected_n is not None and n != expected_n):
        raise ValueError("OR-Library dimensions or price counts disagree.")
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("OR-Library prices must be finite and positive.")
    prices = values.reshape(n + 1, t + 1).T
    returns = prices[1:] / prices[:-1] - 1
    return MarketData(tuple(f"OR{i+1:02}" for i in range(n)), tuple("Unclassified" for _ in range(n)),
                      returns[:, 1:], returns[:, 0],
                      {"kind": "or_library", "dataset": "indtrack1", "full_universe_n": n,
                       "periods": t, "periods_per_year": None, "sector_source": "unavailable",
                       "limitation": "Undated research price series; corporate-action treatment and frequency not independently verified. No annualized claims."})


def import_market_csv(path, manifest_path):
    """Explicit user-supplied wide adjusted-return CSV; never silently use legacy raw prices."""
    import pandas as pd
    manifest = json.loads(Path(manifest_path).read_text())
    required = ("source", "price_adjustment_verified", "point_in_time_universe_verified", "benchmark_verified", "sectors")
    if any(key not in manifest for key in required) or any(manifest[key] is not True for key in required[1:4]):
        raise ValueError("Market manifest has not verified price adjustments, point-in-time universe and benchmark.")
    frame = pd.read_csv(path)
    if "date" not in frame or "benchmark" not in frame:
        raise ValueError("CSV requires date, benchmark and one return column per asset.")
    dates = pd.to_datetime(frame.pop("date"), errors="raise")
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("Dates must increase without duplicates.")
    benchmark = frame.pop("benchmark").to_numpy(float)
    tickers = tuple(frame.columns)
    if set(tickers) != set(manifest["sectors"]):
        raise ValueError("Missing sector classification.")
    returns = frame.to_numpy(float)
    if not np.isfinite(returns).all() or not np.isfinite(benchmark).all() or (returns <= -1).any() or (benchmark <= -1).any():
        raise ValueError("Invalid return data.")
    return MarketData(tickers, tuple(manifest["sectors"][x] for x in tickers), returns, benchmark,
                      {**manifest, "kind": "user_verified_market", "dates": dates.astype(str).tolist(),
                       "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()})


def make_window(data, start=0, train=80, horizon=20, n=8, k=4, text=None, cost_weight=0.01, cost_bps=25):
    if start < 0 or train < 20 or horizon < 2 or start + train + horizon > len(data.returns) or not 1 <= k <= n <= len(data.tickers):
        raise ValueError("Invalid window or universe.")
    # Fixed first-N window, explicitly reported; never select assets using held-out returns.
    tickers, sectors = data.tickers[:n], data.sectors[:n]
    text = text or f"Hold {k} assets"
    mandate = normalize_rules(text, tickers, tuple(sorted(set(sectors))))
    previous = np.zeros(n); previous[:k] = 1 / k
    drift = np.prod(1 + data.returns[start + train - 10:start + train, :n], axis=0)
    previous *= drift; previous /= previous.sum()
    cutoff_index = start + train - 1
    cutoff = data.provenance.get("dates", [])[cutoff_index] if data.provenance.get("dates") else f"period:{cutoff_index}"
    p = ProblemInstance(f"{data.provenance['kind']}-{start}-{n}", tickers, sectors,
                        data.returns[start:start + train, :n], data.benchmark[start:start + train], previous,
                        mandate, np.full(n, cost_bps / 10000), cost_weight,
                        provenance=json.dumps({**data.provenance, "evaluated_universe_n": n,
                                               "screening": "fixed_first_n_not_full_index"}, ensure_ascii=False), cutoff=cutoff)
    return p, data.returns[start + train:start + train + horizon, :n], data.benchmark[start + train:start + train + horizon]
