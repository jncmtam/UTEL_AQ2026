"""Exact statevector QAOA simulator (numpy) for up to ~22 qubits.

Phase separator: exp(-i gamma H_C / s) with H_C the (optionally pruned) Ising form of the
locked QUBO and s a scale that makes angles transfer across dates:
  scale "max" - largest |coefficient| (textbook practice)
  scale "rms" - root-mean-square of the coefficients (Sureshbabu et al. 2024, Quantum 8)
Coupling pruning:
  coupling_keep_fraction - keep a fixed share of pairs, strongest first
  coupling_mass          - keep the fewest strongest pairs covering this share of sum J^2 (data-driven)
Mixers:
  x       - exp(-i beta X) on every qubit; ground state |+>^n  (aligned with 'uniform')
  warm_x  - Egger et al. (2021) warm-start mixer R_y(t) R_z(-2 beta) R_y(-t);
            its eigenstate is the warm-start product state (aligned with 'warm_start', He et al. 2023)
Angles: linear ramp (LR-QAOA, Montanez-Barrera & Michielsen 2025) or constant; optionally refined
by COBYLA / Nelder-Mead on CVaR_alpha of the *full* QUBO energy (Barkoutsos et al. 2020).
Pruning only changes the circuit, never the scoring.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from ..portfolio import Instance, Landscape, all_bitstrings, relaxed_solution
from .spec import CircuitSpec


@dataclass
class QAOAResult:
    spec: CircuitSpec | None
    angles: np.ndarray
    probs: np.ndarray
    evaluations: int
    success_prob: float        # P(feasible and normalised gap <= success_gap)
    feasible_mass: float
    mean_gap: float            # expected normalised gap over feasible mass
    best_sample: int | None    # index of best feasible bitstring among `shots` samples
    best_sample_gap: float
    two_qubit_gates: int
    kept_pairs: int
    better_than_ref: float = float("nan")   # P(affordable and strictly better than the reference bitstring)


class CompiledProblem:
    """Everything the simulator needs, precomputed once per instance."""

    def __init__(self, inst: Instance, land: Landscape):
        self.inst, self.land = inst, land
        self.n = inst.n_qubits
        self.Z = 1 - 2 * all_bitstrings(self.n).astype(np.float64)        # +-1 spins
        J, hz, _ = inst.ising()
        self.J, self.hz = J, hz
        iu = np.triu_indices(self.n, 1)
        self.pairs = np.stack(iu, 1)
        self.pair_w = J[iu]
        self.pair_order = np.argsort(-np.abs(self.pair_w))
        self.energy = land.energy
        self.sort_idx = np.argsort(self.energy)
        self.sorted_energy = self.energy[self.sort_idx]
        self.relaxed = relaxed_solution(inst)
        self._cache: dict[tuple, tuple[np.ndarray, np.ndarray, float]] = {}

    def selected_pairs(self, keep_fraction: float = 1.0, mass: float = 0.0) -> np.ndarray:
        """Indices (into pairs / pair_w) of the couplings kept in the circuit."""
        if mass > 0:
            sq = self.pair_w[self.pair_order] ** 2
            k = int(np.searchsorted(np.cumsum(sq) / max(sq.sum(), 1e-30), mass - 1e-12) + 1)
        else:
            k = int(round(keep_fraction * len(self.pair_w)))
        return self.pair_order[: min(k, len(self.pair_w))]

    def phase_terms(self, spec: CircuitSpec) -> tuple[np.ndarray, np.ndarray, float]:
        """(diagonal of H_C / scale over all bitstrings, kept pair indices, scale)."""
        key = (round(spec.coupling_keep_fraction, 3), round(spec.coupling_mass, 3), spec.hamiltonian_scale)
        if key in self._cache:
            return self._cache[key]
        sel = self.selected_pairs(spec.coupling_keep_fraction, spec.coupling_mass)
        diag = self.Z @ self.hz
        for (i, j), w in zip(self.pairs[sel], self.pair_w[sel]):
            diag += w * self.Z[:, i] * self.Z[:, j]
        coeffs = np.concatenate([self.hz, self.pair_w[sel]])
        if spec.hamiltonian_scale == "rms":
            scale = float(np.sqrt(np.mean(coeffs ** 2)))
        else:
            scale = float(np.abs(coeffs).max())
        scale = max(scale, 1e-12)
        self._cache[key] = (diag / scale, sel, scale)
        return self._cache[key]

    def reference_index(self) -> int:
        """Bitstring of the practitioner's nearest-lot rounding (the classical starting point)."""
        nb = self.inst.meta["nearest_bits"]
        return int((nb * (2 ** np.arange(len(nb)))).sum())


def _apply_1q(psi: np.ndarray, U: np.ndarray, q: int, n: int) -> np.ndarray:
    s = psi.reshape(2 ** (n - q - 1), 2, 2 ** q)
    a, b = s[:, 0, :], s[:, 1, :]
    out = np.empty_like(s)
    out[:, 0, :] = U[0, 0] * a + U[0, 1] * b
    out[:, 1, :] = U[1, 0] * a + U[1, 1] * b
    return out.reshape(-1)


