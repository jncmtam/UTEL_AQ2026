"""Instance pool of the follow-up studies (protocol §1): splits, account sizes, constraint types.

An instance spec is a small dict {split, date, capital_vnd, constraint}. Containers rebuild the instance from
the spec with the main-study configuration (results/final/config.json), so every worker solves exactly the same QUBO.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtest import Account, build_rounding_instance
from ..config import RESULTS_DIR
from ..mandate import Mandate

SIZES = (20e6, 50e6, 100e6, 200e6, 500e6)
CONSTRAINTS = {"none": Mandate(), "bank25": Mandate(sector_caps={"Banking": 0.25}),
               "no_real_estate": Mandate(exclude_sectors=["Real estate"])}
SPLITS = {"calibration": ("2023-01-01", "2023-08-31"), "validation": ("2023-09-01", "2023-12-31"),
          "holdout": ("2024-01-01", "2026-10-31")}
QUARTER_MONTHS = (1, 4, 7, 10)


def split_dates(md, split: str) -> list[pd.Timestamp]:
    lo, hi = SPLITS[split]
    dates = md.rebalance_dates(lo, hi, "MS")
    if split == "holdout":                       # the main study reported the quarter starts; the new holdout is the rest
        dates = [d for d in dates if d.month not in QUARTER_MONTHS]
    return dates


def v3_test_dates(md) -> list[pd.Timestamp]:
    return md.rebalance_dates("2024-01-01", "2026-10-31", "QS")


def specs(md, splits=("calibration", "validation", "holdout"), sizes=SIZES, constraints=tuple(CONSTRAINTS)) -> list[dict]:
    out = []
    for s in splits:
        for d in (v3_test_dates(md) if s == "v3_test" else split_dates(md, s)):
            for c in sizes:
                for k in constraints:
                    out.append({"split": s, "date": str(d.date()), "capital_vnd": float(c), "constraint": k})
    return out


def build(md, ec, spec: dict, universe_cache: dict | None = None):
    """(Instance, Landscape) for one spec on a fresh cash account."""
    from ..portfolio import landscape

    d = pd.Timestamp(spec["date"])
    cache = universe_cache if universe_cache is not None else {}
    if d not in cache:
        cache[d] = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)[0]
    inst = build_rounding_instance(md, d, cache[d], Account(cash=spec["capital_vnd"]), ec, CONSTRAINTS[spec["constraint"]])
    return inst, landscape(inst)


def load_v3_config():
    from ..extras import load_config

    return load_config(RESULTS_DIR)


def extended_features(cp, spec: dict) -> dict:
    """Design inputs for the k-NN variants (no enumeration): main-study features + account/size/constraint context."""
    from ..insight import coupling_decomposition
    from ..quantum.design import design_features

    f = design_features(cp)
    inst = cp.inst
    iu = np.triu_indices(cp.n, 1)
    risk, budget = coupling_decomposition(inst)
    r2, b2 = float((risk[iu] ** 2).sum()), float((budget[iu] ** 2).sum())
    coeffs = np.concatenate([cp.hz, cp.pair_w])
    return f | {"log_capital": float(np.log10(spec["capital_vnd"])), "n_qubits": float(cp.n),
                "has_cap": float(spec["constraint"] == "bank25"), "has_exclusion": float(spec["constraint"] == "no_real_estate"),
                "risk_coupling_share": r2 / max(r2 + b2, 1e-30), "log_rms_scale": float(np.log10(np.sqrt(np.mean(coeffs ** 2)))),
                "relaxed_mean": float(cp.relaxed.mean())}
