"""Build the curated, point-in-time VN30 constituent intervals used by AGQO."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from agqo.universe import load_membership_history, members_as_of


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data" / "vn30_snapshot_20261002"
ANCHOR_PATH = DEFAULT_DIR / "vn30_anchor_2026-02-02.csv"

# The anchor is the HOSE January 2026 review, effective 2026-02-02. The source
# snapshot already in the project is that basket (VPL for BCM, DGC still in).
EVENTS = [
    {
        "effective_date": "2022-08-01", "announcement_date": "2022-07-18",
        "added": ["VIB"], "removed": ["PNJ"], "review_id": "2022-07-regular",
        "source_url": "https://www.phs.vn/tin-tuc/dao-danh-muc-vn30-loai-pnj-them-moi-vib/5608281",
        "source_tier": "exchange_notice_republished",
    },
    {
        "effective_date": "2023-02-06", "announcement_date": "2023-01-17",
        "added": ["BCM"], "removed": ["KDH"], "review_id": "2023-01-regular",
        "source_url": "https://www.funan.com.vn/vi/dao-danh-muc-vn30-thang-12023-them-bcm-loai-kdh.1031504",
        "source_tier": "exchange_notice_republished",
    },
    {
        "effective_date": "2023-08-07", "announcement_date": "2023-07-17",
        "added": ["SHB", "SSB"], "removed": ["NVL", "PDR"], "review_id": "2023-07-regular",
        "source_url": "https://vnexpress.net/hai-co-phieu-bat-dong-san-bi-loai-khoi-ro-von-hoa-lon-4630469.html",
        "source_tier": "secondary_report_of_hose_notice",
    },
    {
        "effective_date": "2025-02-03", "announcement_date": "2025-01-20",
        "added": ["LPB"], "removed": ["POW"], "review_id": "2025-01-regular",
        "source_url": "https://mobi.fireant.vn/News/NewsAttachedFile/1732373",
        "source_tier": "hose_notice_mirror",
    },
    {
        "effective_date": "2025-08-04", "announcement_date": "2025-07-25",
        "added": ["DGC"], "removed": ["BVH"], "review_id": "2025-07-regular",
        "source_url": "https://www.phs.vn/tin-tuc/hose-cai-tien-chi-so-vn30-ky-thang-72025/6313827",
        "source_tier": "hose_notice_republished",
    },
    {
        "effective_date": "2026-02-02", "announcement_date": "2026-01-21",
        "added": ["VPL"], "removed": ["BCM"], "review_id": "2026-01-regular",
        "source_url": "https://www.phs.vn/tin-tuc/dao-danh-muc-vn30-ky-thang-12026-vpl-gia-nhap-bcm-bi-loai-ra/6361458",
        "source_tier": "hose_notice_republished",
    },
    {
        "effective_date": "2026-05-13", "announcement_date": "2026-05-08",
        "added": ["BSR"], "removed": ["DGC"], "review_id": "2026-05-off-cycle",
        "source_url": "https://www.bsr.com.vn/en/web/bsr/w/bsr-chinh-thuc-gia-nhap-ro-vn30-tu-13-5-2026-dau-moc-khang-dinh-vi-the-doanh-nghiep-nang-luong-tru-cot",
        "source_tier": "issuer_report_of_hose_notice",
    },
    {
        "effective_date": "2026-08-03", "announcement_date": "2026-07-15",
        "added": ["MCH", "TCX"], "removed": ["PLX", "TPB"], "review_id": "2026-07-regular",
        "source_url": "https://www.tinnhanhchungkhoan.vn/hose-chot-ro-vn30-mch-tcx-se-thay-the-cho-tpb-va-plx-post394082.html",
        "source_tier": "secondary_report_of_hose_notice",
    },
]

NO_CHANGE_REVIEWS = [
    {"review_id": "2022-01-regular", "announcement_date": "2022-01-17", "source_url": "https://vn.investing.com/news/stock-market-news/dao-vn30-ky-thang-12022-giu-nguyen-danh-muc-1970141", "source_tier": "secondary_report_of_hose_notice"},
    {"review_id": "2024-01-regular", "announcement_date": "2024-01-18", "source_url": "https://www.funan.com.vn/vi/dao-danh-muc-vn30-ky-thang-1-2024-khong-co-thay-doi.1054482", "source_tier": "exchange_notice_republished"},
    {"review_id": "2024-07-regular", "announcement_date": "2024-07-15", "source_url": "https://www.phs.vn/tin-tuc/cac-quy-etf-vn30-vnfinlead-se-dao-danh-muc-ra-sao-trong-ky-review-thang-7/6187821", "source_tier": "secondary_report_of_hose_notice"},
]

GROUPS = {
    **{ticker: "Ngân hàng" for ticker in "ACB BID CTG HDB LPB MBB SHB SSB STB TCB TPB VCB VIB VPB".split()},
    **{ticker: "Bất động sản" for ticker in "BCM KDH NVL PDR VHM VIC VPL VRE".split()},
    **{ticker: "Năng lượng" for ticker in "BSR GAS PLX POW".split()},
    **{ticker: "Nguyên vật liệu" for ticker in "DGC GVR HPG".split()},
    **{ticker: "Tiêu dùng" for ticker in "MCH MSN MWG PNJ SAB VNM".split()},
    "FPT": "Công nghệ",
    "SSI": "Chứng khoán",
    "TCX": "Chứng khoán",
    "BVH": "Bảo hiểm",
    "VJC": "Hàng không",
}


def build(output_dir: Path) -> tuple[Path, Path, Path]:
    anchor_path = output_dir / "members.csv"
    immutable_anchor = output_dir / ANCHOR_PATH.name
    if not immutable_anchor.exists():
        raise FileNotFoundError(
            f"Thiếu snapshot gốc bất biến {immutable_anchor}; không dùng members.csv "
            "vì tệp đó được cập nhật thành rổ hiện hành sau khi dựng lịch."
        )
    anchor = pd.read_csv(immutable_anchor)
    if len(anchor) != 30 or anchor["ticker"].duplicated().any():
        raise ValueError(f"Snapshot anchor không có đúng 30 mã: {anchor_path}")
    anchor_members = set(anchor["ticker"].astype(str).str.upper())

    before_anchor = [event for event in EVENTS if event["effective_date"] <= "2026-02-02"]
    baseline = set(anchor_members)
    for event in reversed(before_anchor):
        if not set(event["added"]).issubset(baseline):
            raise ValueError(f"Không thể đảo ngược kỳ {event['review_id']} từ anchor.")
        baseline.difference_update(event["added"])
        baseline.update(event["removed"])
        if len(baseline) != 30:
            raise ValueError(f"Kỳ {event['review_id']} làm sai số lượng mã khi dựng ngược.")

    snapshots = [{"effective_date": "2022-01-01", "review_id": "2022-01-anchor-reconstructed",
                  "announcement_date": "2022-01-17",
                  "source_url": NO_CHANGE_REVIEWS[0]["source_url"],
                  "source_tier": NO_CHANGE_REVIEWS[0]["source_tier"],
                  "tickers": set(baseline)}]
    current = set(baseline)
    for event in EVENTS:
        removed, added = set(event["removed"]), set(event["added"])
        if not removed.issubset(current):
            raise ValueError(f"Kỳ {event['review_id']} loại mã không có trong rổ trước đó.")
        current.difference_update(removed)
        current.update(added)
        if len(current) != 30 or len(current) != len(set(current)):
            raise ValueError(f"Kỳ {event['review_id']} không tạo được rổ 30 mã.")
        snapshots.append({**event, "tickers": set(current)})

    rows = []
    for index, snapshot in enumerate(snapshots):
        start = pd.Timestamp(snapshot["effective_date"])
        end = (
            pd.Timestamp(snapshots[index + 1]["effective_date"]) - pd.Timedelta(days=1)
            if index + 1 < len(snapshots)
            else pd.Timestamp("2262-04-11")
        )
        for ticker in sorted(snapshot["tickers"]):
            if ticker not in GROUPS:
                raise ValueError(f"Chưa gán nhóm ngành cho {ticker}.")
            rows.append({
                "ticker": ticker,
                "valid_from": start.date().isoformat(),
                "valid_to": end.date().isoformat(),
                "group": GROUPS[ticker],
                "review_id": snapshot["review_id"],
                "announcement_date": snapshot["announcement_date"],
                "source_url": snapshot["source_url"],
                "source_tier": snapshot["source_tier"],
            })
    history_path = output_dir / "vn30_membership_history.csv"
    history = pd.DataFrame(rows)
    history.to_csv(history_path, index=False, encoding="utf-8")
    validated = load_membership_history(history_path)

    current_members = members_as_of(validated, "2026-10-19")[["ticker", "group"]]
    current_members.to_csv(anchor_path, index=False, encoding="utf-8")

    events_path = output_dir / "vn30_membership_events.csv"
    events = [{
        "event_type": "constituent_change",
        "review_id": event["review_id"],
        "announcement_date": event["announcement_date"],
        "effective_date": event["effective_date"],
        "added": ";".join(event["added"]),
        "removed": ";".join(event["removed"]),
        "source_url": event["source_url"],
        "source_tier": event["source_tier"],
    } for event in EVENTS]
    events.extend({
        "event_type": "no_constituent_change",
        "review_id": review["review_id"],
        "announcement_date": review["announcement_date"],
        "effective_date": "",
        "added": "",
        "removed": "",
        "source_url": review["source_url"],
        "source_tier": review["source_tier"],
    } for review in NO_CHANGE_REVIEWS)
    pd.DataFrame(events).sort_values("announcement_date").to_csv(
        events_path, index=False, encoding="utf-8"
    )
    return history_path, events_path, anchor_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    history_path, events_path, current_path = build(args.output_dir.resolve())
    print(f"Đã tạo {history_path}, {events_path} và snapshot hiện hành {current_path}.")


if __name__ == "__main__":
    main()

