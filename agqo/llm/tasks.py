"""The two LLM jobs in AGQO, with schemas, validation and evaluation.

1. Mandate compiler: a Vietnamese investor instruction -> a validated Mandate (agqo/mandate.py).
   The Mandate changes the QAOA input: which stocks get a qubit, the QP target the warm start is
   built from, and the caps every sampled lot decision must satisfy. Evaluated on a hand-labelled
   test set against a keyword-rule baseline.
2. Explainer: a code-built evidence pack for one decision -> a Vietnamese explanation for the
   investor. Every number in the text must appear in the evidence pack, and every trade note must
   match an executed trade; the share of explanations that pass is reported.
"""

from __future__ import annotations

import json
import re

from ..config import SECTOR_EN
from ..mandate import SECTORS, Mandate, rule_parse
from .client import LLMClient, make_request

SECTOR_VI = {v: k for k, v in SECTOR_EN.items()}

# ---------------------------------------------------------------- 1. mandate compiler
MANDATE_SYSTEM = """You convert a Vietnamese retail investor's instruction into portfolio constraints for AGQO,
a tool that holds a whole-lot portfolio tracking the VN30 index. Output JSON matching the schema.

Fields:
- exclude_tickers: tickers the investor names (or unambiguously describes) as not wanted. Use only tickers from
  the list given; ignore tickers not in the list.
- exclude_sectors: whole sectors the investor does not want at all.
- sector_caps: a sector with a maximum share, e.g. "ngân hàng tối đa 30%" -> {{"sector": "Banking", "max_weight": 0.30}}.
  Fractions in words: "một phần ba" = 0.333, "1/4" = 0.25.
- max_weight_per_stock: maximum share of any single stock (0..1), e.g. "mỗi mã không quá 10%" -> 0.10.
- max_holdings: maximum number of stocks held.
- min_cash_pct: cash to keep, in percent (0..100), e.g. "giữ 5% tiền mặt" -> 5.
- needs_clarification: true only when the instruction asks for a limit without saying how much (for example
  "đừng mua quá nhiều ngân hàng"); then leave that constraint out and ask one short question in Vietnamese.

Rules: encode only what the instruction states; never invent limits. Weights are fractions 0..1, cash is percent.
Sectors (English label = Vietnamese name): {sectors}.
Tickers with their sectors: {tickers}."""


def mandate_schema(tickers: list[str]) -> dict:
    num01 = {"anyOf": [{"type": "number", "minimum": 0.0, "maximum": 1.0}, {"type": "null"}]}
    return {
        "type": "object",
        "properties": {
            "exclude_tickers": {"type": "array", "items": {"type": "string", "enum": tickers}, "maxItems": 30},
            "exclude_sectors": {"type": "array", "items": {"type": "string", "enum": SECTORS}, "maxItems": 9},
            "sector_caps": {"type": "array", "maxItems": 9, "items": {
                "type": "object",
                "properties": {"sector": {"type": "string", "enum": SECTORS},
                               "max_weight": {"type": "number", "minimum": 0.0, "maximum": 1.0}},
                "required": ["sector", "max_weight"], "additionalProperties": False}},
            "max_weight_per_stock": num01,
            "max_holdings": {"anyOf": [{"type": "integer", "minimum": 1, "maximum": 30}, {"type": "null"}]},
            "min_cash_pct": {"anyOf": [{"type": "number", "minimum": 0.0, "maximum": 99.0}, {"type": "null"}]},
            "needs_clarification": {"type": "boolean"},
            "clarification_question_vi": {"anyOf": [{"type": "string", "maxLength": 200}, {"type": "null"}]},
        },
        "required": ["exclude_tickers", "exclude_sectors", "sector_caps", "max_weight_per_stock", "max_holdings",
                     "min_cash_pct", "needs_clarification", "clarification_question_vi"],
        "additionalProperties": False,
    }


def mandate_request(text: str, sector_of: dict[str, str], seed: int = 0) -> dict:
    tickers = sorted(sector_of)
    system = MANDATE_SYSTEM.format(
        sectors=", ".join(f"{s} = {SECTOR_VI[s]}" for s in SECTORS),
        tickers=", ".join(f"{t} ({sector_of[t]})" for t in tickers))
    return make_request("mandate_compiler", system, text, mandate_schema(tickers), seed=seed,
                        temperature=0.0, max_tokens=512)


