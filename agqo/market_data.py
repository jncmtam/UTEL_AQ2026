"""Đọc, kiểm định và phân tích bộ dữ liệu VN30/VN-Index đã đóng băng."""

from __future__ import annotations

import json
from math import comb
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from .estimators import build_investable_problem
from .problem import exact_solve
from .universe import MEMBERSHIP_COLUMNS, latest_members, load_membership_history

REQUIRED_COLUMNS = {
    "date",
    "ticker",
    "instrument_type",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def load_market_dataset(
    data_path: str | Path,
    members_path: str | Path,
    *,
    require_point_in_time_membership: bool = False,
    require_adjusted_prices: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read OHLCV and either a static snapshot or validated constituent intervals."""
    data = pd.read_csv(data_path)
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Thiếu các cột OHLCV bắt buộc: {sorted(missing)}")
    data["date"] = pd.to_datetime(data["date"], errors="raise").dt.normalize()
    data["ticker"] = data["ticker"].astype(str).str.upper()
    data["instrument_type"] = data["instrument_type"].astype(str)
    for column in ("open", "high", "low", "close", "volume"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    adjusted_columns = [f"{column}_adjusted" for column in ("open", "high", "low", "close")]
    if require_adjusted_prices and not set(adjusted_columns).issubset(data.columns):
        raise ValueError(
            "Backtest tài chính cần đủ open/high/low/close_adjusted từ nguồn đã khai báo; "
            "hãy dựng lại bộ dữ liệu bằng scripts/download_vn30_dataset.py."
        )
    if set(adjusted_columns).issubset(data.columns):
        for column in adjusted_columns:
            data[column] = pd.to_numeric(data[column], errors="raise")
        stock_adjusted = data.loc[data.instrument_type == "stock", adjusted_columns]
        if require_adjusted_prices and stock_adjusted.isna().any().any():
            raise ValueError("OHLC điều chỉnh còn thiếu; không được coi tập dữ liệu là hoàn chỉnh.")
        if not np.isfinite(stock_adjusted.to_numpy()).all():
            raise ValueError("OHLC điều chỉnh chứa giá trị không hữu hạn.")
        if (stock_adjusted <= 0).any().any():
            raise ValueError("OHLC điều chỉnh phải dương.")
    if data.duplicated(["date", "ticker"]).any():
        raise ValueError("Có ngày và mã bị lặp.")
    if not np.isfinite(data[["open", "high", "low", "close", "volume"]].to_numpy()).all():
        raise ValueError("Dữ liệu giá hoặc khối lượng chứa giá trị không hữu hạn.")
    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Giá OHLC phải dương.")
    if (data["volume"] < 0).any():
        raise ValueError("Khối lượng không được âm.")
    membership_file = pd.read_csv(members_path, nrows=1)
    is_history = MEMBERSHIP_COLUMNS.issubset(membership_file.columns)
    if require_point_in_time_membership and not is_history:
        raise ValueError(
            "Đường chạy walk-forward yêu cầu lịch thành phần lịch sử, không nhận snapshot hiện tại. "
            "Dùng data/vn30_snapshot_20261002/vn30_membership_history.csv."
        )
    if is_history:
        history = load_membership_history(members_path)
        members = latest_members(history, data["date"].max())
        required_tickers = set(history["ticker"])
    else:
        members = pd.read_csv(members_path)
        if not {"ticker", "group"}.issubset(members.columns):
            raise ValueError("Tệp thành phần phải có cột ticker và group.")
        if len(members) != 30 or members["ticker"].duplicated().any():
            raise ValueError("Danh sách thành phần phải có đúng 30 mã duy nhất.")
        required_tickers = set(members["ticker"].astype(str).str.upper())
    if not required_tickers.issubset(set(data.loc[data.instrument_type == "stock", "ticker"])):
        absent = sorted(required_tickers - set(data.loc[data.instrument_type == "stock", "ticker"]))
        raise ValueError(
            "Dữ liệu giá thiếu các mã từng thuộc VN30 trong giai đoạn nghiên cứu: "
            f"{absent}. Hãy tải lại toàn bộ hợp nhất thành phần bằng scripts/download_vn30_dataset.py."
        )
    if not {"VN30", "VNINDEX"}.issubset(
        set(data.loc[data.instrument_type == "index", "ticker"])
    ):
        raise ValueError("Dữ liệu phải có cả VN30 và VNINDEX.")
    return data.sort_values(["date", "ticker"]).reset_index(drop=True), members


def _series_metrics(returns: pd.Series) -> dict[str, float]:
    values = returns.to_numpy(dtype=float)
    wealth = np.r_[1.0, np.cumprod(1.0 + values)]
    drawdown = wealth / np.maximum.accumulate(wealth) - 1.0
    return {
        "sessions": int(len(values)),
        "cumulative_return": float(wealth[-1] - 1.0),
        "annualized_volatility": float(np.std(values, ddof=1) * np.sqrt(252)),
        "max_drawdown": float(drawdown.min()),
        "positive_session_fraction": float((values > 0).mean()),
    }


def analyze_market_dataset(
    data_path: str | Path,
    members_path: str | Path,
    lookback: int = 252,
    k: int = 6,
    transaction_cost_bps: float = 25.0,
) -> dict[str, object]:
    """Tạo thống kê mô tả và nghiệm chính xác cho ảnh chụp rổ hiện tại."""
    if lookback < 2 or not 1 <= k <= 6:
        raise ValueError("Cần lookback >= 2 và 1 <= K <= 6.")
    data, members = load_market_dataset(data_path, members_path)
    stock = data.loc[data.instrument_type == "stock"]
    indices = data.loc[data.instrument_type == "index"]
    tickers = tuple(members["ticker"].astype(str))
    index_prices = indices.pivot(index="date", columns="ticker", values="close")
    aligned_index_dates = index_prices[["VN30", "VNINDEX"]].dropna().index
    price_column = "close_adjusted" if "close_adjusted" in stock.columns else "close"
    prices = stock.pivot(index="date", columns="ticker", values=price_column).reindex(
        index=aligned_index_dates, columns=tickers
    )
    returns = prices.pct_change(fill_method=None)
    complete_returns = returns.dropna(how="any")
    if len(complete_returns) < lookback:
        coverage = returns.notna().sum().sort_values()
        raise ValueError(
            f"Chỉ còn {len(complete_returns)} phiên đủ dữ liệu chung, cần {lookback}. "
            f"Mã thiếu lịch sử nhất: {coverage.index[0]} ({coverage.iloc[0]} phiên)."
        )
    window = complete_returns.tail(lookback)

    index_returns = index_prices.pct_change(fill_method=None).reindex(window.index)
    if index_returns[["VN30", "VNINDEX"]].isna().any().any():
        raise ValueError("Dữ liệu chỉ số không bao phủ đủ cửa sổ cổ phiếu được chọn.")

    stock_window_metrics: dict[str, dict[str, float]] = {}
    traded_value = stock.assign(traded_value_proxy=stock["close"] * stock["volume"])
    traded_panel = traded_value.pivot(
        index="date", columns="ticker", values="traded_value_proxy"
    ).reindex(index=window.index, columns=tickers)
    for ticker in tickers:
        stock_window_metrics[ticker] = _series_metrics(window[ticker])
        stock_window_metrics[ticker]["mean_daily_traded_value_proxy_vnd"] = float(
            traded_panel[ticker].mean()
        )

    correlation = window.corr()
    upper_triangle = correlation.where(
        np.triu(np.ones(correlation.shape, dtype=bool), k=1)
    ).stack()
    most_correlated = upper_triangle.sort_values(ascending=False).head(5)
    least_correlated = upper_triangle.sort_values().head(5)

    problem, controls = build_investable_problem(
        window,
        tickers,
        probability_high_volatility=0.5,
        k=k,
        transaction_cost_bps=transaction_cost_bps,
        previous_weights=np.zeros(len(tickers)),
        rebalances_per_year=1,
        ai_enabled=False,
    )
    solve_start = perf_counter()
    bits, objective = exact_solve(problem)
    exact_solve_seconds = perf_counter() - solve_start
    selected = [tickers[i] for i in np.flatnonzero(bits)]
    equal_weight_assets = window.mean(axis=1)

    coverage = (
        stock.groupby("ticker")
        .agg(first_date=("date", "min"), last_date=("date", "max"), sessions=("date", "count"))
        .reindex(tickers)
    )
    return {
        "rows": int(len(data)),
        "date_start": str(data.date.min().date()),
        "date_end": str(data.date.max().date()),
        "stock_count": int(len(tickers)),
        "index_count": 2,
        "members": members.to_dict("records"),
        "member_group_counts": {
            str(key): int(value) for key, value in members["group"].value_counts().items()
        },
        "lookback_sessions": int(lookback),
        "lookback_start": str(window.index.min().date()),
        "lookback_end": str(window.index.max().date()),
        "coverage": [
            {
                "ticker": ticker,
                "first_date": str(coverage.loc[ticker, "first_date"].date()),
                "last_date": str(coverage.loc[ticker, "last_date"].date()),
                "sessions": int(coverage.loc[ticker, "sessions"]),
            }
            for ticker in tickers
        ],
        "index_metrics": {
            index: _series_metrics(index_returns[index])
            for index in ("VN30", "VNINDEX")
        },
        "universe_equal_weight_metrics": _series_metrics(equal_weight_assets),
        "average_pairwise_correlation": float(upper_triangle.mean()),
        "median_pairwise_correlation": float(upper_triangle.median()),
        "most_correlated_pairs": [
            {"pair": f"{left} / {right}", "correlation": float(value)}
            for (left, right), value in most_correlated.items()
        ],
        "least_correlated_pairs": [
            {"pair": f"{left} / {right}", "correlation": float(value)}
            for (left, right), value in least_correlated.items()
        ],
        "top_cumulative_returns": sorted(
            [
                {"ticker": ticker, **metrics}
                for ticker, metrics in stock_window_metrics.items()
            ],
            key=lambda item: item["cumulative_return"],
            reverse=True,
        )[:5],
        "bottom_cumulative_returns": sorted(
            [
                {"ticker": ticker, **metrics}
                for ticker, metrics in stock_window_metrics.items()
            ],
            key=lambda item: item["cumulative_return"],
        )[:5],
        "optimizer": {
            "selected_tickers": selected,
            "k": int(k),
            "risk_aversion": float(problem.risk_aversion),
            "diagonal_shrinkage": float(controls["diagonal_alpha"]),
            "transaction_cost_bps": float(transaction_cost_bps),
            "rebalances_per_year": 1,
            "objective": float(objective),
            "risk_penalty_annual": float(
                problem.risk_aversion * (bits @ problem.covariance @ bits) / k**2
            ),
            "expected_return_reward_annual": float(-problem.mu @ bits / k),
            "transaction_cost_annual": float(problem.annual_transaction_cost(bits)),
            "exact_solve_seconds": float(exact_solve_seconds),
            "annualized_historical_mean_return": float(
                problem.mu @ bits.astype(float) / k
            ),
            "annualized_model_volatility": float(
                np.sqrt(max(bits @ problem.covariance @ bits, 0.0)) / k
            ),
            "exact_combinations_searched": comb(len(tickers), k),
        },
        "qaoa_note": (
            "Không chạy QAOA trên đủ 30 mã: bộ mô phỏng véc-tơ trạng thái có chi phí "
            "tăng theo 2^N; bộ giải chính xác cổ điển dùng được cho N=30, K=6."
        ),
        "data_quality_note": (
            "Lợi suất cổ phiếu dùng OHLC điều chỉnh theo quyền do VCI trả về; giá khớp và "
            "giá trị close×volume dùng OHLC thô từ DNSE. close×volume vẫn là đại diện thanh khoản, "
            "không phải giá trị khớp lệnh xác nhận. Danh sách mô tả là VN30 tại ngày cuối; "
            "walk-forward dùng lịch thành phần theo ngày hiệu lực."
            if "close_adjusted" in data.columns
            else "Tập dữ liệu chưa có cột OHLC điều chỉnh; các số lợi suất chỉ là phân tích thăm dò, "
            "không được dùng làm kết quả backtest đã xử lý sự kiện doanh nghiệp."
        ),
    }


def summarize_qaoa_benchmark(benchmark_path: str | Path) -> dict[str, object] | None:
    """Tóm tắt các bản ghi QAOA tổng hợp để báo cáo không trộn với giá thị trường."""
    path = Path(benchmark_path)
    if not path.exists():
        return None
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records:
        return None
    if any(record.get("data_source") != "synthetic_only" for record in records):
        raise ValueError("Báo cáo này chỉ nhận benchmark đã ghi rõ dữ liệu tổng hợp.")
    mixers = sorted({str(record["mixer"]) for record in records})
    dimensions = sorted({int(record["n"]) for record in records})
    per_mixer: dict[str, object] = {}
    for mixer in mixers:
        mixer_records = [record for record in records if record["mixer"] == mixer]
        gaps = [
            float(record["median_normalized_gap"])
            for record in mixer_records
            if record["median_normalized_gap"] is not None
        ]
        by_dimension = {}
        for n in dimensions:
            subset = [record for record in mixer_records if int(record["n"]) == n]
            subset_gaps = [
                float(record["median_normalized_gap"])
                for record in subset
                if record["median_normalized_gap"] is not None
            ]
            by_dimension[str(n)] = {
                "cases": len(subset),
                "passed": sum(bool(record["meets_case_threshold"]) for record in subset),
                "median_gap": float(np.median(subset_gaps)) if subset_gaps else None,
                "all_runs_feasible": sum(bool(record["all_runs_feasible"]) for record in subset),
            }
        per_mixer[mixer] = {
            "cases": len(mixer_records),
            "passed": sum(bool(record["meets_case_threshold"]) for record in mixer_records),
            "median_gap": float(np.median(gaps)) if gaps else None,
            "all_runs_feasible": sum(bool(record["all_runs_feasible"]) for record in mixer_records),
            "by_dimension": by_dimension,
        }
    first_run = records[0]["runs"][0]
    all_runs = [run for record in records for run in record["runs"]]
    return {
        "path": path,
        "records": len(records),
        "mixers": per_mixer,
        "dimensions": dimensions,
        "k": int(records[0]["k"]),
        "depth": int(first_run["depth"]),
        "seeds": sorted({int(run["seed"]) for run in all_runs}),
        "shots_per_evaluation": int(first_run["shots_per_evaluation"]),
        "max_evaluations": max(int(run["evaluations"]) for run in all_runs),
        "all_runs": len(all_runs),
        "total_elapsed_seconds": float(sum(float(run["elapsed_seconds"]) for run in all_runs)),
    }


def write_market_report(
    summary: dict[str, object],
    output_path: str | Path,
    figure_paths: list[str | Path] | None = None,
    benchmark_path: str | Path | None = None,
) -> Path:
    """Lưu báo cáo nhận định bằng tiếng Việt, kèm giới hạn của nguồn và thiết kế."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    index_metrics = summary["index_metrics"]
    assert isinstance(index_metrics, dict)
    optimizer = summary["optimizer"]
    assert isinstance(optimizer, dict)
    corr_pairs = summary["most_correlated_pairs"]
    least_pairs = summary["least_correlated_pairs"]
    top = summary["top_cumulative_returns"]
    bottom = summary["bottom_cumulative_returns"]
    group_counts = summary["member_group_counts"]
    bank_count = int(group_counts.get("Ngân hàng", 0))
    other_count = int(group_counts.get("Ngành khác", 0))
    row_count = f"{summary['rows']:,}".replace(",", ".")
    combination_count = f"{optimizer['exact_combinations_searched']:,}".replace(",", ".")
    figure_paths = figure_paths or []
    benchmark = summarize_qaoa_benchmark(benchmark_path) if benchmark_path is not None else None

    def percent(value: float) -> str:
        return f"{value:.2%}"

    lines = [
        "# Phân tích dữ liệu VN30 và hai chỉ số tham chiếu",
        "",
        "## Phạm vi dữ liệu",
        "",
        f"- Dữ liệu OHLCV theo ngày: {summary['date_start']} đến {summary['date_end']}.",
        f"- Số dòng: {row_count}; gồm {summary['stock_count']} cổ phiếu và 2 chỉ số.",
        f"- Rổ cổ phiếu được chụp tại ngày 2026-10-02; danh sách ghi nhận {bank_count} mã ngân hàng và {other_count} mã thuộc nhóm ngành khác.",
        f"- Cửa sổ định lượng gần nhất: {summary['lookback_sessions']} phiên hoàn chỉnh, "
        f"từ {summary['lookback_start']} đến {summary['lookback_end']}.",
        "- Giá là OHLCV do nguồn trả về; không có cột giá điều chỉnh, trạng thái quyền/cổ tức, "
        "giá trị giao dịch thực tế hay lịch thành phần chỉ số theo ngày.",
        "",
        "## Câu chuyện dữ liệu qua biểu đồ",
        "",
        "Các hình được dựng lại từ tệp OHLCV và cùng một cửa sổ phân tích với phần định lượng. "
        "Mọi lợi suất cổ phiếu đều dựa trên giá thô nên cần đọc cùng cảnh báo về sự kiện doanh nghiệp. "
        "Hình đối chiếu QAOA dùng bài toán tổng hợp riêng và không được diễn giải thành lợi nhuận thị trường.",
    ]
    figure_notes = [
        (
            "01_coverage.png",
            "Độ phủ theo tháng: các khoảng trắng cho thấy giai đoạn mã chưa có dữ liệu; "
            "nên dùng để thấy giới hạn lịch sử và thiên lệch sống sót.",
        ),
        (
            "02_indices.png",
            "Đường chỉ số được chuẩn hóa về 100 ở đầu kỳ và sụt giảm từ đỉnh, giúp so sánh "
            "xu hướng thị trường với mức lỗ cực đại theo thời gian.",
        ),
        (
            "03_risk_return.png",
            "Bản đồ lợi suất–biến động của 30 mã trong cửa sổ gần nhất; ngôi sao viền đậm là "
            "mã được bộ giải chọn, bong bóng lớn hơn biểu thị giá trị giao dịch xấp xỉ cao hơn.",
        ),
        (
            "04_returns_rank.png",
            "Xếp hạng đủ 30 mã làm lộ rõ độ phân tán lợi suất giá thô; màu vàng đánh dấu nghiệm danh mục.",
        ),
        (
            "05_correlations.png",
            "Ma trận tương quan cho thấy mức độ các mã cùng biến động; nhóm ngân hàng được gom cạnh nhau.",
        ),
        (
            "06_liquidity.png",
            "Thanh khoản xấp xỉ tính bằng giá đóng cửa nhân khối lượng; trục lôgarit giúp đọc cả mã lớn lẫn mã nhỏ.",
        ),
        (
            "07_risk_regimes.png",
            "Biến động trượt 60 phiên của hai chỉ số cho biết rủi ro thị trường thay đổi theo thời gian.",
        ),
        (
            "08_optimizer.png",
            "Tách mục tiêu danh mục thành phạt rủi ro, phần thưởng lợi suất và chi phí vào vị thế; "
            "biểu đồ dưới cho biết lợi suất ước lượng của sáu mã được chọn với tỷ trọng bằng nhau.",
        ),
        (
            "09_qaoa_benchmark.png",
            "Đối chiếu kết quả QAOA p=1 theo kích thước: tỷ lệ đạt ngưỡng, độ lệch so với nghiệm chính xác "
            "và thời gian mô phỏng cổ điển; đây là thí nghiệm trên dữ liệu tổng hợp.",
        ),
    ]
    figure_titles = {
        "01_coverage.png": "Độ phủ dữ liệu theo thời gian",
        "02_indices.png": "Diễn biến hai chỉ số",
        "03_risk_return.png": "Lợi suất và rủi ro theo mã",
        "04_returns_rank.png": "Xếp hạng lợi suất",
        "05_correlations.png": "Tương quan giữa các mã",
        "06_liquidity.png": "Thanh khoản xấp xỉ",
        "07_risk_regimes.png": "Chế độ rủi ro thị trường",
        "08_optimizer.png": "Cấu phần nghiệm danh mục",
        "09_qaoa_benchmark.png": "Kết quả đối chiếu QAOA",
    }
    by_name = {Path(item).name: Path(item) for item in figure_paths}
    for filename, caption in figure_notes:
        image_path = by_name.get(filename)
        if image_path is None:
            continue
        try:
            image_link = image_path.resolve().relative_to(path.parent.resolve())
        except ValueError:
            import os

            image_link = Path(os.path.relpath(image_path.resolve(), path.parent.resolve()))
        lines.extend(
            [
                "",
                f"### {figure_titles[filename]}",
                "",
                f"![{figure_titles[filename]}]({image_link.as_posix()})",
                "",
                caption,
            ]
        )
    lines.extend(
        [
            "",
            "## Kiểm tra V1 trên bài toán tổng hợp nhỏ",
            "",
            "Lượt chạy minh họa dùng N=8, K=6, hạt giống 20261012; xác suất trạng thái biến động 0,70 chỉ là giá trị đặt trước, không phải dự báo. V1 cố định mức co rút α=0,40, dùng λ=7,60, phí giả định 25 điểm cơ bản và 12 lần tái cân bằng năm hóa.",
            "",
            "| Bộ giải | Kết quả |",
            "|---|---|",
            "| Duyệt chính xác | SYN00, SYN02, SYN03, SYN04, SYN06, SYN07; điểm mục tiêu -0,00698667 |",
            "| Tham lam | Tìm cùng danh mục với nghiệm chính xác |",
            "| Tôi luyện | Tìm cùng danh mục với nghiệm chính xác |",
            "| QAOA, bộ trộn X | Tìm đúng nghiệm ở 2/3 hạt giống |",
            "| QAOA, bộ trộn XY | 0/3 lượt đúng nghiệm; độ lệch trung vị 24,93% |",
            "",
            "Phí làm điểm mục tiêu tăng 0,02000000 so với trường hợp không phí nhưng không đổi danh mục trên bài toán này. Kết quả chỉ kiểm tra đường đi của thuật toán trên dữ liệu sinh giả lập; quy mô nhỏ và ba hạt giống không chứng minh hiệu quả đầu tư hay ưu thế lượng tử.",
            "",
            "## Kết quả đối chiếu thuật toán trên dữ liệu tổng hợp",
            "",
            "Đây là thí nghiệm kỹ thuật tách biệt với dữ liệu VN30, không phải lợi nhuận thị trường. "
            "Mỗi cấu hình được so với nghiệm chính xác; cấu hình đạt khi cả ba lượt có nghiệm khả thi "
            "và trung vị độ lệch chuẩn hóa không quá 5%.",
            "",
        ]
    )
    if benchmark is not None:
        benchmark_mixers = benchmark["mixers"]
        assert isinstance(benchmark_mixers, dict)
        lines.extend(
            [
                f"- Cấu hình: QAOA p={benchmark['depth']}, K={benchmark['k']}, N={', '.join(map(str, benchmark['dimensions']))}; "
                f"hạt giống {', '.join(map(str, benchmark['seeds']))}, {benchmark['shots_per_evaluation']} mẫu mỗi đánh giá, "
                f"tối đa {benchmark['max_evaluations']} đánh giá mỗi lượt.",
                f"- Tổng cộng {benchmark['records']} cấu hình ({benchmark['all_runs']} lượt tối ưu), "
                f"thời gian mô phỏng tích lũy {benchmark['total_elapsed_seconds']:.2f} giây. "
                "Đây là thời gian mô phỏng cổ điển, không phải thời gian QPU.",
                "",
                "| Bộ trộn | Đạt / số bài | Độ lệch trung vị | Có nghiệm khả thi ở cả ba lượt |",
                "|---|---:|---:|---:|",
            ]
        )
        for mixer in ("X", "XY"):
            result = benchmark_mixers.get(mixer)
            if not isinstance(result, dict):
                continue
            gap = "—" if result["median_gap"] is None else percent(result["median_gap"])
            lines.append(
                f"| {mixer} | {result['passed']} / {result['cases']} | {gap} | "
                f"{result['all_runs_feasible']} / {result['cases']} |"
            )
        lines.extend(
            [
                "",
                "### Kết quả theo kích thước",
                "",
                "| N | X đạt | Độ lệch trung vị X | XY đạt | Độ lệch trung vị XY |",
                "|---:|---:|---:|---:|---:|",
            ]
        )
        x_results = benchmark_mixers.get("X", {})
        xy_results = benchmark_mixers.get("XY", {})
        for n in benchmark["dimensions"]:
            x_case = x_results.get("by_dimension", {}).get(str(n), {})
            xy_case = xy_results.get("by_dimension", {}).get(str(n), {})
            x_gap = "—" if x_case.get("median_gap") is None else percent(x_case["median_gap"])
            xy_gap = "—" if xy_case.get("median_gap") is None else percent(xy_case["median_gap"])
            lines.append(
                f"| {n} | {x_case.get('passed', 0)} / {x_case.get('cases', 0)} | {x_gap} | "
                f"{xy_case.get('passed', 0)} / {xy_case.get('cases', 0)} | {xy_gap} |"
            )
        lines.extend(
            [
                "",
                "Kết quả tổng thể của cả hai bộ trộn thấp hơn ngưỡng đã đăng ký 29/36. Bộ trộn XY giữ ràng buộc số mã "
                "trong các mẫu đã đo nhưng chất lượng mục tiêu chưa đạt; bộ trộn X giảm mạnh khi tăng N. "
                "Chưa có lượt chạy QPU thật và chưa có bằng chứng ưu thế lượng tử.",
                "",
                f"- Bản ghi chi tiết có từng hạt giống, tỷ lệ khả thi, khoảng cách, góc và thời gian: `{benchmark['path']}`.",
            ]
        )
    else:
        lines.append("Chưa có tệp benchmark tổng hợp để lập bảng đối chiếu.")
    lines.extend(
        [
            "",
            "## Hiệu suất quan sát trong cửa sổ gần nhất",
            "",
            "Các lợi suất bên dưới là thay đổi giá đóng cửa, trước chi phí. Chuỗi 30 mã là danh mục "
            "trọng số đều tái cân bằng mỗi phiên. Đây là thống kê mô tả trên cửa sổ dùng để ước lượng "
            "đầu vào, không phải kết quả ngoài mẫu của chiến lược.",
            "",
            "| Chuỗi | Lợi suất gộp | Biến động năm hóa | Sụt giảm tối đa | Tỷ lệ phiên tăng |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for name in ("VN30", "VNINDEX"):
        metrics = index_metrics[name]
        lines.append(
            f"| {name} | {percent(metrics['cumulative_return'])} | "
            f"{percent(metrics['annualized_volatility'])} | "
            f"{percent(metrics['max_drawdown'])} | "
            f"{percent(metrics['positive_session_fraction'])} |"
        )
    universe = summary["universe_equal_weight_metrics"]
    assert isinstance(universe, dict)
    lines.append(
        f"| Tái cân bằng đều 30 mã mỗi phiên | {percent(universe['cumulative_return'])} | "
        f"{percent(universe['annualized_volatility'])} | "
        f"{percent(universe['max_drawdown'])} | "
        f"{percent(universe['positive_session_fraction'])} |"
    )
    lines.extend(
        [
            "",
            "## Nhận định về cấu trúc dữ liệu",
            "",
            f"- Rổ có {bank_count} mã ngân hàng trên 30 mã "
            f"({bank_count / 30:.1%} theo số mã). Đây là mức tập trung đáng lưu ý "
            "khi chọn sáu cổ phiếu; tối ưu hóa tương quan và rủi ro riêng có ý nghĩa thực tế.",
            f"- Trung bình tương quan cặp là {summary['average_pairwise_correlation']:.3f}; "
            f"trung vị là {summary['median_pairwise_correlation']:.3f}. Các mã không độc lập, "
            "nên chỉ chọn theo lợi suất lịch sử có thể giữ lại nhiều rủi ro chung.",
            "- Số phiên theo mã không đồng nhất; một số mã gia nhập thị trường muộn hơn. "
            "Bộ tính toán chỉ dùng các ngày có lợi suất hợp lệ đồng thời cho đủ 30 mã.",
            "",
            "### Năm cặp tương quan cao nhất",
            "",
            "| Cặp mã | Tương quan |",
            "|---|---:|",
        ]
    )
    for item in corr_pairs:
        lines.append(f"| {item['pair']} | {item['correlation']:.3f} |")
    lines.extend(["", "### Năm cặp tương quan thấp nhất", "", "| Cặp mã | Tương quan |", "|---|---:|"])
    for item in least_pairs:
        lines.append(f"| {item['pair']} | {item['correlation']:.3f} |")
    lines.extend(
        [
            "",
            "### Mã tăng/giảm mạnh nhất theo giá đóng cửa thô",
            "",
            "Các thứ hạng này chưa điều chỉnh quyền và cổ tức; cần kiểm tra sự kiện doanh nghiệp "
            "trước khi diễn giải là hiệu suất đầu tư.",
            "",
            "| Mã | Lợi suất gộp | Biến động năm hóa | Sụt giảm tối đa | GTGD bình quân xấp xỉ (tỷ đồng/ngày) |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for item in list(top) + list(bottom):
        lines.append(
            f"| {item['ticker']} | {percent(item['cumulative_return'])} | "
            f"{percent(item['annualized_volatility'])} | {percent(item['max_drawdown'])} | "
            f"{item['mean_daily_traded_value_vnd'] / 1e9:,.1f} |"
        )
    lines.extend(
        [
            "",
            "## Bài toán danh mục trên dữ liệu thật",
            "",
            f"- Nghiệm chính xác chọn: **{', '.join(optimizer['selected_tickers'])}** "
            f"(N=30, K={optimizer['k']}). Duyệt hết {combination_count} "
            f"tổ hợp khả thi trong {optimizer['exact_solve_seconds']:.3f} giây trên máy hiện tại.",
            f"- Đầu vào: lợi suất ngày trong cửa sổ trên; lợi suất trung bình và hiệp phương sai "
            f"năm hóa; co rút đường chéo α={optimizer['diagonal_shrinkage']:.2f}; "
            f"λ={optimizer['risk_aversion']:.1f}; phí giả định {optimizer['transaction_cost_bps']:.0f} "
            "điểm cơ bản cho một lần mua từ tiền mặt, chưa mô phỏng tái cân bằng định kỳ.",
            f"- Ước lượng lịch sử trong mẫu của danh mục chọn: lợi suất trung bình "
            f"{percent(optimizer['annualized_historical_mean_return'])}/năm, "
            f"biến động mô hình {percent(optimizer['annualized_model_volatility'])}/năm. "
            "Đây là tham số đầu vào/đầu ra của mục tiêu, không phải dự báo hay bằng chứng sinh lời.",
            f"- {summary['qaoa_note']}",
            "",
            "## Chất lượng dữ liệu và giới hạn kết luận",
            "",
            "1. Rổ thành phần được chụp tại một ngày rồi áp ngược lên lịch sử; kiểm định lịch sử như vậy có "
            "thiên lệch sống sót. Cần lịch thành phần theo ngày hiệu lực từ HOSE để khắc phục.",
            "2. Nguồn trả OHLCV chứ không xác nhận giá đóng cửa điều chỉnh. Lợi suất cổ phiếu có thể "
            "bị gián đoạn bởi cổ tức, chia tách hoặc quyền mua. Không nên công bố CAGR, Sharpe hay "
            "tuyên bố chiến lược thắng thị trường từ bộ này.",
            "3. GTGD xấp xỉ trong báo cáo được tính bằng giá đóng cửa nhân khối lượng, không thay thế "
            "trường giá trị khớp lệnh chính thức.",
            "4. Lợi thế kỹ thuật hiện chứng minh được là: cùng một hàm mục tiêu rủi ro–lợi nhuận có "
            "chi phí, bộ giải chính xác cổ điển tìm nghiệm toàn cục cho VN30/K=6; QAOA vẫn cần được "
            "đối chiếu trên bài toán rút gọn và cùng cửa sổ dữ liệu.",
            "",
            "## Nguồn và cách tái lập",
            "",
            f"- Kết quả đối chiếu QAOA trên dữ liệu tổng hợp: `{benchmark['path']}`." if benchmark is not None else "- Không có tệp kết quả QAOA tổng hợp.",
            "- Bộ nạp: kho GitHub nguyenthdat/vnstock-data, mã nguồn ghim trong "
            "requirements-data.txt; gọi stock_historical_data theo ngày.",
            "- Dịch vụ lịch sử mà bộ kết nối gọi: DNSE chart API.",
            "- Danh sách rổ ngày 02/10/2026: "
            "[HODL.VN](https://www.hodl.vn/bai-hoc/vn30-gom-nhung-ma-nao); "
            "đây là bản chụp bên thứ ba, không phải tệp lịch sử thành phần HOSE.",
            "- Tệp gốc, phạm vi ngày, số dòng và mã băm nằm trong "
            "data/vn30_snapshot_20261002/manifest.json.",
            "- Mã dựng biểu đồ: `agqo/plots.py`; mã phân tích và ghi báo cáo: `agqo/market_data.py`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def summary_json(summary: dict[str, object]) -> str:
    """Định dạng kết quả dạng JSON dùng được trong lệnh dòng lệnh."""
    return json.dumps(summary, ensure_ascii=False, indent=2, default=str)
