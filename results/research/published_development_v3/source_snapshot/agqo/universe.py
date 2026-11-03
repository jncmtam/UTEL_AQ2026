"""Point-in-time VN30 constituent history and membership lookups."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


MEMBERSHIP_COLUMNS = {
    "ticker",
    "valid_from",
    "valid_to",
    "group",
    "review_id",
    "announcement_date",
    "source_url",
    "source_tier",
}


def load_membership_history(path: str | Path) -> pd.DataFrame:
    """Load and validate historical index constituents with documented intervals."""
    history = pd.read_csv(path)
    missing = MEMBERSHIP_COLUMNS - set(history.columns)
    if missing:
        raise ValueError(
            "Cần tệp lịch thành phần theo thời gian với các cột "
            f"{sorted(MEMBERSHIP_COLUMNS)}; thiếu {sorted(missing)}."
        )
    history = history.copy()
    history["ticker"] = history["ticker"].astype(str).str.upper().str.strip()
    history["valid_from"] = pd.to_datetime(history["valid_from"], errors="raise").dt.normalize()
    history["valid_to"] = pd.to_datetime(history["valid_to"], errors="raise").dt.normalize()
    history["announcement_date"] = pd.to_datetime(
        history["announcement_date"], errors="raise"
    ).dt.normalize()
    if history.duplicated(["ticker", "valid_from", "valid_to"]).any():
        raise ValueError("Lịch thành phần có dòng mã/ngày hiệu lực bị trùng.")
    if (history["valid_from"] > history["valid_to"]).any():
        raise ValueError("Ngày bắt đầu hiệu lực phải trước ngày kết thúc.")
    if history[["ticker", "group", "review_id", "source_url"]].isna().any().any():
        raise ValueError("Lịch thành phần còn thiếu mã, nhóm, kỳ rà soát hoặc nguồn.")
    if not history["source_url"].astype(str).str.startswith("https://").all():
        raise ValueError("Mọi kỳ thành phần phải có nguồn HTTPS.")

    history = history.sort_values(["valid_from", "ticker"]).reset_index(drop=True)
    for effective_date, snapshot in history.groupby("valid_from", sort=True):
        if snapshot["ticker"].nunique() != 30:
            raise ValueError(
                f"Kỳ hiệu lực {effective_date.date()} phải có đúng 30 mã duy nhất; "
                f"nhận {snapshot['ticker'].nunique()}."
            )
    for ticker, rows in history.groupby("ticker", sort=False):
        ordered = rows.sort_values("valid_from")
        prior_end = ordered["valid_to"].shift()
        overlaps = prior_end.notna() & (ordered["valid_from"].to_numpy() <= prior_end.to_numpy())
        if overlaps.any():
            raise ValueError(f"Các khoảng hiệu lực của {ticker} chồng lấn.")
    return history


def members_as_of(history: pd.DataFrame, as_of: str | pd.Timestamp) -> pd.DataFrame:
    """Return the 30 constituents effective on a signal date."""
    date = pd.Timestamp(as_of).normalize()
    active = history.loc[
        history["valid_from"].le(date) & history["valid_to"].ge(date)
    ].copy()
    if len(active) != 30 or active["ticker"].nunique() != 30:
        raise ValueError(
            f"Không có đúng một danh sách VN30 đã kiểm chứng cho ngày {date.date()}: "
            f"nhận {active['ticker'].nunique()} mã."
        )
    return active.sort_values("ticker").reset_index(drop=True)


def latest_members(history: pd.DataFrame, as_of: str | pd.Timestamp) -> pd.DataFrame:
    """Return a compact ticker/group snapshot for descriptive plots and summaries."""
    return members_as_of(history, as_of)[["ticker", "group"]].reset_index(drop=True)

