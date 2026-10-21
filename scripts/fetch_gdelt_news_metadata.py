"""Capture point-in-time GDELT news metadata without retaining article text."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_ALIASES = ROOT / "data/news/company_aliases.csv"
DEFAULT_OUTPUT = ROOT / "data/news/gdelt_metadata.csv"
DEFAULT_MANIFEST = ROOT / "data/news/manifest.json"
FIELDS = [
    "evidence_id", "source_name", "source_tier", "canonical_url", "headline",
    "ticker_entities", "event_category", "published_at", "availability_at",
    "availability_basis", "collected_at", "timezone", "timestamp_precision",
    "content_sha256", "extraction_version", "revision_id",
]


def _gdelt_datetime(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as file:
        return {row["evidence_id"]: row for row in csv.DictReader(file)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--days", type=int, default=30, help="Cửa sổ truy vấn gần đây, tối đa 90 ngày.")
    parser.add_argument("--pause-seconds", type=float, default=5.5)
    parser.add_argument("--max-records", type=int, default=250)
    parser.add_argument("--ticker", action="append", help="Chỉ thu thập cho một hoặc nhiều mã cụ thể.")
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        parser.error("GDELT DOC được dùng ở đây cho cửa sổ gần; chọn 1–90 ngày.")
    if args.pause_seconds < 5:
        parser.error("GDELT yêu cầu giới hạn tối thiểu một truy vấn mỗi 5 giây.")
    if not 1 <= args.max_records <= 250:
        parser.error("--max-records phải nằm trong 1–250.")

    with args.aliases.open(newline="", encoding="utf-8") as alias_file:
        all_aliases = list(csv.DictReader(alias_file))
    aliases = list(all_aliases)
    if args.ticker:
        selected = {ticker.upper() for ticker in args.ticker}
        aliases = [row for row in aliases if row["ticker"].upper() in selected]
        missing = selected - {row["ticker"].upper() for row in aliases}
        if missing:
            parser.error(f"Thiếu bí danh công ty cho {sorted(missing)} trong {args.aliases}.")

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=args.days)
    start_param = start.strftime("%Y%m%d%H%M%S")
    end_param = now.strftime("%Y%m%d%H%M%S")
    collected_at = now.isoformat()
    records = _existing(args.output)
    pending_records: dict[str, dict[str, str]] = {}
    query_stats = []
    rate_limited = False
    for number, alias in enumerate(aliases, start=1):
        ticker = alias["ticker"].upper().strip()
        phrase = alias["query_alias"].strip()
        print(f"[{number}/{len(aliases)}] {ticker}: tìm siêu dữ liệu theo bí danh đã chọn", flush=True)
        params = {
            "query": f'"{phrase}"',
            "mode": "ArtList",
            "format": "json",
            "maxrecords": args.max_records,
            "startdatetime": start_param,
            "enddatetime": end_param,
            "sort": "HybridRel",
        }
        try:
            response = requests.get(
                API,
                params=params,
                headers={"User-Agent": "AGQO research metadata collector/1.0"},
                timeout=45,
            )
            response.raise_for_status()
            payload = response.json()
            articles = payload.get("articles", []) if isinstance(payload, dict) else []
            accepted = 0
            for article in articles:
                url = str(article.get("url") or "").strip()
                parsed_url = urlparse(url)
                if parsed_url.scheme != "https" or not parsed_url.netloc:
                    continue
                first_seen = _gdelt_datetime(str(article.get("seendate") or ""))
                if first_seen is None or first_seen < start or first_seen > now:
                    continue
                # GDELT's returned title is deliberately not retained. The SHA-256
                # fingerprints URL, ticker and first-seen timestamp only.
                metadata_key = f"{url}\n{ticker}\n{first_seen.isoformat()}"
                digest = _digest(metadata_key)
                evidence_id = f"GDELT:{digest[:24]}"
                pending_records[evidence_id] = {
                    "evidence_id": evidence_id,
                    "source_name": "GDELT DOC 2.0",
                    "source_tier": "secondary",
                    "canonical_url": url,
                    "headline": "",
                    "ticker_entities": json.dumps([ticker]),
                    "event_category": "general_news",
                    "published_at": "",
                    "availability_at": first_seen.isoformat(),
                    "availability_basis": "source_first_seen",
                    "collected_at": collected_at,
                    "timezone": "UTC",
                    "timestamp_precision": "exact",
                    "content_sha256": digest,
                    "extraction_version": f"gdelt-doc-alias-v1:{_digest(phrase)[:12]}",
                    "revision_id": "first_seen_snapshot",
                }
                accepted += 1
            query_stats.append({"ticker": ticker, "alias_hash": _digest(phrase), "records_received": len(articles), "metadata_rows_accepted": accepted})
        except Exception as exc:
            query_stats.append({"ticker": ticker, "alias_hash": _digest(phrase), "error": repr(exc)})
            print(f"  Lỗi nguồn cho {ticker}: {exc}", flush=True)
            if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429:
                rate_limited = True
                print("  Dừng truy vấn tiếp theo để tôn trọng giới hạn của nguồn.", flush=True)
                break
        if number < len(aliases):
            time.sleep(args.pause_seconds)

    query_errors = any("error" in row for row in query_stats)
    full_universe_query = (
        not args.ticker
        and not query_errors
        and len(query_stats) == len(all_aliases)
    )
    if not query_errors:
        records.update(pending_records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records.values(), key=lambda row: (row.get("availability_at", ""), row["evidence_id"]))
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(ordered)
    manifest = {
        "manifest_version": "agqo-news-v2-gdelt-metadata",
        "status": (
            "temporarily_rate_limited" if rate_limited
            else "partial_collection" if query_errors
            else "collected_metadata_only" if ordered
            else "ready_for_collection_no_records"
        ),
        "records_count": len(ordered),
        "news_context_available": bool(ordered) and full_universe_query and not query_errors,
        "query_scope_tickers": [row["ticker"].upper() for row in aliases],
        "complete_universe_query": full_universe_query,
        "query_window_start_utc": start.isoformat(),
        "query_window_end_utc": now.isoformat(),
        "collection_completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision_time_timezone": "Asia/Ho_Chi_Minh",
        "source": "GDELT DOC 2.0; API returns article URL, title and GDELT seendate; AGQO discards title and stores only URL, source first-seen timestamp, ticker alias query and metadata hash.",
        "timestamp_policy": "GDELT seendate is treated as source first-seen/availability time, never as publisher publication time. Historical rows retrieved after a decision are excluded by collected_at <= decision cutoff.",
        "entity_matching": "Each record is associated with the exact company-name query alias used; the match is a retrieval proxy, not human-confirmed ticker entity resolution. No sentiment is inferred.",
        "rights_status": "GDELT dataset metadata may be used and redistributed with attribution under https://www.gdeltproject.org/about.html; source article text and headlines are not stored or redistributed. Underlying publisher terms continue to govern article content.",
        "raw_article_text_stored": False,
        "article_headline_stored": False,
        "source_url_stored": True,
        "feed_file": args.output.name,
        "feed_sha256": _digest(args.output.read_text(encoding="utf-8")),
        "query_window_days": args.days,
        "query_details": query_stats,
        "disabled_reason": (
            "GDELT returned HTTP 429; stop and retry after the source cooldown. No partial batch is added."
            if rate_limited else
            "At least one source query failed; partial collection is not enabled for model use."
            if query_errors else
            "A ticker-scoped query is diagnostic only; query every configured issuer before model use."
            if not full_universe_query else
            "No source records returned; model receives no news features."
            if not ordered else None
        ),
        "usage_guard": "News is context only; it is not a return forecast and is not added to the QAOA financial objective.",
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã ghi {len(ordered)} bản ghi siêu dữ liệu vào {args.output}; không lưu tiêu đề hoặc nội dung bài báo.")
    return 0 if not query_errors else 2


if __name__ == "__main__":
    sys.exit(main())

