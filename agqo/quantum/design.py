"""Phase 2: turn the data insight into a QAOA circuit and its optimiser.

Structural rules (no tuning; each reads one HamiltonianInsight field computed from the data):
  R1 initial state  - warm start: qubit k starts in R_y(theta_k)|0>, sin^2(theta_k/2) = x*_k, the
                      continuous relaxation of the lot problem, clipped to [eps, 1-eps]
                      (Egger, Marecek & Woerner 2021, Quantum 5, 479)              <- warm_probs
  R2 mixer          - the warm-start mixer whose ground state is that initial state
                      (alignment: He et al. 2023, npj Quantum Inf. 9, 121)           <- warm_probs
  R3 couplings      - keep the strongest ZZ terms covering `coupling_mass` of sum J^2; weak
                      co-movement pairs are dropped to save CX gates, the scoring keeps all terms
                                                                                    <- coupling mass profile
  R4 energy scale   - divide H_C by the RMS of its coefficients so one angle schedule fits every
                      quarter (Sureshbabu et al. 2024, Quantum 8, arXiv:2305.15201)  <- rms_scale
  R5 schedule       - linear ramp: gamma rises, beta falls over p layers (LR-QAOA,
                      Montanez-Barrera & Michielsen 2025, npj Quantum Inf. 11, 131)

Calibrated on the training quarters only, then frozen (parameter transfer): p, eps, d_gamma, d_beta.

Two optimiser modes are reported:
  transfer - frozen schedule, zero per-quarter optimisation (deployable: no classical loop on device)
  refine   - COBYLA on CVaR_alpha (Barkoutsos et al. 2020, Quantum 4, 256) started from the
             transferred schedule, with a small budget
The designer never reads the enumerated landscape; that is used only to score the result.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .simulator import CompiledProblem, initial_angles, statevector
from .spec import CircuitSpec


def designed_spec(layers: int, epsilon: float, dgamma: float, dbeta: float, coupling_mass: float,
                  refine_iters: int = 0, cvar_alpha: float = 0.1) -> CircuitSpec:
    mode = f"refine {refine_iters} COBYLA steps" if refine_iters else "transferred schedule, no optimiser"
    return CircuitSpec(
        layers=layers, initial_state="warm_start", mixer="warm_x", warm_start_epsilon=epsilon,
        coupling_keep_fraction=1.0, coupling_mass=coupling_mass, hamiltonian_scale="rms",
        angle_init="linear_ramp", ramp_dt=dgamma, ramp_dbeta=dbeta,
        optimizer="cobyla" if refine_iters else "none", max_iter=refine_iters, cvar_alpha=cvar_alpha,
        rationale=f"insight design: warm start + aligned mixer, {coupling_mass:.0%} coupling mass, RMS scale, "
                  f"linear ramp p={layers}; {mode}")


def _success(cp: CompiledProblem, spec: CircuitSpec, success_gap: float) -> tuple[float, float]:
    probs = np.abs(statevector(cp, spec, initial_angles(spec))) ** 2
    probs /= probs.sum()
    gap = cp.land.gap()
    ok = np.isfinite(gap)
    return float(probs[ok & (gap <= success_gap)].sum()), float(probs[ok].sum())


def calibrate(train: list[CompiledProblem], dc, success_gap: float, cx_budget: int) -> tuple[CircuitSpec, pd.DataFrame]:
    """Grid-search the four schedule scalars on the training quarters; return the frozen spec and the grid."""
    rows = []
    for p, eps, dg, db in itertools.product(dc.layers_grid, dc.epsilon_grid, dc.dgamma_grid, dc.dbeta_grid):
        spec = designed_spec(p, eps, dg, db, dc.coupling_mass)
        cx = max(2 * len(cp.phase_terms(spec)[1]) * p for cp in train)
        if cx > cx_budget:
            continue
        res = [_success(cp, spec, success_gap) for cp in train]
        rows.append({"layers": p, "epsilon": eps, "dgamma": dg, "dbeta": db, "cx_max": cx,
                     "train_success": float(np.mean([r[0] for r in res])),
                     "train_feasible_mass": float(np.mean([r[1] for r in res]))})
    grid = pd.DataFrame(rows)
    grid["rank_key"] = grid.train_success.round(4)
    best = grid.sort_values(["rank_key", "cx_max"], ascending=[False, True]).iloc[0]
    spec = designed_spec(int(best.layers), float(best.epsilon), float(best.dgamma), float(best.dbeta),
                         dc.coupling_mass)
    return spec, grid.drop(columns="rank_key")


def design_card(cp: CompiledProblem, spec: CircuitSpec, hi) -> dict:
    """How this quarter's data set each circuit element (shown in the report and the demo)."""
    _, sel, scale = cp.phase_terms(spec)
    reg = cp.inst.register
    top = [(reg[int(i)], reg[int(j)]) for i, j in cp.pairs[sel[:5]]]
    return {
        "date": cp.inst.date, "qubits": cp.n,
        "R1_R2_warm_start": {"mean_confidence": round(hi.warm_confidence, 3),
                             "clipped_to": [spec.warm_start_epsilon, 1 - spec.warm_start_epsilon]},
        "R3_couplings": {"kept": int(len(sel)), "of": int(len(cp.pair_w)),
                         "mass_kept": spec.coupling_mass,
                         "share_of_mass_from_co_movement": round(hi.coupling_mass_from_risk, 3),
                         "strongest_pairs": [f"{a}-{b}" for a, b in top]},
        "R4_scale": {"rms": scale, "field_to_coupling_rms": round(hi.field_to_coupling_rms, 3)},
        "R5_schedule": {"layers": spec.layers, "d_gamma": spec.ramp_dt, "d_beta": spec.ramp_dbeta},
        "two_qubit_gates": int(2 * len(sel) * spec.layers),
    }