def parse_mandate(parsed: dict | None, tickers: set[str]) -> tuple[Mandate, bool, list[str]]:
    """(mandate, needs_clarification, validation errors). Invalid answers become an empty mandate."""
    if not isinstance(parsed, dict):
        return Mandate(), False, ["no valid JSON"]
    m = Mandate.from_dict(parsed)
    errs = m.validate(tickers)
    return (Mandate(), bool(parsed.get("needs_clarification")), errs) if errs else \
        (m, bool(parsed.get("needs_clarification")), [])


def _norm(m: Mandate) -> dict:
    d = m.to_dict()
    d["sector_caps"] = {k: round(v, 2) for k, v in sorted(d["sector_caps"].items())}
    for k in ("max_weight_per_stock", "min_cash_pct"):
        d[k] = None if d[k] is None else round(float(d[k]), 2)
    return d


def effective(m: Mandate) -> Mandate:
    """Drop limits that cannot bind (0 % minimum cash, 100 % caps) so equivalent answers compare equal."""
    d = m.to_dict()
    if d["min_cash_pct"] in (0, 0.0):
        d["min_cash_pct"] = None
    if d["max_weight_per_stock"] is not None and d["max_weight_per_stock"] >= 1:
        d["max_weight_per_stock"] = None
    d["sector_caps"] = {k: v for k, v in d["sector_caps"].items() if v < 1}
    return Mandate.from_dict(d)


def mandate_matches(pred: Mandate, gold: Mandate, effective_only: bool = False) -> dict[str, bool]:
    p, g = (_norm(effective(pred)), _norm(effective(gold))) if effective_only else (_norm(pred), _norm(gold))
    return {k: p[k] == g[k] for k in g}


# Hand-labelled evaluation set: (instruction, gold mandate, gold needs_clarification).
# Written with typical retail phrasing, including text typed without diacritics, fractions in words,
# tickers outside the universe (HVN) and two vague instructions that should trigger a question.
M = Mandate
TEST_SET = [
    ("Bỏ NVL và PDR", M(exclude_tickers=["NVL", "PDR"]), False),
    ("Không đầu tư vào bất động sản", M(exclude_sectors=["Real estate"]), False),
    ("Ngân hàng tối đa 30%", M(sector_caps={"Banking": 0.30}), False),
    ("khong mua co phieu ngan hang qua 25%", M(sector_caps={"Banking": 0.25}), False),
    ("Tôi chỉ muốn giữ tối đa 12 mã", M(max_holdings=12), False),
    ("Mỗi mã không quá 10%", M(max_weight_per_stock=0.10), False),
    ("Giữ lại 5% tiền mặt", M(min_cash_pct=5.0), False),
    ("Tránh các doanh nghiệp năng lượng và hàng không", M(exclude_sectors=["Aviation", "Energy"]), False),
    ("Không mua VIC, VHM, VRE vì tôi đã có nhiều cổ phiếu nhóm này", M(exclude_tickers=["VHM", "VIC", "VRE"]), False),
    ("Nhóm ngân hàng không vượt quá một phần ba danh mục", M(sector_caps={"Banking": 0.333}), False),
    ("Danh mục giống VN30, không có yêu cầu gì đặc biệt", M(), False),
    ("Tôi không thích rủi ro, hãy để 10% tiền mặt và mỗi cổ phiếu tối đa 8%",
     M(min_cash_pct=10.0, max_weight_per_stock=0.08), False),
    ("Loại bỏ cổ phiếu chứng khoán và bảo hiểm", M(exclude_sectors=["Brokerage", "Insurance"]), False),
    ("Bất động sản tối đa 10%, ngân hàng tối đa 35%", M(sector_caps={"Real estate": 0.10, "Banking": 0.35}), False),
    ("Không mua MWG", M(exclude_tickers=["MWG"]), False),
    ("Tôi muốn tập trung, chỉ 8 mã thôi", M(max_holdings=8), False),
    ("Tỷ trọng ngân hàng dưới 40% và giữ 2% tiền mặt", M(sector_caps={"Banking": 0.40}, min_cash_pct=2.0), False),
    ("Đừng mua FPT, tôi đang làm việc ở đó", M(exclude_tickers=["FPT"]), False),
    ("Không quá 15 cổ phiếu, mỗi cổ phiếu tối đa 12%", M(max_holdings=15, max_weight_per_stock=0.12), False),
    ("Tránh ngành tiêu dùng", M(exclude_sectors=["Consumer"]), False),
    ("Tôi muốn danh mục không có ngân hàng", M(exclude_sectors=["Banking"]), False),
    ("Ngân hàng không quá 1/4 danh mục", M(sector_caps={"Banking": 0.25}), False),
    ("toi muon giu 3% tien mat, bo SSI", M(min_cash_pct=3.0, exclude_tickers=["SSI"]), False),
    ("Không có điều kiện gì", M(), False),
    ("Không mua cổ phiếu công nghệ và năng lượng; ngân hàng tối đa 30%",
     M(exclude_sectors=["Energy", "Technology"], sector_caps={"Banking": 0.30}), False),
    ("Hạn chế bất động sản ở mức 5%", M(sector_caps={"Real estate": 0.05}), False),
    ("Bỏ hai mã hàng không VJC và HVN", M(exclude_tickers=["VJC"]), False),
    ("Ưu tiên an toàn: giữ 20% tiền mặt", M(min_cash_pct=20.0), False),
    ("Không nắm giữ HPG và GAS", M(exclude_tickers=["GAS", "HPG"]), False),
    ("Mỗi mã tối đa 15%, tổng cộng không quá 20 mã", M(max_weight_per_stock=0.15, max_holdings=20), False),
    ("Đừng mua quá nhiều cổ phiếu ngân hàng", M(), True),
    ("Tôi muốn ít rủi ro hơn", M(), True),
    # demo mandates used in the personalised backtest
    ("Không đầu tư bất động sản, ngân hàng tối đa 30%",
     M(exclude_sectors=["Real estate"], sector_caps={"Banking": 0.30}), False),
    ("Chỉ giữ tối đa 12 mã, mỗi mã không quá 10%, giữ 5% tiền mặt",
     M(max_holdings=12, max_weight_per_stock=0.10, min_cash_pct=5.0), False),
    ("Bỏ VIC, VHM, VRE và giữ ngành ngân hàng dưới 35%",
     M(exclude_tickers=["VHM", "VIC", "VRE"], sector_caps={"Banking": 0.35}), False),
]
DEMO = TEST_SET[-3:]


