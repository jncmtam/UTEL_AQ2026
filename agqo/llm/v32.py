"""V3.2 instruction compiler used by the product (prompt and schema: agqo/research/mandate_eval_v2.py).

status: ok | needs_clarification | conflict. Anything but ok blocks the personalised run until the investor
answers. Logged live answers (results/v32/llm_log_mandates.jsonl, then the V3 log) are replayed by text.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import ROOT
from ..mandate import Mandate

V32_LOG = ROOT / "results" / "v32" / "llm_log_mandates.jsonl"


def request(text: str, sector_of: dict[str, str], seed: int = 0) -> dict:
    from ..research.mandate_eval_v2 import request_v32

    return request_v32(text, sector_of, seed)


def parse(parsed: dict | None, tickers: set[str]) -> dict:
    """{mandate, status, question, conflicts, missing, errors}; invalid answers become an empty mandate."""
    if not isinstance(parsed, dict):
        return {"mandate": Mandate().to_dict(), "status": "ok", "question": None, "conflicts": [], "missing": [],
                "errors": ["no valid JSON"]}
    m = Mandate.from_dict(parsed)
    errs = m.validate(tickers)
    status = parsed.get("status", "ok")
    return {"mandate": (Mandate() if errs else m).to_dict(), "status": status if status in
            ("ok", "needs_clarification", "conflict") else "ok", "question": parsed.get("clarification_question_vi"),
            "conflicts": parsed.get("conflicts") or [], "missing": parsed.get("missing_fields") or [], "errors": errs}


def logged(text: str, path: Path = V32_LOG) -> dict | None:
    """Latest logged live V3.2 answer for exactly this instruction, if any."""
    if not path.exists():
        return None
    hit = None
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("agent") == "mandate_compiler_v3.2" and rec["user"].strip() == text.strip() and rec.get("parsed"):
            hit = rec
    return hit
