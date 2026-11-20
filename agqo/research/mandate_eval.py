"""Instruction-parsing experiment (protocol §3a): evaluation set, the current English prompt, scoring.

The evaluation set was written before the first run and shares no instruction with the first set
(agqo/llm/tasks.py TEST_SET). It is team-written, so it measures the parser on realistic phrasing, not on
independent users. Categories:

  clear        every limit is stated; gold = the constraints
  ambiguous    a limit is wanted but its size or target is not stated; the system must ask before trading
  conflicting  two rules contradict each other; the system must ask before trading
  infeasible   the rules are clear and consistent but no whole-lot portfolio satisfies them at that capital;
               the deterministic check must name the blocking rule (the LLM is not asked about feasibility)
"""

from __future__ import annotations

import re

from ..config import SECTOR_EN
from ..llm.client import make_request
from ..mandate import SECTORS, Mandate

M = Mandate
SECTOR_VI = {v: k for k, v in SECTOR_EN.items()}
ALL_SECTORS = sorted(SECTORS)

# (id, category, capital_million, instruction, gold mandate, extra)
ITEMS = [
    # ---------------- clear (24)
    ("c01", "clear", 50, "Tôi không muốn có cổ phiếu ngân hàng nào", M(exclude_sectors=["Banking"]), {}),
    ("c02", "clear", 30, "bo HPG voi HSG ra nhe", M(exclude_tickers=["HPG"]), {"note": "HSG is not a VN30 ticker"}),
    ("c03", "clear", 100, "Ngành ngân hàng chiếm không quá 35% thôi", M(sector_caps={"Banking": 0.35}), {}),
    ("c04", "clear", 80, "Giữ 15% tiền mặt phòng khi cần", M(min_cash_pct=15.0), {}),
    ("c05", "clear", 200, "Mỗi cổ phiếu đừng quá 8%", M(max_weight_per_stock=0.08), {}),
    ("c06", "clear", 100, "Tôi chỉ muốn nắm tối đa 10 mã", M(max_holdings=10), {}),
    ("c07", "clear", 60, "Không đầu tư chứng khoán và bảo hiểm, giữ 5% tiền mặt",
     M(exclude_sectors=["Brokerage", "Insurance"], min_cash_pct=5.0), {}),
    ("c08", "clear", 300, "Bất động sản dưới 15%, mỗi mã dưới 10%",
     M(sector_caps={"Real estate": 0.15}, max_weight_per_stock=0.10), {}),
    ("c09", "clear", 40, "Loại VNM và SAB vì tôi không thích ngành đồ uống", M(exclude_tickers=["SAB", "VNM"]), {}),
    ("c10", "clear", 120, "ngan hang toi da mot phan tu danh muc", M(sector_caps={"Banking": 0.25}), {}),
    ("c11", "clear", 25, "Tôi làm ở MBB nên không muốn mua thêm MBB", M(exclude_tickers=["MBB"]), {}),
    ("c12", "clear", 150, "Tránh hàng không, năng lượng; tối đa 15 mã",
     M(exclude_sectors=["Aviation", "Energy"], max_holdings=15), {}),
    ("c13", "clear", 70, "Giữ lại 1/10 số tiền dưới dạng tiền mặt", M(min_cash_pct=10.0), {}),
    ("c14", "clear", 90, "Không quá 20% cho nhóm nguyên vật liệu", M(sector_caps={"Materials": 0.20}), {}),
    ("c15", "clear", 250, "Công nghệ tối đa 10%, tiêu dùng tối đa 20%",
     M(sector_caps={"Technology": 0.10, "Consumer": 0.20}), {}),
    ("c16", "clear", 100, "Không mua cổ phiếu nhà Vingroup: VIC, VHM, VRE", M(exclude_tickers=["VHM", "VIC", "VRE"]), {}),
    ("c17", "clear", 180, "Mỗi mã tối đa 12% và giữ 3% tiền mặt", M(max_weight_per_stock=0.12, min_cash_pct=3.0), {}),
    ("c18", "clear", 20, "Tôi muốn danh mục bám sát VN30, không cần điều kiện gì", M(), {}),
    ("c19", "clear", 45, "Loại bỏ ngành bất động sản", M(exclude_sectors=["Real estate"]), {}),
    ("c20", "clear", 400, "ngân hàng <= 30%, bđs <= 10%", M(sector_caps={"Banking": 0.30, "Real estate": 0.10}), {}),
    ("c21", "clear", 100, "Chỉ 6 mã thôi, giữ 10% tiền", M(max_holdings=6, min_cash_pct=10.0), {}),
    ("c22", "clear", 60, "Không mua GAS, PLX, POW", M(exclude_tickers=["GAS", "PLX", "POW"]), {}),
    ("c23", "clear", 500, "Tối đa một nửa danh mục là ngân hàng", M(sector_caps={"Banking": 0.50}), {}),
    ("c24", "clear", 35, "Không mua SSI và tránh luôn ngành bảo hiểm", M(exclude_tickers=["SSI"], exclude_sectors=["Insurance"]), {}),
    # ---------------- ambiguous (10): gold keeps only what is stated
    ("a01", "ambiguous", 100, "Đừng mua nhiều bất động sản quá", M(), {"missing": "sector_caps", "dimension": "bất động sản"}),
    ("a02", "ambiguous", 50, "Tôi muốn ít rủi ro", M(), {"missing": "risk", "dimension": "rủi ro"}),
    ("a03", "ambiguous", 80, "Giữ một ít tiền mặt", M(), {"missing": "min_cash_pct", "dimension": "tiền mặt"}),
    ("a04", "ambiguous", 100, "Đừng dồn tiền vào vài mã", M(), {"missing": "max_weight_per_stock", "dimension": "mỗi mã"}),
    ("a05", "ambiguous", 60, "Không muốn nắm quá nhiều mã", M(), {"missing": "max_holdings", "dimension": "mã"}),
    ("a06", "ambiguous", 100, "Giữ 5% tiền mặt và đừng mua nhiều ngân hàng quá", M(min_cash_pct=5.0),
     {"missing": "sector_caps", "dimension": "ngân hàng"}),
    ("a07", "ambiguous", 120, "Hạn chế cổ phiếu họ Vin", M(), {"missing": "exclude_or_cap", "dimension": "vin"}),
    ("a08", "ambiguous", 90, "Ngân hàng vừa phải thôi", M(), {"missing": "sector_caps", "dimension": "ngân hàng"}),
    ("a09", "ambiguous", 200, "Tôi muốn danh mục an toàn hơn VN30", M(), {"missing": "risk", "dimension": "an toàn"}),
    ("a10", "ambiguous", 70, "Bỏ VJC, và bớt công nghệ đi", M(exclude_tickers=["VJC"]),
     {"missing": "sector_caps", "dimension": "công nghệ"}),
    # ---------------- conflicting (8): gold keeps the non-conflicting part
    ("k01", "conflicting", 100, "Không mua ngân hàng, nhưng ngân hàng tối đa 20%", M(), {"conflict": ["exclude_sectors", "sector_caps"]}),
    ("k02", "conflicting", 80, "Giữ 30% tiền mặt và dùng hết 100% vốn mua cổ phiếu", M(), {"conflict": ["min_cash_pct", "invest_all"]}),
    ("k03", "conflicting", 50, "Loại FPT ra nhưng nhớ mua FPT thật nhiều", M(), {"conflict": ["exclude_tickers", "include"]}),
    ("k04", "conflicting", 100, "Chỉ giữ 3 mã nhưng phải có ít nhất 10 mã", M(), {"conflict": ["max_holdings", "min_holdings"]}),
    ("k05", "conflicting", 200, "Mỗi mã tối đa 5%, tối đa 4 mã, và đầu tư hết tiền", M(),
     {"conflict": ["max_weight_per_stock", "max_holdings", "invest_all"]}),
    ("k06", "conflicting", 150, "Bất động sản tối đa 10% nhưng ít nhất 20%", M(), {"conflict": ["sector_caps", "sector_min"]}),
    ("k07", "conflicting", 60, "Không giữ tiền mặt, giữ 10% tiền mặt", M(), {"conflict": ["min_cash_pct"]}),
    ("k08", "conflicting", 100, "Tránh ngành tiêu dùng nhưng tiêu dùng chiếm 30% danh mục", M(), {"conflict": ["exclude_sectors", "sector_target"]}),
    # ---------------- infeasible (8): clear rules, blocked by the deterministic check
    ("i01", "infeasible", 20, "Mỗi mã tối đa 1%", M(max_weight_per_stock=0.01), {"blocking": "per_stock_cap_below_one_lot"}),
    ("i02", "infeasible", 10, "Không mua ngân hàng, bất động sản, tiêu dùng, nguyên vật liệu, năng lượng, chứng khoán, công nghệ, "
     "bảo hiểm và hàng không", M(exclude_sectors=ALL_SECTORS), {"blocking": "empty_universe"}),
    ("i03", "infeasible", 5, "Giữ 95% tiền mặt", M(min_cash_pct=95.0), {"blocking": "no_affordable_lot"}),
    ("i04", "infeasible", 20, "Chỉ mua, mỗi mã tối đa 0,5%", M(max_weight_per_stock=0.005), {"blocking": "per_stock_cap_below_one_lot"}),
    ("i05", "infeasible", 50, "Chỉ mua cổ phiếu hàng không, mỗi mã tối đa 2%",
     M(exclude_sectors=[s for s in ALL_SECTORS if s != "Aviation"], max_weight_per_stock=0.02), {"blocking": "per_stock_cap_below_one_lot"}),
    ("i06", "infeasible", 5, "Giữ 90% tiền mặt", M(min_cash_pct=90.0), {"blocking": "no_affordable_lot"}),
    ("i07", "infeasible", 8, "Tôi chỉ mua cổ phiếu hàng không",
     M(exclude_sectors=[s for s in ALL_SECTORS if s != "Aviation"]), {"blocking": "no_affordable_lot"}),
    ("i08", "infeasible", 30, "Mỗi cổ phiếu không quá 3%", M(max_weight_per_stock=0.03), {"blocking": "per_stock_cap_below_one_lot"}),
]

