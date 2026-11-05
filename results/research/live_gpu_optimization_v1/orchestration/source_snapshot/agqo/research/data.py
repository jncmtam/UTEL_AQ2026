"""Free US data acquisition and fail-closed, point-in-time dataset auditing."""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import requests

COHORT = (
    "AXP",
    "BA",
    "CAT",
    "CSCO",
    "CVX",
    "DD",
    "DIS",
    "GE",
    "GS",
    "HD",
    "IBM",
    "INTC",
    "JNJ",
    "JPM",
    "KO",
    "MCD",
    "MMM",
    "MRK",
    "MSFT",
    "NKE",
    "PFE",
    "PG",
    "T",
    "TRV",
    "UNH",
    "UTX",
    "V",
    "VZ",
    "WMT",
    "XOM",
)
ANNOUNCEMENT = "https://press.spglobal.com/2013-09-10-Goldman-Sachs-Visa-Nike-Set-to-Join-the-Dow-Jones-Industrial-Average"
USER_AGENT = "AGQOResearch/0.2 (+https://github.com/jncmtam/UTEL_AQ2026)"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def candidate(directory):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    if (path / "dataset_manifest.json").exists():
        return json.loads((path / "dataset_manifest.json").read_text())
    manifest = {
        "version": "us-market-manifest-v3",
        "dataset_kind": "market_candidate",
        "universe_policy": "fixed_inception_cohort_not_dynamic_DJIA",
        "effective_date": "2013-09-23",
        "benchmark": "DIA",
        "benchmark_kind": "ETF_total_return_proxy_not_official_index",
        "start": "2012-01-01",
        "end_exclusive": "2026-01-01",
        "membership_verified": False,
        "membership_sources": [ANNOUNCEMENT],
        "membership_note": "Announcement verifies the three replacements, not the complete security master. Full cohort remains an audit candidate.",
        "price_mode": "adjusted_total_return",
        "corporate_actions_verified": False,
        "sector_history_verified": False,
        "redistribution": "Raw provider data is local-only; publish manifests and acquisition code, not assumed redistribution rights.",
        "securities": [
            {
                "asset_id": f"DJIA20130923:{t}",
                "ticker_at_inception": t,
                "permanent_identifier": None,
                "identity_verified": False,
                "ticker_history": [],
                "corporate_actions": [],
                "sources": [],
            }
            for t in COHORT
        ],
        "files": [],
        "acquisition": [],
        "status": "blocked_pending_audit",
    }
    write_json(path / "dataset_manifest.json", manifest)
    return manifest