def evaluate_mandates(client: LLMClient | None, sector_of: dict[str, str]) -> dict:
    """Run the LLM compiler and the keyword baseline on the test set; return per-item rows and scores."""
    tickers = set(sector_of)
    llm_out = client.generate([mandate_request(t, sector_of, seed=i) for i, (t, _, _) in enumerate(TEST_SET)]) \
        if client else [None] * len(TEST_SET)
    rows = []
    for (text, gold, gold_q), rec in zip(TEST_SET, llm_out):
        base = rule_parse(text, tickers)
        r = {"instruction": text, "gold": gold.to_dict(), "gold_needs_clarification": gold_q,
             "rule": base.to_dict(), "rule_exact": all(mandate_matches(base, gold).values()) and not gold_q,
             "rule_effective": all(mandate_matches(base, gold, True).values()) and not gold_q}
        if rec is not None:
            m, q, errs = parse_mandate(rec["parsed"] if rec["status"] == "ok" else None, tickers)
            r |= {"llm": m.to_dict(), "llm_needs_clarification": q, "llm_errors": errs,
                  "llm_question": (rec["parsed"] or {}).get("clarification_question_vi"),
                  "llm_exact": all(mandate_matches(m, gold).values()) and q == gold_q,
                  "llm_effective": all(mandate_matches(m, gold, True).values()) and q == gold_q}
        rows.append(r)
    n = len(rows)
    score = {"items": n, "rule_exact_pct": 100 * sum(r["rule_exact"] for r in rows) / n,
             "rule_effective_pct": 100 * sum(r["rule_effective"] for r in rows) / n}
    if client:
        score |= {"llm_exact_pct": 100 * sum(r["llm_exact"] for r in rows) / n,
                  "llm_effective_pct": 100 * sum(r["llm_effective"] for r in rows) / n,
                  "llm_clarification_correct": sum(r["llm_needs_clarification"] == r["gold_needs_clarification"]
                                                   for r in rows),
                  "llm_invalid": sum(bool(r["llm_errors"]) for r in rows),
                  "llm_wrong_constraint_items": sum(not r["llm_effective"] for r in rows)}
    return {"score": score, "rows": rows}


