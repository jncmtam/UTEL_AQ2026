"""Experiment configuration: one place for every financial, quantum and evaluation assumption."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "vn30"
RESULTS_DIR = ROOT / "results" / "final"

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
    """HOSE trading frictions used for accounting (verify with the broker before live use)."""

    lot_size: int = 100            # shares per board lot on HOSE
    commission: float = 0.0015     # broker fee on traded value, both sides
    sell_tax: float = 0.001        # personal-income tax on sale value


@dataclass(frozen=True)
class ProblemConfig:
    """How one rebalancing decision becomes a binary optimisation problem."""

    capital_vnd: float = 100_000_000   # small retail account: 100 million VND
    register_size: int = 16            # stocks whose "one more lot?" decision gets a qubit
    invest_target: float = 0.98        # target invested fraction (cash buffer for fees)
    lookback_days: int = 250           # trading days of history for risk estimates
    min_history: int = 180
    shrinkage: float = 0.05            # joint covariance shrinkage towards its diagonal
    turnover_weight: float = 0.002     # gamma: quadratic turnover penalty (annual TE^2 units)
    budget_penalty: float = 0.005      # lambda: overwritten by the calibration on training data
    success_gap: float = 0.05          # a sample "succeeds" if its normalised gap is <= 5 %


@dataclass(frozen=True)
class DesignConfig:
    """AI-guided circuit design (agqo/quantum/design.py).

    Structure comes from rules on the data insight. The schedule (depth, warm-start
    regularisation, coupling mass, ramp heights) is chosen per quarter by a model fitted on
    training instances only; the frozen single best schedule is the ablation it must beat.
    """

    layers_grid: tuple = (2, 4, 6, 8)
    epsilon_grid: tuple = (0.02, 0.05, 0.10)
    coupling_mass_grid: tuple = (0.75, 0.90, 1.00)
    dgamma_grid: tuple = (0.2, 0.35, 0.5, 0.7, 0.9, 1.2)       # LR-QAOA ramp heights (RMS-normalised H)
    dbeta_grid: tuple = (0.2, 0.4, 0.6, 0.8, 1.0)
    knn_grid: tuple = (3, 5, 10, 20, 0)                          # 0 = all training instances (= frozen schedule)
    polish_iters: int = 40                                       # COBYLA steps on CVaR from the chosen schedule
    polish_cvar_alpha: float = 0.10
    penalty_grid: tuple = (0.001, 0.002, 0.005, 0.01, 0.02)
    train_sizes: tuple = (50e6, 100e6, 200e6, 500e6)            # account sizes of the training instances
    cx_budget: int = 1500
    workers: int = 8


@dataclass(frozen=True)
class SearchConfig:
    """Black-box control: random search over the whole circuit design space."""

    designs: int = 24
    seeds: tuple = (7, 8, 9)
    shots: int = 512
    seed: int = 7


@dataclass(frozen=True)
class ExperimentConfig:
    problem: ProblemConfig = field(default_factory=ProblemConfig)
    design: DesignConfig = field(default_factory=DesignConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    rules: MarketRules = field(default_factory=MarketRules)
    train_start: str = "2023-01-01"    # every calibration uses only 2023
    train_end: str = "2023-12-31"
    test_start: str = "2024-01-01"     # every reported result is after 2023
    test_end: str = "2026-10-31"
    sweep_sizes: tuple = (20e6, 50e6, 100e6, 200e6, 500e6)
    primary_etf: str = "E1VFVN30"

    def to_dict(self) -> dict:
        return asdict(self)
