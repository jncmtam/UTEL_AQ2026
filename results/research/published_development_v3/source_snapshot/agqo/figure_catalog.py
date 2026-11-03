"""Catalog and validation helpers for figures embedded in AGQO reports."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_FIGURES: dict[str, dict[str, str]] = {
    "01_ai_regime_walkforward.png": {
        "title": "Dự báo chế độ biến động theo thời gian",
        "explanation": "Đối chiếu xác suất do bộ phân loại tạo ra với nhãn biến động đã trưởng thành; Brier của mô hình là 0,237, kém nền 0,217, nên hiện chưa có căn cứ dùng xác suất này như tín hiệu tăng rủi ro.",
        "source": "results/final/agqo_final_walkforward.json · ai.daily_forecasts",
        "period": "giai đoạn huấn luyện đến 2026-08",
        "units": "xác suất, độ biến động năm hóa",
        "caveat": "Nhãn 21 phiên chồng lấn; kiểm định đã xem.",
    },
    "02_net_equity_curves.png": {
        "title": "Đường vốn ròng và chuẩn so sánh",
        "explanation": "Giá trị vốn mô phỏng 100 triệu đồng của AGQO, bộ chọn quy tắc, VN30 và các đối chứng; AGQO kết thúc thấp hơn VN30 trong 16 kỳ, nên đây là bằng chứng chống lại tuyên bố alpha hiện tại.",
        "source": "results/final/agqo_final_walkforward.json · portfolio.performance",
        "period": "2025-06 đến 2026-10",
        "units": "VND, lợi nhuận ròng",
        "caveat": "Giá thô, giả định phí và lệnh khớp; tập đã xem.",
    },
    "03_qaoa_optimality_gap.png": {
        "title": "Regret QAOA so với nghiệm chính xác",
        "explanation": "Regret chuẩn hóa đo khoảng cách giữa nghiệm khả thi tốt nhất tìm được và nghiệm vét cạn trên cùng mục tiêu; giá trị thấp hơn là tốt hơn, nhưng không phải lợi nhuận đầu tư.",
        "source": "results/final/agqo_final_walkforward.json · qaoa.monthly_runs",
        "period": "16 tín hiệu tháng 2025-05 đến 2026-08",
        "units": "phần trăm regret chuẩn hóa",
        "caveat": "Statevector CPU; exact enumeration làm chuẩn ở quy mô nhỏ.",
    },
    "04_risk_return_tradeoff.png": {
        "title": "Lợi nhuận và rủi ro sau chi phí",
        "explanation": "CAGR và biến động/độ sụt giảm đặt cạnh nhau để tránh chọn chiến lược chỉ theo lợi nhuận; Ledoit–Wolf toàn rổ mạnh hơn trong cửa sổ này nhưng rủi ro và phạm vi tài sản cũng khác.",
        "source": "results/final/agqo_final_walkforward.json · portfolio.performance",
        "period": "2025-06 đến 2026-10",
        "units": "CAGR, biến động, sụt giảm",
        "caveat": "Chỉ 16 kỳ; các phương pháp có thể khác quy mô vũ trụ.",
    },
    "05_cost_and_capacity.png": {
        "title": "Độ nhạy với phí và sức chứa",
        "explanation": "Cho biết thay đổi phí giả định và giới hạn tham gia thanh khoản ảnh hưởng ra sao đến kết quả mô phỏng; cần đọc như độ nhạy trên proxy, không phải mô hình khớp lệnh đầy đủ.",
        "source": "results/final/agqo_final_walkforward.json · portfolio.cost_capacity_sensitivity",
        "period": "2025-06 đến 2026-10",
        "units": "điểm cơ bản, phần trăm ADTV, CAGR/Sharpe",
        "caveat": "Không có sổ lệnh, spread, thuế đầy đủ hoặc trượt giá quan sát.",
    },
    "06_exposure_and_holdings.png": {
        "title": "Mức tập trung danh mục và tần suất nắm giữ",
        "explanation": "Thể hiện tần suất mã/ngành được chọn và mức tập trung; dùng để đánh giá liệu lợi nhuận có phụ thuộc quá nhiều vào vài cổ phiếu hay nhóm ngành.",
        "source": "results/final/agqo_final_walkforward.json · portfolio.selection_summary",
        "period": "2025-06 đến 2026-10",
        "units": "tỷ trọng, số kỳ được chọn",
        "caveat": "Thành phần VN30 hiện tại áp ngược lịch sử.",
    },
    "07_solver_runtime.png": {
        "title": "Thời gian giải các bộ tối ưu",
        "explanation": "So thời gian bộ mô phỏng QAOA với các bộ giải cổ điển ở kích thước đang thử; exact vẫn khả thi ở N nhỏ, do đó chưa có cơ sở gọi QAOA là cần thiết hay nhanh hơn.",
        "source": "results/final/agqo_final_walkforward.json · qaoa.solver_runtime_seconds",
        "period": "16 bài toán theo tháng",
        "units": "giây CPU trong môi trường nghiên cứu",
        "caveat": "Không phải so sánh phần cứng tương đương hay chi phí QPU.",
    },
    "08_agqo_policy_comparison.png": {
        "title": "So sánh chính sách thích nghi và cố định",
        "explanation": "Đặt AGQO, bộ chọn quy tắc và danh mục policy cố định trên cùng các kỳ đã ghi; khoảng cách với bộ chọn quy tắc cho thấy Qwen chưa tạo thêm giá trị trong mẫu hiện có.",
        "source": "results/final/agqo_final_walkforward.json · portfolio.performance",
        "period": "2025-06 đến 2026-10",
        "units": "CAGR, Sharpe, sụt giảm tối đa",
        "caveat": "Kỳ đã mở và ngắn; không dùng làm xác nhận ngoài mẫu.",
    },
    "09_qaoa_gate_and_mixer_design.png": {
        "title": "Nguyên lý cổng logic và đồ thị bộ trộn",
        "explanation": "Hình khái quát cách mã hóa cost Hamiltonian và mixer X/XY để giải thích lựa chọn thiết kế; đây là sơ đồ phương pháp, không đại diện cho một lần chạy cụ thể.",
        "source": "agqo/simulator.py · statevector và mixer_edges_for_problem",
        "period": "thiết kế bộ giải hiện tại",
        "units": "cổng logic, qubit, lớp p",
        "caveat": "Sơ đồ nguyên lý; mạch của một run cụ thể nằm ở Hình 15.",
    },
    "10_qaoa_quality_vs_gate_cost.png": {
        "title": "Regret QAOA so với chi phí cổng logic",
        "explanation": "Biểu đồ chất lượng–tài nguyên cho các policy; kích thước nút biểu diễn độ sâu và màu biểu diễn số qubit, giúp thấy rằng tăng mạch không tự động cải thiện regret.",
        "source": "results/final/agqo_final_walkforward.json · qaoa.quality_summary và policy_catalog",
        "period": "các tín hiệu 2025-05 đến 2026-08",
        "units": "regret phần trăm, số cổng logic hai qubit",
        "caveat": "Bộ đếm logic chưa transpile, không gồm nhiễu phần cứng.",
    },
    "11_agqo_decision_audit.png": {
        "title": "Kiểm toán đề xuất LLM và policy được thực thi",
        "explanation": "Đối chiếu policy Qwen đề xuất với policy vượt qua giám sát số học; biểu đồ giúp xác nhận quyết định nào được chấp nhận hay fallback và lý do.",
        "source": "results/final/agqo_final_walkforward.json · agqo_guidance.decisions",
        "period": "16 tín hiệu 2025-05 đến 2026-08",
        "units": "mã policy, ngày tín hiệu",
        "caveat": "Đầu ra hợp lệ không đồng nghĩa với lợi ích tài chính.",
    },
    "12_agqo_pipeline.png": {
        "title": "Kiến trúc AGQO từ dữ liệu đến bằng chứng",
        "explanation": "Luồng chỉ ra ranh giới cắt thời gian, local/Modal, RAG, Qwen, bộ giám sát, QAOA, đối chứng cổ điển và đường fallback; lớp tin ngoài được đánh dấu tắt do chưa có dữ liệu hợp lệ.",
        "source": "Mã nguồn AGQO và manifest tin tức",
        "period": "kiến trúc phiên bản hiện tại",
        "units": "thành phần và luồng dữ liệu",
        "caveat": "QAOA hiện mô phỏng trên CPU; không có QPU.",
    },
    "13_market_regime_timeline.png": {
        "title": "Giá, biến động, độ rộng và phân tán thị trường",
        "explanation": "Các trục căn chỉnh cho thấy giai đoạn thị trường theo chỉ số, biến động thực hiện, tỷ lệ cổ phiếu dương và phân tán chéo; không gắn tiêu đề tin khi kho sự kiện đang rỗng.",
        "source": "CSV OHLCV cục bộ",
        "period": "2022-01-04 đến 2026-10-19",
        "units": "chỉ số chuẩn hóa, phần trăm, độ lệch chuẩn",
        "caveat": "Dữ liệu giá chưa xác nhận điều chỉnh; vũ trụ có thiên lệch sống sót.",
    },
    "14_cross_section_monthly_returns.png": {
        "title": "Bản đồ lợi suất tháng theo cổ phiếu",
        "explanation": "Ma trận mã–tháng dùng thang màu phân kỳ có tâm 0 để nhìn rõ tháng tăng/giảm và độ đa dạng thực tế; thang màu được giới hạn theo phân vị 97,5 nhưng lợi suất gốc không bị thay đổi.",
        "source": "CSV OHLCV cục bộ · monthly close-to-close",
        "period": "2022-01 đến 2026-10",
        "units": "lợi suất tháng phần trăm",
        "caveat": "Ô xám là thiếu lịch sử; giá chưa xác nhận điều chỉnh và snapshot thành phần gây survivorship bias.",
    },
    "15_actual_qaoa_circuit_comparison.png": {
        "title": "Mạch QAOA qua ba bối cảnh thị trường đã lưu",
        "explanation": "Ba đồ thị dùng tín hiệu xác suất biến động thấp, cao và tương quan chéo cao; từng ánh xạ mã–qubit, seed, góc beta/gamma, cạnh cost, cạnh mixer, shots và regret được dựng từ lần chạy đã lưu. Màu nút cho biết mã thuộc nghiệm tốt nhất đã lấy mẫu; nhãn phân biệt policy AGQO thực thi với policy đối chứng cố định.",
        "source": "results/final/circuit_metadata.json và results/final/agqo_final_walkforward.json",
        "period": "tín hiệu 2025-05-30, 2026-03-31 và 2025-07-31; kết quả tháng liền sau",
        "units": "qubit, RZZ/RXX/RYY/RX, shots, regret",
        "caveat": "Cổng logic của simulator, chưa transpile hoặc chạy QPU.",
    },
    "01_coverage.png": {
        "title": "Độ phủ lịch sử theo mã",
        "explanation": "Bản đồ phiên có quan sát cho từng cổ phiếu cho thấy VPL chỉ có 360 phiên trong khi phần lớn mã có 1.192; lịch sử không đồng đều ảnh hưởng đến khả năng tạo vũ trụ điểm-thời-gian.",
        "source": "CSV OHLCV cục bộ · dataset_summary.json",
        "period": "2022-01-04 đến 2026-10-19",
        "units": "tỷ lệ phiên có dữ liệu",
        "caveat": "Màu trắng không phân biệt ngày nghỉ, tạm ngừng hay thiếu feed.",
    },
    "02_indices.png": {
        "title": "Diễn biến VN30 và VN-Index cùng sụt giảm",
        "explanation": "Chỉ số chuẩn hóa và drawdown minh họa diễn biến thị trường chung và khoảng cách từ đỉnh; dùng để đặt kết quả danh mục vào bối cảnh thị trường.",
        "source": "CSV OHLCV cục bộ · VN30 và VNINDEX",
        "period": "2022-01-04 đến 2026-10-19",
        "units": "chỉ số cơ sở 100, drawdown phần trăm",
        "caveat": "Chỉ số giá không thay thế total-return index.",
    },
    "03_risk_return.png": {
        "title": "Rủi ro, lợi suất và thanh khoản chéo",
        "explanation": "Mỗi điểm là một mã; vị trí so sánh lợi suất tích lũy và rủi ro, kích thước biểu thị thanh khoản đại diện; không dùng để chọn mã hậu nghiệm.",
        "source": "CSV OHLCV cục bộ · 252 phiên hoàn chỉnh gần nhất",
        "period": "252 phiên kết thúc 2026-10-19",
        "units": "lợi suất, độ biến động, VND giao dịch proxy",
        "caveat": "Kết quả mô tả và giá đóng cửa thô.",
    },
    "04_returns_rank.png": {
        "title": "Phân tán lợi suất tích lũy giữa các mã",
        "explanation": "Sắp xếp mã từ thấp lên cao để thấy độ phân tán lớn trong cùng cửa sổ; chỉ là thống kê mô tả trên giá hiện có, không đại diện cho danh mục đầu tư tại thời điểm lịch sử.",
        "source": "CSV OHLCV cục bộ · 252 phiên hoàn chỉnh gần nhất",
        "period": "252 phiên kết thúc 2026-10-19",
        "units": "lợi suất tích lũy phần trăm",
        "caveat": "Giá thô và thành phần snapshot hiện tại.",
    },
    "05_correlations.png": {
        "title": "Tương quan lợi suất theo nhóm cổ phiếu",
        "explanation": "Ma trận cho thấy tương quan có cấu trúc theo ngành; cùng chiều cao làm giảm lợi ích đa dạng hóa. Dải màu hiển thị hệ số tương quan từ −1 đến 1.",
        "source": "CSV OHLCV cục bộ · 252 phiên hoàn chỉnh gần nhất",
        "period": "252 phiên kết thúc 2026-10-19",
        "units": "hệ số tương quan Pearson",
        "caveat": "Các cặp cùng snapshot hiện tại; không phải bằng chứng quan hệ nhân quả.",
    },
    "06_liquidity.png": {
        "title": "Thanh khoản đại diện và quy mô lệnh mô phỏng",
        "explanation": "Giá đóng cửa nhân khối lượng làm proxy giá trị giao dịch ngày để so với quy mô danh mục; đây chưa phải turnover xác minh hay dữ liệu sổ lệnh.",
        "source": "CSV OHLCV cục bộ · close × volume",
        "period": "252 phiên kết thúc 2026-10-19",
        "units": "VND/ngày, tỷ lệ participation",
        "caveat": "Proxy thanh khoản; thiếu spread, độ sâu và impact quan sát.",
    },
    "07_risk_regimes.png": {
        "title": "Biến động VN30 và các chế độ ngưỡng",
        "explanation": "Đường biến động thực hiện và mốc phân vị dùng mô tả các đợt rủi ro khác nhau; không đồng nhất mốc ngưỡng với khả năng dự báo.",
        "source": "CSV OHLCV cục bộ · VN30 close",
        "period": "2022-01-04 đến 2026-10-19",
        "units": "độ biến động năm hóa",
        "caveat": "Chế độ ngưỡng không phải tin tức hoặc tín hiệu giao dịch.",
    },
    "08_optimizer.png": {
        "title": "Nghiệm chính xác trên ảnh chụp toàn rổ",
        "explanation": "Hiển thị lựa chọn chính xác cho một snapshot 30 mã, K=6; có 593.775 tổ hợp nên kết quả exact là mốc quan trọng cho so sánh solver.",
        "source": "dataset_summary.json · nghiệm vét cạn cổ điển",
        "period": "cửa sổ 252 phiên kết thúc 2026-10-19",
        "units": "mã cổ phiếu, điểm mục tiêu",
        "caveat": "Ảnh chụp hiện tại, mô tả; không phải chiến lược ngoài mẫu.",
    },
}


def figure_record(image_path: str, number: int) -> dict[str, Any]:
    basename = Path(image_path).name
    metadata = _FIGURES.get(basename)
    if metadata is None:
        raise ValueError(f"Thiếu metadata caption cho ảnh {image_path}.")
    return {
        "number": number,
        "path": image_path,
        "title": metadata["title"],
        "caption": metadata["explanation"],
        "source": metadata["source"],
        "result_json_fields": metadata["source"].split("·", 1)[1].strip() if "·" in metadata["source"] else "OHLCV fields and derived series described in source",
        "period": metadata["period"],
        "units": metadata["units"],
        "caveat": metadata["caveat"],
    }


def build_catalog(image_paths: list[str]) -> list[dict[str, Any]]:
    return [figure_record(path, index + 1) for index, path in enumerate(image_paths)]


def markdown_caption(record: dict[str, Any]) -> str:
    return (
        f"**Hình {record['number']}. {record['title']}.** {record['caption']} "
        f"Nguồn: {record['source']}. Kỳ: {record['period']}. Đơn vị: {record['units']}. "
        f"Lưu ý: {record['caveat']}"
    )


def update_markdown_captions(path: str | Path, repo_root: str | Path, catalog: list[dict[str, Any]]) -> None:
    """Ensure each local Markdown image is followed immediately by its caption."""
    markdown_path = Path(path)
    text = markdown_path.read_text(encoding="utf-8")
    by_name = {Path(item["path"]).name: item for item in catalog}
    lines = text.splitlines()
    result: list[str] = []
    image_pattern = re.compile(r"^!\[[^\]]*\]\(([^)]+)\)\s*$")
    index = 0
    while index < len(lines):
        line = lines[index]
        result.append(line)
        match = image_pattern.match(line.strip())
        if not match:
            index += 1
            continue
        raw_path = match.group(1).strip().strip("<>")
        record = by_name.get(Path(raw_path).name)
        if record is None:
            raise ValueError(f"Thiếu catalog cho ảnh Markdown: {raw_path}")
        next_index = index + 1
        while next_index < len(lines) and not lines[next_index].strip():
            next_index += 1
        if next_index < len(lines) and lines[next_index].lstrip().startswith("**Hình "):
            result.extend(lines[index + 1:next_index])
            result.append(markdown_caption(record))
            index = next_index + 1
            continue
        result.append("")
        result.append(markdown_caption(record))
        index += 1
    markdown_path.write_text("\n".join(result).rstrip() + "\n", encoding="utf-8")


def validate_markdown_images(path: str | Path, repo_root: str | Path) -> list[str]:
    """Return image-path or missing-caption problems for one report."""
    markdown_path = Path(path)
    text = markdown_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors: list[str] = []
    pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    for index, line in enumerate(lines):
        for match in pattern.finditer(line):
            raw_path = match.group(1).strip().strip("<>")
            candidate = (markdown_path.parent / raw_path).resolve()
            if not candidate.is_file():
                errors.append(f"{markdown_path}:{index + 1}: ảnh không tồn tại: {raw_path}")
            following = index + 1
            while following < len(lines) and not lines[following].strip():
                following += 1
            if following >= len(lines) or not re.match(r"\*\*Hình \d+\. .+\*\*", lines[following].strip()):
                errors.append(f"{markdown_path}:{index + 1}: thiếu tên hình và chú thích ngay sau ảnh")
            elif len(re.sub(r"\*", "", lines[following].strip()).split()) < 18:
                errors.append(f"{markdown_path}:{following + 1}: chú thích quá ngắn, thiếu ý nghĩa/nguồn")
    return errors


def write_catalog(path: str | Path, records: list[dict[str, Any]]) -> None:
    Path(path).write_text(json.dumps({"figure_count": len(records), "figures": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
