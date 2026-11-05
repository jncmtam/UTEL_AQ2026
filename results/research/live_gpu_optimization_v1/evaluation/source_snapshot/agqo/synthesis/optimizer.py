"""Finite-shot numerical angle fitting; original objective and explicit total-shot accounting."""
from __future__ import annotations

from time import perf_counter
import numpy as np
from scipy.optimize import minimize

from agqo.repair.solvers import result
from .compiler import execute, mapped_indices


def optimize(ir, problem, compiled, seed=11, evaluations=24, shots=128, use_proposed_angles=False):
    if type(evaluations) is not int or evaluations < 1 or type(shots) is not int or shots < 1:
        raise ValueError("Positive finite evaluation/shot budget required.")
    start, rng = perf_counter(), np.random.default_rng(seed)
    initial = rng.uniform(-np.pi, np.pi, len(ir["parameters"]))
    if use_proposed_angles:
        for i, parameter in enumerate(ir["parameters"]):
            if parameter["initial"] is not None:
                initial[i] = parameter["initial"]
    permutation = mapped_indices(ir)
    energies = compiled["energies"][permutation]
    calls, best, best_energy = 0, initial.copy(), float("inf")

    class Exhausted(Exception):
        pass

    def evaluate(angles):
        nonlocal calls, best, best_energy
        if calls >= evaluations:
            raise Exhausted
        calls += 1
        probability = np.abs(execute(ir, compiled["energies"], angles))**2
        samples = rng.choice(len(probability), shots, p=probability / probability.sum())
        energy = float(energies[samples].mean())
        if energy < best_energy:
            best, best_energy = angles.copy(), energy
        return energy

    try:
        minimize(evaluate, initial, method="COBYLA", options={"maxiter": max(evaluations, len(initial) + 2), "rhobeg": 0.5})
    except Exhausted:
        pass
    probability = np.abs(execute(ir, compiled["energies"], best))**2
    samples = rng.choice(len(probability), shots, p=probability / probability.sum())
    decoded = permutation[samples]
    feasible = decoded[compiled["feasible"][decoded]]
    index = None if not len(feasible) else int(feasible[np.argmin(compiled["objective"][feasible])])
    bits = None if index is None else compiled["bits"][index]
    original_probability=np.zeros_like(probability)
    original_probability[permutation]=probability
    feasible_mask=compiled['feasible']
    feasible_probability=float(original_probability@feasible_mask)
    feasible_values=compiled['objective'][feasible_mask]
    if len(feasible_values):
        optimum=float(feasible_values.min());span=float(np.ptp(feasible_values))
        optimal_mask=feasible_mask & (compiled['objective']<=optimum+1e-12)
        near_mask=feasible_mask & (compiled['objective']<=optimum+.05*span+1e-12)
        conditional=None if feasible_probability<=1e-15 else float((original_probability[feasible_mask]@feasible_values)/feasible_probability)
        distribution={'probability_optimal':float(original_probability@optimal_mask),
                      'probability_near_optimal_5pct':float(original_probability@near_mask),
                      'conditional_feasible_objective_expectation':conditional}
    else:
        distribution={'probability_optimal':None,'probability_near_optimal_5pct':None,'conditional_feasible_objective_expectation':None}
    output = result(problem, "gate_ir_qaoa", bits, "feasible" if bits is not None else "unknown", start,
                    seed=seed, evaluations=calls, total_shots=(calls + 1) * shots, shots_per_evaluation=shots,
                    sampled_feasible_probability=len(feasible) / shots,
                    ideal_feasible_probability=feasible_probability,
                    encoded_energy_expectation=float(probability@energies),**distribution,
                    angles=best.tolist(), angle_initialization="llm_proposed" if use_proposed_angles else "seeded_standard")
    return output
