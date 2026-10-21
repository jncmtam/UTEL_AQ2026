from __future__ import annotations

from datetime import date

import pytest

from agqo.news import NewsRecord, content_digest, filter_point_in_time


def _record(**overrides):
    value = {
        "evidence_id": "HOSE:2025:001",
        "source_name": "HOSE",
        "source_tier": "primary",
        "canonical_url": "https://www.hsx.vn/notice/001",
        "headline": "Company disclosure",
        "ticker_entities": ["fpt", "FPT"],
        "event_category": "company_disclosure",
        "published_at": "2025-06-01T09:00:00+07:00",
        "collected_at": "2025-06-01T09:05:00+07:00",
        "timezone": "Asia/Ho_Chi_Minh",
        "timestamp_precision": "exact",
        "content_sha256": content_digest("metadata only"),
        "extraction_version": "v1",
    }
    value.update(overrides)
    return NewsRecord.from_mapping(value)


def test_point_in_time_filter_keeps_only_published_by_cutoff():
    past = _record()
    future = _record(
        evidence_id="HOSE:2025:002",
        published_at="2025-06-02T09:00:00+07:00",
        collected_at="2025-06-02T09:05:00+07:00",
    )
    assert filter_point_in_time([past, future], date(2025, 6, 1)) == [past]


def test_point_in_time_filter_rejects_records_collected_after_cutoff():
    backfilled = _record(collected_at="2025-06-02T09:05:00+07:00")
    assert filter_point_in_time([backfilled], "2025-06-01") == []


def test_unknown_or_date_only_timestamps_never_enter_primary_sample():
    date_only = _record(
        published_at="2025-06-01",
        timestamp_precision="date_only",
        collected_at="2025-06-01T09:05:00+07:00",
    )
    unknown = _record(
        evidence_id="HOSE:2025:003",
        published_at=None,
        timestamp_precision="unknown",
    )
    assert not date_only.point_in_time_eligible("2025-06-30")
    assert not unknown.point_in_time_eligible("2025-06-30")


def test_timezone_is_required_for_exact_published_and_collected_times():
    with pytest.raises(ValueError, match="múi giờ"):
        _record(published_at="2025-06-01T09:00:00")


def test_duplicate_evidence_ids_are_rejected():
    record = _record()
    with pytest.raises(ValueError, match="bị trùng"):
        filter_point_in_time([record, record], "2025-06-01")


def test_invalid_provenance_fields_fail_closed():
    with pytest.raises(ValueError, match="HTTPS"):
        _record(canonical_url="http://example.com/news")
    with pytest.raises(ValueError, match="SHA-256"):
        _record(content_sha256="abc")
