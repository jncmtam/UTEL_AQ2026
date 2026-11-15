"""Experiment configuration: one place for every financial and quantum assumption."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "vn30"

# Vietnamese sector labels in the membership file -> English labels used everywhere else.
SECTOR_EN = {
    "Ngân hàng": "Banking",
    "Bảo hiểm": "Insurance",
    "Công nghệ": "Technology",
    "Năng lượng": "Energy",
    "Nguyên vật liệu": "Materials",
    "Bất động sản": "Real estate",
    "Tiêu dùng": "Consumer",
    "Chứng khoán": "Brokerage",
    "Hàng không": "Aviation",
}


@dataclass(frozen=True)
class MarketRules:
    """HOSE trading frictions used for accounting (verify before live use)."""

    lot_size: int = 100            # shares per board lot on HOSE
    commission: float = 0.0015     # broker fee on traded value, both sides
    sell_tax: float = 0.001        # personal-income tax on sale value


@dataclass(frozen=True)
class ProblemConfig:
    """How one rebalancing decision is turned into a binary optimisation problem."""

    capital_vnd: float = 100_000_000   # small retail account: 100 million VND
    register_size: int = 16            # rounding mode: stocks whose round-up decision gets a qubit
    n_candidates: int = 8              # basket mode: stocks in the concentrated register
    bits_per_asset: int = 2            # basket mode: q_i in {0..3} position units per stock
    invest_target: float = 0.98        # target invested fraction (cash buffer for fees)
    lookback_days: int = 250           # trading days of history for risk estimates
    min_history: int = 180
    shrinkage: float = 0.05            # joint covariance shrinkage towards its diagonal
    turnover_weight: float = 0.002     # gamma: quadratic turnover penalty (annual TE^2 units)
    view_weight: float = 0.02          # eta: tilt towards LLM / Black-Litterman views
    budget_penalty: float = 0.005      # lambda: (sum w - target)^2, calibrated so the QUBO minimum is affordable
    success_gap: float = 0.05          # a sample "succeeds" if normalised gap <= 5 %



@dataclass(frozen=True)
class DesignConfig:
    """Data-insight-driven circuit design (agqo/quantum/design.py).

    Structural choices come from rules on the data (warm start, aligned mixer, coupling
    pruning by mass, RMS scaling). Only the global schedule scalars below are calibrated,
    on the training quarters only, then frozen and transferred to every later quarter.
    """

    coupling_mass: float = 0.90        # keep the strongest ZZ couplings covering this share of sum J^2
    layers_grid: tuple = (1, 2, 3, 4, 5, 6)
    epsilon_grid: tuple = (0.05, 0.10, 0.20, 0.30)
    dgamma_grid: tuple = (0.1, 0.2, 0.35, 0.5, 0.7, 0.9, 1.2)   # LR-QAOA ramp heights (RMS-normalised H)
    dbeta_grid: tuple = (0.2, 0.4, 0.6, 0.8, 1.0)
    refine_iters: int = 40             # optional per-instance COBYLA polish from the transferred angles
    refine_cvar_alpha: float = 0.10
    penalty_grid: tuple = (0.001, 0.002, 0.005, 0.01, 0.02)   # budget penalty, calibrated on training only


@dataclass(frozen=True)
class SearchConfig:
    """Budget for the circuit-design search (identical for every search arm)."""

    proposals_per_round: int = 6
    rounds: int = 4                    # random-search control: rounds x proposals designs
    train_dates: int = 4               # first N rebalance dates are used to design circuits
    cx_budget: int = 1500              # hard cap on two-qubit gates per circuit
    shots: int = 512
    seed: int = 7


@dataclass(frozen=True)
class ExperimentConfig:
    problem: ProblemConfig = field(default_factory=ProblemConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    design: DesignConfig = field(default_factory=DesignConfig)
    rules: MarketRules = field(default_factory=MarketRules)
    first_rebalance: str = "2023-01-01"
    last_rebalance: str = "2026-10-31"

    def to_dict(self) -> dict:
        return asdict(self)