def _ry(t: float) -> np.ndarray:
    c, s = np.cos(t / 2), np.sin(t / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def warm_angles(cp: CompiledProblem, eps: float) -> np.ndarray:
    c = np.clip(cp.relaxed, eps, 1 - eps) if eps > 0 else np.clip(cp.relaxed, 1e-3, 1 - 1e-3)
    return 2 * np.arcsin(np.sqrt(c))


def initial_state(cp: CompiledProblem, spec: CircuitSpec) -> np.ndarray:
    n = cp.n
    if spec.initial_state == "uniform":
        return np.full(2 ** n, 2 ** (-n / 2), dtype=complex)
    psi = np.zeros(2 ** n, dtype=complex)
    psi[0] = 1.0
    for q, t in enumerate(warm_angles(cp, spec.warm_start_epsilon)):
        psi = _apply_1q(psi, _ry(t), q, n)
    return psi


def statevector(cp: CompiledProblem, spec: CircuitSpec, angles: np.ndarray) -> np.ndarray:
    n, p = cp.n, spec.layers
    diag, _, _ = cp.phase_terms(spec)
    psi = initial_state(cp, spec)
    thetas = warm_angles(cp, spec.warm_start_epsilon) if spec.mixer == "warm_x" else None
    gammas, betas = angles[:p], angles[p:]
    for g, b in zip(gammas, betas):
        psi = psi * np.exp(-1j * g * diag)
        if spec.mixer == "x":
            U = np.array([[np.cos(b), -1j * np.sin(b)], [-1j * np.sin(b), np.cos(b)]])
            for q in range(n):
                psi = _apply_1q(psi, U, q, n)
        else:
            rz = np.diag([np.exp(1j * b), np.exp(-1j * b)])       # R_z(-2 beta)
            for q in range(n):
                U = _ry(thetas[q]) @ rz @ _ry(-thetas[q])
                psi = _apply_1q(psi, U, q, n)
    return psi


def initial_angles(spec: CircuitSpec) -> np.ndarray:
    """Linear ramp: gamma rises to ramp_dt, beta falls from ramp_dbeta (or ramp_dt)."""
    p, dg = spec.layers, spec.ramp_dt
    db = spec.ramp_dbeta if spec.ramp_dbeta > 0 else spec.ramp_dt
    if spec.angle_init == "linear_ramp":
        k = (np.arange(p) + 0.5) / p
        return np.concatenate([dg * k, db * (1 - k)])
    return np.concatenate([np.full(p, dg / 2), np.full(p, db / 2)])


def cvar(cp: CompiledProblem, probs: np.ndarray, alpha: float) -> float:
    ps = probs[cp.sort_idx]
    cum = np.cumsum(ps)
    take = np.clip(alpha - (cum - ps), 0, ps)
    return float((take * cp.sorted_energy).sum() / alpha)


def score(cp: CompiledProblem, probs: np.ndarray, success_gap: float, shots: int, rng: np.random.Generator,
          spec: CircuitSpec | None = None, angles: np.ndarray | None = None, evaluations: int = 0,
          two_qubit_gates: int = 0, kept_pairs: int = 0) -> QAOAResult:
    """Metrics of a measurement distribution, shared by every circuit and baseline."""
    probs = probs / probs.sum()
    gap = cp.land.gap()
    ok = np.isfinite(gap)
    success = float(probs[ok & (gap <= success_gap)].sum())
    fmass = float(probs[ok].sum())
    mgap = float((probs[ok] * gap[ok]).sum() / fmass) if fmass > 0 else float("inf")
    ref = cp.reference_index()
    obj = cp.land.objective
    better = ok & (obj < obj[ref] - 1e-15) if ok[ref] else ok      # any affordable choice beats an unaffordable one
    samples = rng.choice(len(probs), size=shots, p=probs)
    sg = gap[samples]
    if np.isfinite(sg).any():
        best, bgap = int(samples[np.argmin(sg)]), float(sg.min())
    else:
        best, bgap = None, float("inf")
    return QAOAResult(spec, np.array([]) if angles is None else angles, probs, evaluations, success, fmass, mgap,
                      best, bgap, two_qubit_gates, kept_pairs, float(probs[better].sum()))


def run_qaoa(cp: CompiledProblem, spec: CircuitSpec, success_gap: float, shots: int,
             rng: np.random.Generator, angles: np.ndarray | None = None) -> QAOAResult:
    evals = 0

    def loss(a):
        nonlocal evals
        evals += 1
        pr = np.abs(statevector(cp, spec, a)) ** 2
        return cvar(cp, pr, spec.cvar_alpha)

    a0 = initial_angles(spec) if angles is None else angles
    if spec.optimizer == "none" or spec.max_iter == 0:
        a = a0
    else:
        method = "COBYLA" if spec.optimizer == "cobyla" else "Nelder-Mead"
        opts = {"maxiter": spec.max_iter} if method == "COBYLA" else {"maxfev": spec.max_iter}
        a = minimize(loss, a0, method=method, options=opts).x
    probs = np.abs(statevector(cp, spec, a)) ** 2
    evals += 1
    _, sel, _ = cp.phase_terms(spec)
    return score(cp, probs, success_gap, shots, rng, spec, a, evals, 2 * len(sel) * spec.layers, len(sel))


def warm_start_only(cp: CompiledProblem, epsilon: float, success_gap: float, shots: int,
                    rng: np.random.Generator) -> QAOAResult:
    """Classical baseline: sample the warm-start product state with zero quantum layers."""
    spec = CircuitSpec(layers=1, initial_state="warm_start", mixer="warm_x", warm_start_epsilon=epsilon,
                       optimizer="none", max_iter=0, rationale="warm start only (p = 0)")
    probs = np.abs(initial_state(cp, spec)) ** 2
    return score(cp, probs, success_gap, shots, rng, spec)


def uniform_reference(cp: CompiledProblem, success_gap: float) -> float:
    """Success probability of random guessing (uniform over all bitstrings)."""
    gap = cp.land.gap()
    return float((np.isfinite(gap) & (gap <= success_gap)).mean())
