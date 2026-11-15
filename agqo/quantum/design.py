"""Phase 2: the data insight guides the QAOA circuit and its optimiser.

Structural rules (fixed; each reads one HamiltonianInsight field computed from the data):
  R1 initial state  - warm start: qubit k starts in R_y(theta_k)|0>, sin^2(theta_k/2) = x*_k, the
                      continuous relaxation of the lot problem, clipped to [eps, 1-eps]
                      (Egger, Marecek & Woerner 2021, Quantum 5, 479)
  R2 mixer          - the warm-start mixer whose ground state is that initial state
                      (alignment: He et al. 2023, npj Quantum Inf. 9, 121)
  R3 couplings      - keep the strongest ZZ terms covering a share of sum J^2 (co-movement of stocks)
  R4 energy scale   - divide H_C by the RMS of its coefficients so schedules transfer between quarters
                      (Sureshbabu et al. 2024, Quantum 8, arXiv:2305.15201)
  R5 schedule       - linear ramp: gamma rises, beta falls over p layers (LR-QAOA,
                      Montanez-Barrera & Michielsen 2025, npj Quantum Inf. 11, 131)

AI guidance (learned, training instances only):
  Every schedule s = (p, eps, coupling mass, d_gamma, d_beta) is scored on every training instance.
  A k-nearest-neighbour model in the space of standardised insight features predicts, for a new
  quarter, which schedule worked best on the most similar training instances (instance-similarity
  parameter transfer; cf. Galda et al. 2021, Shaydulin et al. 2023). k is chosen by
  leave-one-date-out cross-validation; k = all reduces to one frozen schedule.
  Pre-registered rule: use the learned schedule only if its cross-validated success beats the frozen
  schedule's cross-validated success; otherwise use the frozen schedule.
Optimiser:
  the chosen schedule is used as is ("transfer"). A short COBYLA polish on CVaR_alpha of the full QUBO
  energy (Barkoutsos et al. 2020, Quantum 4, 256) is applied only if it raises success on the training
  problems (`polish_check`); the other choice is reported as an ablation.
The designer never reads the enumerated landscape; that is used only to score training instances.
"""

from __future__ import annotations

import itertools
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .simulator import CompiledProblem, initial_angles, run_qaoa, statevector
from .spec import CircuitSpec

FEATURES = ["warm_confidence", "decided_share", "log_field_to_coupling", "coupling_concentration",
            "lot_weight_pct"]


def designed_spec(layers: int, epsilon: float, coupling_mass: float, dgamma: float, dbeta: float,
                  polish_iters: int = 0, cvar_alpha: float = 0.1, label: str = "") -> CircuitSpec:
    mode = f"polished by {polish_iters} COBYLA steps" if polish_iters else "transferred schedule, no optimiser"
    return CircuitSpec(
        layers=layers, initial_state="warm_start", mixer="warm_x", warm_start_epsilon=epsilon,
        coupling_keep_fraction=1.0, coupling_mass=coupling_mass, hamiltonian_scale="rms",
        angle_init="linear_ramp", ramp_dt=dgamma, ramp_dbeta=dbeta,
        optimizer="cobyla" if polish_iters else "none", max_iter=polish_iters, cvar_alpha=cvar_alpha,
        rationale=f"{label} warm start + aligned mixer, {coupling_mass:.0%} coupling mass, RMS scale, "
                  f"linear ramp p={layers}; {mode}".strip())


def schedule_grid(dc) -> pd.DataFrame:
    rows = itertools.product(dc.layers_grid, dc.epsilon_grid, dc.coupling_mass_grid, dc.dgamma_grid, dc.dbeta_grid)
    return pd.DataFrame(rows, columns=["layers", "epsilon", "coupling_mass", "dgamma", "dbeta"])


def spec_of(row, polish_iters: int = 0, cvar_alpha: float = 0.1, label: str = "") -> CircuitSpec:
    return designed_spec(int(row["layers"]), float(row["epsilon"]), float(row["coupling_mass"]),
                         float(row["dgamma"]), float(row["dbeta"]), polish_iters, cvar_alpha, label)


def design_features(cp: CompiledProblem) -> dict:
    """Insight features the model may read: no enumeration, only the Hamiltonian and its relaxation."""
    x = cp.relaxed
    J, h = cp.pair_w, cp.hz
    sq = np.sort(J ** 2)[::-1]
    k90 = int(np.searchsorted(np.cumsum(sq) / max(sq.sum(), 1e-30), 0.90) + 1)
    a = cp.inst.bit_lots * cp.inst.rules.lot_size * cp.inst.prices[cp.inst.bit_stock] / cp.inst.nav
    return {"warm_confidence": float(np.abs(2 * x - 1).mean()),
            "decided_share": float((np.abs(2 * x - 1) > 0.8).mean()),
            "log_field_to_coupling": float(np.log(np.sqrt(np.mean(h ** 2)) / max(np.sqrt(np.mean(J ** 2)), 1e-30))),
            "coupling_concentration": min(k90, len(J)) / len(J),
            "lot_weight_pct": float(100 * a.mean())}


