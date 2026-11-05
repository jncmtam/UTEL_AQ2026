"""Blinded market-source hygiene audit, independent of strategy/model outcomes.

Passing numerical checks never substitutes for security/entitlement source review.
Yahoo close is historically split-adjusted: never apply split ratios a second time.
"""

from pathlib import Path
from importlib.metadata import version
import json
import numpy as np
import pandas as pd
from .data import write_json, sha, audit


def inspect_chart(payload, ticker, sessions, development_end="2018-12-31"):
    """Inspect a provider object; malformed structures return explicit failures."""
    try:
        return _inspect_chart(payload, ticker, sessions, development_end)
    except (
        AttributeError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        OverflowError,
    ) as exc:
        return {
            "ticker": ticker,
            "status": "invalid",
            "issues": [f"Malformed provider payload: {type(exc).__name__}: {exc}"],
        }


def _inspect_chart(payload, ticker, sessions, development_end):
    issues = []
    result = payload.get("chart", {}).get("result")
    if (
        payload.get("chart", {}).get("error")
        or not isinstance(result, list)
        or len(result) != 1
    ):
        return {
            "ticker": ticker,
            "status": "invalid",
            "issues": ["Invalid source response."],
        }
    source = result[0]
    meta = source.get("meta", {})
    if meta.get("symbol") != ticker:
        issues.append(
            "Source symbol differs from requested ticker; identity review required."
        )
    timestamps = source.get("timestamp", [])
    if not timestamps:
        return {
            "ticker": ticker,
            "status": "invalid",
            "issues": ["No timestamped observations."],
        }
    try:
        dates = (
            pd.to_datetime(timestamps, unit="s", utc=True)
            .tz_convert("America/New_York")
            .normalize()
            .tz_localize(None)
        )
    except Exception as exc:
        return {
            "ticker": ticker,
            "status": "invalid",
            "issues": [f"Invalid source dates: {exc}"],
        }
    q = source.get("indicators", {}).get("quote", [{}])[0]
    adjusted = source.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
    fields = {key: q.get(key, []) for key in ("open", "high", "low", "close", "volume")}
    fields["adjusted"] = adjusted
    if any(len(v) != len(dates) for v in fields.values()):
        return {
            "ticker": ticker,
            "status": "invalid",
            "issues": ["Timestamp/price/volume lengths disagree."],
        }
    frame = pd.DataFrame(fields, index=dates, dtype=float)
    duplicates = int(dates.duplicated().sum())
    if duplicates:
        issues.append(f"{duplicates} duplicate NY-session dates.")
    if not dates.is_monotonic_increasing:
        issues.append("Source observations are not sorted.")
    expected = pd.DatetimeIndex(sessions)
    expected = expected[(expected >= dates.min()) & (expected <= dates.max())]
    missing = expected.difference(dates)
    extra = dates.difference(expected)
    if len(missing):
        issues.append(
            f"{len(missing)} missing expected exchange sessions within observed span."
        )
    if len(extra):
        issues.append(
            f"{len(extra)} observations outside the exchange reference calendar."
        )
    prices = frame[["open", "high", "low", "close", "adjusted"]].to_numpy()
    bad_rows = np.any(~np.isfinite(prices) | (prices <= 0), axis=1)
    if bad_rows.any():
        issues.append(f"{int(bad_rows.sum())} nonfinite/nonpositive price rows.")
    valid = np.isfinite(frame[["open", "high", "low", "close"]]).all(axis=1)
    envelope = valid & (
        (frame.high + 1e-6 < frame[["open", "close", "low"]].max(axis=1))
        | (frame.low - 1e-6 > frame[["open", "close", "high"]].min(axis=1))
    )
    if envelope.any():
        issues.append(f"{int(envelope.sum())} OHLC envelope violations.")
    volume = frame.volume.to_numpy()
    bad_vol = ~np.isfinite(volume) | (volume < 0)
    if bad_vol.any():
        issues.append(f"{int(bad_vol.sum())} invalid volume rows.")
    events = source.get("events", {})
    event_dates = set()
    dividends = {}
    split_count = 0
    noninteger_splits = []
    bad_events = []
    for kind in ("dividends", "splits", "capitalGains"):
        for event in events.get(kind, {}).values():
            try:
                date = (
                    pd.Timestamp(event["date"], unit="s", tz="UTC")
                    .tz_convert("America/New_York")
                    .normalize()
                    .tz_localize(None)
                )
                event_dates.add(date)
                if kind == "splits":
                    ratio = float(event["numerator"]) / float(event["denominator"])
                    if not np.isfinite(ratio) or ratio <= 0:
                        raise ValueError("Invalid split ratio.")
                    split_count += 1
                    if not (
                        np.isclose(ratio, round(ratio), atol=1e-6)
                        or np.isclose(1 / ratio, round(1 / ratio), atol=1e-6)
                    ):
                        noninteger_splits.append(
                            {
                                "session": str(date.date()),
                                "provider_ratio": ratio,
                                "interpretation": "Unclassified provider split label; may encode a noncash price adjustment. Not an entitlement ratio.",
                            }
                        )
                else:
                    amount = float(event["amount"])
                    if not np.isfinite(amount) or amount < 0:
                        raise ValueError("Invalid cash distribution.")
                    if kind == "dividends":
                        dividends[date] = dividends.get(date, 0) + amount
            except (ValueError, KeyError, TypeError, ZeroDivisionError):
                bad_events.append(kind)
    if bad_events:
        issues.append(f"{len(bad_events)} malformed action records.")
    if noninteger_splits:
        issues.append(
            f"{len(noninteger_splits)} non-integer provider split labels require independent entitlement classification."
        )
    # Internal adjustment-factor changes, not certified entitlement reconciliation.
    factor = frame.adjusted / frame.close
    change = np.log(factor).diff()
    changed = change.abs() > 5e-6
    explained = np.array([d in event_dates for d in dates])
    unknown = int(np.sum(changed.to_numpy() & ~explained))
    if unknown:
        issues.append(
            f"{unknown} adjustment-factor changes without same-session provider action metadata; review required."
        )
    cash_checks = []
    if not duplicates and dates.is_monotonic_increasing:
        for date, amount in dividends.items():
            if date not in dates:
                continue
            i = dates.get_loc(date)
            if i == 0:
                continue
            previous = float(frame.close.iloc[i - 1])
            if not np.isfinite(previous) or previous <= amount:
                continue
            observed = change.iloc[i]
            predicted = -np.log1p(-amount / previous)
            if np.isfinite(observed):
                cash_checks.append(abs(float(observed) - predicted))
    residuals_above = int(sum(v > 5e-5 for v in cash_checks))
    # Return-shape fitting is strictly development-only. Future hygiene is counts.
    development = (
        frame.loc[:development_end, "adjusted"].pct_change(fill_method=None).dropna()
    )
    periods = {}
    for name, start, end in [
        ("development", "2014-01-01", "2018-12-31"),
        ("validation", "2019-01-01", "2021-12-31"),
        ("test", "2022-01-01", "2025-12-31"),
    ]:
        exp = pd.DatetimeIndex(sessions)
        exp = exp[(exp >= start) & (exp <= end)]
        obs = frame.loc[start:end]
        available = obs.index[obs[["close", "adjusted"]].notna().all(axis=1)]
        periods[name] = {
            "expected_sessions": len(exp),
            "usable_close_and_adjusted_sessions": len(available.unique()),
            "missing_sessions": len(exp.difference(available)),
            "exposure": "development_diagnostics"
            if name == "development"
            else "hygiene_only_no_strategy_or_profile_fitting",
        }
    return {
        "ticker": ticker,
        "status": "hygiene_clear_not_financially_certified"
        if not issues
        else "review_required",
        "issues": issues,
        "observations": len(frame),
        "first_session": str(dates.min().date()),
        "last_session": str(dates.max().date()),
        "duplicate_dates": duplicates,
        "missing_internal_sessions": len(missing),
        "unexpected_sessions": len(extra),
        "invalid_price_rows": int(bad_rows.sum()),
        "ohlc_violations": int(envelope.sum()),
        "invalid_volume_rows": int(bad_vol.sum()),
        "provider_dividends": len(dividends),
        "provider_splits": split_count,
        "unclassified_noninteger_split_labels": noninteger_splits,
        "malformed_actions": len(bad_events),
        "unexplained_adjustment_changes": unknown,
        "cash_adjustment_checks": len(cash_checks),
        "cash_adjustment_residual_above_5e_minus_5": residuals_above,
        "adjustment_check_scope": "Internal backward cash-adjustment convention only; not independent total-return verification.",
        "development_return_observations": len(development),
        "development_abs_daily_return_above_25pct": int(
            (development.abs() > 0.25).sum()
        ),
        "period_coverage": periods,
        "identity_verified": False,
        "entitlements_verified": False,
        "numerical_cleanliness_is_not_financial_admission": True,
    }


