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
class SearchConfig:
    """Budget for the circuit-design search (identical for every search arm)."""

    proposals_per_round: int = 6
    rounds: int = 4                    # round 0 + 3 feedback rounds -> 24 designs per arm
    train_dates: int = 4               # first N rebalance dates are used to design circuits
    cx_budget: int = 1500              # hard cap on two-qubit gates per circuit
    shots: int = 512
    seed: int = 7


@dataclass(frozen=True)
class ExperimentConfig:
    problem: ProblemConfig = field(default_factory=ProblemConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    rules: MarketRules = field(default_factory=MarketRules)
    first_rebalance: str = "2023-01-01"
    last_rebalance: str = "2026-07-31"

    def to_dict(self) -> dict:
        return asdict(self)
