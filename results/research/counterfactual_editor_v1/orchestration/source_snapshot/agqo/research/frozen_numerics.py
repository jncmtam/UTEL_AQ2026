"""Source-bound numerical coefficients for reproducible cross-platform compilation."""

import numpy as np
from .finance import FinancialSpec
from agqo.synthesis.profile import digest


class _PinnedFinancialSpec(FinancialSpec):
    def quadratic(self):
        return self._canonical_quadratic


def freeze(spec, h):
    matrix, linear, offset = spec.quadratic()
    payload = {
        "version": "frozen-financial-numerics-v1",
        "problem_hash": spec.fingerprint(),
        "matrix": matrix.tolist(),
        "linear": linear.tolist(),
        "offset": float(offset),
        "hamiltonian": h,
    }
    payload["numerical_hash"] = digest(payload)
    return payload


def bind(spec, frozen):
    from .quantum import compile_cost

    body = {k: v for k, v in frozen.items() if k != "numerical_hash"}
    if (
        digest(body) != frozen.get("numerical_hash")
        or frozen["problem_hash"] != spec.fingerprint()
    ):
        raise ValueError(
            "Frozen numerical identity does not match the financial source."
        )
    h = frozen["hamiltonian"]
    if h.get("hamiltonian_hash") != digest(
        {k: v for k, v in h.items() if k != "hamiltonian_hash"}
    ):
        raise ValueError("Frozen Hamiltonian hash is invalid.")
    if spec.objective_kind != "tracking_cost":
        raise ValueError("Numerical transport contract supports tracking_cost only.")
    original = spec.quadratic()
    values = (
        np.asarray(frozen["matrix"], dtype=float),
        np.asarray(frozen["linear"], dtype=float),
        float(frozen["offset"]),
    )
    if values[0].shape != (spec.n, spec.n) or values[1].shape != (spec.n,):
        raise ValueError("Frozen numerical dimensions disagree.")
    for old, new in zip(original, values):
        if not np.isfinite(new).all() or not np.allclose(
            old, new, rtol=1e-12, atol=1e-18
        ):
            raise ValueError(
                "Frozen statistics change the financial objective beyond transport tolerance."
            )
    pinned = _PinnedFinancialSpec(
        **{name: getattr(spec, name) for name in FinancialSpec.__dataclass_fields__}
    )
    for value in values[:2]:
        value.setflags(write=False)
    object.__setattr__(pinned, "_canonical_quadratic", values)
    rebuilt = compile_cost(
        pinned, constrained_subspace=h.get("certified_subspace", False)
    )
    if rebuilt != h or pinned.fingerprint() != spec.fingerprint():
        raise ValueError("Frozen canonical Hamiltonian not reproduced exactly.")
    unpinned = compile_cost(
        spec, constrained_subspace=h.get("certified_subspace", False)
    )
    certificate = {
        "problem_hash": spec.fingerprint(),
        "numerical_hash": frozen["numerical_hash"],
        "canonical_hamiltonian_hash": h["hamiltonian_hash"],
        "platform_recomputed_hamiltonian_hash": unpinned["hamiltonian_hash"],
        "platform_bitwise_same": unpinned == h,
        "maximum_matrix_difference": float(np.max(abs(original[0] - values[0]))),
        "maximum_linear_difference": float(np.max(abs(original[1] - values[1]))),
        "offset_difference": abs(float(original[2]) - values[2]),
        "executed_hamiltonian_bitwise_original": True,
        "tolerance_scope": "Reconstruction audit only; executed coefficients and Hamiltonian are exact frozen originals",
    }
    return pinned, h, certificate