def fetch_prices(directory):
    path = Path(directory)
    mp = path / "dataset_manifest.json"
    manifest = json.loads(mp.read_text()) if mp.exists() else candidate(path)
    start = int(datetime(2012, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    for ticker in (*COHORT, "DIA"):
        target = path / "raw" / f"{ticker}.json"
        if target.exists():
            continue
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        record = {
            "ticker": ticker,
            "source": url,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = requests.get(
                url,
                params={
                    "period1": start,
                    "period2": end,
                    "interval": "1d",
                    "events": "div,splits",
                    "includeAdjustedClose": "true",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("chart", {}).get("error") or not payload["chart"].get(
                "result"
            ):
                raise ValueError("Provider returned no valid history.")
            write_json(target, payload)
            record.update(
                status="downloaded_not_audited",
                sha256=sha(target),
                path=str(target.relative_to(path)),
            )
            manifest["files"].append(
                {k: record[k] for k in ("path", "sha256", "source")}
            )
        except (requests.RequestException, ValueError, KeyError) as exc:
            record.update(status="failed", reason=str(exc)[:500])
        manifest["acquisition"].append(record)
        write_json(mp, manifest)
        print(f"{ticker}: {record['status']}", flush=True)
    write_json(path / "data_audit.json", audit(manifest, path))
    return manifest


def fetch_filings(cik, directory):
    if not str(cik).isdigit():
        raise ValueError("CIK must be numeric.")
    url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    target = Path(directory) / f"CIK{int(cik):010d}.json"
    write_json(target, response.json())
    return {
        "path": str(target),
        "sha256": sha(target),
        "source": url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "use_policy": "Filter acceptance timestamps before decision cutoff; current company metadata is not historical identity evidence.",
    }


def audit(manifest, directory, cutoff=None):
    path = Path(directory)
    issues = []
    if manifest.get("version") != "us-market-manifest-v3":
        issues.append("Unsupported manifest version.")
    for field in (
        "membership_verified",
        "corporate_actions_verified",
        "sector_history_verified",
    ):
        if manifest.get(field) is not True:
            issues.append(f"{field} has not been verified.")
    review = manifest.get("review", {})
    if not all(
        review.get(k)
        for k in (
            "reviewer",
            "reviewed_at",
            "identity_policy",
            "corporate_action_policy",
            "sector_policy",
        )
    ):
        issues.append("Missing explicit source-backed dataset review record.")
    if manifest.get("price_mode") != "adjusted_total_return":
        issues.append(
            "Aligned market execution currently supports audited adjusted total returns only."
        )
    securities = manifest.get("securities", [])
    if not securities:
        issues.append("Missing security master.")
    if len({s.get("asset_id") for s in securities}) != len(securities):
        issues.append("Duplicate asset identity.")
    for security in securities:
        if (
            not security.get("identity_verified")
            or not security.get("permanent_identifier")
            or not security.get("ticker_history")
            or not security.get("sources")
        ):
            issues.append(
                f"Incomplete point-in-time identity: {security.get('asset_id')}."
            )
        if (
            not security.get("sector")
            or not security.get("sector_effective_from")
            or not security.get("sector_source")
        ):
            issues.append(f"Missing dated sector evidence: {security.get('asset_id')}.")
        for record in security.get("ticker_history", []):
            if not all(record.get(k) for k in ("ticker", "effective_from", "source")):
                issues.append("Incomplete ticker interval evidence.")
    if not manifest.get("files"):
        issues.append("No source files.")
    for entry in manifest.get("files", []):
        target = (path / entry["path"]).resolve()
        if (
            not target.is_relative_to(path.resolve())
            or not target.is_file()
            or sha(target) != entry.get("sha256")
            or not entry.get("source")
        ):
            issues.append(f"Missing or altered source: {entry.get('path')}.")
    processed = manifest.get("processed_prices")
    if not processed:
        issues.append(
            "No audited aligned total-return prices; raw downloads cannot be used directly."
        )
    else:
        target = (path / processed["path"]).resolve()
        if (
            not target.is_relative_to(path.resolve())
            or not target.is_file()
            or sha(target) != processed.get("sha256")
        ):
            issues.append("Aligned-price checksum mismatch.")
        else:
            frame = pd.read_csv(target, index_col=0, parse_dates=True)
            expected = [s["asset_id"] for s in securities] + [manifest.get("benchmark")]
            if list(frame.columns) != expected:
                issues.append("Aligned security columns differ from manifest.")
            if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
                issues.append("Duplicate or unordered dates.")
            if not np.isfinite(frame.to_numpy()).all() or (frame <= 0).any().any():
                issues.append("Invalid/missing total-return prices.")
            if len(frame) < 253:
                issues.append("Insufficient estimation history.")
    for record in manifest.get("context", []):
        if not all(
            record.get(k) for k in ("source", "published_at", "sha256", "accession")
        ):
            issues.append("Context lacks publication evidence.")
        elif cutoff and pd.Timestamp(record["published_at"]) > pd.Timestamp(cutoff):
            issues.append("Future context at decision cutoff.")
    return {
        "status": "passed" if not issues else "blocked",
        "financial_evaluation_allowed": not issues,
        "issues": issues,
        "dataset_kind": manifest.get("dataset_kind"),
        "future_price_rows_policy": "Permitted in source storage, sliced before decision; held-out rows never enter features.",
    }


def load_market(directory):
    path = Path(directory)
    manifest = json.loads((path / "dataset_manifest.json").read_text())
    report = audit(manifest, path)
    if not report["financial_evaluation_allowed"]:
        raise ValueError("Financial evaluation blocked: " + "; ".join(report["issues"]))
    frame = pd.read_csv(
        path / manifest["processed_prices"]["path"], index_col=0, parse_dates=True
    )
    return frame.pct_change().iloc[1:], manifest
