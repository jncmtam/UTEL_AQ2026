"""Paired case-level summaries; optimizer seeds do not inflate sample counts."""

import numpy as np


def paired_summary(case_pairs, seed=11, replicates=5000):
    """Input: one paired aggregate per independent case, candidate minus control."""
    values = np.asarray(case_pairs, float)
    if values.ndim != 2 or values.shape[1] != 2 or not np.isfinite(values).all():
        raise ValueError("Expected finite paired case-level values.")
    differences = values[:, 0] - values[:, 1]
    n = len(values)
    if n < 2:
        return {
            "cases": n,
            "status": "insufficient_cases",
            "mean_difference": float(differences.mean()) if n else None,
        }
    rng = np.random.default_rng(seed)
    boots = differences[rng.integers(0, n, (replicates, n))].mean(axis=1)
    return {
        "cases": n,
        "mean_difference": float(differences.mean()),
        "paired_bootstrap_95pct": np.quantile(boots, [0.025, 0.975]).tolist(),
        "status": "descriptive_small_sample" if n < 10 else "estimated",
        "resampling_unit": "independent_case_aggregate_not_optimizer_seed",
        "claim": "Unadjusted descriptive interval; does not establish superiority across multiple comparisons.",
    }


def holm_adjust(pvalues):
    values = np.asarray(pvalues, float)
    if (
        values.ndim != 1
        or not np.isfinite(values).all()
        or ((values < 0) | (values > 1)).any()
    ):
        raise ValueError("Expected probabilities in [0,1].")
    order = np.argsort(values)
    adjusted = np.maximum.accumulate(
        (len(values) - np.arange(len(values))) * values[order]
    )
    result = np.empty(len(values))
    result[order] = np.minimum(adjusted, 1)
    return result.tolist()
