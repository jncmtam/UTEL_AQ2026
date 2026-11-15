"""Investor mandate: the personal rules that change the optimisation problem.

A mandate is produced from a Vietnamese instruction by the LLM compiler (agqo/llm/tasks.py)
or by the keyword-rule baseline below, validated against the universe, and then applied:

  exclude_tickers / exclude_sectors -> removed from the universe (no qubit, no weight)
  sector_caps, max_weight_per_stock -> linear constraints in the continuous QP and exact
                                       feasibility checks on every sampled lot decision
  max_holdings                      -> keep the N largest continuous weights, re-solve
  min_cash_pct                      -> invested target = 1 - min_cash_pct / 100
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field

import numpy as np

from .config import SECTOR_EN

SECTORS = list(SECTOR_EN.values())


@dataclass
class Mandate:
    exclude_tickers: list[str] = field(default_factory=list)
    exclude_sectors: list[str] = field(default_factory=list)
    sector_caps: dict[str, float] = field(default_factory=dict)      # sector -> max weight (0..1)
    max_weight_per_stock: float | None = None
    max_holdings: int | None = None
    min_cash_pct: float | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Mandate":
        caps = d.get("sector_caps") or {}
        if isinstance(caps, list):
            caps = {c["sector"]: float(c["max_weight"]) for c in caps}
        return cls(exclude_tickers=sorted(set(d.get("exclude_tickers") or [])),
                   exclude_sectors=sorted(set(d.get("exclude_sectors") or [])),
                   sector_caps={k: float(v) for k, v in caps.items()},
                   max_weight_per_stock=d.get("max_weight_per_stock"),
                   max_holdings=d.get("max_holdings"), min_cash_pct=d.get("min_cash_pct"))

    def to_dict(self) -> dict:
        return asdict(self)

    def is_empty(self) -> bool:
        return self == Mandate()

    def validate(self, tickers: set[str]) -> list[str]:
        errs = [f"unknown ticker {t}" for t in self.exclude_tickers if t not in tickers]
        errs += [f"unknown sector {s}" for s in [*self.exclude_sectors, *self.sector_caps] if s not in SECTORS]
        errs += [f"cap for {s} must be in (0, 1]" for s, c in self.sector_caps.items() if not 0 < c <= 1]
        if self.max_weight_per_stock is not None and not 0 < self.max_weight_per_stock <= 1:
            errs.append("max_weight_per_stock must be in (0, 1]")
        if self.max_holdings is not None and not 1 <= self.max_holdings <= 30:
            errs.append("max_holdings must be 1..30")
        if self.min_cash_pct is not None and not 0 <= self.min_cash_pct < 100:
            errs.append("min_cash_pct must be in [0, 100)")
        return errs

    # ------------------------------------------------------------ application
    def filter_universe(self, universe: list[str], sector_of) -> list[str]:
        return [t for t in universe if t not in self.exclude_tickers and sector_of(t) not in self.exclude_sectors]

    def invest_target(self, default: float) -> float:
        return default if self.min_cash_pct is None else min(default, 1 - self.min_cash_pct / 100)

    def caps(self, tickers: list[str], sector_of) -> list[tuple[np.ndarray, float]]:
        """Linear caps sum(w[mask]) <= cap for the QP and the exact feasibility check."""
        out = []
        for s, c in self.sector_caps.items():
            mask = np.array([sector_of(t) == s for t in tickers])
            if mask.any():
                out.append((mask, c))
        if self.max_weight_per_stock is not None:
            for j in range(len(tickers)):
                m = np.zeros(len(tickers), bool)
                m[j] = True
                out.append((m, self.max_weight_per_stock))
        if self.min_cash_pct:                     # total invested weight: a hard check on every decision
            out.append((np.ones(len(tickers), bool), 1 - self.min_cash_pct / 100))
        return out


# ---------------------------------------------------------------- keyword-rule baseline
def _plain(text: str) -> str:
    """Lower-case, strip Vietnamese diacritics (đ -> d) so rules match typed-without-accents text."""
    t = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


SECTOR_KEYWORDS = {
    "Banking": ["ngan hang"], "Insurance": ["bao hiem"], "Technology": ["cong nghe"],
    "Energy": ["nang luong", "dau khi"], "Materials": ["nguyen vat lieu", "thep", "hoa chat"],
    "Real estate": ["bat dong san", "dia oc"], "Consumer": ["tieu dung", "ban le"],
    "Brokerage": ["chung khoan"], "Aviation": ["hang khong"],
}
NEG = ["khong", "bo", "loai", "tranh", "tru"]


def rule_parse(text: str, tickers: set[str]) -> Mandate:
    """Transparent keyword baseline the LLM compiler must beat. No learning, no context."""
    raw, t = text, _plain(text)
    m = Mandate()
    for tk in re.findall(r"\b[A-Z]{3}\b", raw):
        if tk in tickers:
            m.exclude_tickers.append(tk)
    for sec, kws in SECTOR_KEYWORDS.items():
        for kw in kws:
            for hit in re.finditer(kw, t):
                window = t[hit.end(): hit.end() + 40]
                pct = re.search(r"(\d+(?:[.,]\d+)?)\s*%", window)
                before = t[max(0, hit.start() - 25): hit.start()]
                if pct and re.search(r"toi da|khong qua|duoi|max", before + window[: pct.start()]):
                    m.sector_caps[sec] = float(pct.group(1).replace(",", ".")) / 100
                elif any(re.search(rf"\b{n}\b", before) for n in NEG):
                    m.exclude_sectors.append(sec)
    hold = re.search(r"(?:toi da|khong qua|chi)\s*(\d+)\s*(?:ma|co phieu)", t)
    if hold:
        m.max_holdings = int(hold.group(1))
    each = re.search(r"moi (?:ma|co phieu)[^%]{0,25}?(\d+(?:[.,]\d+)?)\s*%", t)
    if each:
        m.max_weight_per_stock = float(each.group(1).replace(",", ".")) / 100
    cash = re.search(r"tien mat", t)
    if cash:                                   # the percentage closest to "tien mat" (before, else after)
        before = re.findall(r"(\d+(?:[.,]\d+)?)\s*%", t[max(0, cash.start() - 20): cash.start()])
        after = re.findall(r"(\d+(?:[.,]\d+)?)\s*%", t[cash.end(): cash.end() + 20])
        if before or after:
            m.min_cash_pct = float((before[-1] if before else after[0]).replace(",", "."))
    m.exclude_tickers = sorted(set(m.exclude_tickers))
    m.exclude_sectors = sorted(set(m.exclude_sectors) - set(m.sector_caps))
    return m
