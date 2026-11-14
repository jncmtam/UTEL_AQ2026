"""CircuitSpec: the typed design language the LLM writes in, plus its verifier.

The LLM never emits free-form code. It emits a CircuitSpec (JSON). The compiler
turns a spec plus the locked Hamiltonian into gates; the verifier rejects specs
that are malformed, inconsistent or over the two-qubit-gate budget *before* any
simulation time is spent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

import numpy as np

MIXERS = ("x", "warm_x")
INITS = ("uniform", "warm_start")
ANGLE_INITS = ("linear_ramp", "constant")
OPTIMIZERS = ("cobyla", "nelder_mead", "none")

BOUNDS = {
    "layers": (1, 6),
    "warm_start_epsilon": (0.0, 0.5),
    "coupling_keep_fraction": (0.1, 1.0),
    "ramp_dt": (0.05, 2.0),
    "max_iter": (0, 300),
    "cvar_alpha": (0.02, 1.0),
}

SPEC_SCHEMA = {
    "type": "object",
    "properties": {
        "layers": {"type": "integer", "minimum": 1, "maximum": 6},
        "initial_state": {"type": "string", "enum": list(INITS)},
        "mixer": {"type": "string", "enum": list(MIXERS)},
        "warm_start_epsilon": {"type": "number", "minimum": 0.0, "maximum": 0.5},
        "coupling_keep_fraction": {"type": "number", "minimum": 0.1, "maximum": 1.0},
        "angle_init": {"type": "string", "enum": list(ANGLE_INITS)},
        "ramp_dt": {"type": "number", "minimum": 0.05, "maximum": 2.0},
        "optimizer": {"type": "string", "enum": list(OPTIMIZERS)},
        "max_iter": {"type": "integer", "minimum": 0, "maximum": 300},
        "cvar_alpha": {"type": "number", "minimum": 0.02, "maximum": 1.0},
        "rationale": {"type": "string", "maxLength": 300},
    },
    "required": ["layers", "initial_state", "mixer", "warm_start_epsilon", "coupling_keep_fraction",
                 "angle_init", "ramp_dt", "optimizer", "max_iter", "cvar_alpha", "rationale"],
    "additionalProperties": False,
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
    """Each kept ZZ coupling compiles to RZZ = 2 CX per layer."""
    kept = int(round(spec.coupling_keep_fraction * n_pairs))
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
    if cx > cx_budget:
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


def mutate(spec: CircuitSpec, rng: np.random.Generator) -> CircuitSpec:
    """Classical evolutionary control: perturb 1-3 fields of a parent spec."""
    d = spec.to_dict()
    for name in rng.choice(list(BOUNDS) + ["initial_state", "mixer", "angle_init", "optimizer"],
                           size=int(rng.integers(1, 4)), replace=False):
        if name == "layers":
            d[name] = int(np.clip(d[name] + rng.choice([-1, 1]), 1, 6))
        elif name == "max_iter":
            d[name] = int(np.clip(d[name] + rng.integers(-60, 61), 0, 300))
        elif name in BOUNDS:
            lo, hi = BOUNDS[name]
            d[name] = float(np.round(np.clip(d[name] + rng.normal(0, 0.15 * (hi - lo)), lo, hi), 3))
        elif name == "initial_state":
            d[name] = str(rng.choice(INITS))
        elif name == "mixer":
            d[name] = str(rng.choice(MIXERS))
        elif name == "angle_init":
            d[name] = str(rng.choice(ANGLE_INITS))
        elif name == "optimizer":
            d[name] = str(rng.choice(OPTIMIZERS))
    # repair to an admissible neighbour
    if d["mixer"] == "warm_x":
        d["initial_state"] = "warm_start"
    if d["optimizer"] == "none":
        d["max_iter"] = 0
    elif d["max_iter"] < 10:
        d["max_iter"] = 10
    d["rationale"] = "classical mutation"
    return CircuitSpec.from_dict(d)
