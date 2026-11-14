"""Build the evidence-led Vietnamese AGQO research report from one run JSON."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any


def _pct(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return "—" if not math.isfinite(number) else f"{number * 100:.{digits}f}%"


def _num(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return "—" if not math.isfinite(number) else f"{number:.{digits}f}"


def _money(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number / 1_000_000:,.2f} triệu đồng" if math.isfinite(number) else "—"


def _key(metrics: dict[str, Any], *needles: str) -> str | None:
    return next((name for name in metrics if all(needle in name for needle in needles)), None)


def render_walkforward_report(result: dict[str, Any]) -> str:
    data, config = result["data"], result["config"]
    ai, portfolio, qaoa = result["ai"], result["portfolio"], result["qaoa"]
    guidance = result.get("agqo_guidance", {})
    performance = portfolio["performance"]
    enabled = bool(guidance.get("enabled"))
    agqo_name = "AGQO Qwen→giám sát→QAOA / chính sách thích nghi"
    rule_name = "Bộ chọn quy tắc→QAOA / đối chứng không LLM"
    vn30 = performance["VN30"]["metrics"]
    vnindex = performance["VN-Index"]["metrics"]
    agqo_metric = performance.get(agqo_name, {}).get("metrics", {})
    decisions = guidance.get("decisions", [])
    first_entry = portfolio["entry_dates"][0] if portfolio["entry_dates"] else "—"
    last_exit = portfolio["exit_dates"][-1] if portfolio["exit_dates"] else "—"
    period_count = portfolio["period_count"]

    lines = [
        "# Báo cáo kết quả cuối cùng: AGQO trên cổ phiếu Việt Nam",
        "",
        f"**Giai đoạn danh mục:** {first_entry} đến {last_exit} · **{period_count} kỳ tháng** · "
        f"**vốn mô phỏng:** {_money(portfolio['capital_vnd'])} · **phí cơ sở:** "
        f"{config['fee_bps']:.0f} điểm cơ bản mỗi chiều · **ngày tạo:** {result['generated_at_local']}",
        "",
        "> Kết quả là nghiên cứu lịch sử, không phải lợi nhuận đầu tư có thể thực hiện. Dữ liệu dùng giá OHLCV thô "
        "và ảnh chụp thành phần VN30 hiện tại áp ngược lịch sử. Các phiên bản trước của dự án đã xem cùng khoảng "
        "kiểm định; vì vậy đây không còn là một tập kiểm tra độc lập chưa từng được quan sát.",
        "",
        "## Kết luận điều hành",
        "",
    ]
    if enabled and agqo_metric:
        compare = portfolio["comparisons"].get(f"{agqo_name} vs VN30", {})
        ci3 = compare.get("active_return_confidence_interval", {})
        ci6 = compare.get("active_return_confidence_interval_block6", {})
        lines += [
            f"- AGQO sau bộ giám sát đạt CAGR ròng **{_pct(agqo_metric.get('cagr'))}**, Sharpe "
            f"**{_num(agqo_metric.get('sharpe'))}**, Sortino **{_num(agqo_metric.get('sortino'))}** và sụt giảm tối đa "
            f"**{_pct(agqo_metric.get('max_drawdown'))}**. VN30 đạt {_pct(vn30.get('cagr'))} CAGR, "
            f"Sharpe {_num(vn30.get('sharpe'))}, sụt giảm {_pct(vn30.get('max_drawdown'))}.",
            f"- Chênh CAGR AGQO so với VN30 là {(agqo_metric.get('cagr', 0) - vn30.get('cagr', 0)) * 100:+.2f} điểm phần trăm. "
            f"Khoảng tin cậy 95% của lợi nhuận vượt bình quân năm hóa theo khối 3 tháng là "
            f"[{_pct(ci3.get('lower'))}, {_pct(ci3.get('upper'))}]" +
            (f"; khối 6 tháng là [{_pct(ci6.get('lower'))}, {_pct(ci6.get('upper'))}]." if ci6 else "."),
            f"- LLM tạo {len(decisions)} đề xuất. Bộ giám sát đổi {guidance.get('execution_guardrail', {}).get('fallback_count', 0)} "
            f"đề xuất theo bằng chứng đã khép; {guidance.get('execution_guardrail', {}).get('repaired_llm_response_count', 0)} "
            "phản hồi có trường định dạng phải sửa. Đề xuất ban đầu, cấu hình thực thi và lý do đều được lưu.",
            "- Nếu AGQO không vượt VN30, bộ chọn quy tắc, nghiệm chính xác hoặc cấu hình cố định, kết quả được báo đúng như vậy; "
            "không diễn giải việc pipeline chạy thành bằng chứng tạo thêm lợi nhuận.",
        ]
    else:
        lines += [
            "- Lượt này chưa bật LLM; các kết quả chỉ là đối chứng nền và chưa phải kết quả AGQO đầy đủ.",
            f"- VN30 đạt {_pct(vn30.get('cagr'))} CAGR và VN-Index đạt {_pct(vnindex.get('cagr'))} trong cửa sổ đo.",
        ]
    lines += [
        "- QAOA được mô phỏng bằng véc-tơ trạng thái trên CPU. Nghiệm vét cạn cổ điển là chuẩn tối ưu từng bài toán nhỏ; "
        "không có QPU hay bằng chứng ưu thế lượng tử trong báo cáo này.",
        "",
        "## Kết quả tài chính",
        "",
        "Lợi suất danh mục tính từ giá mở cửa phiên sau tín hiệu đến phiên thoát lệnh kế tiếp. Sổ giao dịch trừ phí, "
        "mô phỏng khớp lệnh giới hạn theo ADTV và cho phép tiền mặt khi lệnh không khớp đủ. Sharpe/Sortino giả định "
        "lãi suất phi rủi ro tháng bằng 0.",
        "",
        "| Phương pháp | CAGR ròng | Biến động năm hóa | Sharpe | Sortino | Sụt giảm tối đa | CVaR tháng 95% | Giá trị cuối từ 100 triệu | Phí giao dịch |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    named_rows = [
        ("VN30", "VN30"),
        ("VN-Index", "VN-Index"),
        (_key(performance, "Ledoit–Wolf") or "", "Ledoit–Wolf, nghiệm chính xác"),
        (_key(performance, "AI điều chỉnh λ và α", "nghiệm chính xác", "12 mã") or "", "AI tham số + nghiệm chính xác, 12 mã"),
        (_key(performance, "AI + QAOA p=1", "bộ trộn X") or "", "QAOA X, p=1, 12 mã"),
        (_key(performance, "AI + QAOA p=2", "bộ trộn X") or "", "QAOA X, p=2, 12 mã"),
        (_key(performance, "AI + QAOA p=1", "bộ trộn XY") or "", "QAOA XY, p=1, 12 mã"),
        (_key(performance, "Tham lam") or "", "Tham lam cổ điển, 12 mã"),
        (_key(performance, "Tôi luyện mô phỏng") or "", "Tôi luyện mô phỏng, 12 mã"),
    ]
    if enabled:
        named_rows.extend([(rule_name, "Bộ chọn quy tắc → QAOA"), (agqo_name, "AGQO: Qwen3.8-27B → giám sát → QAOA")])
    seen = set()
    for name, label in named_rows:
        if not name or name not in performance or name in seen:
            continue
        seen.add(name)
        item = performance[name]
        metric, execution = item["metrics"], item.get("execution_summary") or {}
        ending = portfolio["capital_vnd"] * metric.get("ending_value_per_unit", 1)
        lines.append(
            f"| {label} | {_pct(metric.get('cagr'))} | {_pct(metric.get('annualized_volatility'))} | "
            f"{_num(metric.get('sharpe'))} | {_num(metric.get('sortino'))} | {_pct(metric.get('max_drawdown'))} | "
            f"{_pct(metric.get('monthly_cvar_95'))} | {_money(ending)} | {_money(execution.get('total_transaction_cost_vnd'))} |"
        )
    if enabled:
        lines += [
            "",
            "### So sánh AGQO với các mốc",
            "",
            "| Mốc so sánh | CAGR ròng | Sharpe | Sụt giảm tối đa | Chênh lợi suất chủ động năm hóa | Khoảng 95%, khối 3 tháng | Khoảng 95%, khối 6 tháng |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for benchmark in ("VN30", "VN-Index"):
            if not benchmark or benchmark == agqo_name or benchmark not in performance:
                continue
            comp = portfolio["comparisons"].get(f"{agqo_name} vs {benchmark}")
            if not comp:
                continue
            ci3, ci6 = comp.get("active_return_confidence_interval", {}), comp.get("active_return_confidence_interval_block6", {})
            metric = performance[benchmark]["metrics"]
            lines.append(
                f"| {benchmark} | {_pct(metric.get('cagr'))} | {_num(metric.get('sharpe'))} | {_pct(metric.get('max_drawdown'))} | "
                f"{_pct(comp.get('annualized_mean_active_return'))} | [{_pct(ci3.get('lower'))}, {_pct(ci3.get('upper'))}] | "
                f"[{_pct(ci6.get('lower'))}, {_pct(ci6.get('upper'))}] |"
            )
    lines += [
        "",
        "![Đường vốn sau phí](figures/02_net_equity_curves.png)",
        "",
        "![Lợi nhuận và biến động](figures/04_risk_return_tradeoff.png)",
        "",
        "![Nhạy cảm với phí và giới hạn thanh khoản](figures/05_cost_and_capacity.png)",
        "",
        "### Bộ phân loại chế độ biến động",
        "",
    ]
    monthly_ai = ai["metrics"].get("monthly_signal_metrics", {})
    lines += [
        f"Mô hình LogisticRegression sau StandardScaler dự báo biến động VN30 trong {config['horizon']} phiên vượt "
        f"ngưỡng phân vị 70% của tập huấn luyện. Đặc trưng là biến động 20/60/120 phiên, lợi suất 20/60 phiên và "
        "tỷ số biến động 20/120. Đây không phải mô hình dự báo lợi suất.",
        "",
        f"- Brier ở các tín hiệu tháng: {_num(monthly_ai.get('brier_score'), 3)}; nền tỷ lệ huấn luyện: "
        f"{_num(monthly_ai.get('expanding_base_rate_brier'), 3)}; kỹ năng Brier: "
        f"{_pct(monthly_ai.get('brier_skill_vs_expanding_base_rate'))}.",
        f"- Brier dự báo ngày chồng lấn: {_num(ai['metrics'].get('brier_score'), 3)}; nền mở rộng: "
        f"{_num(ai['metrics'].get('expanding_base_rate_brier'), 3)}; kỹ năng: "
        f"{_pct(ai['metrics'].get('brier_skill_vs_expanding_base_rate'))}. Dự báo ngày không độc lập vì nhãn 21 phiên chồng lấn.",
        "- Khi kỹ năng Brier âm hoặc có dưới 6 dự báo tháng đã trưởng thành, prompt yêu cầu Qwen3.8-27B xem xác suất này là tín hiệu yếu; "
        "không được tự tăng rủi ro hay độ sâu mạch chỉ vì xác suất biến động cao.",
        "",
        "![Dự báo và nhãn biến động](figures/01_ai_regime_walkforward.png)",
        "",
        "## Insight dữ liệu và ý nghĩa tài chính",
        "",
        f"Tập dữ liệu cục bộ gồm {data['rows']:,} dòng OHLCV, {data['ticker_count']} mã/chỉ số, từ {data['first_date']} đến {data['last_date']}. "
        "Tại mỗi tín hiệu, AGQO tổng hợp xác suất chế độ, biến động và xu hướng VN30, tương quan chéo, độ phân tán, "
        "độ rộng tăng giảm, thanh khoản đại diện và kết quả các cấu hình đã thoát lệnh.",
    ]
    markets = [record.get("context", {}).get("market", {}) for record in decisions]
    if markets:
        def avg(key: str):
            vals = [float(item[key]) for item in markets if item.get(key) is not None and math.isfinite(float(item[key]))]
            return sum(vals) / len(vals) if vals else None
        lines += [
            "",
            "Trung bình các ngày tín hiệu trong lượt chạy:",
            "",
            f"- Xác suất chế độ biến động cao do mô hình dự báo: {_pct(avg('ai_high_volatility_probability'))}.",
            f"- Tỷ số biến động VN30 20/120 phiên: {_num(avg('volatility_ratio_20d_to_120d'))}; tương quan cặp cổ phiếu: {_num(avg('mean_pairwise_correlation_252d'))}.",
            f"- Độ phân tán lợi suất 20 phiên giữa cổ phiếu: {_pct(avg('cross_sectional_20d_return_dispersion'))}; tỷ lệ mã dương: {_pct(avg('fraction_stocks_positive_20d'))}.",
            f"- Tỷ trọng ngân hàng trong rổ đủ điều kiện: {_pct(avg('bank_fraction_of_eligible_stocks'))}; trung vị giá trị giao dịch đại diện của ứng viên: {_money(avg('candidate_median_daily_traded_value_proxy_vnd'))} mỗi ngày.",
        ]
        if decisions[0].get("context", {}).get("submodels", {}).get("regime_classifier", {}).get("reliability_to_date"):
            reliability = decisions[-1]["context"]["submodels"]["regime_classifier"]["reliability_to_date"]
            lines.append(
                f"- Tại tín hiệu cuối, mô hình có {reliability.get('matured_monthly_signals', 0)} dự báo tháng đã trưởng thành; "
                f"Brier skill đến thời điểm đó là {_pct(reliability.get('brier_skill_vs_training_prevalence'))}."
            )
    lines += [
        "",
        "![Ngành và tần suất chọn mã](figures/06_exposure_and_holdings.png)",
        "",
        "## Cách AGQO dùng LLM, RAG và bộ giám sát",
        "",
        "Qwen3.8-27B (Alibaba Qwen, 27,8B tham số dense, checkpoint FP8 chính thức, Apache-2.0) chạy bằng vLLM trên Modal 1×H100, mức suy luận `medium`. "
        "LLM không tự giải danh mục và không được tự tạo λ, α, số qubit, bộ trộn, "
        "độ sâu hay số shots; nó chỉ chọn một mã trong danh mục đã chạy đối chứng. Toàn bộ prompt được viết bằng tiếng Anh. "
        "Do không giả định LLM là chuyên gia tài chính, system prompt yêu cầu chỉ dùng định nghĩa và bằng chứng trong payload, "
        "không lấp chỗ trống bằng kiến thức ghi nhớ và không sinh nhận định tự do.",
        "",
        f"Phiên bản prompt: `{guidance.get('prompt_version', '—')}`. Trong {guidance.get('decision_count', len(decisions))} tín hiệu, bộ giám sát đổi "
        f"{guidance.get('execution_guardrail', {}).get('fallback_count', 0)} đề xuất; "
        f"{guidance.get('execution_guardrail', {}).get('repaired_llm_response_count', 0)} phản hồi cần sửa lược đồ. "
        f"Tổng mức dùng: {guidance.get('recorded_token_usage', {}).get('input_tokens', 0):,} token đầu vào, "
        f"{guidance.get('recorded_token_usage', {}).get('output_tokens', 0):,} token đầu ra.",
        "",
        "RAG dùng kho bảy ghi chú cục bộ có phiên bản, không truy cập mạng trong lúc suy luận. Mỗi tín hiệu lưu các ghi chú được truy xuất, "
        "nguồn, phiên bản và JSON gửi đến mô hình. Nội dung định nghĩa metrics, fields, mục tiêu danh mục, QAOA, benchmark và giới hạn dữ liệu. "
        "Bộ luật insight định lượng áp dụng ngưỡng đã khóa; LogisticRegression là tiểu mô hình dự báo duy nhất và ước tính chế độ biến động, "
        "không phải lợi suất. Hiệu quả của classifier được đo bằng Brier so với tỷ lệ nền đã trưởng thành.",
        "",
        "Mỗi payload chứa lược đồ đầu ra riêng, chỉ liệt kê cấu hình, mã insight và mã evidence được phép tại ngày tín hiệu. "
        "Sau phần suy luận, Qwen3.8-27B trả ba trường JSON: `policy_id`, `insight_codes`, `evidence_ids`; mã cục bộ xác thực lại và tạo câu giải thích tiếng Việt "
        "cùng cờ rủi ro từ số đo. Bộ giám sát độc lập dùng tối thiểu 6 kỳ đã khép rồi kiểm tra tỷ lệ mẫu khả thi, sai lệch nghiệm, "
        "Sharpe và sụt giảm lịch sử. Khi bằng chứng chưa đủ hoặc đề xuất kém rõ rệt so với bộ chọn quy tắc, hệ thống lưu đề xuất ban đầu "
        "nhưng thực thi cấu hình đối chứng.",
        "",
    ]
    if enabled:
        lines += [
            "| Ngày tín hiệu | LLM đề xuất | Cấu hình thực thi | λ | α | Bộ trộn / bố trí / p | Lý do giám sát | Regret sau QAOA |",
            "|---|---|---|---:|---:|---|---|---:|",
        ]
        for record in decisions:
            policy = record.get("policy", {})
            qresult = record.get("qaoa_result", {})
            reason = record.get("guardrail_reason") or "Chấp nhận đề xuất"
            lines.append(
                f"| {record.get('signal_date')} | `{record.get('proposed_policy_id')}` | `{record.get('executed_policy_id')}` | "
                f"{_num(policy.get('risk_aversion'), 1)} | {_num(policy.get('shrinkage'), 2)} | "
                f"{policy.get('mixer')} / {policy.get('mixer_layout')} / {policy.get('depth')} | {reason} | "
                f"{_pct(qresult.get('normalized_objective_regret'))} |"
            )
        lines += [
            "",
            "![Kiểm toán đề xuất và cấu hình thực thi](figures/11_agqo_decision_audit.png)",
            "",
        ]
        all_notes = {}
        for record in decisions:
            for note in record.get("context", {}).get("method_notes", []):
                all_notes[note["id"]] = note
        lines += ["Ghi chú phương pháp được truy xuất trong lượt chạy:", ""]
        for note_id, note in sorted(all_notes.items()):
            lines.append(f"- **{note_id} · {note['title']}** — {note['source']}")

    lines += [
        "",
        "## Thiết kế QAOA và phép đo",
        "",
        f"Danh mục AGQO gồm {len(guidance.get('policy_catalog', []))} cấu hình kiểm soát: N=8, 12, 16 qubit; K={config['k']}; "
        "bộ trộn X hoặc XY; p=1/2; vòng, đường thẳng, đầy đủ hoặc tương quan; λ và mức co rút hiệp phương sai khác nhau. "
        f"Mỗi lần tối ưu dùng {config['qaoa_shots']:,} shots, COBYLA tối đa {config['qaoa_max_evaluations']} lần đánh giá "
        f"mỗi seed và các seed {', '.join(map(str, config['qaoa_seeds']))}.",
        "",
        "Hàm mục tiêu tối thiểu hóa `λ(xᵀΣαx)/K² − (μᵀx)/K + chi phí tái cân bằng năm hóa`, với `Σα=(1−α)Σ+α diag(Σ)` và `Σxᵢ=K`. "
        "`λ` là trọng số phạt rủi ro, `α` là mức co rút hiệp phương sai. Bộ trộn X có hạng phạt cardinality; bộ trộn XY khởi tạo "
        "trạng thái khả thi và dùng cổng RXX/RYY để bảo toàn số bit 1. Hệ số `p` là số lớp cost/mixer xen kẽ.",
        "",
        "Chuẩn so sánh là duyệt chính xác mọi tổ hợp khả thi trên cùng N, K và cùng mục tiêu. Sai lệch chuẩn hóa là "
        "`(điểm QAOA khả thi − điểm tối ưu chính xác)/(điểm lớn nhất − nhỏ nhất trong các nghiệm khả thi)`; 0 nghĩa là khớp nghiệm chính xác. "
        "Tỷ lệ mẫu khả thi là tỷ phần shots có đúng K lựa chọn, không phải xác suất kiếm lời. Báo cả chất lượng, tỷ lệ khả thi, số cổng logic "
        "và thời gian CPU; cổng logic không đồng nghĩa với cổng vật lý sau biên dịch.",
        "",
        "![Sơ đồ cổng logic và cấu trúc bộ trộn](figures/09_qaoa_gate_and_mixer_design.png)",
        "",
        "![Regret theo chi phí cổng logic](figures/10_qaoa_quality_vs_gate_cost.png)",
        "",
        "### Đối chứng lượng tử và cổ điển",
        "",
        "| Cấu hình | N/K | Mixer / bố trí / p | Kỳ regret ≤5% | Regret trung bình | Tỷ lệ feasible trung bình | Cổng hai qubit logic TB | CAGR / Sharpe / MaxDD |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ]
    if enabled:
        lines += ["", "![So sánh các chính sách QAOA](figures/08_agqo_policy_comparison.png)", ""]
    strategy_names = guidance.get("policy_strategy_names", {})
    catalog = guidance.get("policy_catalog", [])
    for policy in catalog:
        policy_id = policy["policy_id"]
        key = f"POLICY:{policy_id}"
        strategy = strategy_names.get(policy_id)
        quality = qaoa["quality_summary"].get(key, {})
        metric = performance.get(strategy, {}).get("metrics", {}) if strategy else {}
        rows = [row for row in qaoa["monthly_runs"] if row.get("variant") == key]
        gate_count = [
            (row.get("logical_cost_two_qubit_gate_count") or 0)
            + (row.get("logical_mixer_two_qubit_gate_count") or 0)
            for row in rows
        ]
        lines.append(
            f"| `{policy_id}` | {policy['n_qubits']}/{config['k']} | {policy['mixer']} / {policy['mixer_layout']} / {policy['depth']} | "
            f"{quality.get('instances_with_regret_le_5_percent', 0)}/{quality.get('monthly_instances', 0)} | "
            f"{_pct(quality.get('mean_normalized_regret'))} | {_pct(quality.get('mean_best_seed_feasible_probability'))} | "
            f"{_num(sum(gate_count) / len(gate_count) if gate_count else None, 0)} | "
            f"{_pct(metric.get('cagr'))} / {_num(metric.get('sharpe'))} / {_pct(metric.get('max_drawdown'))} |"
        )
    for label, key in (("X, p=1", "X_p1"), ("X, p=2", "X_p2"), ("XY, p=1", "XY_p1")):
        quality = qaoa["quality_summary"].get(key, {})
        lines.append(
            f"| Đối chứng cố định {label} | {qaoa['n_qubits']}/{config['k']} | {label} | "
            f"{quality.get('instances_with_regret_le_5_percent', 0)}/{quality.get('monthly_instances', 0)} | "
            f"{_pct(quality.get('mean_normalized_regret'))} | {_pct(quality.get('mean_best_seed_feasible_probability'))} | — | — |"
        )
    lines += [
        "",
        "### Đọc kết quả QAOA",
        "",
        f"Không gian trạng thái của bài cơ sở N={qaoa['n_qubits']} là {qaoa['statevector_basis_states']:,}; "
        f"có {qaoa['feasible_combinations_per_month']:,} tổ hợp khả thi K={qaoa['k']}. Trong AGQO, N=8/12/16 tương ứng "
        "256/4.096/65.536 trạng thái mô phỏng cổ điển và 28/924/8.008 tập con khả thi.",
        "",
        "Mạch XY bảo toàn cardinality, trong khi X cần hạng phạt và có thể lấy mẫu trạng thái sai K. Đồ thị tương quan được xây từ "
        "hai liên kết đồng biến mạnh nhất cho mỗi mã cùng với vòng liên thông. Độ sâu lớn và đồ thị dày làm tăng công việc logic; "
        "chỉ nên chọn nếu regret giảm đủ để bù chi phí tính toán và rủi ro thực thi.",
        "",
        "Bộ giải vét cạn là đối chứng cổ điển khả thi cho N≤16 và K=6; greedy và simulated annealing cũng chạy trên cùng hàm mục tiêu. "
        "Nếu exact giải nhanh hơn QAOA mô phỏng, đó là kết quả thực nghiệm cần trình bày. Không có căn cứ gọi QAOA vượt trội chỉ vì nó dùng cổng lượng tử trong mô hình toán học.",
        "",
        "![Khoảng regret của các cấu hình cơ sở](figures/03_qaoa_optimality_gap.png)",
        "",
        "## Quy trình và mốc thời gian",
        "",
        "| Giai đoạn | Mốc | Cách dùng |",
        "|---|---|---|",
        f"| Huấn luyện ban đầu | đến {ai['training_end']} | Fit scaler/logistic và xác lập ngưỡng biến động |",
        f"| Xác nhận | {ai['validation_start']} đến {ai['validation_end']} | Chọn C theo log-loss; chặn nhãn tương lai trước ranh giới |",
        f"| Kiểm định walk-forward | tín hiệu từ {config['test_start']} | Mở rộng huấn luyện theo nhãn đã trưởng thành; chỉ dùng kết quả kỳ đã đóng cho kỳ sau |",
        f"| Thời gian danh mục | {first_entry} đến {last_exit} | Tín hiệu tháng, giao dịch ở phiên mở cửa kế tiếp |",
        "",
        "LLM chạy zero-shot inference, không có epoch huấn luyện Qwen3.8-27B. Dữ liệu chỉ có ít tín hiệu tháng và không đủ để fine-tune "
        "hoặc đánh giá đáng tin cậy mô hình ngôn ngữ. Tăng `max_evaluations`, số shots hay seed là tăng ngân sách tối ưu QAOA, "
        "không phải tăng epoch huấn luyện LLM.",
        "",
        "## Dữ liệu, tái lập và giới hạn",
        "",
        f"Nguồn tệp đã lưu trong dự án: `{data['path']}` · {data['rows']:,} dòng · {data['first_date']}–{data['last_date']}. "
        "Bản đầy đủ về nguồn và cách xử lý nằm ở README và tài liệu kỹ thuật.",
        "",
    ]
    lines.extend(f"- {limitation}" for limitation in result.get("limitations", []))
    lines += [
        "- Kết quả của nhiều cấu hình dùng chung một cửa sổ kiểm định; lựa chọn tốt nhất hậu nghiệm có thiên lệch lựa chọn.",
        "- Kỳ thử nghiệm ngắn và các phiên bản AGQO cũ đã xem cùng mốc dữ liệu; cần khóa một giai đoạn tương lai riêng trước khi tuyên bố khả năng tổng quát.",
        "",
        "Mọi quyết định, payload, ghi chú RAG, phản hồi token, số liệu theo tháng, cấu hình, kết quả từng seed và chỉ số tài chính được lưu trong JSON cạnh báo cáo.",
        "",
        "### Tài liệu phương pháp",
        "",
        "- [Qwen3.8-27B model card và phiên bản đã ghim](https://huggingface.co/Qwen/Qwen3.8-27B-FP8/tree/c3a462cc3d38cf351f3b26cbd763469eeb74ef81)",
        "- [vLLM recipe cho Qwen3.8-27B](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)",
        "- [Modal: cấu hình GPU](https://modal.com/docs/guide/gpu)",
        "- [Farhi, Goldstone và Gutmann: QAOA](https://arxiv.org/abs/1411.4028)",
        "- [Hadfield và cộng sự: mixer cho tối ưu tổ hợp](https://arxiv.org/abs/1709.03489)",
        "",
        "### Hình kiểm toán bổ sung",
        "",
        "Các hình dưới đây nối insight thị trường với luồng xử lý và mạch thật của ba tín hiệu đã lưu. Metadata của từng hình ghi rõ nguồn, kỳ, đơn vị và giới hạn.",
        "",
        "![Kiến trúc AGQO từ dữ liệu đến bằng chứng](figures/12_agqo_pipeline.png)",
        "",
        "![Giá, biến động, độ rộng và phân tán thị trường](figures/13_market_regime_timeline.png)",
        "",
        "![Bản đồ lợi suất tháng theo cổ phiếu](figures/14_cross_section_monthly_returns.png)",
        "",
        "![Mạch QAOA qua ba bối cảnh thị trường đã lưu](figures/15_actual_qaoa_circuit_comparison.png)",
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
        report = report.replace("figures/", f"{figure_prefix}/")
    destination.write_text(report, encoding="utf-8")
    return destination