# ---------------------------------------------------------------- 2. explainer
EXPLAIN_SYSTEM = """You write the quarterly note a Vietnamese retail investor reads next to their AGQO trade list.
Write in Vietnamese, plainly, for a non-expert. Use ONLY the numbers that appear in the evidence JSON, written
exactly as they appear there (same decimals); do not compute new numbers, percentages or totals. Do not promise
returns and do not give investment advice. Explain: what the portfolio does this quarter, why buying whole lots
needs an optimiser, what the quantum step (QAOA) contributed compared with the classical check, and the main risk.
Every number must be written together with what it measures; "labels_vi" gives the Vietnamese meaning of each
field (rephrase naturally, do not paste field names). Fields ending in _pct are percentages: write the % sign.
Tracking errors are always measured against the VN30 index: say "so với chỉ số VN30" in the same sentence.
The numbers in "vn30_market_structure" describe VN30 stocks in general: put them in a sentence about the VN30
group that does not mention the investor's portfolio.
Output JSON matching the schema: a 3-5 sentence summary, notes for at most 5 of the listed trades (ticker, action,
lots exactly as given), and 1-3 risk notes."""


LABELS_VI = {
    "tracking_error_vs_vn30_index_pct": "sai số bám so với chỉ số VN30",
    "agqo_whole_lot_portfolio": "danh mục lô chẵn do AGQO chọn",
    "nearest_lot_rounding_portfolio": "cách làm tròn từng mã về lô gần nhất",
    "ideal_fractional_share_portfolio": "danh mục lý tưởng nếu mua được cổ phiếu lẻ",
    "portfolio_sector_weights_pct": "tỷ trọng ngành trong danh mục của bạn",
    "vn30_market_structure": "đặc điểm chung của nhóm cổ phiếu VN30",
    "effective_independent_bets_among_vn30_stocks": "số nguồn rủi ro độc lập hiệu dụng của nhóm VN30",
    "share_of_vn30_stock_variance_from_one_market_factor_pct":
        "phần biến động của cổ phiếu VN30 do một yếu tố thị trường chung giải thích",
}

# Numbers whose sentence must name their reference (field group -> words that must appear / must not appear).
CONTEXT_RULES = {
    "tracking_error_vs_vn30_index_pct": (("VN30",), ()),
    "vn30_market_structure": (("VN30",), ("danh mục",)),
}


def describe_evidence(e: dict) -> dict:
    """Self-describing evidence: every field name states its reference, with Vietnamese labels.
    Accepts the older format (tracking_error_pct / market) and returns the new one; idempotent."""
    if "labels_vi" in e:
        return e
    out = {k: v for k, v in e.items() if k not in ("tracking_error_pct", "sector_weights_pct", "market")}
    te = e["tracking_error_pct"]
    out["tracking_error_vs_vn30_index_pct"] = {"agqo_whole_lot_portfolio": te["agqo_choice"],
                                               "nearest_lot_rounding_portfolio": te["nearest_lot_rounding"],
                                               "ideal_fractional_share_portfolio": te["ideal_fractional_shares"]}
    out["portfolio_sector_weights_pct"] = {SECTOR_VI.get(k, k): v for k, v in e["sector_weights_pct"].items()}
    out["vn30_market_structure"] = {
        "effective_independent_bets_among_vn30_stocks": e["market"]["effective_independent_bets"],
        "share_of_vn30_stock_variance_from_one_market_factor_pct": e["market"]["market_factor_share_pct"]}
    out["labels_vi"] = LABELS_VI
    return out


def explain_schema(tickers: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "summary_vi": {"type": "string", "maxLength": 1200},
            "trade_notes": {"type": "array", "maxItems": 5, "items": {
                "type": "object",
                "properties": {"ticker": {"type": "string", "enum": tickers},
                               "action": {"type": "string", "enum": ["mua", "bán"]},
                               "lots": {"type": "integer", "minimum": 1, "maximum": 1000},
                               "reason_vi": {"type": "string", "maxLength": 300}},
                "required": ["ticker", "action", "lots", "reason_vi"], "additionalProperties": False}},
            "risk_notes_vi": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string", "maxLength": 300}},
        },
        "required": ["summary_vi", "trade_notes", "risk_notes_vi"],
        "additionalProperties": False,
    }


