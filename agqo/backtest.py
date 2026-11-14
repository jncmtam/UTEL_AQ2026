"""Walk-forward VN30 tracking backtest with exact lot, fee and tax accounting."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .classical import continuous_min_te, round_to_lots
from .config import ExperimentConfig
from .data import MarketData, history_window, shrunk_covariance
from .portfolio import Instance, black_litterman


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


def _common(md: MarketData, date, tickers: list[str], views: dict, account: Account, ec: ExperimentConfig):
    cfg = ec.problem
    prices = md.close.loc[date, tickers].to_numpy()
    all_px = md.close.loc[date]
    nav = account.value(all_px)
    cov, cov_b, var_b = risk_inputs(md, date, tickers, cfg)
    v = np.array([views.get(t, (0, 0.0))[0] for t in tickers], float)
    c = np.array([views.get(t, (0, 0.0))[1] for t in tickers], float)
    mu = black_litterman(252 * cov, v, c)
    prev = np.array([account.shares.get(t, 0.0) for t in tickers])
    other = sum(s * all_px[t] for t, s in account.shares.items() if t not in tickers)
    return dict(date=str(pd.Timestamp(date).date()), tickers=list(tickers), prices=prices, nav=nav, cov=cov,
                cov_b=cov_b, var_b=var_b, mu=mu, prev_shares=prev, other_value=other, cash=account.cash,
                cfg=cfg, rules=ec.rules)


def build_selection_instance(md: MarketData, date, tickers: list[str], views: dict, account: Account,
                             ec: ExperimentConfig) -> Instance:
    """Basket mode: b bits per register stock encode 0..2^b-1 position units; nothing else is held."""
    cfg, rules = ec.problem, ec.rules
    kw = _common(md, date, tickers, views, account, ec)
    n, b = len(tickers), cfg.bits_per_asset
    unit_frac = cfg.invest_target / (n * (2 ** b - 1) / 2)
    units = np.maximum(1, np.round(unit_frac * kw["nav"] / (rules.lot_size * kw["prices"])))
    bit_stock = np.repeat(np.arange(n), b)
    bit_lots = np.array([units[i] * 2 ** j for i in range(n) for j in range(b)])
    return Instance(**kw, base_shares=np.zeros(n), bit_stock=bit_stock, bit_lots=bit_lots, mode="selection")


def build_rounding_instance(md: MarketData, date, universe: list[str], views: dict, account: Account,
                            ec: ExperimentConfig) -> Instance:
    """Rounding mode: continuous optimum over every member, floored to lots; one qubit per register
    stock decides whether to add one more lot. The register holds the stocks where rounding matters
    most: lot value x distance of the continuous lot count from an integer."""
    cfg, rules = ec.problem, ec.rules
    kw = _common(md, date, universe, views, account, ec)
    nav, px = kw["nav"], kw["prices"]
    w = continuous_min_te(kw["cov"], kw["cov_b"], cfg.invest_target, mu=kw["mu"], eta=cfg.view_weight,
                          w_prev=kw["prev_shares"] * px / nav, gamma=cfg.turnover_weight)
    lots = w * nav / (rules.lot_size * px)
    floor = np.floor(lots + 1e-9)
    frac = lots - floor
    score = (rules.lot_size * px / nav) * np.minimum(frac, 1 - frac) + 1e-6 * frac
    reg = np.sort(np.argsort(-score)[: min(cfg.register_size, len(universe))])
    base = np.round(lots)                     # stocks outside the register: nearest lot
    base[reg] = floor[reg]                    # register stocks: floor, the qubit may add one lot
    inst = Instance(**kw, base_shares=base * rules.lot_size, bit_stock=reg, bit_lots=np.ones(len(reg)),
                    mode="rounding")
    inst.meta["continuous_weights"] = w
    inst.meta["nearest_bits"] = (frac[reg] >= 0.5).astype(int)   # plain rounding = one specific bitstring
    return inst


def qp_round_target(md: MarketData, date, universe: list[str], account: Account, ec: ExperimentConfig) -> dict:
    """Practitioner baseline: continuous min-TE over every usable member, floored to whole lots."""
    cfg, rules = ec.problem, ec.rules
    cov, cov_b, _ = risk_inputs(md, date, universe, cfg)
    px = md.close.loc[date, universe].to_numpy()
    nav = account.value(md.close.loc[date])
    w_prev = np.array([account.shares.get(t, 0.0) for t in universe]) * px / nav
    w = continuous_min_te(cov, cov_b, cfg.invest_target, w_prev=w_prev, gamma=cfg.turnover_weight)
    sh = round_to_lots(w, px, nav, rules.lot_size)
    return dict(zip(universe, sh))


def daily_values(md: MarketData, account: Account, start, end) -> pd.Series:
    px = md.close.loc[start:end]
    v = pd.Series(account.cash, index=px.index)
    for t, s in account.shares.items():
        v = v + s * px[t]
    return v


def performance(values: pd.Series, index: pd.Series) -> dict:
    rp = values.pct_change().dropna()
    rb = index.pct_change().loc[rp.index]
    act = rp - rb
    yrs = len(rp) / 252
    tot_p = values.iloc[-1] / values.iloc[0] - 1
    tot_b = index.loc[values.index[-1]] / index.loc[values.index[0]] - 1
    return {"tracking_error_ann_pct": float(100 * act.std() * np.sqrt(252)),
            "active_return_ann_pct": float(100 * ((1 + tot_p) ** (1 / yrs) - (1 + tot_b) ** (1 / yrs))),
            "portfolio_return_total_pct": float(100 * tot_p),
            "index_return_total_pct": float(100 * tot_b),
            "correlation": float(np.corrcoef(rp, rb)[0, 1]),
            "days": int(len(rp))}
