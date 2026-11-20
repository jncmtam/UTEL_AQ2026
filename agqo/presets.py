"""Product presets: starting points grounded in the data and in where AGQO helps (or does not).

Each preset fills the structured constraint form; the user can edit every field before running. The
`expect` class is what the V3 evidence predicts; the V3.2 preset run (protocol §6) measures it again and the
app shows the measured numbers next to each preset.
"""

from __future__ import annotations

from .mandate import Mandate

PRESETS = [
    {"id": "small20", "title_vi": "Tài khoản nhỏ 20 triệu, không quy tắc", "capital_million": 20,
     "mandate": Mandate(), "expect": "favourable",
     "why_vi": "Ở 20 triệu, một lô của nhiều mã chiếm 3–7% vốn. Làm tròn từng mã về lô gần nhất làm lệch danh mục "
               "nhiều nhất; đây là nơi chọn tổ hợp lô có lợi rõ nhất.",
     "tradeoff_vi": "Vẫn chỉ giữ được khoảng 10–15 mã, nên sai số bám cao hơn ETF dù thấp hơn làm tròn."},
    {"id": "bank25_200", "title_vi": "200 triệu, ngân hàng tối đa 25%", "capital_million": 200,
     "mandate": Mandate(sector_caps={"Banking": 0.25}), "expect": "favourable",
     "why_vi": "Ngân hàng chiếm khoảng 40% VN30. Trần 25% là yêu cầu cá nhân hóa mà ETF không làm được. Trần được "
               "kiểm tra trên giá trị tài khoản sau phí.",
     "tradeoff_vi": "Giới hạn ngành làm danh mục lệch khỏi chỉ số: sai số bám tăng so với không có trần."},
    {"id": "exclude_100", "title_vi": "100 triệu, bỏ bất động sản và VIC, VHM, VRE", "capital_million": 100,
     "mandate": Mandate(exclude_sectors=["Real estate"], exclude_tickers=["VHM", "VIC", "VRE"]), "expect": "favourable",
     "why_vi": "Người đã có nhiều cổ phiếu nhóm Vingroup hoặc bất động sản muốn tránh trùng rủi ro.",
     "tradeoff_vi": "Bỏ cả một nhóm có tỷ trọng lớn trong VN30 làm sai số bám tăng rõ."},
    {"id": "large500", "title_vi": "500 triệu, không quy tắc", "capital_million": 500, "mandate": Mandate(),
     "expect": "unfavourable",
     "why_vi": "Ở 500 triệu, mỗi lô chỉ chiếm dưới 1,5% vốn nên làm tròn đơn giản đã gần tối ưu.",
     "tradeoff_vi": "AGQO gần như không hơn làm tròn lô gần nhất; dùng để thấy giới hạn của sản phẩm."},
    {"id": "one_stock_20", "title_vi": "Chỉ giữ 1 mã (20 triệu)", "capital_million": 20,
     "mandate": Mandate(max_holdings=1), "expect": "unfavourable",
     "why_vi": "Ca biên hợp lệ: hệ thống chọn mã bám VN30 tốt nhất có thể mua, không cần mạch lượng tử.",
     "tradeoff_vi": "Một mã không thể bám chỉ số; sai số bám rất cao. Hệ thống vẫn tuân thủ đúng yêu cầu."},
    {"id": "cap2_20", "title_vi": "Mỗi mã tối đa 2% (20 triệu)", "capital_million": 20,
     "mandate": Mandate(max_weight_per_stock=0.02), "expect": "infeasible",
     "why_vi": "Mỗi mã 2% của 20 triệu là 400 nghìn đồng, nhỏ hơn một lô của mọi mã VN30.",
     "tradeoff_vi": "Không có danh mục lô chẵn nào thỏa; hệ thống nói rõ quy tắc nào chặn và gợi ý nới."},
    {"id": "vague_bank", "title_vi": "Câu mơ hồ: “Đừng mua quá nhiều ngân hàng”", "capital_million": 50,
     "mandate": Mandate(), "instruction_vi": "Đừng mua quá nhiều cổ phiếu ngân hàng", "expect": "clarification",
     "why_vi": "Câu không nói giới hạn bao nhiêu. Hệ thống hỏi lại và không hiện lệnh cá nhân hóa cho đến khi bạn trả lời.",
     "tradeoff_vi": "Cần thêm một bước trả lời; đổi lại không có giới hạn nào bị đoán."},
]


def preset(pid: str) -> dict:
    return next(p for p in PRESETS if p["id"] == pid)


def public(p: dict) -> dict:
    return {k: (v.to_dict() if isinstance(v, Mandate) else v) for k, v in p.items()}
