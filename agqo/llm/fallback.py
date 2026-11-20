"""Deterministic Vietnamese explanation built only from the code-made evidence pack, plus checks for factual
market claims the evidence cannot support.

Used when the LLM explanation fails any verifier check (numbers, trades, context, attribution, market claims),
so the page never shows an unchecked sentence as the explanation of a decision.
"""

from __future__ import annotations

import re
import unicodedata

# Claims about market rules that are false or outside the evidence. HOSE has an odd-lot order book (1–99
# shares); AGQO's board-lot rule is an assumption of the scenario, not a market prohibition.
FALSE_MARKET_CLAIMS = [
    (r"khong (?:cho phep|the|duoc)(?: mua ban| mua| giao dich)?(?: co phieu)? (?:le|lo le)",
     "says odd lots cannot be traded; HOSE has an odd-lot order book, board lots are AGQO's scenario rule"),
    (r"cam (?:giao dich |mua ban |mua )?(?:co phieu |lo )?le", "says odd lots are prohibited"),
    (r"chi (?:duoc|cho phep) (?:mua ban|mua|giao dich) (?:theo )?lo chan", "says only board lots may be traded"),
    (r"(?:dam bao|chac chan|cam ket) (?:loi nhuan|lai|sinh loi)", "promises returns"),
]


def _fold(s: str) -> str:
    t = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def market_claim_issues(texts: list[str]) -> list[dict]:
    out = []
    for text in texts:
        f = _fold(text)
        for pat, why in FALSE_MARKET_CLAIMS:
            m = re.search(pat, f)
            if m:
                out.append({"type": "false_market_claim", "why": why, "text": text[max(0, m.start() - 20): m.end() + 20]})
    return out


def _n(v, d=2) -> str:
    return f"{v:.{d}f}".replace(".", ",")


def deterministic_explanation(ev: dict) -> dict:
    """Same schema as the LLM explanation; every number copied from the evidence with its reference."""
    te = ev["tracking_error_vs_vn30_index_pct"]
    q = ev.get("quantum", {})
    summary = (
        f"Ngày {ev['date']}, tài khoản trị giá {_n(ev['account_value_million_vnd'])} triệu đồng giữ "
        f"{ev['stocks_held_after_trade']} mã sau giao dịch. Kịch bản của AGQO chỉ đặt lệnh theo lô chẵn, "
        f"nên cần chọn cả tổ hợp lô thay vì làm tròn từng mã. "
        f"Sai số bám so với chỉ số VN30 ước tính của danh mục lô chẵn do AGQO chọn là {_n(te['agqo_whole_lot_portfolio'])}%. "
        f"Với cách làm tròn từng mã về lô gần nhất, sai số bám so với chỉ số VN30 là {_n(te['nearest_lot_rounding_portfolio'])}%. "
        f"Nếu mua được cổ phiếu lẻ, danh mục lý tưởng có sai số bám so với chỉ số VN30 là "
        f"{_n(te['ideal_fractional_share_portfolio'])}%.")
    if q:
        gap = q.get("normalised_gap_to_exact_optimum_pct")
        summary += (f" Mạch QAOA {q['qubits']} qubit, {q['layers']} lớp đưa {_n(q['near_optimal_share_of_shots_pct'], 1)}% "
                    f"số lượt đo vào nhóm lựa chọn gần tối ưu"
                    + (f"; lựa chọn được dùng cách tối ưu chính xác {_n(gap)}%" if gap is not None else "")
                    + ", được kiểm tra bằng liệt kê toàn bộ các lựa chọn lô.")
    notes = [{"ticker": t["ticker"], "action": t["action"], "lots": t["lots"],
              "reason_vi": f"{t['action'].capitalize()} {t['lots']} lô {t['ticker']}, giá trị {_n(t['value_million_vnd'])} triệu đồng, "
                           "để đưa tỷ trọng về gần danh mục lý tưởng."} for t in ev.get("trades", [])[:5]]
    risks = ["Sai số bám là ước tính từ dữ liệu quá khứ, không phải dự báo lợi nhuận; giá cổ phiếu có thể biến động mạnh.",
             "Giá lịch sử là giá đã điều chỉnh cổ tức và chia tách; giá khớp lệnh thực tế có thể khác."]
    return {"summary_vi": summary, "trade_notes": notes, "risk_notes_vi": risks}
