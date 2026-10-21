"""Kiểm tra nguồn gốc và mốc thời gian của bằng chứng tin tức AGQO.

Mô-đun này chỉ nhận siêu dữ liệu được phép dùng; không tải, lưu hay chuyển tiếp
toàn văn bài báo. Bằng chứng chỉ được dùng khi có mốc xuất bản chính xác hoặc
mốc nguồn ghi nhận đầu tiên chính xác, cùng giờ thu thập không sau quyết định.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from zoneinfo import ZoneInfo


VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
SOURCE_TIERS = {"primary", "secondary"}
EVENT_CATEGORIES = {
    "company_disclosure",
    "exchange_notice",
    "regulatory_notice",
    "macro_release",
    "analyst_commentary",
    "general_news",
}


@dataclass(frozen=True)
class NewsRecord:
    """Dấu vết tin ngắn có thể kiểm toán, không chứa toàn văn bài báo."""

    evidence_id: str
    source_name: str
    source_tier: str
    canonical_url: str
    headline: str | None
    ticker_entities: tuple[str, ...]
    event_category: str
    published_at: str | None
    collected_at: str
    timezone: str
    timestamp_precision: str
    content_sha256: str
    extraction_version: str
    revision_id: str = "original"
    availability_at: str | None = None
    availability_basis: str = "published_at"

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "NewsRecord":
        """Tạo bản ghi đã kiểm tra cấu trúc, đường dẫn và dấu thời gian."""
        required = {
            "evidence_id", "source_name", "source_tier", "canonical_url",
            "ticker_entities", "event_category", "published_at",
            "collected_at", "timezone", "timestamp_precision", "content_sha256",
            "extraction_version",
        }
        missing = required - set(row)
        if missing:
            raise ValueError(f"Thiếu trường nguồn tin: {sorted(missing)}")
        evidence_id = _nonempty(row["evidence_id"], "evidence_id")
        source_tier = _nonempty(row["source_tier"], "source_tier")
        if source_tier not in SOURCE_TIERS:
            raise ValueError("source_tier phải là primary hoặc secondary.")
        url = _nonempty(row["canonical_url"], "canonical_url")
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("canonical_url phải là địa chỉ HTTPS đầy đủ.")
        category = _nonempty(row["event_category"], "event_category")
        if category not in EVENT_CATEGORIES:
            raise ValueError(f"event_category không được hỗ trợ: {category}.")
        precision = _nonempty(row["timestamp_precision"], "timestamp_precision")
        if precision not in {"exact", "date_only", "unknown"}:
            raise ValueError("timestamp_precision phải là exact, date_only hoặc unknown.")
        timezone_name = _nonempty(row["timezone"], "timezone")
        try:
            ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Múi giờ không hợp lệ: {timezone_name}.") from exc
        published_at = row["published_at"]
        if published_at is not None:
            _parse_published(published_at, precision, timezone_name)
        collected_at = _parse_instant(row["collected_at"], "collected_at")
        if published_at is not None and _parse_published(published_at, precision, timezone_name) > collected_at:
            raise ValueError("published_at không thể nằm sau collected_at.")
        availability_basis = str(row.get("availability_basis", "published_at"))
        if precision == "exact" and published_at is None and availability_basis != "source_first_seen":
            raise ValueError("Dấu thời gian chính xác bắt buộc có published_at.")
        if availability_basis not in {"published_at", "source_first_seen"}:
            raise ValueError("availability_basis phải là published_at hoặc source_first_seen.")
        availability_at = row.get("availability_at")
        if availability_basis == "source_first_seen":
            if availability_at is None:
                raise ValueError("Nguồn dùng mốc first-seen phải có availability_at.")
            available = _parse_instant(availability_at, "availability_at")
            if precision != "exact":
                raise ValueError("Mốc source_first_seen chỉ hợp lệ với timestamp_precision=exact.")
            if available > collected_at:
                raise ValueError("availability_at không thể nằm sau collected_at.")
        elif availability_at not in (None, ""):
            _parse_instant(availability_at, "availability_at")
        digest = _nonempty(row["content_sha256"], "content_sha256").lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("content_sha256 phải là SHA-256 dạng 64 ký tự hex.")
        tickers = row["ticker_entities"]
        if not isinstance(tickers, (list, tuple)) or any(
            not isinstance(ticker, str) or not ticker.strip() for ticker in tickers
        ):
            raise ValueError("ticker_entities phải là danh sách mã dạng chuỗi.")
        return cls(
            evidence_id=evidence_id,
            source_name=_nonempty(row["source_name"], "source_name"),
            source_tier=source_tier,
            canonical_url=url,
            headline=(
                None if row.get("headline") in (None, "")
                else _nonempty(row["headline"], "headline")
            ),
            ticker_entities=tuple(dict.fromkeys(ticker.upper() for ticker in tickers)),
            event_category=category,
            published_at=(None if published_at is None else str(published_at)),
            collected_at=str(row["collected_at"]),
            timezone=timezone_name,
            timestamp_precision=precision,
            content_sha256=digest,
            extraction_version=_nonempty(row["extraction_version"], "extraction_version"),
            revision_id=str(row.get("revision_id", "original")),
            availability_at=(None if availability_at in (None, "") else str(availability_at)),
            availability_basis=availability_basis,
        )

    def point_in_time_eligible(self, as_of: str | date | datetime) -> bool:
        """Chỉ nhận mốc công bố/thu thập chính xác, có múi giờ và không sau cutoff."""
        cutoff = _parse_cutoff(as_of)
        collected = _parse_instant(self.collected_at, "collected_at")
        if collected > cutoff:
            return False
        if self.availability_basis == "source_first_seen":
            if self.availability_at is None:
                return False
            return _parse_instant(self.availability_at, "availability_at") <= cutoff
        if self.timestamp_precision != "exact" or self.published_at is None:
            return False
        published = _parse_published(self.published_at, self.timestamp_precision, self.timezone)
        return published <= cutoff

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def filter_point_in_time(
    records: Iterable[NewsRecord], as_of: str | date | datetime
) -> list[NewsRecord]:
    """Lọc theo ngày quyết định và loại bỏ mã bằng chứng bị trùng."""
    result: list[NewsRecord] = []
    seen: set[str] = set()
    for record in records:
        if record.evidence_id in seen:
            raise ValueError(f"evidence_id bị trùng: {record.evidence_id}.")
        seen.add(record.evidence_id)
        if record.point_in_time_eligible(as_of):
            result.append(record)
    return result


def content_digest(content: str | bytes) -> str:
    """Trả mã băm nội dung để kiểm tra phiên bản; không giữ lại nội dung."""
    value = content.encode("utf-8") if isinstance(content, str) else content
    return sha256(value).hexdigest()


def load_news_records(path: str | Path) -> list[NewsRecord]:
    """Read point-in-time evidence metadata from CSV or JSONL, never article text."""
    source = Path(path)
    if source.suffix.lower() in {".jsonl", ".ndjson"}:
        rows = [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        rows = []
        with source.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                row["ticker_entities"] = json.loads(row.get("ticker_entities") or "[]")
                for field in ("published_at", "availability_at"):
                    if row.get(field) == "":
                        row[field] = None
                rows.append(row)
    return [NewsRecord.from_mapping(row) for row in rows]


def summarize_news_as_of(
    records: Iterable[NewsRecord],
    as_of: str | date | datetime,
    tickers: Iterable[str],
) -> dict[str, Any]:
    """Return counts from locally captured, point-in-time ticker evidence."""
    cutoff = _parse_cutoff(as_of)
    ticker_set = {ticker.upper() for ticker in tickers}
    eligible = filter_point_in_time(records, as_of)
    rows: list[tuple[NewsRecord, datetime]] = []
    for record in eligible:
        available_value = (
            record.availability_at
            if record.availability_basis == "source_first_seen"
            else record.published_at
        )
        if available_value is None or record.timestamp_precision != "exact":
            continue
        available = _parse_instant(available_value, "available_at")
        if available <= cutoff and ticker_set.intersection(record.ticker_entities):
            rows.append((record, available))

    by_ticker: dict[str, dict[str, Any]] = {}
    for ticker in sorted(ticker_set):
        matching = [(record, available) for record, available in rows if ticker in record.ticker_entities]
        ticker_counts: dict[str, Any] = {}
        for days in (5, 20):
            threshold = cutoff - timedelta(days=days)
            ticker_counts[f"mentions_{days}d"] = sum(available >= threshold for _, available in matching)
        ticker_counts["latest_available_at"] = (
            max(available for _, available in matching).isoformat() if matching else None
        )
        ticker_counts["evidence_ids"] = [record.evidence_id for record, _ in matching[-10:]]
        by_ticker[ticker] = ticker_counts
    evidence_ids = {record.evidence_id for record, _ in rows}
    source_references = [
        {
            "evidence_id": record.evidence_id,
            "url": record.canonical_url,
            "available_at": available.isoformat(),
            "ticker_entities": list(record.ticker_entities),
        }
        for record, available in sorted(rows, key=lambda item: item[1], reverse=True)[:10]
    ]
    return {
        "eligible_record_count": len(evidence_ids),
        "coverage_window_days": [5, 20],
        "aggregate_mentions_5d": sum(
            count for row in by_ticker.values() for key, count in row.items()
            if key == "mentions_5d"
        ),
        "aggregate_mentions_20d": sum(
            count for row in by_ticker.values() for key, count in row.items()
            if key == "mentions_20d"
        ),
        "tickers": by_ticker,
        "source_references": source_references,
        "source": "GDELT DOC metadata; source first-seen timestamp, not publisher publication time",
        "article_text_or_headlines_retained": False,
    }


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} phải là chuỗi không rỗng.")
    return value.strip()


def _parse_instant(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} phải là mốc thời gian ISO có múi giờ.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} không phải mốc ISO hợp lệ.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} phải ghi rõ múi giờ hoặc độ lệch UTC.")
    return parsed.astimezone(timezone.utc)


def _parse_published(value: Any, precision: str, timezone_name: str) -> datetime:
    """Allow date-only metadata for storage, but never for point-in-time use."""
    if precision == "date_only" and isinstance(value, str) and len(value.strip()) == 10:
        try:
            local_date = date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError("published_at không phải ngày YYYY-MM-DD hợp lệ.") from exc
        return datetime.combine(local_date, time.min, tzinfo=ZoneInfo(timezone_name)).astimezone(timezone.utc)
    return _parse_instant(value, "published_at")


def _parse_cutoff(value: str | date | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            # Research signals are exchange-local dates represented by naive
            # pandas timestamps. Treat them as the full Vietnam trading day.
            local = value.replace(tzinfo=VIETNAM_TZ)
            if local.time() == time.min:
                local = local.replace(hour=23, minute=59, second=59, microsecond=999999)
            return local.astimezone(timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        cutoff_date = value
    elif isinstance(value, str):
        if "T" in value or " " in value:
            return _parse_instant(value, "as_of")
        try:
            cutoff_date = date.fromisoformat(value[:10])
        except ValueError as exc:
            raise ValueError("as_of phải là ngày YYYY-MM-DD hoặc datetime ISO.") from exc
    else:
        raise ValueError("Kiểu as_of không được hỗ trợ.")
    return datetime.combine(cutoff_date, time.max, tzinfo=VIETNAM_TZ).astimezone(timezone.utc)
