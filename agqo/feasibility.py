"""Pre-solve diagnosis: can the investor's rules be met with whole lots, and if not, which rule blocks it?

Deterministic and cheap (no optimisation). `diagnose` returns

    {"feasible": bool,
     "blocking": [reason, ...],     # each makes the request infeasible on its own or in combination
     "notes":    [reason, ...],     # rules that bind or override each other but leave a solution
     "investable": [tickers]}       # stocks that can hold at least one lot under every rule

A reason is {"code", "rule", "message_en", "message_vi", "detail"}. All weights are on the post-trade NAV
(cash after fees plus holdings), bounded with the same fee margin the optimiser uses.
"""

from __future__ import annotations

from .backtest import Account, fee_margin
from .config import SECTOR_EN, ExperimentConfig
from .mandate import Mandate

SECTOR_VI = {v: k for k, v in SECTOR_EN.items()}


def _vnd(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def _reason(code: str, rule: str, en: str, vi: str, **detail) -> dict:
    return {"code": code, "rule": rule, "message_en": en, "message_vi": vi, "detail": detail}


def diagnose(md, date, universe: list[str], account: Account, mandate: Mandate, ec: ExperimentConfig) -> dict:
    m, rules = mandate, ec.rules
    px = md.px.loc[date]
    nav = account.value(px)
    margin = fee_margin(account, rules)
    blocking, notes = [], []

    # 1. exclusions
    allowed = m.filter_universe(universe, md.sector)
    if not allowed:
        blocking.append(_reason(
            "empty_universe", "exclusions",
            f"Every usable VN30 stock is excluded (sectors: {', '.join(m.exclude_sectors) or '-'}; "
            f"tickers: {', '.join(m.exclude_tickers) or '-'}).",
            "Mọi mã VN30 dùng được đều bị loại bởi quy tắc loại ngành/mã "
            f"({', '.join(SECTOR_VI.get(s, s) for s in m.exclude_sectors) or 'không loại ngành'}"
            f"{'; mã: ' + ', '.join(m.exclude_tickers) if m.exclude_tickers else ''}).",
            excluded_sectors=m.exclude_sectors, excluded_tickers=m.exclude_tickers))
        return {"feasible": False, "blocking": blocking, "notes": notes, "investable": [], "nav_vnd": nav}
    for s in m.exclude_sectors:
        if s in m.sector_caps:
            notes.append(_reason("exclusion_overrides_cap", "conflict",
                                 f"{s} is both excluded and capped at {m.sector_caps[s]:.0%}; the exclusion applies.",
                                 f"Ngành {SECTOR_VI.get(s, s)} vừa bị loại vừa có trần {100 * m.sector_caps[s]:.0f}%: "
                                 "áp dụng quy tắc loại.", sector=s))

    lot_value = {t: rules.lot_size * float(px[t]) for t in allowed}
    lot_cost = {t: v * (1 + rules.commission) for t, v in lot_value.items()}       # buy one lot incl. commission
    invest_frac = 1 - (m.min_cash_pct or 0) / 100
    budget = nav * invest_frac * (1 - margin)
    cheapest = min(allowed, key=lambda t: lot_cost[t])

    # 2. cash: can one lot of anything be bought?
    ok = {t for t in allowed if lot_cost[t] <= min(budget, nav)}
    if not ok:
        cash_txt = f" after keeping {m.min_cash_pct:g}% cash" if m.min_cash_pct else ""
        blocking.append(_reason(
            "no_affordable_lot", "capital" if not m.min_cash_pct else "min_cash_pct",
            f"One lot of the cheapest allowed stock ({cheapest}, {_vnd(lot_cost[cheapest])} VND incl. fee) costs more "
            f"than the {_vnd(budget)} VND available{cash_txt}.",
            f"Một lô của mã rẻ nhất được phép ({cheapest}, {_vnd(lot_cost[cheapest])} đ kể cả phí) đắt hơn số tiền "
            f"có thể đầu tư {_vnd(budget)} đ{' sau khi giữ ' + format(m.min_cash_pct, 'g') + '% tiền mặt' if m.min_cash_pct else ''}.",
            cheapest=cheapest, cheapest_lot_vnd=lot_cost[cheapest], investable_vnd=budget))

    # 3. single-stock cap below one lot
    if m.max_weight_per_stock is not None:
        limit = m.max_weight_per_stock * (1 - margin) * nav
        fit = {t for t in ok if lot_value[t] <= limit}
        if ok and not fit:
            blocking.append(_reason(
                "per_stock_cap_below_one_lot", "max_weight_per_stock",
                f"'Each stock <= {m.max_weight_per_stock:.0%}' allows at most {_vnd(limit)} VND per stock, but the cheapest "
                f"lot ({cheapest}) costs {_vnd(lot_value[cheapest])} VND.",
                f"Quy tắc mỗi mã tối đa {100 * m.max_weight_per_stock:g}% chỉ cho phép {_vnd(limit)} đ mỗi mã, nhưng lô rẻ "
                f"nhất ({cheapest}) đã là {_vnd(lot_value[cheapest])} đ.",
                limit_vnd=limit, cheapest=cheapest, cheapest_lot_vnd=lot_value[cheapest]))
        elif len(fit) < len(ok):
            notes.append(_reason(
                "per_stock_cap_excludes", "max_weight_per_stock",
                f"{len(ok) - len(fit)} stocks cost more than the per-stock limit for one lot and cannot be held.",
                f"{len(ok) - len(fit)} mã có một lô vượt trần mỗi mã nên không thể nắm giữ.",
                excluded=sorted(ok - fit)))
        ok = fit

    # 4. sector caps below one lot of every stock in the sector
    for s, cap in m.sector_caps.items():
        members = [t for t in ok if md.sector(t) == s]
        if not members or s in m.exclude_sectors:
            continue
        limit = cap * (1 - margin) * nav
        fit = [t for t in members if lot_value[t] <= limit]
        if not fit:
            notes.append(_reason(
                "sector_cap_below_one_lot", "sector_caps",
                f"The {s} cap of {cap:.0%} ({_vnd(limit)} VND) is smaller than one lot of any {s} stock: none can be held.",
                f"Trần ngành {SECTOR_VI.get(s, s)} {100 * cap:g}% ({_vnd(limit)} đ) nhỏ hơn một lô của mọi mã trong ngành: "
                "không giữ được mã nào của ngành này.", sector=s, limit_vnd=limit))
            ok -= set(members)
    if not ok and not blocking:
        blocking.append(_reason(
            "rules_leave_nothing", "combination",
            "Together the rules leave no stock that can hold one lot.",
            "Kết hợp các quy tắc không còn mã nào mua được dù chỉ một lô.", rules=m.to_dict()))

    # 5. holdings limit (binding, not blocking)
    if m.max_holdings is not None and m.max_holdings < len(ok):
        notes.append(_reason(
            "max_holdings_binds", "max_holdings",
            f"At most {m.max_holdings} of the {len(ok)} investable stocks are held; tracking error rises.",
            f"Chỉ giữ tối đa {m.max_holdings} trong {len(ok)} mã có thể mua: sai số bám sẽ tăng.",
            investable=len(ok)))
    return {"feasible": not blocking, "blocking": blocking, "notes": notes, "investable": sorted(ok), "nav_vnd": nav}