def _row_success(args) -> np.ndarray:
    cp, grid, success_gap, cx_budget = args
    gap = cp.land.gap()
    good = np.isfinite(gap) & (gap <= success_gap)
    out = np.empty(len(grid))
    for i, row in enumerate(grid.to_dict("records")):
        spec = spec_of(row)
        if 2 * len(cp.phase_terms(spec)[1]) * spec.layers > cx_budget:
            out[i] = -1.0                                   # over the two-qubit-gate budget: never chosen
            continue
        probs = np.abs(statevector(cp, spec, initial_angles(spec))) ** 2
        out[i] = probs[good].sum() / probs.sum()
    return out


def success_table(cps: list[CompiledProblem], grid: pd.DataFrame, success_gap: float, cx_budget: int,
                  workers: int = 8) -> np.ndarray:
    """success[instance, schedule] with no per-instance optimisation (exact statevector)."""
    jobs = [(cp, grid, success_gap, cx_budget) for cp in cps]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            return np.vstack(list(ex.map(_row_success, jobs)))
    return np.vstack([_row_success(j) for j in jobs])


def _polish_pair(args) -> tuple[float, float]:
    cp, row, iters, alpha, success_gap = args
    rng = np.random.default_rng(0)
    plain = run_qaoa(cp, spec_of(row), success_gap, 64, rng).success_prob
    polished = run_qaoa(cp, spec_of(row, iters, alpha), success_gap, 64, rng).success_prob
    return plain, polished


def polish_check(cps: list[CompiledProblem], row, dc, success_gap: float) -> dict:
    """Does a short CVaR polish raise success on the training problems? Decided on training data only."""
    jobs = [(cp, row, dc.polish_iters, dc.polish_cvar_alpha, success_gap) for cp in cps]
    with ProcessPoolExecutor(max_workers=dc.workers) as ex:
        res = np.array(list(ex.map(_polish_pair, jobs)))
    return {"train_success_plain": float(res[:, 0].mean()), "train_success_polished": float(res[:, 1].mean()),
            "polish_wins": int((res[:, 1] > res[:, 0]).sum()), "n": len(cps),
            "use_polish": bool(res[:, 1].mean() > res[:, 0].mean())}


@dataclass
class ScheduleModel:
    """k-NN schedule selector over standardised insight features (k = 0 means all = frozen)."""

    k: int
    mean: np.ndarray
    std: np.ndarray
    X: np.ndarray            # training features (standardised)
    table: np.ndarray        # training success table

    @classmethod
    def fit(cls, feats: pd.DataFrame, table: np.ndarray, k: int) -> "ScheduleModel":
        X = feats[FEATURES].to_numpy(float)
        mean, std = X.mean(0), X.std(0) + 1e-12
        return cls(k, mean, std, (X - mean) / std, table)

    def choose(self, f: dict) -> int:
        if self.k == 0 or self.k >= len(self.X):
            return int(np.argmax(self.table.mean(0)))
        z = (np.array([f[c] for c in FEATURES]) - self.mean) / self.std
        nn = np.argsort(((self.X - z) ** 2).sum(1))[: self.k]
        return int(np.argmax(self.table[nn].mean(0)))


def cross_validate(feats: pd.DataFrame, table: np.ndarray, groups: np.ndarray, k_grid) -> pd.DataFrame:
    """Leave-one-group-out success of the schedule each k would pick for the held-out instances."""
    rows = []
    for k in k_grid:
        scores = []
        for g in np.unique(groups):
            tr, te = groups != g, groups == g
            model = ScheduleModel.fit(feats[tr], table[tr], k)
            for i in np.flatnonzero(te):
                scores.append(table[i, model.choose(feats.iloc[i].to_dict())])
        rows.append({"k": k, "label": "all (frozen)" if k == 0 else f"{k}-NN", "cv_success": float(np.mean(scores)),
                     "cv_success_sd": float(np.std(scores)), "n": len(scores)})
    return pd.DataFrame(rows)


def design_card(cp: CompiledProblem, spec: CircuitSpec, f: dict) -> dict:
    """How this quarter's data set each circuit element (report and demo)."""
    _, sel, scale = cp.phase_terms(spec)
    reg = cp.inst.register
    top = [f"{reg[int(i)]}-{reg[int(j)]}" for i, j in cp.pairs[sel[:5]]]
    return {"date": cp.inst.date, "qubits": cp.n, "features": {k: round(v, 4) for k, v in f.items()},
            "R1_R2_warm_start": {"epsilon": spec.warm_start_epsilon},
            "R3_couplings": {"kept": int(len(sel)), "of": int(len(cp.pair_w)), "mass": spec.coupling_mass,
                             "strongest_pairs": top},
            "R4_scale": {"rms": scale},
            "R5_schedule": {"layers": spec.layers, "d_gamma": spec.ramp_dt, "d_beta": spec.ramp_dbeta},
            "two_qubit_gates": int(2 * len(sel) * spec.layers)}