def run(directory, data_directory="data/us_equities"):
    import exchange_calendars as calendars

    path = Path(directory)
    data = Path(data_directory)
    if (path / "audit.json").exists():
        raise ValueError("Preserve the original audit; use a new directory.")
    manifest = json.loads((data / "dataset_manifest.json").read_text())
    sessions = calendars.get_calendar(
        "XNYS", start="2012-01-01", end="2025-12-31"
    ).sessions
    protocol = {
        "version": "historical-hygiene-audit-v3",
        "evidence": "docs/research/QUALIFICATION_PROTOCOL.md",
        "calendar": "XNYS",
        "calendar_package": "exchange_calendars",
        "calendar_version": version("exchange_calendars"),
        "calendar_status": "Independent software reference; not a primary exchange attestation.",
        "development_end": "2018-12-31",
        "test_exposure": "Integrity/date/entitlement hygiene only; no strategy outcome or profile fitting.",
        "adjustment_factor_change_threshold": 5e-6,
        "cash_residual_threshold": 5e-5,
        "cohort_preserved": True,
        "raw_manifest_sha256": sha(data / "dataset_manifest.json"),
        "model_inference_calls": 0,
    }
    write_json(path / "protocol.json", protocol)
    from .sources import capture_sources

    capture_sources(path)
    entries = {e["path"]: e for e in manifest.get("files", [])}
    rows = []
    for ticker in [s["ticker_at_inception"] for s in manifest["securities"]] + [
        manifest["benchmark"]
    ]:
        relative = f"raw/{ticker}.json"
        file = data / relative
        entry = entries.get(relative)
        if not file.exists():
            rows.append(
                {
                    "ticker": ticker,
                    "status": "missing",
                    "issues": [
                        "No source history; do not substitute a current ticker."
                    ],
                }
            )
            continue
        if not entry or sha(file) != entry.get("sha256"):
            rows.append(
                {
                    "ticker": ticker,
                    "status": "tampered_or_unmanifested",
                    "issues": ["Source checksum or provenance mismatch."],
                }
            )
            continue
        try:
            row = inspect_chart(json.loads(file.read_text()), ticker, sessions)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            row = {"ticker": ticker, "status": "invalid", "issues": [str(exc)]}
        row.update(source=entry["source"], source_sha256=entry["sha256"])
        rows.append(row)
    gate = audit(manifest, data)
    report = {
        "version": "historical-audit-report-v1",
        "status": "blocked",
        "financial_evaluation_allowed": False,
        "rows": rows,
        "market_contract_audit": gate,
        "verified_full_security_lineages": 0,
        "benchmark_not_official_index": manifest.get("benchmark_kind"),
        "scope": "Comprehensive available-source numerical audit; historical issuer/class/action/sector verification incomplete.",
        "model_selection_status": "No winner qualified; financial utility gate blocked.",
        "new_inference_calls": 0,
    }
    write_json(path / "audit.json", report)
    text = [
        "# Historical data audit",
        "",
        report["scope"],
        "",
        "**Financial evaluation remains blocked. No asset was removed or relabeled.**",
        "",
        "| Asset | Source status | Rows | Missing internal sessions | Unexplained adjustment changes | Provider dividends/splits |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        text.append(
            f"| {r['ticker']} | {r['status']} | {r.get('observations', '—')} | {r.get('missing_internal_sessions', '—')} | {r.get('unexplained_adjustment_changes', '—')} | {r.get('provider_dividends', '—')}/{r.get('provider_splits', '—')} |"
        )
    text += [
        "",
        "## Interpretation",
        "",
        "Price/event algebra uses the provider’s own records and cannot independently certify dividends, merger lineage or spin-off entitlements. A numerically clean file is not a verified investable security history. Split factors are not applied again to split-adjusted closes.",
        "",
        "The original continuous-allocation task also retains measured B/F distortion. No final financial test or production LLM selection is justified from this audit alone.",
        "",
        "## Repair queue",
        "",
        "1. Reconstruct dated share-class identity and all successor/distributed-security entitlements, beginning with missing UTX and complex DD/GE histories.",
        "2. Reconcile all flagged adjustments with independent primary issuer records and verify dividends/splits beyond the vendor’s own metadata.",
        "3. Add dated sector evidence and a declared classification policy; reconcile the complete inception membership and publication time.",
        "4. Produce source-backed aligned total-return data, re-run admission, resolve financial proxy fidelity, then freeze model and final-test evaluation.",
    ]
    (path / "AUDIT.md").write_text("\n".join(text) + "\n")
    return report
