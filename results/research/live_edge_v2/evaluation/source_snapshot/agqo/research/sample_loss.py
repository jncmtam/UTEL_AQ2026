"""Empirical lower-tail score and separate all-observation feasibility gate.

This aggregates candidate-portfolio scores, not future investment return risk.
"""

from collections import Counter
from numbers import Real
import numpy as np


def _fraction(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real fraction in (0,1].")
    if not np.isfinite(value) or not 0 < value <= 1:
        raise ValueError(f"{name} must be a real fraction in (0,1].")
    return float(value)


def lower_tail_mean(losses, alpha):
    """Average the lowest alpha empirical mass, including a fractional boundary."""
    alpha = _fraction(alpha, "alpha")
    values = np.asarray(losses, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("Expected a nonempty finite one-dimensional loss vector.")
    ordered = np.sort(values)
    mass = alpha * len(values)
    whole = int(np.floor(mass))
    remainder = mass - whole
    total = float(ordered[:whole].sum())
    if remainder:
        total += remainder * float(ordered[whole])
    return total / mass


def batch_loss(
    losses, feasible, statuses, *, kind="mean", alpha=0.25, min_feasible_fraction=0.95
):
    """Invalid/unknown outcomes count; a good tail cannot bypass feasibility."""
    if kind not in ("mean", "lower_tail"):
        raise ValueError("Unknown allocated fitting aggregation.")
    alpha = _fraction(alpha, "alpha")
    threshold = _fraction(min_feasible_fraction, "min_feasible_fraction")
    values = np.asarray(losses, dtype=float)
    flags = np.asarray(feasible)
    states = np.asarray(statuses)
    if (
        values.ndim != 1
        or not len(values)
        or flags.shape != values.shape
        or flags.dtype.kind != "b"
        or states.shape != values.shape
        or not all(isinstance(s, str) for s in statuses)
        or not np.isfinite(values).all()
    ):
        raise ValueError("Losses, boolean feasibility and string statuses must align.")
    if (
        np.any(values < -1e-7)
        or np.any(values > 2)
        or np.any(values[flags] > 1 + 1e-7)
        or np.any(values[~flags] != 2)
    ):
        raise ValueError(
            "Expected bounded tracking losses; invalid outcomes must have loss2."
        )
    if any(
        flag and state in ("unknown", "infeasible")
        for flag, state in zip(flags, states)
    ):
        raise ValueError("Unknown/infeasible outcomes cannot be feasible.")
    fraction = float(flags.mean())
    eligible = fraction >= threshold
    mean = float(values.mean())
    tail = lower_tail_mean(values, alpha)
    objective = (
        (mean if kind == "mean" else tail) if eligible else 2 + threshold - fraction
    )
    return {
        "mean_loss": mean,
        "lower_tail_loss": tail,
        "objective_loss": objective,
        "feasible_fraction": fraction,
        "eligible": eligible,
        "status_counts": dict(Counter(map(str, states))),
        "observations": len(values),
        "tail_mass": alpha * len(values),
    }