def explain_request(evidence: dict, seed: int = 0) -> dict:
    tickers = sorted({t["ticker"] for t in evidence["trades"]}) or ["NONE"]
    return make_request("explainer", EXPLAIN_SYSTEM, evidence, explain_schema(tickers), seed=seed,
                        temperature=0.3, max_tokens=1200)


_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def _numbers(text: str) -> set[str]:
    """Normalised numeric tokens: '2,65' -> '2.65', '5.380.000' -> '5380000', '07' -> '7'."""
    out = set()
    for tok in _NUM.findall(text):
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", tok) or re.fullmatch(r"\d{1,3}(?:,\d{3})+", tok):
            tok = re.sub(r"[.,]", "", tok)
        tok = tok.replace(",", ".")
        try:
            out.add(f"{float(tok):g}")
        except ValueError:
            pass
    return out


_CLAUSE = re.compile(r",?\s+(?:nghĩa là|vì vậy|do đó|nên|khiến|làm)\s+")


def _context_issues(texts: list[str], evidence: dict) -> list[str]:
    """Meaning check: a number from a rule group must sit in a sentence that names its reference."""
    def leaves(v):                                             # values only: key names like "..._vn30_..." hold no data
        if isinstance(v, dict):
            return [x for u in v.values() for x in leaves(u)]
        if isinstance(v, list):
            return [x for u in v for x in leaves(u)]
        return [str(v)]

    owner: dict[str, set] = {}
    for group in CONTEXT_RULES:
        for n in _numbers(" ".join(leaves(evidence.get(group, {})))):
            owner.setdefault(n, set()).add(group)
    rest = {k: v for k, v in evidence.items() if k not in CONTEXT_RULES and k != "labels_vi"}
    for n in _numbers(" ".join(leaves(rest))):
        owner.setdefault(n, set()).add("other")
    issues = []
    for text in texts:
        for sent in re.split(r"(?<=[.!?;])\s+", text):
            for n in _numbers(sent):
                groups = owner.get(n, set())
                if len(groups) != 1 or "other" in groups:
                    continue                                   # ambiguous or unconstrained number
                need, forbid = CONTEXT_RULES[next(iter(groups))]
                low = re.sub(r"không phải (là )?danh mục( của bạn)?", "", sent.lower())
                # the reference must be named in the sentence; a forbidden word must not share the number's
                # clause (a consequence such as "..., nghĩa là danh mục vẫn chịu ảnh hưởng" is a valid inference)
                clause = next((c for c in _CLAUSE.split(low) if n in _numbers(c)), low)
                if not all(w.lower() in low for w in need) or any(w.lower() in clause for w in forbid):
                    issues.append(f"{n}: {sent.strip()[:120]}")
    return issues


def verify_explanation(parsed: dict | None, evidence: dict) -> dict:
    if not isinstance(parsed, dict):
        return {"ok": False, "unverified_numbers": [], "trade_mismatches": ["no valid JSON"], "context_issues": [],
                "attribution_issues": []}
    allowed = _numbers(json.dumps(evidence, ensure_ascii=False))
    text = " ".join([parsed.get("summary_vi", ""), *[n.get("reason_vi", "") for n in parsed.get("trade_notes", [])],
                     *parsed.get("risk_notes_vi", [])])
    bad = sorted(_numbers(text) - allowed)
    trades = {(t["ticker"], t["action"], t["lots"]) for t in evidence["trades"]}
    mism = [f"{n['ticker']} {n['action']} {n['lots']}" for n in parsed.get("trade_notes", [])
            if (n["ticker"], n["action"], n["lots"]) not in trades]
    ctx = _context_issues([text], evidence) if "labels_vi" in evidence else []
    attr = []
    if "labels_vi" in evidence:                      # V3.2: each number tied to its strategy, metric and unit
        from .attribution import check_attribution

        pieces = [parsed.get("summary_vi", ""), *parsed.get("risk_notes_vi", []),
                  *[f"{n.get('ticker', '')} {n.get('reason_vi', '')}" for n in parsed.get("trade_notes", [])]]
        attr = [i for s in pieces for i in check_attribution(s, evidence)]
    return {"ok": not bad and not mism and not ctx and not attr, "unverified_numbers": bad, "trade_mismatches": mism,
            "context_issues": ctx, "attribution_issues": attr}
