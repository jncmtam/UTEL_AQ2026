"""Exact best-of-budget metrics for a supplied discrete operational distribution.

The score table is an input, not an efficient financial oracle. Conditional
incumbent clipping describes future independent draws after a fixed history.
"""

import numpy as np


def expected_minimum(scores, probabilities, shots, incumbent=None):
    if type(shots) is not int or shots <= 0:
        raise ValueError("Shots must be a positive integer.")
    values = np.asarray(scores, dtype=float)
    weights = np.asarray(probabilities, dtype=float)
    if (values.ndim != 1 or not len(values) or values.shape != weights.shape
        or not np.isfinite(values).all() or not np.isfinite(weights).all()
        or (weights < 0).any() or abs(weights.sum()-1) > 1e-10):
        raise ValueError("Finite scores and a normalized nonnegative distribution are required.")
    if incumbent is not None:
        if not np.isfinite(incumbent):
            raise ValueError("Incumbent must be finite.")
        values = np.minimum(values, float(incumbent))
    order = np.argsort(values, kind="stable")
    values, weights = values[order], weights[order]/weights.sum()
    survival = np.cumsum(weights[::-1])[::-1]
    # Accumulation can exceed one by machine epsilon; the input tolerance is
    # checked above. This does not clip financial scores or omit failure mass.
    survival = np.minimum(survival, 1.0)
    return float(values[0] + np.dot(np.diff(values), survival[1:]**shots))


def hit_probability(probability, shots):
    if type(shots) is not int or shots <= 0 or not np.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("A probability and positive integer shot budget are required.")
    if probability == 1:
        return 1.0
    return float(-np.expm1(shots*np.log1p(-probability)))


def decision_metrics(scores, probabilities, feasible, shots, incumbent=None):
    values, p, flags = np.asarray(scores, float), np.asarray(probabilities, float), np.asarray(feasible)
    expected = expected_minimum(values, p, shots)
    if flags.dtype.kind != "b" or flags.shape != values.shape:
        raise ValueError("Boolean feasibility must align with every score.")
    mass = float(p[flags].sum()/p.sum())
    found_probability = hit_probability(mass, shots)
    no_feasible = 1-found_probability
    conditional = None
    if mass > 0:
        # The conditional feasible minimum is computed directly, avoiding
        # cancellation when almost all trials fail. The failure ceiling is not
        # assumed equal across unlabelled user scores.
        ordered = np.argsort(values[flags], kind="stable")
        f, q = values[flags][ordered], p[flags][ordered]/p.sum()
        before = np.r_[0., np.cumsum(q)[:-1]]
        differences = []
        for prior, atom in zip(before, q, strict=True):
            remaining = max(0., 1-prior)
            differences.append(remaining**shots * hit_probability(min(1., atom/remaining), shots) if remaining else 0.)
        conditional = float(np.dot(f, differences)/found_probability)
    return {"shots": shots, "mean_score": float(np.dot(values, p)/p.sum()),
        "expected_minimum": expected, "feasible_probability": mass,
        "no_feasible_probability": no_feasible,
        "conditional_feasible_minimum": conditional,
        "expected_with_incumbent": expected_minimum(values, p, shots, incumbent) if incumbent is not None else None,
        "scope": "Fixed distribution; incumbent metric conditions on a realized history, not an adaptive-policy expectation"}