# ---------------------------------------------------------------- current prompt (English) and schema
PROMPT_VERSION = "mandate-v3.2-2026-11-20"
SYSTEM_PROMPT = """You are the constraint compiler of AGQO, a tool that builds a whole-lot (100-share) stock portfolio that tracks
the VN30 index for a Vietnamese retail investor. The investor writes in Vietnamese, sometimes without diacritics
or with abbreviations (e.g. "bđs" = bất động sản = real estate, "nh" = ngân hàng = banking). You return JSON that
matches the schema. Code validates your answer, checks feasibility and computes every trade; you never do that.

Fields
- exclude_tickers: tickers the investor does not want. Only tickers from the list below; ignore other tickers.
- exclude_sectors: sectors the investor does not want at all.
- sector_caps: a maximum share of the portfolio for a sector, as a fraction (35% -> 0.35, "một phần tư" -> 0.25,
  "một nửa" -> 0.5, "một phần ba" -> 0.333).
- max_weight_per_stock: maximum share of any single stock, fraction 0..1.
- max_holdings: maximum number of stocks held (integer).
- min_cash_pct: cash to keep, in percent 0..100 ("1/10 số tiền" -> 10).
- status: one of
    "ok"                  every rule the investor wants is fully specified;
    "needs_clarification" the investor wants a limit but does not say how large it is or what it applies to
                          (e.g. "đừng mua nhiều ngân hàng quá", "ít rủi ro", "giữ một ít tiền mặt");
    "conflict"            two requests contradict each other (e.g. exclude a sector and also cap or require it;
                          keep cash and also invest everything; at most 3 stocks and at least 10 stocks).
- missing_fields: for needs_clarification, the field(s) whose value is missing; otherwise [].
- conflicts: for conflict, one short English sentence per contradiction; otherwise [].
- clarification_question_vi: for needs_clarification or conflict, ONE short question in Vietnamese that asks
  exactly for the missing value or for which of the contradicting requests to keep; otherwise null.

Rules
1. Encode only what the instruction states. Never invent a number. Vague words (nhiều, ít, vừa phải, hạn chế,
   an toàn) without a number are not limits: put status "needs_clarification" and leave that field out.
2. Keep every clearly stated rule even when another part of the instruction needs clarification.
3. When two rules conflict, leave both out, list the conflict, and ask which one to keep.
4. Do not judge whether the rules can be met with the investor's money; code checks that.
5. AGQO cannot force a minimum holding of a stock or sector; a request for one together with an exclusion or a
   cap on the same name is a conflict.

Sectors (English label = Vietnamese name): {sectors}.
Tickers with their sectors: {tickers}."""


