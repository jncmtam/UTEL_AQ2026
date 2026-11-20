"""Phase 1: extract decision-relevant structure from the market data.

Two layers, both computed by code from data strictly before the rebalance date:

MarketInsight     - what the data say about the VN30 universe at this date:
                    correlation structure (one market factor? how many independent bets?),
                    correlation clusters, how coarse whole lots are for this account, and
                    how much tracking quality naive rounding gives up.
HamiltonianInsight - what that market structure implies for the 16-qubit lot-rounding
                    problem: how confident the classical relaxation is about each qubit,
                    where the coupling strength comes from (co-movement of stocks vs the
                    cash budget), how concentrated it is, and its natural energy scale.

Phase 2 (agqo/quantum/design.py) turns HamiltonianInsight into a circuit. The design
may only read fields marked `design input`; fields marked `diagnostic` use the exact
(enumerated) answer and exist to explain results, never to build the circuit.

References
  Mantegna (1999) Hierarchical structure in financial markets. Eur. Phys. J. B 11, 193.
  Meucci (2009) Managing diversification. Risk 22(5), 74 (effective number of bets).
  Egger, Marecek, Woerner (2021) Warm-starting quantum optimization. Quantum 5, 479.
  Sureshbabu et al. (2024) Parameter setting in quantum approximate optimization of weighted problems. Quantum 8 (2024), arXiv:2305.15201.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from .data import MarketData, history_window
from .portfolio import Instance, Landscape

CLUSTER_DISTANCE = 1.0      # Mantegna distance sqrt(2(1-rho)); 1.0 <=> correlation 0.5


@dataclass
class MarketInsight:
    date: str
    usable: int
    excluded: list[str]
    avg_correlation: float              # mean pairwise daily-return correlation
    market_factor_share: float          # largest eigenvalue of the correlation matrix / n
    effective_bets: float               # exp(entropy of eigenvalue shares), Meucci (2009)
    clusters: list[list[str]]           # correlation clusters (average linkage, rho >= 0.5)
    sector_weights: dict[str, float]    # continuous optimum by sector
    lot_cost_pct_median: float          # one lot as % of NAV, median over held stocks
    lot_cost_pct_max: float
    te_continuous_pct: float            # ideal fractional-share portfolio
    te_nearest_pct: float               # practitioner: nearest whole lot
    te_exact_pct: float                 # diagnostic: best whole-lot choice in the register
    register: list[dict]                # per qubit: ticker, sector, lot % NAV, fractional lot, relaxed prob

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HamiltonianInsight:
    n_qubits: int
    n_pairs: int
    warm_probs: list[float]             # design input: continuous relaxation x* in [0,1]
    warm_confidence: float              # design input: mean |2x*-1| (1 = relaxation already binary)
    rms_scale: float                    # design input: RMS of Ising coefficients (Sureshbabu et al.)
    field_to_coupling_rms: float        # design input: RMS(h) / RMS(J)
    coupling_mass_from_risk: float      # design input: share of sum J^2 from stock co-movement
    coupling_mass_from_budget: float    # design input: share of sum J^2 from the cash-budget penalty
    pairs_for_90pct_mass: int           # design input: couplings needed to keep 90% of sum J^2
    feasible_fraction: float            # diagnostic
    near_optimal_states: int            # diagnostic: bitstrings within the success gap
    nearest_rounding_gap: float         # diagnostic: gap of the practitioner's bitstring

    def to_dict(self) -> dict:
        return asdict(self)


def _eigen_stats(corr: np.ndarray) -> tuple[float, float]:
    ev = np.clip(np.linalg.eigvalsh(corr), 0, None)
    share = ev / ev.sum()
    nz = share[share > 0]
    return float(ev.max() / len(ev)), float(np.exp(-(nz * np.log(nz)).sum()))


def correlation_clusters(corr: np.ndarray, tickers: list[str], distance: float = CLUSTER_DISTANCE) -> list[list[str]]:
    if len(tickers) < 2:
        return [list(tickers)]
    d = np.sqrt(np.clip(2 * (1 - corr), 0, None))
    np.fill_diagonal(d, 0)
    labels = fcluster(linkage(squareform(d, checks=False), method="average"), t=distance, criterion="distance")
    groups: dict[int, list[str]] = {}
    for t, lab in zip(tickers, labels):
        groups.setdefault(int(lab), []).append(t)
    return sorted(groups.values(), key=len, reverse=True)


def market_insight(md: MarketData, inst: Instance, land: Landscape, excluded: list[str], lookback: int) -> MarketInsight:
    tickers = inst.tickers
    r, _ = history_window(md, inst.date, tickers, lookback)
    corr = np.atleast_2d(np.corrcoef(r, rowvar=False))       # one stock: corrcoef returns a scalar
    iu = np.triu_indices(len(tickers), 1)
    factor, bets = _eigen_stats(corr)
    avg_corr = float(corr[iu].mean()) if len(iu[0]) else float("nan")
    w = inst.meta["continuous_weights"]
    sectors: dict[str, float] = {}
    for t, wi in zip(tickers, w):
        sectors[md.sector(t)] = sectors.get(md.sector(t), 0.0) + float(wi)
    lot_pct = 100 * inst.rules.lot_size * inst.prices / inst.nav
    held = w > 1e-4
    nb = inst.meta["nearest_bits"]
    x_opt = (land.opt_index >> np.arange(inst.n_qubits)) & 1
    lots = w * inst.nav / (inst.rules.lot_size * inst.prices)
    relaxed = inst.meta.get("relaxed")
    reg = []
    for k, j in enumerate(inst.bit_stock):
        reg.append({"ticker": tickers[j], "sector": md.sector(tickers[j]), "lot_pct_nav": round(float(lot_pct[j]), 2),
                    "fractional_lot": round(float(lots[j] - np.floor(lots[j] + 1e-9)), 3),
                    "relaxed_prob": None if relaxed is None else round(float(relaxed[k]), 3)})
    return MarketInsight(
        date=inst.date, usable=len(tickers), excluded=list(excluded),
        avg_correlation=avg_corr, market_factor_share=factor, effective_bets=bets,
        clusters=correlation_clusters(corr, tickers), sector_weights={k: round(v, 4) for k, v in sectors.items()},
        lot_cost_pct_median=float(np.median(lot_pct[held])) if held.any() else float("nan"),
        lot_cost_pct_max=float(lot_pct[held].max()) if held.any() else float("nan"),
        te_continuous_pct=float(100 * inst.tracking_error(w)[0]),
        te_nearest_pct=float(100 * inst.tracking_error(inst.weights(nb))[0]),
        te_exact_pct=float(100 * inst.tracking_error(inst.weights(x_opt))[0]),
        register=reg)


def coupling_decomposition(inst: Instance) -> tuple[np.ndarray, np.ndarray]:
    """Split the Ising couplings J = J_risk + J_budget.

    In rounding mode qubit k adds one lot of stock j(k), i.e. weight a_k on that stock, so the
    QUBO pair term is a_k a_l (252 Sigma_{j(k)j(l)} + lambda): co-movement of the two stocks
    plus the all-to-all cash-budget penalty. J = Q/2 inherits the same split.
    """
    a = inst.bit_lots * inst.rules.lot_size * inst.prices[inst.bit_stock] / inst.nav
    s = inst.bit_stock
    risk = 252 * inst.cov[np.ix_(s, s)] * np.outer(a, a) / 2
    budget = inst.cfg.budget_penalty * np.outer(a, a) / 2
    np.fill_diagonal(risk, 0)
    np.fill_diagonal(budget, 0)
    return risk, budget


def hamiltonian_insight(cp, success_gap: float) -> HamiltonianInsight:
    """`cp` is a quantum.simulator.CompiledProblem (holds the Ising form and the relaxation)."""
    inst, land = cp.inst, cp.land
    J, h = cp.pair_w, cp.hz
    iu = np.triu_indices(cp.n, 1)
    risk, budget = coupling_decomposition(inst)
    r2, b2 = (risk[iu] ** 2).sum(), (budget[iu] ** 2).sum()
    sq = np.sort(J ** 2)[::-1]
    k90 = int(np.searchsorted(np.cumsum(sq) / max(sq.sum(), 1e-30), 0.90) + 1)
    rms_j = float(np.sqrt(np.mean(J ** 2)))
    nb = inst.meta["nearest_bits"]
    near_idx = int((nb * (2 ** np.arange(len(nb)))).sum())
    gap = land.gap()
    return HamiltonianInsight(
        n_qubits=cp.n, n_pairs=len(J), warm_probs=np.round(cp.relaxed, 4).tolist(),
        warm_confidence=float(np.abs(2 * cp.relaxed - 1).mean()),
        rms_scale=float(np.sqrt(np.mean(np.concatenate([h, J]) ** 2))),
        field_to_coupling_rms=float(np.sqrt(np.mean(h ** 2)) / max(rms_j, 1e-30)),
        coupling_mass_from_risk=float(r2 / max(r2 + b2, 1e-30)),
        coupling_mass_from_budget=float(b2 / max(r2 + b2, 1e-30)),
        pairs_for_90pct_mass=min(k90, len(J)),
        feasible_fraction=float(land.feasible.mean()),
        near_optimal_states=int((np.isfinite(gap) & (gap <= success_gap)).sum()),
        nearest_rounding_gap=float(gap[near_idx]))
