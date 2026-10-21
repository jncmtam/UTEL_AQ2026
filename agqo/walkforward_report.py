"""Tạo báo cáo tiếng Việt từ kết quả JSON walk-forward đã lưu."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from .walkforward_plots import SHORT


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _money(value: float) -> str:
    return f"{value / 1_000_000:.2f} triệu"


def _optional_pct(value: float | None) -> str:
    return "—" if value is None or not math.isfinite(float(value)) else _pct(float(value))


def _optional_num(value: float | None, digits: int = 2) -> str:
    return "—" if value is None or not math.isfinite(float(value)) else f"{float(value):.{digits}f}"


def render_walkforward_report(result: dict[str, object]) -> str:
    ai = result["ai"]
    ai_monthly = ai["metrics"]["monthly_signal_metrics"]
    portfolio = result["portfolio"]
    performance = portfolio["performance"]
    qaoa = result["qaoa"]
    config = result["config"]
    guidance = result.get("agqo_guidance", {"enabled": False, "decisions": []})
    agqo_name = "AGQO LLM→QAOA / chính sách thích nghi / 12 mã thanh khoản cao"
    policy_names = guidance.get("policy_strategy_names", {})
    llm_models = sorted({record.get("model") for record in guidance.get("decisions", []) if record.get("model")})
    token_usage = guidance.get("recorded_token_usage", {})
    policy_runtime_note = (
        "Lưới đối chứng AGQO chạy "
        f"{sum(qaoa['quality_summary'][f'POLICY:{policy_id}']['seed_runs'] for policy_id in policy_names)} "
        f"lượt QAOA trên 12 chính sách, tốn "
        f"{qaoa['solver_runtime_seconds']['policy_catalog_qaoa_total']:.3f} giây mô phỏng CPU "
        "(không tính thời gian chờ LLM)."
        if guidance.get("enabled") else ""
    )
    lines = [
        "# Kiểm định ngoài mẫu: AI, QAOA và danh mục VN30",
        "",
        f"**Khoảng đo danh mục:** {portfolio['entry_dates'][0]} đến {portfolio['exit_dates'][-1]} · "
        f"**Số kỳ:** {portfolio['period_count']} · **Vốn mô phỏng:** "
        f"{_money(portfolio['capital_vnd'])} · **Phí:** {config['fee_bps']:.0f} điểm cơ bản mỗi chiều.",
        "",
        "> Đây là thí nghiệm nghiên cứu trên giá OHLCV thô, dùng ảnh chụp thành phần VN30 ngày 02/10/2026. "
        "Chưa có điều chỉnh cổ tức/quyền hoặc lịch sử thành phần theo ngày. Kết quả chưa đủ căn cứ để "
        "tuyên bố chiến lược có thể tạo lợi nhuận thật.",
        "",
        "## Kết luận điều hành",
        "",
        f"- Mô hình AI chọn C = {ai['chosen_c']:.2g} sau khi so log-loss trên "
        f"{ai['validation_samples']} quan sát xác nhận; tỷ lệ nhãn biến động cao là "
        f"{_pct(ai['validation_high_volatility_rate'])}.",
        f"- Trên {ai['metrics']['n_daily_overlapping_forecasts']} dự báo ngày ngoài mẫu, điểm Brier là "
        f"{ai['metrics']['brier_score']:.3f}, cao hơn mức nền mở rộng "
        f"{ai['metrics']['expanding_base_rate_brier']:.3f}; kỹ năng Brier so với nền là "
        f"{_pct(ai['metrics']['brier_skill_vs_expanding_base_rate'])}. Log-loss AI "
        f"{ai['metrics']['log_loss']:.3f} cũng kém mức nền "
        f"{ai['metrics']['expanding_base_rate_log_loss']:.3f}. Nhãn 21 phiên chồng lấn, nên số này "
        "không tương đương số quan sát độc lập.",
        f"- Ở tần suất tái cân bằng, điểm Brier là {ai_monthly['brier_score']:.3f} so với "
        f"{ai_monthly['expanding_base_rate_brier']:.3f} của dự báo nền trên {ai_monthly['n']} tín hiệu tháng; "
        f"kỹ năng so với nền là {_pct(ai_monthly['brier_skill_vs_expanding_base_rate'])}.",
        f"- Tổ hợp AI điều chỉnh λ và α cùng nghiệm chính xác trên toàn bộ mã đủ điều kiện đạt CAGR ròng "
        f"{_pct(performance['AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện']['metrics']['cagr'])}, "
        f"Sharpe {performance['AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện']['metrics']['sharpe']:.2f}. "
        f"Đối chứng Ledoit–Wolf cao hơn với CAGR "
        f"{_pct(performance['Ledoit–Wolf, λ=5 / nghiệm chính xác / toàn bộ mã đủ điều kiện']['metrics']['cagr'])}; "
        "vì vậy kết quả chưa chứng minh AI là thành phần tạo thêm giá trị.",
        f"- Trên 12 mã thanh khoản cao, QAOA X p=1 đạt sai lệch mục tiêu chuẩn hóa trung bình "
        f"{_pct(qaoa['quality_summary']['X_p1']['mean_normalized_regret'])} và đạt sai lệch không quá 5% ở "
        f"{qaoa['quality_summary']['X_p1']['instances_with_regret_le_5_percent']}/"
        f"{qaoa['quality_summary']['X_p1']['monthly_instances']} kỳ; p=2 đạt "
        f"{qaoa['quality_summary']['X_p2']['instances_with_regret_le_5_percent']}/"
        f"{qaoa['quality_summary']['X_p2']['monthly_instances']}. Đây là kết quả mô phỏng cổ điển, chưa chạy QPU.",
        "- Trên cùng 12 mã, bộ giải chính xác cổ điển nhanh hơn mô phỏng QAOA; hiện chưa có bằng chứng ưu thế lượng tử.",
        (
            f"- Bộ điều khiển AGQO dùng {', '.join(llm_models) or 'LLM trên Modal'} để chọn chính sách ở "
            f"{guidance['decision_count']} tín hiệu; đã ghi nhận {token_usage.get('total_tokens', 0):,} token "
            "trong các phản hồi đã lưu. Kết quả được đo cùng các đối chứng bên dưới."
            if guidance.get("enabled")
            else "- Lượt này chưa bật LLM; các hàng bên dưới là đối chứng hiện tại để so với AGQO sau khi chạy Modal."
        ),
        "",
        "## 1. Thiết kế và chia thời gian",
        "",
        "| Giai đoạn | Mốc | Cách sử dụng |",
        "|---|---|---|",
        f"| Huấn luyện ban đầu | đến {ai['training_end']} | Chuẩn hóa, xác lập ngưỡng phân vị 70% và khớp hồi quy logistic |",
        f"| Xác nhận | {ai['validation_start']}–{ai['validation_end']} | Chọn C theo log-loss; nhãn được chặn 21 phiên trước ranh giới |",
        f"| Kiểm tra khóa trước | tín hiệu từ {config['test_start']} | Cố định C/ngưỡng, sau đó mở rộng huấn luyện chỉ bằng nhãn đã trưởng thành |",
        f"| Danh mục ngoài mẫu | {portfolio['entry_dates'][0]}–{portfolio['exit_dates'][-1]} | Tín hiệu cuối tháng, giao dịch ở phiên kế tiếp, nắm giữ đến lần vào lệnh tháng kế tiếp |",
        "",
        f"Ngưỡng biến động cao được ước lượng là {_pct(ai['threshold_annualized_volatility'])} năm hóa. "
        f"Tập huấn luyện ban đầu có {ai['training_samples_before_validation']} nhãn trưởng thành; "
        f"tập xác nhận có {ai['validation_samples']} quan sát, trong đó "
        f"{_pct(ai['validation_high_volatility_rate'])} là nhãn biến động cao. "
        "Đặc trưng AI chỉ lấy từ VN30: biến động 20/60/120 phiên, lợi suất tích lũy 20/60 phiên và tỷ số biến động 20/120. "
        "Mô hình được khớp lại tại từng ngày tín hiệu bằng các nhãn tương lai đã đủ 21 phiên.",
        "",
        "| C | Log-loss tập xác nhận |",
        "|---:|---:|",
    ]
    for c, loss in sorted(
        ((float(c), value) for c, value in ai["validation_log_loss_by_c"].items()),
        key=lambda item: item[0],
    ):
        lines.append(f"| {c:g} | {loss:.3f} |")
    lines += [
        "",
        f"Ở các tín hiệu tháng, tỷ lệ nhãn biến động cao thực tế là "
        f"{_pct(ai_monthly['observed_high_volatility_rate'])}, trong khi xác suất AI trung bình là "
        f"{_pct(ai_monthly['mean_forecast_probability'])}. Đây là thước đo sát tần suất giao dịch hơn, "
        "nhưng số quan sát vẫn nhỏ.",
        "",
        "![Xác suất AI và nhãn biến động cao](figures/walkforward/01_ai_regime_walkforward.png)",
        "",
        "## 2. Hiệu quả tài chính trong kỳ kiểm tra",
        "",
        "Lợi suất được tính từ giá mở cửa phiên kế tiếp đến giá mở cửa lần tái cân bằng kế tiếp. "
        "Phí được trừ ở mỗi lần mua và bán; lệnh bị giới hạn theo ADTV. Sharpe giả định lãi suất phi rủi ro bằng 0.",
        "",
        "| Phương pháp | CAGR ròng | Biến động năm hóa | Sharpe | Sụt giảm tối đa | Giá trị cuối kỳ từ 100 triệu | Chi phí giao dịch | Doanh số hai chiều TB/kỳ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    table_order = [
        "VN30",
        "VN-Index",
        "Cố định λ=5, α=0,40 / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI chỉ điều chỉnh λ / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI chỉ điều chỉnh α / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "Ledoit–Wolf, λ=5 / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=2, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn XY / 12 mã thanh khoản cao",
    ]
    if guidance.get("enabled"):
        table_order.append(agqo_name)
    for name in table_order:
        item = performance[name]
        metric = item["metrics"]
        exec_summary = item["execution_summary"]
        ending = config["capital_vnd"] * metric["ending_value_per_unit"]
        cost = _money(exec_summary["total_transaction_cost_vnd"]) if exec_summary else "—"
        turnover = _pct(exec_summary["mean_executed_turnover"]) if exec_summary else "—"
        lines.append(
            f"| {SHORT[name]} | {_pct(metric['cagr'])} | "
            f"{_pct(metric['annualized_volatility'])} | {metric['sharpe']:.2f} | "
            f"{_pct(metric['max_drawdown'])} | {_money(ending)} | {cost} | {turnover} |"
        )
    lines += [
        "",
        "### Chỉ số giao dịch bổ sung",
        "",
        "| Phương pháp | Sortino | Calmar | VaR tháng 95% | CVaR tháng 95% | Hệ số lợi nhuận | Tỷ lệ tháng dương |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in table_order:
        metric = performance[name]["metrics"]
        lines.append(
            f"| {SHORT[name]} | {_optional_num(metric.get('sortino'))} | "
            f"{_optional_num(metric.get('calmar'))} | {_optional_pct(metric.get('monthly_var_95'))} | "
            f"{_optional_pct(metric.get('monthly_cvar_95'))} | "
            f"{_optional_num(metric.get('profit_factor'))} | "
            f"{_optional_pct(metric.get('positive_month_fraction'))} |"
        )
    lines += [
        "",
        "![Đường vốn ngoài mẫu sau phí](figures/walkforward/02_net_equity_curves.png)",
        "",
        "![Lợi nhuận và rủi ro](figures/walkforward/04_risk_return_tradeoff.png)",
        "",
        "### Đối chiếu lợi nhuận vượt VN30",
        "",
        "Khoảng tin cậy lấy mẫu khối dùng chênh lệch lợi nhuận theo tháng; báo cả khối 3 và 6 tháng vì chỉ có 16 kỳ.",
        "",
        "| Phương pháp | Lợi nhuận vượt năm hóa | Khoảng 95% (khối 3 tháng) | Khoảng 95% (khối 6 tháng) |",
        "|---|---:|---:|---:|",
    ]
    comparison_names = [
        "Cố định λ=5, α=0,40 / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện",
        "AI điều chỉnh λ và α / nghiệm chính xác / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=2, bộ trộn X / 12 mã thanh khoản cao",
        "AI + QAOA p=1, bộ trộn XY / 12 mã thanh khoản cao",
    ]
    if guidance.get("enabled"):
        comparison_names.append(agqo_name)
    for name in comparison_names:
        compare = portfolio["comparisons"][f"{name} vs VN30"]
        ci3 = compare["active_return_confidence_interval"]
        ci6 = compare["active_return_confidence_interval_block6"]
        lines.append(
            f"| {SHORT[name]} | {_pct(compare['annualized_mean_active_return'])} | "
            f"[{_pct(ci3['lower'])}, {_pct(ci3['upper'])}] | "
            f"[{_pct(ci6['lower'])}, {_pct(ci6['upper'])}] |"
        )
    ai_full = performance["AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện"]
    ledoit = performance["Ledoit–Wolf, λ=5 / nghiệm chính xác / toàn bộ mã đủ điều kiện"]
    qaoa_x = performance["AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao"]
    vn30 = performance["VN30"]
    ai_cost = ai_full["execution_summary"]
    qaoa_cost = qaoa_x["execution_summary"]
    lines += [
        "",
        "### Diễn giải tài chính",
        "",
        f"- Trong cửa sổ này, danh mục AI trên toàn bộ mã đủ điều kiện tạo {_pct(ai_full['metrics']['cagr'])} CAGR ròng "
        f"so với {_pct(vn30['metrics']['cagr'])} của VN30. Nhưng Ledoit–Wolf đạt {_pct(ledoit['metrics']['cagr'])}, "
        "nên phần vượt trội không thể quy riêng cho AI.",
        "- Bộ phân loại AI không thắng dự báo tỷ lệ nền về Brier và log-loss. Lợi suất danh mục cao hơn không chứng minh "
        "AI đã dự báo đúng chế độ; thay đổi mức co rút, nhiễu ước lượng, thành phần sống sót và diễn biến thị trường "
        "đều có thể giải thích khác biệt.",
        f"- QAOA X p=1 trên 12 mã tạo {_pct(qaoa_x['metrics']['cagr'])} CAGR ròng và "
        f"Sharpe {qaoa_x['metrics']['sharpe']:.2f}, thấp hơn VN30 trong kỳ này. Mức doanh số hai chiều trung bình "
        f"{_pct(qaoa_cost['mean_executed_turnover'])} so với {_pct(ai_cost['mean_executed_turnover'])} của danh mục "
        "AI toàn rổ làm chi phí giao dịch cao hơn.",
        f"- Với vốn 100 triệu đồng, lệnh lớn nhất của QAOA X bằng "
        f"{_pct(qaoa_cost['max_requested_adtv_participation'])} ADTV, thấp hơn giới hạn thấp nhất 1%; "
        "sức chứa không phải nút thắt ở quy mô vốn giả định này. Phí và lựa chọn mã là yếu tố kinh tế đáng quan tâm hơn.",
        "- Khoảng tin cậy của các cấu hình QAOA so với VN30 đều cắt qua 0; 16 kỳ và các lựa chọn cấu hình song song "
        "không đủ để khẳng định ưu thế thống kê.",
        f"- Tổ hợp AI toàn rổ có lợi nhuận vượt VN30 năm hóa "
        f"{_pct(portfolio['comparisons']['AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện vs VN30']['annualized_mean_active_return'])}; "
        "khoảng lấy mẫu khối trong cửa sổ này dương, nhưng 16 kỳ, thiên lệch sống sót và việc so nhiều cấu hình "
        "khiến kết quả chưa đủ làm bằng chứng đầu tư.",
        f"- Tỷ trọng mục tiêu thuộc nhóm ngân hàng trung bình là "
        f"{_pct(portfolio['selection_summary']['AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện']['bank_weight_mean'])} "
        f"ở nghiệm AI toàn rổ và "
        f"{_pct(portfolio['selection_summary']['AI + QAOA p=1, bộ trộn X / 12 mã thanh khoản cao']['bank_weight_mean'])} "
        "ở QAOA X. VIC xuất hiện ở "
        f"{portfolio['selection_summary']['AI điều chỉnh λ và α / nghiệm chính xác / toàn bộ mã đủ điều kiện']['ticker_selection_frequency'][0]['selected_months']}/16 "
        "kỳ của nghiệm AI toàn rổ; mức tập trung này cần được kiểm soát.",
        *(
            [
                f"- AGQO LLM→QAOA đạt CAGR {_pct(performance[agqo_name]['metrics']['cagr'])}, "
                f"Sharpe {performance[agqo_name]['metrics']['sharpe']:.2f}, "
                f"Sortino {_optional_num(performance[agqo_name]['metrics'].get('sortino'))} và "
                f"sụt giảm tối đa {_pct(performance[agqo_name]['metrics']['max_drawdown'])}; "
                f"LLM chọn {guidance['decision_count']} cấu hình theo insight đã lưu. Đây là kết quả cần đối chiếu, "
                "không phải bằng chứng LLM tốt hơn các phương pháp hiện tại."
            ]
            if guidance.get("enabled") else []
        ),
        "",
        "![Độ nhạy phí và sức chứa](figures/walkforward/05_cost_and_capacity.png)",
        "",
        "![Mức tiếp xúc ngành và tần suất chọn mã](figures/walkforward/06_exposure_and_holdings.png)",
        "",
        "## 3. QAOA được thiết kế và đo như thế nào",
        "",
        "| Thành phần | Thiết lập |",
        "|---|---|",
        f"| Mã hóa | 1 qubit cho mỗi ứng viên trong 12 mã có ADTV 20 phiên cao nhất; tổng cộng {qaoa['n_qubits']} qubit |",
        f"| Ràng buộc | Chọn đúng K={qaoa['k']} mã; có {qaoa['feasible_combinations_per_month']} tổ hợp khả thi |",
        "| Hàm mục tiêu | Giảm phương sai danh mục theo λ, thưởng lợi nhuận trung bình ước lượng; đường cơ sở dùng AI, AGQO để LLM chọn λ và α trong danh mục |",
        "| Bộ trộn X | Chồng chập đều, cộng hạng phạt để giữ K; trạng thái có 2^12 = 4.096 chuỗi bit |",
        "| Bộ trộn XY | Khởi tạo một chuỗi khả thi và dùng trao đổi lân cận trên vòng để bảo toàn K |",
        "| Độ sâu | p=1 cơ sở; p=2 kiểm tra độ sâu; mỗi lớp có 66 tương tác cặp do ma trận hiệp phương sai dày |",
        f"| Tối ưu góc | COBYLA, tối đa {config['qaoa_max_evaluations']} lần đánh giá, {config['qaoa_shots']} mẫu/lần |",
        f"| Lặp lại | Hạt giống {', '.join(map(str, config['qaoa_seeds']))}; chọn mẫu khả thi có điểm tốt nhất trong ba lượt |",
        "| Đối chứng | Duyệt chính xác mọi tổ hợp N=12,K=6, dùng cùng μ, Σ, λ, α |",
        "",
        (
            "AGQO tối ưu λ(xᵀΣαx)/K² − (μᵀx)/K cộng phí đổi danh mục năm hóa 12 × phí × "
            "Σᵢ|xᵢ/K − wᵢ_trước|; w trước là danh mục mục tiêu AGQO kỳ liền trước. "
            "Đường cơ sở giữ nguyên hàm mục tiêu cũ và tính phí ở lớp mô phỏng giao dịch. "
            "Bộ trộn X cộng hạng phạt bình phương (Σxᵢ−K)²; XY bảo toàn số mã được chọn. "
            "Mỗi nghiệm được chấm lại bằng đúng hàm mục tiêu của nhánh trước khi so với nghiệm chính xác."
            if guidance.get("enabled") else
            "QUBO dùng mục tiêu λ(xᵀΣαx)/K² − (μᵀx)/K; phí giao dịch được đo ở lớp mô phỏng danh mục. "
            "Bộ trộn X cộng hạng phạt bình phương (Σxᵢ−K)²; XY bảo toàn số mã được chọn. "
            "Mỗi nghiệm được chấm lại bằng hàm mục tiêu danh mục gốc trước khi so với chuẩn chính xác."
        ),
        "",
        "| Cấu hình | Kỳ đạt sai lệch ≤5% | Sai lệch TB | Kỳ dự phòng nghiệm chính xác | Có mẫu khả thi trong lượt tối ưu | Xác suất khả thi TB của seed được chọn | Thời gian CPU tổng 48 lượt |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    qaoa_rows = [("X_p1", "X, p=1"), ("X_p2", "X, p=2"), ("XY_p1", "XY, p=1")]
    if guidance.get("enabled"):
        qaoa_rows.append(("AGQO", "AGQO LLM→QAOA"))
    for key, label in qaoa_rows:
        summary = qaoa["quality_summary"][key]
        lines.append(
            f"| {label} | {summary['instances_with_regret_le_5_percent']}/"
            f"{summary['monthly_instances']} | {_optional_pct(summary['mean_normalized_regret'])} | "
            f"{summary.get('exact_fallback_months', 0)} | "
            f"{_optional_pct(summary['feasible_seed_run_fraction'])} | "
            f"{_optional_pct(summary['mean_best_seed_feasible_probability'])} | "
            f"{summary['total_cpu_simulation_seconds']:.3f} giây |"
        )
    if guidance.get("enabled"):
        lines += [
            "",
            "### LLM đã đọc insight nào và chọn cấu hình ra sao?",
            "",
            "LLM chỉ nhận số liệu đến ngày tín hiệu: xác suất biến động từ mô hình học máy, biến động và xu hướng VN30, "
            "tương quan giữa cổ phiếu, độ phân tán lợi suất, tỷ lệ ngân hàng, thanh khoản ước tính và kết quả các kỳ đã đóng. "
            "Đầu ra bị giới hạn vào danh mục chính sách; λ, α, bộ trộn, độ sâu và số mẫu đều được kiểm tra lại trong mã trước khi chạy QAOA.",
            "",
            "| Ngày tín hiệu | Mã chính sách | λ | α | Bộ trộn | p | Số mẫu | Kỳ lịch sử | Lợi suất 3 kỳ đã khép | Sharpe lịch sử | Mức giảm lịch sử | Insight được gắn | Tin cậy | Sai lệch nghiệm |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
        ]
        rationale_lines = []
        for record in guidance["decisions"]:
            policy = record["policy"]
            past = record["context"].get("past_completed_policy_benchmarks", {}).get(
                policy["policy_id"], {}
            )
            run = next(
                (row for row in qaoa["monthly_runs"]
                 if row["variant"] == "AGQO" and row["signal_date"] == record["signal_date"]),
                {},
            )
            lines.append(
                f"| {record['signal_date']} | {policy['policy_id']} | {policy['risk_aversion']:.1f} | "
                f"{policy['shrinkage']:.2f} | {policy['mixer']} | {policy['depth']} | {policy['shots']} | "
                f"{past.get('completed_periods', 0)} | "
                f"{_optional_pct(past.get('trailing_3_period_net_return'))} | "
                f"{_optional_num(past.get('annualized_sharpe_to_date'))} | "
                f"{_optional_pct(past.get('max_drawdown_to_date'))} | "
                f"{', '.join(record['decision']['insight_codes'])} | "
                f"{record['decision']['confidence']:.0%} | "
                f"{_optional_pct(run.get('normalized_objective_regret'))} |"
            )
            rationale_lines.append(
                f"- **{record['signal_date']}** {record['decision']['rationale']} "
                f"Ghi chú rủi ro: {record['decision']['risk_note']}"
            )
        lines += ["", "**Lý do và ghi chú rủi ro do LLM trả về:**", "", *rationale_lines]
        lines += [
            "",
            "### Dữ liệu định lượng LLM nhận tại từng tín hiệu",
            "",
            f"Mô hình: {', '.join(llm_models) or 'không rõ'}; tổng token đầu vào {token_usage.get('input_tokens', 0):,}, "
            f"đầu ra {token_usage.get('output_tokens', 0):,}. Đây là số token trong các phản hồi đã lưu, không phải ước lượng chi phí tiền tệ.",
            "",
            "| Ngày | Xác suất biến động cao | Biến động VN30 20/60/120 phiên | Lợi suất VN30 20/60 phiên | Tỷ số biến động | Tương quan cặp TB / phân vị 90% | Độ phân tán 20 phiên | Mã tăng 20 phiên | Tỷ trọng ngân hàng trong rổ / ứng viên | Cơ cấu ngành 12 ứng viên | ADTV ứng viên min / trung vị / max | Số chính sách có lịch sử |",
            "|---|---:|---|---|---:|---|---:|---:|---|---|---|---:|",
        ]
        for record in guidance["decisions"]:
            insight = record["context"]["market_insights"]
            history = record["context"].get("past_completed_policy_benchmarks", {})
            vol = "/".join(
                _optional_pct(insight.get(key)) for key in (
                    "vn30_annualized_volatility_20d", "vn30_annualized_volatility_60d",
                    "vn30_annualized_volatility_120d",
                )
            )
            market_return = "/".join(
                _optional_pct(insight.get(key)) for key in ("vn30_return_20d", "vn30_return_60d")
            )
            corr = "/".join(
                _optional_num(insight.get(key), 3) for key in (
                    "mean_pairwise_correlation_252d",
                    "90th_percentile_pairwise_correlation_252d",
                )
            )
            group_summary = ", ".join(
                f"{group} {_pct(fraction)}"
                for group, fraction in insight.get("candidate_group_fraction", {}).items()
            )
            liquidity_range = "/".join(
                _money(insight.get(key, 0)) for key in (
                    "candidate_min_daily_traded_value_proxy_vnd",
                    "candidate_median_daily_traded_value_proxy_vnd",
                    "candidate_max_daily_traded_value_proxy_vnd",
                )
            )
            lines.append(
                f"| {record['signal_date']} | "
                f"{_optional_pct(insight.get('ai_high_volatility_probability'))} | {vol} | "
                f"{market_return} | {_optional_num(insight.get('volatility_ratio_20d_to_120d'), 2)} | "
                f"{corr} | {_optional_pct(insight.get('cross_sectional_20d_return_dispersion'))} | "
                f"{_optional_pct(insight.get('fraction_stocks_positive_20d'))} | "
                f"{_optional_pct(insight.get('bank_fraction_of_eligible_stocks'))} / "
                f"{_optional_pct(insight.get('candidate_group_fraction', {}).get('Ngân hàng'))} | "
                f"{group_summary} | {liquidity_range} | "
                f"{sum(item.get('completed_periods', 0) > 0 for item in history.values())}/"
                f"{len(policy_names)} |"
            )
        lines += [
            "",
            "### AGQO so với từng chính sách cố định",
            "",
            "Các chính sách cố định được chạy song song ở chế độ bóng trên từng tín hiệu. Chúng không được dùng để thay đổi lợi nhuận đã xảy ra; tại tín hiệu kế tiếp, LLM chỉ thấy các kỳ đã đóng. Bảng này so danh mục thích nghi với từng chính sách cố định trên cùng cửa sổ, nhưng chính sách tốt nhất sau toàn bộ kỳ là đối chứng hậu nghiệm chứ không phải lựa chọn có thể biết trước.",
            "",
            "| Danh mục | CAGR ròng | Vượt VN30 năm hóa TB | Sharpe | Sortino | Sụt giảm tối đa | VaR tháng 95% | CVaR tháng 95% | Hệ số lợi nhuận | Tháng dương | Doanh số TB | Sai lệch QAOA TB | Số kỳ sai lệch ≤5% | Kỳ dự phòng chính xác |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        policy_rows = [("AGQO thích nghi", agqo_name, "AGQO")]
        policy_rows.extend(
            (policy_id, strategy_name, f"POLICY:{policy_id}")
            for policy_id, strategy_name in sorted(policy_names.items())
        )
        for label, strategy_name, variant in policy_rows:
            metrics = performance[strategy_name]["metrics"]
            execution = performance[strategy_name]["execution_summary"]
            quality = qaoa["quality_summary"][variant]
            active_return = portfolio["comparisons"][
                f"{strategy_name} vs VN30"
            ]["annualized_mean_active_return"]
            lines.append(
                f"| {label} | {_optional_pct(metrics.get('cagr'))} | "
                f"{_optional_pct(active_return)} | "
                f"{_optional_num(metrics.get('sharpe'))} | {_optional_num(metrics.get('sortino'))} | "
                f"{_optional_pct(metrics.get('max_drawdown'))} | "
                f"{_optional_pct(metrics.get('monthly_var_95'))} | "
                f"{_optional_pct(metrics.get('monthly_cvar_95'))} | "
                f"{_optional_num(metrics.get('profit_factor'))} | "
                f"{_optional_pct(metrics.get('positive_month_fraction'))} | "
                f"{_optional_pct(execution.get('mean_executed_turnover'))} | "
                f"{_optional_pct(quality.get('mean_normalized_regret'))} | "
                f"{quality.get('instances_with_regret_le_5_percent', 0)}/"
                f"{quality.get('monthly_instances', 0)} | "
                f"{quality.get('exact_fallback_months', 0)} |"
            )
        lines += [
            "",
            "![So sánh AGQO với danh mục chính sách cố định](figures/walkforward/08_agqo_policy_comparison.png)",
        ]
    else:
        lines += [
            "",
            "Lượt báo cáo này chưa gọi LLM. Khi bật AGQO trên Modal, phần quyết định theo từng tín hiệu, "
            "insight đầu vào, chính sách đã chọn và kết quả QAOA sẽ được ghi tại đây.",
        ]
    lines += [
        "",
        "![Sai lệch mục tiêu QAOA](figures/walkforward/03_qaoa_optimality_gap.png)",
        "",
        (
            f"Chuẩn chính xác N=12 cần tổng {qaoa['solver_runtime_seconds'].get('exact_ai12_universe_total', qaoa['solver_runtime_seconds']['exact_12_universe_total']):.4f} giây "
            f"cho 16 tín hiệu, còn QAOA X p=1 cần {qaoa['quality_summary']['X_p1']['total_cpu_simulation_seconds']:.3f} giây "
            "cho 48 lượt mô phỏng. Khi đủ 30 mã, nghiệm chính xác xét tối đa 593.775 tổ hợp mỗi kỳ; "
            "các kỳ đầu có 29 mã do VPL chưa đủ lịch sử. "
            f"Tổng thời gian của năm cấu hình cổ điển trên 16 tín hiệu là "
            f"{qaoa['solver_runtime_seconds']['exact_full_universe_total']:.2f} giây. "
            "Hai cách không cùng quy mô; máy véc-tơ trạng thái chỉ là mô phỏng cổ điển. "
            f"{policy_runtime_note}"
        ).rstrip(),
        "",
        "![Thời gian bộ giải](figures/walkforward/07_solver_runtime.png)",
        "",
        "### Kết luận chọn hướng đi",
        "",
        "**Hướng AGQO:** AI/LLM rút insight tài chính từ dữ liệu có sẵn tại ngày tín hiệu, chọn một chính sách QAOA "
        "trong danh mục đã khóa, rồi QAOA giải danh mục theo chính sách đó. Hồi quy logistic, cấu hình QAOA cố định, "
        "Ledoit–Wolf và nghiệm chính xác vẫn được giữ làm đối chứng. Chỉ công nhận LLM có ích nếu AGQO thắng đối chứng "
        "theo tiêu chí tài chính và chất lượng nghiệm đã đăng ký trên dữ liệu ngoài mẫu.",
        (
            "Các kỳ AGQO sau sử dụng kết quả của các kỳ đã đóng trước đó trong cùng cửa sổ; đây là walk-forward thích nghi. "
            "Cần thêm một giai đoạn kiểm tra cuối được khóa trước khi dùng kết quả để tuyên bố khả năng khái quát."
            if guidance.get("enabled") else ""
        ),
        (
            "Kết quả hiện tại có bật LLM và đã đo đường AGQO cùng CAGR, Sharpe, Sortino, sụt giảm, chi phí, doanh số và sai lệch QAOA."
            if guidance.get("enabled")
            else "Báo cáo này chưa bật LLM; các con số đang thấy là chuẩn đối chiếu, chưa phải kết quả của vòng AGQO đầy đủ."
        ),
        "",
        "Trước khi biến kết quả thành tuyên bố đầu tư, cần thay dữ liệu bằng chuỗi đã điều chỉnh, lấy thành phần VN30 "
        "theo ngày hiệu lực, mở rộng các chu kỳ thị trường độc lập, xác định phí/thuế/trượt giá theo nhà môi giới, "
        "và đăng ký trước tiêu chí chọn mô hình. Cần chạy lời hướng dẫn LLM trên Modal, lưu nguyên quyết định theo "
        "ngày, rồi kiểm định thêm nhiều chu kỳ chưa dùng để chọn chính sách.",
        "",
        "## 4. Nguồn dữ liệu và xử lý",
        "",
        f"- Tệp: {result['data']['path']}; {result['data']['rows']:,} dòng; "
        f"{result['data']['first_date']}–{result['data']['last_date']}.",
        "- Nguồn bộ lấy: thư viện vnstock-data; nguồn giá là DNSE chart API; danh sách thành phần là bản chụp HODL.VN ngày 02/10/2026.",
        "- Lợi suất tính từ giá đóng cửa; chỉ dùng phiên cả VN30 và VN-Index đều có giá để thống nhất lịch chỉ số; không nội suy giá thiếu.",
        "- Đầu vào danh mục dùng tối đa 252 phiên gần nhất, yêu cầu tối thiểu 126 quan sát đầy đủ mỗi mã.",
        "- Mỗi tháng, 12 ứng viên QAOA là các mã đủ điều kiện có giá trị giao dịch ước tính close × volume bình quân 20 phiên cao nhất.",
        "- Giới hạn ADTV được mô phỏng bằng lệnh khớp một phần; giá mở cửa, vốn 100 triệu đồng, phí 10/25/50 điểm cơ bản.",
        "- Tệp dữ liệu thô bị bỏ khỏi Git; cần đối chiếu mã băm và giấy phép trước khi phân phối.",
        "",
        "## 5. Giới hạn cần nói rõ với ban giám khảo",
        "",
    ]
    for limitation in result["limitations"]:
        lines.append(f"- {limitation}")
    lines += [
        "",
        "Tệp JSON lưu dự báo, xác suất, danh mục theo tháng, lợi nhuận từng kỳ, phí, doanh số, đối chiếu lấy mẫu khối, "
        "kết quả từng hạt giống QAOA và thời gian chạy: vn30_ai_qaoa_walkforward.json.",
        "",
    ]
    return "\n".join(lines)


def write_walkforward_report(
    result_json: str | Path,
    output_report: str | Path,
    figures_dir: str | Path | None = None,
) -> Path:
    result = json.loads(Path(result_json).read_text(encoding="utf-8"))
    destination = Path(output_report)
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = render_walkforward_report(result)
    if figures_dir is not None:
        figure_prefix = Path(os.path.relpath(Path(figures_dir).resolve(), destination.parent.resolve()))
        figure_prefix = figure_prefix.as_posix().rstrip("/")
        report = report.replace("figures/walkforward/", f"{figure_prefix}/")
    destination.write_text(report, encoding="utf-8")
    return destination
