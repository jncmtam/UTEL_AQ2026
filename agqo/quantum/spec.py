"""CircuitSpec: the typed description of one QAOA circuit, plus its verifier.

A spec is produced either by the insight-driven designer (agqo/quantum/design.py) or by
the black-box controls (textbook QAOA, random search). The compiler turns a spec plus the
locked Hamiltonian into gates; the verifier rejects malformed or over-budget specs before
any simulation time is spent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

import numpy as np

MIXERS = ("x", "warm_x")
SCALES = ("max", "rms")
INITS = ("uniform", "warm_start")
ANGLE_INITS = ("linear_ramp", "constant")
OPTIMIZERS = ("cobyla", "nelder_mead", "none")

BOUNDS = {
    "layers": (1, 8),                    # the V3 schedule grid uses up to 8 layers
    "warm_start_epsilon": (0.0, 0.5),
    "coupling_keep_fraction": (0.1, 1.0),
    "ramp_dt": (0.05, 2.0),
    "max_iter": (0, 300),
    "cvar_alpha": (0.02, 1.0),
    "coupling_mass": (0.0, 1.0),
    "ramp_dbeta": (0.0, 2.0),
}

@dataclass(frozen=True)
class CircuitSpec:
    layers: int = 2
    initial_state: str = "uniform"
    mixer: str = "x"
    warm_start_epsilon: float = 0.25
    coupling_keep_fraction: float = 1.0
    angle_init: str = "linear_ramp"
    ramp_dt: float = 0.75
    optimizer: str = "cobyla"
    max_iter: int = 100
    cvar_alpha: float = 0.25
    # Insight-driven options (defaults reproduce the textbook behaviour):
    coupling_mass: float = 0.0         # >0: keep the strongest couplings covering this share of sum J^2
    hamiltonian_scale: str = "max"     # "rms": divide H by the RMS of its coefficients (Sureshbabu et al.)
    ramp_dbeta: float = 0.0            # >0: separate beta ramp height (LR-QAOA); 0 = use ramp_dt
    rationale: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "CircuitSpec":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    def to_dict(self) -> dict:
        return asdict(self)

    def key(self) -> tuple:
        d = self.to_dict()
        d.pop("rationale")
        return tuple(round(v, 3) if isinstance(v, float) else v for v in d.values())


DEFAULT_SPEC = CircuitSpec(rationale="Textbook QAOA: uniform superposition, X mixer, p=2, COBYLA, CVaR 0.25.")


def two_qubit_gates(spec: CircuitSpec, n_pairs: int) -> int:
    """Each kept ZZ coupling compiles to RZZ = 2 CX per layer (upper bound for mass-based pruning)."""
    kept = n_pairs if spec.coupling_mass > 0 else int(round(spec.coupling_keep_fraction * n_pairs))
    return 2 * kept * spec.layers


def verify(spec: CircuitSpec, n_qubits: int, cx_budget: int) -> list[str]:
    """Return a list of violations; empty list means admitted."""
    errs = []
    if spec.mixer not in MIXERS:
        errs.append(f"unknown mixer {spec.mixer}")
    if spec.initial_state not in INITS:
        errs.append(f"unknown initial_state {spec.initial_state}")
    if spec.angle_init not in ANGLE_INITS:
        errs.append(f"unknown angle_init {spec.angle_init}")
    if spec.optimizer not in OPTIMIZERS:
        errs.append(f"unknown optimizer {spec.optimizer}")
    if spec.hamiltonian_scale not in SCALES:
        errs.append(f"unknown hamiltonian_scale {spec.hamiltonian_scale}")
    for name, (lo, hi) in BOUNDS.items():
        v = getattr(spec, name)
        if not isinstance(v, (int, float)) or not lo <= v <= hi:
            errs.append(f"{name}={v} outside [{lo}, {hi}]")
    if spec.mixer == "warm_x" and spec.initial_state != "warm_start":
        errs.append("warm_x mixer requires the warm_start initial state (its ground state)")
    if spec.optimizer == "none" and spec.max_iter != 0:
        errs.append("optimizer 'none' must have max_iter 0")
    if spec.optimizer != "none" and spec.max_iter < 10:
        errs.append("an optimiser needs max_iter >= 10")
    n_pairs = n_qubits * (n_qubits - 1) // 2
    cx = two_qubit_gates(spec, n_pairs)
    if spec.coupling_mass == 0 and cx > cx_budget:   # mass-pruned circuits are checked after compilation
        errs.append(f"{cx} two-qubit gates exceed budget {cx_budget}")
    return errs


def random_spec(rng: np.random.Generator) -> CircuitSpec:
    init = rng.choice(INITS)
    mixer = "warm_x" if (init == "warm_start" and rng.random() < 0.5) else "x"
    opt = rng.choice(OPTIMIZERS)
    return CircuitSpec(
        layers=int(rng.integers(1, 7)),
        initial_state=str(init), mixer=mixer,
        warm_start_epsilon=float(np.round(rng.uniform(0, 0.5), 3)),
        coupling_keep_fraction=float(np.round(rng.uniform(0.1, 1.0), 3)),
        angle_init=str(rng.choice(ANGLE_INITS)),
        ramp_dt=float(np.round(rng.uniform(0.05, 2.0), 3)),
        optimizer=str(opt), max_iter=0 if opt == "none" else int(rng.integers(10, 301)),
        cvar_alpha=float(np.round(rng.uniform(0.02, 1.0), 3)),
        rationale="random search",
    )
