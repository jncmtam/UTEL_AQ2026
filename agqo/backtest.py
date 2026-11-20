"""Walk-forward VN30 tracking: instance construction, exact lot/fee/tax accounting, performance."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .classical import continuous_min_te, round_to_lots
from .config import ExperimentConfig
from .data import MarketData, history_window, shrunk_covariance
from .mandate import Mandate
from .portfolio import Instance


@dataclass
class Account:
    cash: float
    shares: dict[str, float] = field(default_factory=dict)
    fees_paid: float = 0.0
    traded_value: float = 0.0

    def value(self, prices: pd.Series) -> float:
        return self.cash + sum(s * prices[t] for t, s in self.shares.items() if s)

    def rebalance(self, target: dict[str, float], prices: pd.Series, rules) -> None:
        tickers = set(self.shares) | set(target)
        buys = sells = 0.0
        for t in tickers:
            d = (target.get(t, 0.0) - self.shares.get(t, 0.0)) * prices[t]
            if d > 0:
                buys += d
            else:
                sells -= d
        fees = rules.commission * (buys + sells) + rules.sell_tax * sells
        self.cash += sells - buys - fees
        self.fees_paid += fees
        self.traded_value += buys + sells
        self.shares = {t: s for t, s in target.items() if s > 0}
        if self.cash < -1e-6:
            raise ValueError(f"negative cash {self.cash:.0f} after rebalance")


def risk_inputs(md: MarketData, date, tickers: list[str], cfg) -> tuple[np.ndarray, np.ndarray, float]:
    """Joint covariance of [assets, index], shrunk towards its own diagonal.

    Shrinking the *joint* matrix keeps the tracking-error quadratic form positive
    semi-definite (TE^2 >= 0 for every w); shrinking only the asset block does not.
    """
    r, b = history_window(md, date, tickers, cfg.lookback_days)
    S = shrunk_covariance(np.column_stack([r, b]), cfg.shrinkage)
    n = len(tickers)
    return S[:n, :n], S[:n, n], float(S[n, n])


def fee_margin(account: Account, rules) -> float:
    """Upper bound on fees / pre-trade NAV for any rebalance of this account.

    A cash-only account can only buy (bought value <= NAV): fees <= commission x NAV. An account with
    holdings can at most sell everything and buy NAV again: fees <= (2 commission + sales tax) x NAV.
    A cap c on the pre-trade NAV basis scaled to c x (1 - margin) therefore holds on the post-trade NAV
    (NAV - fees) for every lot choice, which is what lets the register keep all 2^n states inside the rules.
    """
    held = any(s for s in account.shares.values())
    return 2 * rules.commission + rules.sell_tax if held else rules.commission


def continuous_target(md: MarketData, date, universe: list[str], account: Account, ec: ExperimentConfig,
                      mandate: Mandate | None = None) -> tuple[list[str], np.ndarray, float, list]:
    """Mandate-aware continuous minimum-TE weights: (tickers, weights, invest target, construction caps).

    The returned caps are the investor's caps tightened by `fee_margin`, on the pre-trade NAV basis. They
    shape the continuous target, the register and practitioner rounding. The investor's own caps are
    checked exactly on the post-trade NAV (`Instance.feasible`).
    """
    m = mandate or Mandate()
    cfg = ec.problem
    tickers = m.filter_universe(universe, md.sector)
    if not tickers:
        from .portfolio import NoFeasiblePortfolio

        raise NoFeasiblePortfolio("every usable stock is excluded by the investor's rules")
    target = m.invest_target(cfg.invest_target)
    nav = account.value(md.px.loc[date])
    margin = fee_margin(account, ec.rules)

    def solve(tk):
        cov, cov_b, _ = risk_inputs(md, date, tk, cfg)
        w_prev = np.array([account.shares.get(t, 0.0) for t in tk]) * md.px.loc[date, tk].to_numpy() / nav
        caps = [(mask, cap * (1 - margin)) for mask, cap in m.caps(tk, md.sector)]
        return continuous_min_te(cov, cov_b, target, w_prev=w_prev, gamma=cfg.turnover_weight, caps=caps), caps

    w, caps = solve(tickers)
    if m.max_holdings is not None and m.max_holdings < len(tickers):
        # keep the largest continuous weights among stocks of which one lot is affordable
        px = md.px.loc[date, tickers].to_numpy()
        room = nav * target * (1 - margin)
        if m.max_weight_per_stock is not None:                # one lot must also fit under the per-stock cap
            room = min(room, nav * m.max_weight_per_stock * (1 - margin))
        afford = ec.rules.lot_size * px * (1 + ec.rules.commission) <= room
        for s, cap in m.sector_caps.items():                  # ... and under its sector cap
            sec = np.array([md.sector(x) == s for x in tickers])
            afford &= ~sec | (ec.rules.lot_size * px <= nav * cap * (1 - margin))
        order = [i for i in np.argsort(-w) if afford[i]] + [i for i in np.argsort(-w) if not afford[i]]
        keep = sorted(order[: m.max_holdings])
        tickers = [tickers[i] for i in keep]
        w, caps = solve(tickers)
    return tickers, w, target, caps


def build_rounding_instance(md: MarketData, date, universe: list[str], account: Account, ec: ExperimentConfig,
                            mandate: Mandate | None = None) -> Instance:
    """Continuous optimum over the (mandate-filtered) members, rounded to lots; one qubit per register
    stock decides whether to add one more lot. The register holds the stocks where rounding matters
    most: lot value x distance of the continuous lot count from an integer."""
    cfg, rules = ec.problem, ec.rules
    tickers, w, target, caps = continuous_target(md, date, universe, account, ec, mandate)
    px = md.px.loc[date, tickers].to_numpy()
    all_px = md.px.loc[date]
    nav = account.value(all_px)
    cov, cov_b, var_b = risk_inputs(md, date, tickers, cfg)
    lots = w * nav / (rules.lot_size * px)
    floor = np.floor(lots + 1e-9)
    frac = lots - floor
    lot_w = rules.lot_size * px / nav                     # weight of one lot of each stock
    score = lot_w * np.minimum(frac, 1 - frac) + 1e-6 * frac
    floor_w = floor * lot_w

    def fits(reg: list[int]) -> bool:
        """Constraint-aware register: even with every qubit set, each cap holds (all 2^n states obey the mandate)."""
        for mask, cap in caps:
            if mask.all():                    # the total-cash cap is checked exactly on each sample instead
                continue
            if floor_w[mask].sum() + lot_w[[j for j in reg if mask[j]]].sum() > cap + 1e-12:
                return False
        return True

    reg: list[int] = []
    for j in np.argsort(-score):
        if len(reg) == cfg.register_size:
            break
        if fits(reg + [int(j)]):
            reg.append(int(j))
    reg = np.array(sorted(reg), dtype=int)
    base = np.round(lots)                     # stocks outside the register: nearest lot
    base[reg] = floor[reg]                    # register stocks: floor, the qubit may add one lot
    for mask, cap in caps:                    # fixed part + every qubit set must stay inside each cap
        extra = 0.0 if mask.all() else lot_w[[j for j in reg if mask[j]]].sum()
        while (base * lot_w)[mask].sum() + extra > cap + 1e-12:
            j = np.flatnonzero(mask & (base > floor) & ~np.isin(np.arange(len(base)), reg))
            j = j if len(j) else np.flatnonzero(mask & (base > 0))
            base[j[np.argmax((base * px)[j])]] -= 1
    prev = np.array([account.shares.get(t, 0.0) for t in tickers])
    other = sum(s * all_px[t] for t, s in account.shares.items() if t not in tickers)
    investor_caps = (mandate or Mandate()).caps(list(tickers), md.sector)   # checked exactly, post-trade NAV
    inst = Instance(date=str(pd.Timestamp(date).date()), tickers=list(tickers), prices=px, nav=nav, cov=cov,
                    cov_b=cov_b, var_b=var_b, prev_shares=prev, other_value=other, cash=account.cash,
                    base_shares=base * rules.lot_size, bit_stock=reg, bit_lots=np.ones(len(reg)), cfg=cfg,
                    rules=rules, invest_target=target, caps=investor_caps)
    inst.meta["continuous_weights"] = w
    inst.meta["nearest_bits"] = (frac[reg] >= 0.5).astype(int)   # plain rounding = one specific bitstring
    inst.meta["register_dropped_by_caps"] = int(min(cfg.register_size, len(tickers)) - len(reg))
    return inst


def practitioner_target(md: MarketData, date, universe: list[str], account: Account, ec: ExperimentConfig,
                        mandate: Mandate | None = None) -> dict:
    """Practitioner baseline: the same continuous optimum, nearest whole lot, trimmed until affordable."""
    tickers, w, target, caps = continuous_target(md, date, universe, account, ec, mandate)
    nav = account.value(md.px.loc[date])
    sh = round_to_lots(w, md.px.loc[date, tickers].to_numpy(), nav, ec.rules.lot_size,
                       max_invest=min(0.985, target + 0.005), caps=caps)
    return dict(zip(tickers, sh))


def equal_weight_target(md: MarketData, date, universe: list[str], account: Account, ec: ExperimentConfig) -> dict:
    """Naive 1/N baseline: equal weight in every usable member, rounded to whole lots."""
    px = md.px.loc[date, universe].to_numpy()
    nav = account.value(md.px.loc[date])
    w = np.full(len(universe), ec.problem.invest_target / len(universe))
    return dict(zip(universe, round_to_lots(w, px, nav, ec.rules.lot_size)))


def etf_buy_and_hold(md: MarketData, ticker: str, start, end, ec: ExperimentConfig,
                     capital: float | None = None) -> tuple[pd.Series, float]:
    """What the investor could do instead: buy whole lots of one VN30 ETF on day one and hold.

    ETF units trade in 100-unit lots with the same commission; days without a trade carry the last price.
    Returns (daily account value, fees paid).
    """
    px = md.etf_close[ticker].loc[:end].ffill().loc[start:end]
    cap, r = capital or ec.problem.capital_vnd, ec.rules
    p0 = px.iloc[0]
    units = np.floor(cap / (p0 * r.lot_size * (1 + r.commission))) * r.lot_size
    fee = units * p0 * r.commission
    cash = cap - units * p0 - fee
    return cash + units * px, float(fee)


def daily_values(md: MarketData, account: Account, start, end) -> pd.Series:
    px = md.px.loc[start:end]
    v = pd.Series(account.cash, index=px.index)
    for t, s in account.shares.items():
        v = v + s * px[t]
    return v


def performance(values: pd.Series, index: pd.Series, etf: pd.Series | None = None) -> dict:
    """Tracking vs the VN30 price index (excludes dividends) and, if given, vs a VN30 ETF (includes them).

    Weekly tracking error is reported next to the daily one because ETF market prices carry
    day-to-day noise around NAV that is not tracking skill.
    """
    rp = values.pct_change().dropna()
    rb = index.pct_change().loc[rp.index]
    act = rp - rb
    yrs = len(rp) / 252
    tot_p = values.iloc[-1] / values.iloc[0] - 1
    tot_b = index.loc[values.index[-1]] / index.loc[values.index[0]] - 1
    wk = values.resample("W-FRI").last().pct_change().dropna() - index.resample("W-FRI").last().pct_change().dropna()
    out = {"tracking_error_ann_pct": float(100 * act.std() * np.sqrt(252)),
           "tracking_error_weekly_ann_pct": float(100 * wk.std() * np.sqrt(52)),
           "return_ann_pct": float(100 * ((1 + tot_p) ** (1 / yrs) - 1)),
           "active_return_ann_pct": float(100 * ((1 + tot_p) ** (1 / yrs) - (1 + tot_b) ** (1 / yrs))),
           "correlation": float(np.corrcoef(rp, rb)[0, 1]), "days": int(len(rp))}
    if etf is not None:
        e = etf.ffill().loc[values.index]
        tot_e = e.iloc[-1] / e.iloc[0] - 1
        out["excess_return_vs_etf_ann_pct"] = float(100 * ((1 + tot_p) ** (1 / yrs) - (1 + tot_e) ** (1 / yrs)))
    return out


def active_returns(values: pd.Series, index: pd.Series) -> pd.Series:
    rp = values.pct_change().dropna()
    return rp - index.pct_change().loc[rp.index]