def compiler_schema(tickers: list[str]) -> dict:
    num01 = {"anyOf": [{"type": "number", "minimum": 0.0, "maximum": 1.0}, {"type": "null"}]}
    fields = ["exclude_tickers", "exclude_sectors", "sector_caps", "max_weight_per_stock", "max_holdings", "min_cash_pct"]
    return {
        "type": "object",
        "properties": {
            "exclude_tickers": {"type": "array", "items": {"type": "string", "enum": tickers}, "maxItems": 30},
            "exclude_sectors": {"type": "array", "items": {"type": "string", "enum": SECTORS}, "maxItems": 9},
            "sector_caps": {"type": "array", "maxItems": 9, "items": {
                "type": "object", "properties": {"sector": {"type": "string", "enum": SECTORS},
                                                 "max_weight": {"type": "number", "minimum": 0.0, "maximum": 1.0}},
                "required": ["sector", "max_weight"], "additionalProperties": False}},
            "max_weight_per_stock": num01,
            "max_holdings": {"anyOf": [{"type": "integer", "minimum": 1, "maximum": 30}, {"type": "null"}]},
            "min_cash_pct": {"anyOf": [{"type": "number", "minimum": 0.0, "maximum": 99.0}, {"type": "null"}]},
            "status": {"type": "string", "enum": ["ok", "needs_clarification", "conflict"]},
            "missing_fields": {"type": "array", "items": {"type": "string", "enum": fields + ["risk_preference", "target"]},
                               "maxItems": 6},
            "conflicts": {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 4},
            "clarification_question_vi": {"anyOf": [{"type": "string", "maxLength": 240}, {"type": "null"}]},
        },
        "required": fields + ["status", "missing_fields", "conflicts", "clarification_question_vi"],
        "additionalProperties": False,
    }


