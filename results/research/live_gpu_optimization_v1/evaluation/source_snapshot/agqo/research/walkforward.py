"""Continuous accounts with close-to-close returns and one-session execution lag."""

from dataclasses import replace
import numpy as np
from .finance import Account, FinancialSpec, diagnose


def walk_forward(
    returns,
    benchmark,
    dates,
    tickers,
    sectors,
    selector,
    *,
    k,
    lookback=252,
    interval=21,
    initial_nav=100000.0,
    mandates=None,
    provenance="synthetic_diagnostic",
    initial_weights=None,
):
    """Selector returns an allocation record using information through signal day.

    Pending orders execute after the NEXT session's return, at that close. They
    receive no same-session return. A failed decision keeps actual holdings and
    is explicitly recorded; it is never credited as solver success.
    """
    r = np.asarray(returns, float)
    b = np.asarray(benchmark, float)
    if (
        r.ndim != 2
        or r.shape != (len(dates), len(tickers))
        or b.shape != (len(r),)
        or not np.isfinite(r).all()
        or not np.isfinite(b).all()
        or (r < -1).any()
    ):
        raise ValueError("Invalid aligned return series.")
    if (
        lookback < 3
        or interval < 1
        or len(r) <= lookback + 1
        or not 1 <= k <= len(tickers)
    ):
        raise ValueError("Invalid walk-forward configuration.")
    if list(dates) != sorted(dates) or len(set(dates)) != len(dates):
        raise ValueError("Dates must be unique and sorted.")
    initial = (
        np.zeros(len(tickers))
        if initial_weights is None
        else np.asarray(initial_weights, float)
    )
    if (
        initial.shape != (len(tickers),)
        or not np.isfinite(initial).all()
        or (initial < 0).any()
        or initial.sum() > 1 + 1e-10
    ):
        raise ValueError("Invalid initial account weights.")
    account = Account(initial_nav * initial, initial_nav * (1 - initial.sum()))
    pending = None
    decisions = []
    daily = []
    active_mandate = {}
    for day in range(lookback, len(r)):
        before = account.nav
        account.advance_total_return(r[day])
        if account.nav <= 0:
            if pending is not None:
                pending[2]["execution_status"] = "cancelled_bankruptcy"
            daily.append(
                {
                    "date": str(dates[day]),
                    "nav": 0.0,
                    "net_return": -1.0,
                    "benchmark_return": float(b[day]),
                    "weights": [0.0] * len(tickers),
                    "cash": 0.0,
                    "status": "bankrupt",
                }
            )
            break
        if pending is not None:
            spec, allocation, record = pending
            execution_spec = replace(spec, previous_weights=account.weights())
            violations = execution_spec.violations_weights(allocation["weights"])
            if violations:
                record.update(
                    execution_status="rejected_at_execution",
                    execution_violations=violations,
                )
            else:
                record["order"] = account.rebalance(
                    allocation["weights"], spec.cost_rate
                )
                record["execution_status"] = "executed"
            record["execution_date"] = str(dates[day])
            pending = None
        daily.append(
            {
                "date": str(dates[day]),
                "nav": account.nav,
                "net_return": account.nav / before - 1,
                "benchmark_return": float(b[day]),
                "weights": account.weights().tolist(),
                "cash": account.cash,
            }
        )
        if (day - lookback) % interval == 0 and day + 1 < len(r):
            active_mandate.update((mandates or {}).get(str(dates[day]), {}))
            changes = dict(active_mandate)
            spec = FinancialSpec(
                tuple(tickers),
                tuple(sectors),
                r[day - lookback + 1 : day + 1],
                b[day - lookback + 1 : day + 1],
                account.weights(),
                k,
                str(dates[day]),
                provenance=provenance,
                **changes,
            )
            record = {
                "signal_date": str(dates[day]),
                "cutoff": spec.cutoff,
                "previous_weights": account.weights().tolist(),
                "problem_hash": spec.fingerprint(),
                "diagnosis": diagnose(spec),
                "execution_status": "no_order",
            }
            if record["diagnosis"]["status"] == "infeasible":
                record["allocation"] = {"feasible": False, "status": "infeasible"}
            else:
                allocation = selector(spec)
                record["allocation"] = allocation
                if allocation.get("feasible"):
                    if spec.violations_weights(allocation["weights"]):
                        raise ValueError(
                            "Selector claimed an invalid allocation as feasible."
                        )
                    if allocation.get("action") == "hold":
                        record["execution_status"] = "held"
                        decisions.append(record)
                        continue
                    pending = (spec, allocation, record)
                    record["execution_status"] = "pending"
            decisions.append(record)
    return {
        "version": "continuous-account-v3",
        "provenance": provenance,
        "execution_lag_sessions": 1,
        "decisions": decisions,
        "daily": daily,
        "final_nav": account.nav,
        "initial_nav": initial_nav,
        "account_reset_count": 0,
        "fallback_used": False,
    }
