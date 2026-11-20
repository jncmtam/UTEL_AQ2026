"""Attribution check for LLM explanations: is each number tied to the right strategy, metric and unit?

V3.1 only checked that every number in the text also appears somewhere in the evidence. Two correct numbers
written for the wrong strategies (AGQO's tracking error given as the rounding baseline's, and vice versa) passed.

Here the evidence is turned into facts (value, unit, metric, entity). For every number in the text the checker
finds, in the same clause, the nearest words that name an entity (AGQO, nearest-lot rounding, the ideal
fractional portfolio, a ticker, a sector) and a metric (tracking error, lots, share of shots, ...), and the unit
written right after the number. It reports

  misattributed  the clause names entity E and metric M, the evidence has that fact, and the number differs
                 from it (typically: the number belongs to another entity)
  wrong_unit     the unit written after the number matches no fact with that value
  missing_unit   the number is a percentage in every matching fact but no % sign follows it

Clauses are split at punctuation and at contrast connectors ("so với", "còn", "trong khi"), so
"AGQO là 5,39% so với 5,56% của cách làm tròn" attributes each number to its own strategy.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..config import SECTOR_EN

SECTOR_VI = {v: k for k, v in SECTOR_EN.items()}


@dataclass(frozen=True)
class Fact:
    value: str          # normalised like _numbers(): f"{float:g}"
    unit: str           # pct | lot | million | stocks | qubit | layer | gate | count | date | none
    metric: str
    entity: str | None
    path: str


def _norm_num(tok: str) -> str | None:
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", tok) or re.fullmatch(r"\d{1,3}(?:,\d{3})+", tok):
        tok = re.sub(r"[.,]", "", tok)
    tok = tok.replace(",", ".")
    try:
        return f"{float(tok):g}"
    except ValueError:
        return None


def _g(v) -> str:
    return f"{float(v):g}"


def facts(evidence: dict) -> list[Fact]:
    """Facts of a described evidence pack (llm.tasks.describe_evidence output)."""
    out: list[Fact] = []
    te = evidence.get("tracking_error_vs_vn30_index_pct", {})
    for key, ent in (("agqo_whole_lot_portfolio", "agqo"), ("nearest_lot_rounding_portfolio", "rounding"),
                     ("ideal_fractional_share_portfolio", "ideal")):
        if key in te and te[key] is not None:
            out.append(Fact(_g(te[key]), "pct", "tracking_error", ent, f"tracking_error_vs_vn30_index_pct.{key}"))
    if evidence.get("account_value_million_vnd") is not None:
        out.append(Fact(_g(evidence["account_value_million_vnd"]), "million", "account_value", None,
                        "account_value_million_vnd"))
    if evidence.get("stocks_held_after_trade") is not None:
        out.append(Fact(_g(evidence["stocks_held_after_trade"]), "stocks", "holdings", None, "stocks_held_after_trade"))
    for t in evidence.get("trades", []):
        out.append(Fact(_g(t["lots"]), "lot", "trade_lots", t["ticker"], f"trades.{t['ticker']}.lots"))
        if "value_million_vnd" in t:
            out.append(Fact(_g(t["value_million_vnd"]), "million", "trade_value", t["ticker"],
                            f"trades.{t['ticker']}.value_million_vnd"))
    for sec, v in evidence.get("portfolio_sector_weights_pct", {}).items():
        out.append(Fact(_g(v), "pct", "sector_weight", _fold(sec), f"portfolio_sector_weights_pct.{sec}"))
    q = evidence.get("quantum", {})
    for key, unit, metric in (("qubits", "qubit", "qubits"), ("layers", "layer", "layers"),
                              ("two_qubit_gates", "gate", "gates"),
                              ("near_optimal_share_of_shots_pct", "pct", "near_optimal_share"),
                              ("normalised_gap_to_exact_optimum_pct", "pct", "gap")):
        if q.get(key) is not None:
            out.append(Fact(_g(q[key]), unit, metric, None, f"quantum.{key}"))
    ms = evidence.get("vn30_market_structure", {})
    if ms.get("effective_independent_bets_among_vn30_stocks") is not None:
        out.append(Fact(_g(ms["effective_independent_bets_among_vn30_stocks"]), "count", "effective_bets", None,
                        "vn30_market_structure.effective_independent_bets_among_vn30_stocks"))
    if ms.get("share_of_vn30_stock_variance_from_one_market_factor_pct") is not None:
        out.append(Fact(_g(ms["share_of_vn30_stock_variance_from_one_market_factor_pct"]), "pct",
                        "market_factor_share", None,
                        "vn30_market_structure.share_of_vn30_stock_variance_from_one_market_factor_pct"))
    for part in re.findall(r"\d+", str(evidence.get("date", ""))):
        out.append(Fact(_g(part), "date", "date", None, "date"))
    for n in re.findall(r"\d+", str(q.get("checked_by", ""))):
        out.append(Fact(_g(n), "count", "states", None, "quantum.checked_by"))
    return out


def _fold(s: str) -> str:
    """Lower case without diacritics (đ -> d) for cue matching."""
    t = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


ENTITY_CUES = {
    "agqo": ["agqo", "lo chan", "danh muc cua ban", "danh muc ban"],
    "rounding": ["lam tron", "lo gan nhat"],
    "ideal": ["ly tuong", "co phieu le", "mua le", "chia nho"],
}
# Metric words (folded). Lots and trade values are recognised from the unit, not from words.
METRIC_CUES = {
    "tracking_error": ["sai so bam", "sai so", "sai lech bam", "do lech", "bam sat", "bam theo", "bam chi so"],
    "near_optimal_share": ["luot do", "lan do", "phep do", "gan toi uu"],
    "gap": ["cach toi uu", "khoang cach", "chenh lech so voi toi uu"],
    "qubits": ["qubit"],
    "layers": ["lop"],
    "gates": ["cong hai qubit", "cong 2 qubit", "cong logic", "cong luong tu"],
    "account_value": ["gia tri tai khoan", "tai khoan", "so von"],
    "holdings": ["ma co phieu", "nam giu"],
    "sector_weight": ["ty trong", "chiem", "nganh"],
    "effective_bets": ["nguon rui ro", "doc lap"],
    "market_factor_share": ["yeu to thi truong", "nhan to thi truong", "yeu to chung", "nhan to chung"],
}
METRIC_UNIT = {"tracking_error": "pct", "near_optimal_share": "pct", "gap": "pct", "qubits": "qubit",
               "layers": "layer", "gates": "gate", "account_value": "million", "holdings": "stocks",
               "sector_weight": "pct", "effective_bets": "count", "market_factor_share": "pct",
               "trade_lots": "lot", "trade_value": "million"}
MULTI_ENTITY = {"tracking_error", "sector_weight", "trade_lots", "trade_value"}
UNITS = [("pct", r"%|phần trăm"), ("lot", r"lô\b"), ("million", r"triệu"), ("stocks", r"mã\b|cổ phiếu"),
         ("qubit", r"qubit"), ("layer", r"lớp"), ("gate", r"cổng")]
_NUM = re.compile(r"(?<![A-Za-zÀ-ỹ\d^])\d+(?:[.,]\d+)*")
_SENT = re.compile(r"[;!?]|\.(?!\d)")
_SPLIT = re.compile(r"[;:!?]|[.,](?!\d)|\s(?:so với|còn|trong khi|nhưng|thay vì|và)\s")


def _spans(text: str, rx) -> list[tuple[int, int]]:
    spans, last = [], 0
    for m in rx.finditer(text):
        spans.append((last, m.start()))
        last = m.end()
    spans.append((last, len(text)))
    return spans


def _nearest(cues: dict[str, list[str]], folded: str, lo: int, hi: int, pos: int, allowed: set,
             before_only: bool = False) -> str | None:
    best, bd = None, None
    seg = folded[lo:hi]
    for key, words in cues.items():
        if key not in allowed:
            continue
        for w in words:
            for m in re.finditer(re.escape(w), seg):
                a = lo + m.start()
                if before_only and a > pos:
                    continue
                d = abs(a - pos) if a < pos else abs(a - pos) + 0.5       # prefer cues before on ties
                if bd is None or d < bd:
                    best, bd = key, d
    return best


def _unit_after(text: str, end: int) -> str | None:
    tail = text[end:end + 14].lower()
    for unit, pat in UNITS:
        if re.match(rf"\s*(?:{pat})", tail):
            return unit
    return None


def check_attribution(text: str, evidence: dict) -> list[dict]:
    fs = facts(evidence)
    by_value: dict[str, list[Fact]] = {}
    for f in fs:
        by_value.setdefault(f.value, []).append(f)
    tickers = sorted({f.entity for f in fs if f.metric in ("trade_lots", "trade_value") and f.entity}, key=len,
                     reverse=True)
    sectors = sorted({f.entity for f in fs if f.metric == "sector_weight" and f.entity}, key=len, reverse=True)
    present = {f.metric for f in fs}
    folded = _fold(text)
    issues = []
    clauses, sentences = _spans(text, _SPLIT), _spans(text, _SENT)
    for m in _NUM.finditer(text):
        v = _norm_num(m.group())
        if v is None or v not in by_value:
            continue                                          # unverified numbers are reported elsewhere
        cands = by_value[v]
        if all(f.unit == "date" for f in cands):
            continue
        lo, hi = next((a, b) for a, b in clauses if a <= m.start() <= b)
        slo, _ = next((a, b) for a, b in sentences if a <= m.start() <= b)
        clause = text[lo:hi].strip()
        unit = _unit_after(text, m.end())
        if unit is not None and not any(f.unit == unit or (unit == "stocks" and f.unit == "count") for f in cands):
            issues.append({"type": "wrong_unit", "number": m.group(), "unit_written": unit,
                           "evidence_units": sorted({f.unit for f in cands}), "clause": clause})
            continue
        if unit is None and all(f.unit == "pct" for f in cands):
            issues.append({"type": "missing_unit", "number": m.group(), "expected": "%", "clause": clause})
        if unit is None:     # no unit written: only unitless metrics, or the metrics this value already has
            allowed = {k for k, u in METRIC_UNIT.items() if u == "count" and k in present} | {f.metric for f in cands}
        else:
            allowed = {k for k, u in METRIC_UNIT.items() if u == unit and k in present}
        seg = text[lo:hi]
        ticker_hits = [(abs(seg.find(tk) + lo - m.start()), tk) for tk in tickers if tk in seg]
        if unit == "lot":
            metric = "trade_lots"
        elif unit == "million" and ticker_hits:
            metric = "trade_value"
        else:
            metric = (_nearest(METRIC_CUES, folded, lo, hi, m.start(), allowed)
                      or _nearest(METRIC_CUES, folded, slo, m.start(), m.start(), allowed, before_only=True))
        if metric is None:
            continue
        entity = None
        if metric == "tracking_error":
            entity = _nearest(ENTITY_CUES, folded, lo, hi, m.start(), set(ENTITY_CUES))
        elif metric in ("trade_lots", "trade_value"):
            entity = min(ticker_hits)[1] if ticker_hits else None
        elif metric == "sector_weight":
            hits = [(abs(folded[lo:hi].find(s) + lo - m.start()), s) for s in sectors if s in folded[lo:hi]]
            entity = min(hits)[1] if hits else None
        expected = [f for f in fs if f.metric == metric and (metric not in MULTI_ENTITY or entity is None
                                                               or f.entity == entity)]
        if not expected or any(f.value == v for f in expected):
            continue
        owner = [f.path for f in cands]
        issues.append({"type": "misattributed", "number": m.group(), "metric": metric, "entity": entity,
                       "evidence_value": [f.value for f in expected], "number_belongs_to": owner,
                       "clause": clause})
    return issues
