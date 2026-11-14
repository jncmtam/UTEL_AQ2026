"""LLM Market Analyst: reads the market-data table, returns views and a basket.

Output per rebalance date:
  regime     - risk_on / neutral / risk_off
  views      - per-id relative view in {-2..2} with confidence in [0,1]; these tilt the
               full-universe portfolio through Black-Litterman (main AGQO strategy)
  shortlist  - exactly n anonymised ids for the concentrated-basket mandate
 Malformed answers are repaired deterministically and the
repair is recorded -- never hidden.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

SYSTEM = """You are the market-analysis agent of AGQO, a quantum-assisted rebalancing system for a small retail
account that tracks the Vietnamese VN30 index with only a few stocks bought in whole board lots.

You receive a point-in-time table of anonymised VN30 constituents (ids S01, S02, ...; real names and dates are
hidden on purpose) with numbers computed from past prices only, plus a benchmark summary.

Your job:
1. Classify the market regime.
2. Give a relative view for stocks where the data justify it: -2 strong underperform ... +2 strong outperform the
   index over the next quarter, with confidence 0..1. Use 0 / low confidence when evidence is weak. Views tilt the
   main portfolio slightly away from pure index tracking, so be calibrated: wrong confident views cost money.
3. For investors who want a concentrated basket, choose EXACTLY {n} ids that together REPLICATE THE INDEX: favour
   high correlation and beta near 1, cover the heavy sectors (banking dominates VN30), prefer liquid names, avoid
   redundant near-duplicates. Lot value matters: a stock whose single lot is a large share of a
   {capital:.0f}-million-VND account is hard to size.

Reason only from the numbers provided. Return JSON that matches the schema. Keep the rationale under 60 words."""


def schema(ids: list[str], n: int) -> dict:
    return {
        "type": "object",
        "properties": {
            "regime": {"type": "string", "enum": ["risk_on", "neutral", "risk_off"]},
            "shortlist": {"type": "array", "items": {"type": "string", "enum": ids},
                          "minItems": n, "maxItems": n},
            "views": {"type": "array", "maxItems": len(ids), "items": {
                "type": "object",
                "properties": {"id": {"type": "string", "enum": ids},
                               "view": {"type": "integer", "minimum": -2, "maximum": 2},
                               "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
                "required": ["id", "view", "confidence"], "additionalProperties": False}},
            "rationale": {"type": "string", "maxLength": 500},
        },
        "required": ["regime", "shortlist", "views", "rationale"],
        "additionalProperties": False,
    }


def user_payload(table: pd.DataFrame, bench: dict, n: int, capital_mvnd: float) -> dict:
    t = table.round(3).reset_index()
    return {"task": f"select {n} ids and give views", "account_capital_million_vnd": capital_mvnd,
            "benchmark": bench, "columns": list(t.columns), "rows": t.values.tolist()}


def parse(parsed: dict | None, alias: dict[str, str], n: int, fallback_order: list[str]) -> dict:
    """Validate an analyst answer; repair to a usable decision and record what was repaired."""
    repairs = []
    if not isinstance(parsed, dict):
        parsed, repairs = {}, ["no valid JSON: shortlist from fallback, no views"]
    raw_sl = parsed.get("shortlist", []) if isinstance(parsed.get("shortlist"), list) else []
    seen, shortlist = set(), []
    for i in raw_sl:
        if i in alias and i not in seen:
            seen.add(i)
            shortlist.append(alias[i])
    if len(shortlist) != len(raw_sl):
        repairs.append("dropped unknown/duplicate ids")
    if len(shortlist) > n:
        shortlist = shortlist[:n]
        repairs.append("truncated shortlist")
    for t in fallback_order:
        if len(shortlist) >= n:
            break
        if t not in shortlist:
            shortlist.append(t)
            repairs.append(f"filled {t} from fallback")
    views = {}
    for v in parsed.get("views", []) or []:
        try:
            tk = alias[v["id"]]
            views[tk] = (int(np.clip(v["view"], -2, 2)), float(np.clip(v["confidence"], 0, 1)))
        except (KeyError, TypeError, ValueError):
            repairs.append("ignored malformed view")
    return {"shortlist": shortlist, "views": views, "regime": parsed.get("regime", "unknown"),
            "rationale": parsed.get("rationale", ""), "repairs": repairs}


def to_json(decision: dict) -> str:
    return json.dumps(decision, ensure_ascii=False)
