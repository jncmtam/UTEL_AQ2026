"""Fail-closed bilingual mandate parsing and evidence validation. No code execution."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
import unicodedata


def folded(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
                   if unicodedata.category(c) != "Mn")


@dataclass(frozen=True)
class MandateSpec:
    source_text: str
    k: int | None = None
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    sector_caps: dict[str, float] = field(default_factory=dict)
    turnover_cap: float | None = None
    cost_weight: float | None = None
    evidence: tuple[dict, ...] = ()
    issues: tuple[str, ...] = ()
    status: str = "needs_clarification"
    origin: str = "rules"

    def to_dict(self) -> dict:
        return asdict(self)


def _number(value, name: str, upper: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected a number, not a boolean or string.")
    value = float(value)
    if not math.isfinite(value) or value < 0 or (upper is not None and value > upper):
        raise ValueError(f"{name}: value is outside the permitted range.")
    return value


def validate_mandate(payload: dict, text: str, tickers: tuple[str, ...], sectors: tuple[str, ...],
                     origin: str = "llm") -> MandateSpec:
    """Validate typed constraints and exact source spans; refuse unsupported source clauses.

    Evidence anchoring is necessary, not a proof of unrestricted natural-language semantics.
    Unrecognized wording must be confirmed by a human or covered by benchmark gold labels.
    """
    if not isinstance(payload, dict) or set(payload) - {"constraints", "issues"}:
        raise ValueError("Mandate response must contain only constraints and issues.")
    constraints, issues = payload.get("constraints"), payload.get("issues", [])
    if not isinstance(constraints, list) or not isinstance(issues, list) or not all(isinstance(v, str) for v in issues):
        raise ValueError("constraints/issues must be valid lists.")
    issues = list(issues)
    values: dict = {"include": [], "exclude": [], "sector_caps": {}}
    evidence, covered = [], set()
    singleton = set()
    for item in constraints:
        if not isinstance(item, dict) or set(item) != {"kind", "target", "value", "start", "end", "quote"}:
            raise ValueError("Each constraint requires kind, target, value, start, end and quote.")
        kind, target, value = item["kind"], item["target"], item["value"]
        start, end, quote = item["start"], item["end"], item["quote"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text) or text[start:end] != quote:
            raise ValueError("Evidence span does not match the source text.")
        if kind not in {"cardinality", "include", "exclude", "sector_cap", "turnover_cap", "cost_weight"}:
            raise ValueError("Unsupported constraint type.")
        fquote = folded(quote)
        if ";" in quote or "\n" in quote:
            raise ValueError("Each evidence span may cover only one source clause.")
        # Avoid treating an exception, negated instruction or bound as a simple equality.
        if any(v in fquote for v in ("ngoai tru", "tru khi", "unless", "except", "khong loai", "do not exclude", "khong giu", "do not keep")):
            issues.append("Negated or exceptional requirement needs clarification: " + quote)
        if kind in {"include", "exclude"}:
            if target not in tickers or value is not True or not re.search(r"\b" + re.escape(target) + r"\b", quote, re.I):
                raise ValueError("Invalid include/exclude security or evidence.")
            anchors = ("loai", "exclude", "khong nam giu") if kind == "exclude" else ("bat buoc", "must hold", "include", "giu ma")
            if not any(v in fquote for v in anchors):
                issues.append("Include/exclude direction is unverified: " + quote)
            values[kind].append(target)
        else:
            value = _number(value, kind, 1 if kind == "sector_cap" else 2 if kind == "turnover_cap" else None)
            numeric = re.findall(r"\d+(?:[.,]\d+)?", quote)
            percent = "%" in quote
            candidates = [float(v.replace(",", ".")) / (100 if percent else 1) for v in numeric]
            if not any(math.isclose(value, v, abs_tol=1e-10) for v in candidates):
                raise ValueError("Value or unit is unsupported by the evidence.")
            if kind == "sector_cap":
                if target not in sectors or folded(target) not in fquote:
                    raise ValueError("Sector is outside the universe or absent from the evidence.")
                if target in values["sector_caps"] and values["sector_caps"][target] != value:
                    issues.append("Conflict in sector limits: " + target)
                values["sector_caps"][target] = value
            else:
                if target is not None:
                    raise ValueError("Portfolio-wide constraints require target=null.")
                if kind == "cardinality":
                    if percent or not value.is_integer() or not 1 <= value <= len(tickers):
                        raise ValueError("Asset count must be an integer in [1,N].")
                    if any(v in fquote for v in ("toi da", "at most", "toi thieu", "at least", "khong qua")):
                        issues.append("This version requires exactly K holdings.")
                    key, value = "k", int(value)
                else:
                    key = kind
                if key in singleton and values[key] != value:
                    issues.append("Conflict in constraints: " + key)
                singleton.add(key)
                values[key] = value
            if kind in {"sector_cap", "turnover_cap"} and not any(anchor in fquote for anchor in ("khong qua", "toi da", "at most", "maximum", "capped at", "no more than")):
                issues.append("Upper-bound direction is unverified: " + quote)
            if kind == "turnover_cap" and not any(anchor in fquote for anchor in ("turnover", "luan chuyen")):
                issues.append("Turnover meaning is unverified: " + quote)
        evidence.append(dict(item))
        covered.update(range(start, end))
    # Every non-punctuation character must be accounted for; never silently drop a clause.
    if any(c.isalnum() and i not in covered for i, c in enumerate(text)):
        issues.append("Some content remains unnormalized and needs clarification.")
    values["include"] = tuple(sorted(set(values["include"])))
    values["exclude"] = tuple(sorted(set(values["exclude"])))
    conflict = bool(set(values["include"]) & set(values["exclude"])) or any("Conflict" in v for v in issues)
    if conflict:
        issues.append("Conflict: requirements cannot all be applied.")
    if "k" not in values:
        issues.append("Missing number of holdings K.")
    if len(values["include"]) > values.get("k", len(tickers)):
        issues.append("Conflict: mandatory holdings exceed K.")
        conflict = True
    status = "conflict" if conflict else "needs_clarification" if issues else "ready"
    return MandateSpec(text, **values, evidence=tuple(evidence), issues=tuple(issues), status=status, origin=origin)


def normalize_rules(text: str, tickers: tuple[str, ...], sectors: tuple[str, ...]) -> MandateSpec:
    """Conservative controlled grammar, used as an explicit non-LLM baseline."""
    constraints = []
    for match in re.finditer(r"[^;\n.]+(?:\.(?=\d)[^;\n.]*)?", text):
        raw = match.group().strip().strip(",")
        if not raw:
            continue
        start = text.find(raw, match.start())
        f = folded(raw)
        kind, target, value = None, None, None
        m = re.fullmatch(r"(?:giu|hold|select)\s+(\d+)\s+(?:ma|assets|stocks)", f)
        if m:
            kind, value = "cardinality", int(m[1])
        for word, key in (("loai ma", "exclude"), ("exclude", "exclude"), ("bat buoc giu ma", "include"), ("must hold", "include")):
            if f.startswith(word + " "):
                token = raw.split()[-1].upper()
                if token in tickers and f == word + " " + folded(token):
                    kind, target, value = key, token, True
        m = re.fullmatch(r"(?:ty trong nganh|sector)\s+(.+?)\s+(?:khong qua|at most)\s+(\d+(?:[.,]\d+)?)\s*%", f)
        if m:
            target = next((s for s in sectors if folded(s) == m[1]), None)
            if target:
                kind, value = "sector_cap", float(m[2].replace(",", ".")) / 100
        m = re.fullmatch(r"(?:turnover|muc luan chuyen)\s+(?:khong qua|at most)\s+(\d+(?:[.,]\d+)?)\s*%", f)
        if m:
            kind, value = "turnover_cap", float(m[1].replace(",", ".")) / 100
        m = re.fullmatch(r"(?:he so chi phi|cost weight)\s+(\d+(?:[.,]\d+)?)", f)
        if m:
            kind, value = "cost_weight", float(m[1].replace(",", "."))
        if kind:
            constraints.append(dict(kind=kind, target=target, value=value, start=start, end=start + len(raw), quote=raw))
    return validate_mandate({"constraints": constraints, "issues": []}, text, tickers, sectors, "rules")