def compiler_request(text: str, sector_of: dict[str, str], seed: int = 0) -> dict:
    tickers = sorted(sector_of)
    system = SYSTEM_PROMPT.format(sectors=", ".join(f"{s} = {SECTOR_VI[s]}" for s in SECTORS),
                               tickers=", ".join(f"{t} ({sector_of[t]})" for t in tickers))
    return make_request("mandate_compiler_v3.2", system, text, compiler_schema(tickers), seed=seed, temperature=0.0,
                        max_tokens=600)


def status_of(parsed: dict | None, version: str) -> str:
    if not isinstance(parsed, dict):
        return "invalid"
    if version == "v3.2":
        return parsed.get("status", "invalid")
    return "needs_clarification" if parsed.get("needs_clarification") else "ok"


# ---------------------------------------------------------------- scoring
FIELDS = ["exclude_tickers", "exclude_sectors", "sector_caps", "max_weight_per_stock", "max_holdings", "min_cash_pct"]
DIMENSION_WORDS = {"sector_caps": None, "risk": ["tiền mặt", "mỗi mã", "mỗi cổ phiếu", "tỷ trọng", "rủi ro"],
                   "min_cash_pct": ["tiền mặt"], "max_weight_per_stock": ["mỗi mã", "mỗi cổ phiếu", "một mã", "tỷ trọng"],
                   "max_holdings": ["mã", "cổ phiếu"], "exclude_or_cap": ["vic", "vhm", "vre", "vin"]}


def question_quality(q: str | None, extra: dict) -> dict:
    """Deterministic rubric: Vietnamese, one question, short, names what is missing."""
    if not q:
        return {"asked": False, "score": 0.0}
    low = q.lower()
    vi = bool(re.search(r"[ăâđêôơưàáạảãèéẹẻẽìíịỉĩòóọỏõùúụủũỳýỵỷỹ]", low))
    one = q.count("?") == 1
    short = len(q) <= 200
    dim = extra.get("dimension")
    words = DIMENSION_WORDS.get(extra.get("missing"), None) or ([dim] if dim else [])
    names = any(w in low for w in words) if words else True
    checks = {"vietnamese": vi, "one_question": one, "short": short, "names_missing": names}
    return {"asked": True, **checks, "score": sum(checks.values()) / 4}


def norm(m: Mandate) -> dict:
    from ..llm.tasks import _norm, effective

    return _norm(effective(m))


def field_matches(pred: Mandate, gold: Mandate) -> dict[str, bool]:
    p, g = norm(pred), norm(gold)
    return {k: p[k] == g[k] for k in FIELDS}
