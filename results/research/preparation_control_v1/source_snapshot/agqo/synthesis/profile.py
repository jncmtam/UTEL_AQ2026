"""Causal numerical descriptors and immutable financial/Hamiltonian identities."""
from __future__ import annotations

import hashlib
import json
import numpy as np
from agqo.repair.circuits import compile_diagonal


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def correlation(returns):
    centered = returns - returns.mean(axis=0)
    covariance = centered.T @ centered / max(len(returns) - 1, 1)
    std = np.sqrt(np.maximum(np.diag(covariance), 0))
    denominator = np.outer(std, std)
    c = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 1e-20)
    np.fill_diagonal(c, 1)
    return np.clip(c, -1, 1), covariance, np.flatnonzero(std <= 1e-10).tolist()


def financial_ir(problem):
    q = problem.objective_qubo()
    return {"version": "financial-ir-v1", "problem_hash": problem.fingerprint(), "cutoff": problem.cutoff,
            "tickers": list(problem.tickers), "sectors": list(problem.sectors), "n": problem.n, "k": problem.k,
            "previous_weights": problem.previous_weights.tolist(), "cost_rates": problem.cost_rates.tolist(),
            "cost_weight": problem.effective_cost_weight, "mandate": problem.mandate.to_dict(),
            "objective": "mean((returns @ (x/K) - benchmark)**2) + cost_weight * cost_rates @ abs(x/K - previous_weights)",
            "objective_coefficients": {"linear": q.linear.tolist(), "upper_quadratic": q.quadratic.tolist(), "offset": q.offset},
            "units": {"returns": "fraction_per_observation", "turnover": "two_way_fraction_NAV", "fees": "fraction_per_side"}}


def data_profile(problem):
    r = problem.returns
    c, covariance, zero_variance = correlation(r)
    eigen = np.linalg.eigvalsh(covariance)
    cutoff = max(float(eigen.max()), 1e-20) * 1e-10
    positive = eigen[eigen > cutoff]
    rank = len(positive)
    condition = None if rank < problem.n else float(positive.max() / positive.min())
    half = max(2, len(r) // 2)
    short, _, _ = correlation(r[-half:])
    edges = [(i, j, float(c[i, j])) for i in range(problem.n) for j in range(i + 1, problem.n)]
    strong = sorted(edges, key=lambda edge: -abs(edge[2]))[:min(16, len(edges))]
    # Connected components at a declared, fixed |rho| threshold, not a claim of causation.
    unseen, clusters = set(range(problem.n)), []
    while unseen:
        seed = min(unseen); unseen.remove(seed); group, queue = [seed], [seed]
        while queue:
            i = queue.pop()
            neighbors = sorted(j for j in unseen if abs(c[i, j]) >= 0.65)
            for j in neighbors:
                unseen.remove(j); group.append(j); queue.append(j)
        clusters.append(sorted(group))
    q = problem.objective_qubo()
    coefficients = [{"id": f"h_{i}", "qubits": [i], "value": float(v)} for i, v in enumerate(q.linear)]
    coefficients += [{"id": f"J_{i}_{j}", "qubits": [i, j], "value": float(q.quadratic[i, j])} for i in range(problem.n) for j in range(i + 1, problem.n)]
    magnitudes = np.abs([x["value"] for x in coefficients])
    return {"version": "data-profile-v1", "problem_hash": problem.fingerprint(), "cutoff": problem.cutoff,
            "feature_ids": ["CORRELATION", "CLUSTERS", "SPECTRUM", "OBJECTIVE_TERMS", "INCUMBENT", "STABILITY"],
            "correlation": c.tolist(), "covariance": covariance.tolist(), "zero_variance_assets": zero_variance,
            "clusters": clusters, "cluster_rule": "connected_components_abs_correlation_ge_0.65",
            "eigenvalues": eigen.tolist(), "numerical_rank": rank, "condition_number": condition,
            "condition_policy": "null if rank deficient; eigenvalue cutoff=max_eigenvalue*1e-10",
            "correlation_dispersion": float(np.std([e[2] for e in edges])),
            "strong_pairs": [{"assets": [i, j], "correlation": v} for i, j, v in strong],
            "objective_coefficients": coefficients,
            "interaction_density": float(np.count_nonzero(np.triu(np.abs(q.quadratic) > 1e-14, 1)) / max(len(edges), 1)),
            "coefficient_abs_quantiles": np.quantile(magnitudes, [0, 0.5, 0.9, 1]).tolist(),
            "previous_weights": problem.previous_weights.tolist(),
            "current_violations": problem.violations_weights(problem.previous_weights),
            "correlation_window_sensitivity_frobenius": float(np.linalg.norm(short - c)),
            "formulas": {"covariance": "centered.T@centered/(T-1)", "correlation": "cov_ij/(std_i*std_j), zero variance -> offdiag 0",
                         "stability": "norm(corr(last_half)-corr(full),fro)"},
            "interpretation": "Design descriptors only. Correlation does not establish causal or quantum performance benefits."}


def hamiltonian_ir(problem):
    compiled = compile_diagonal(problem)
    payload = {"version": "hamiltonian-ir-v1", "problem_hash": problem.fingerprint(),
               "encoding": compiled["encoding"], "energies": compiled["energies"].tolist(),
               "objective_scale": compiled["scale"], "bit_order": "asset_i_is_bit_i_little_endian",
               "phase": "exp(-i*gamma*energy)", "hard_barrier": 2.0}
    payload["hamiltonian_hash"] = digest(payload)
    payload["construction_seconds"] = compiled["seconds"]
    payload["classical_states"] = compiled["states"]
    payload["limitation"] = compiled["limitation"]
    return payload, compiled


def ablate_profile(profile, mode, donor=None):
    if mode == "full":
        return profile
    if mode == "constraints_only":
        return {"version": profile["version"], "problem_hash": profile["problem_hash"], "cutoff": profile["cutoff"], "feature_ids": []}
    removed = {"correlation", "covariance", "clusters", "cluster_rule", "strong_pairs", "correlation_dispersion", "correlation_window_sensitivity_frobenius"}
    if mode == "no_correlation":
        return {**{k: v for k, v in profile.items() if k not in removed},
                "feature_ids": [x for x in profile["feature_ids"] if x not in {"CORRELATION", "CLUSTERS", "STABILITY"}]}
    if mode == "shuffled" and donor is not None:
        return {**profile, **{k: donor[k] for k in removed if k in donor}, "ablation": "correlation_descriptors_from_different_instance"}
    raise ValueError("Unknown ablation or missing donor profile.")
