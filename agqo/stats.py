"""Statistics used in the report: paired tests across quarters and block-bootstrap intervals.

* Quantum metrics are paired by quarter (same Hamiltonian, different circuit), so circuits are
  compared with the Wilcoxon signed-rank test (no normality assumption, 12 pairs) and a
  bootstrap interval for the ratio of means.
* Tracking-error differences use a moving-block bootstrap of daily active returns
  (Kuensch 1989): blocks of ~one month keep volatility clustering and autocorrelation,
  and both strategies are resampled on the same days so the comparison stays paired.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


def paired_test(a: np.ndarray, b: np.ndarray, n_boot: int = 5000, seed: int = 0) -> dict:
    """a vs b per quarter: Wilcoxon p-value (two-sided), wins, ratio of means with a 95 % bootstrap CI."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), (n_boot, len(a)))
    ratios = a[idx].mean(1) / np.maximum(b[idx].mean(1), 1e-12)
    try:
        p = float(wilcoxon(a, b).pvalue) if np.any(a != b) else 1.0
    except ValueError:
        p = float("nan")
    return {"n": int(len(a)), "wins": int((a > b).sum()), "mean_a": float(a.mean()), "mean_b": float(b.mean()),
            "ratio": float(a.mean() / max(b.mean(), 1e-12)), "ratio_ci_low": float(np.quantile(ratios, 0.025)),
            "ratio_ci_high": float(np.quantile(ratios, 0.975)), "wilcoxon_p": p}


def te(x: np.ndarray) -> float:
    return float(np.std(x, ddof=1) * np.sqrt(252) * 100)


def block_bootstrap_te_diff(act_a: pd.Series, act_b: pd.Series, block: int = 21, n_boot: int = 2000,
                            seed: int = 0) -> dict:
    """TE(a) - TE(b) in percentage points with a 95 % moving-block-bootstrap interval."""
    j = act_a.index.intersection(act_b.index)
    a, b = act_a.loc[j].to_numpy(), act_b.loc[j].to_numpy()
    n = len(a)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block + 1, (n_boot, int(np.ceil(n / block))))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_boot, -1)[:, :n]
    diffs = np.array([te(a[i]) - te(b[i]) for i in idx])
    d = te(a) - te(b)
    return {"te_a": te(a), "te_b": te(b), "diff_pp": d, "ci_low": float(np.quantile(diffs, 0.025)),
            "ci_high": float(np.quantile(diffs, 0.975)), "p_one_sided": float((diffs >= 0).mean()), "days": n}
