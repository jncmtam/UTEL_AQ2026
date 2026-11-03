"""Polynomial QUBO/Ising compilation with explicit slack registers and provenance.

Only the bounded simulator/reference path allocates 2**qubits states. Compilation
and Qiskit export do not enumerate a cost truth table.
"""

from __future__ import annotations
from time import perf_counter
import json
import numpy as np
from agqo.synthesis.profile import digest
from agqo.synthesis.compiler import apply_gate, angle_value, parameter_values
from agqo.synthesis.ir import check_ir


def compile_cost(spec, constrained_subspace=False):
    q = spec.objective_qubo()
    linear = list(map(float, q.linear))
    pairs = {
        (i, j): float(q.quadratic[i, j])
        for i in range(spec.n)
        for j in range(i + 1, spec.n)
    }
    offset = float(q.offset)
    scale = max(
        sum(abs(v) for v in linear) + sum(abs(v) for v in pairs.values()), 1e-12
    )
    linear = [v / scale for v in linear]
    pairs = {ij: v / scale for ij, v in pairs.items()}
    offset /= scale
    # Every violated integer equality contributes >=2; the objective range is <=1.
    penalty = 2.0
    slack = []
    equalities = []

    def equality(coeff, target, label):
        nonlocal offset
        offset += penalty * target**2
        for i, a in coeff.items():
            linear[i] += penalty * (a * a - 2 * target * a)
        for i, a in coeff.items():
            for j, b in coeff.items():
                if i < j:
                    pairs[i, j] = pairs.get((i, j), 0) + 2 * penalty * a * b
        equalities.append(
            {
                "label": label,
                "coefficients": {str(k): v for k, v in coeff.items()},
                "target": target,
            }
        )

    def upper(indices, bound, label):
        coeff = {i: 1 for i in indices}
        if bound >= len(indices):
            return
        if bound < 0:
            raise ValueError("Negative integer bound.")
        # Ordinary binary slack may represent unused larger values; each feasible
        # asset assignment still has a unique zero-penalty slack representation.
        for bit in range(int(bound).bit_length()):
            index = len(linear)
            linear.append(0.0)
            coeff[index] = 1 << bit
            slack.append({"qubit": index, "weight": 1 << bit, "constraint": label})
        equality(coeff, bound, label)

    if not constrained_subspace:
        equality(dict.fromkeys(range(spec.n), 1), spec.k, "cardinality")
        for name in spec.include:
            equality({spec.tickers.index(name): 1}, 1, "include:" + name)
        for name in spec.exclude:
            equality({spec.tickers.index(name): 1}, 0, "exclude:" + name)
    for sector, cap in spec.sector_count_caps.items():
        upper(
            [i for i, s in enumerate(spec.sectors) if s == sector],
            cap,
            "sector_count:" + sector,
        )
    if spec.max_replacements is not None:
        upper(
            np.flatnonzero(spec.previous_weights <= 1e-10).tolist(),
            spec.max_replacements,
            "replacements",
        )
    h = -np.asarray(linear) / 2
    constant = offset + sum(linear) / 2
    zz = []
    for (i, j), value in sorted(pairs.items()):
        if value == 0:
            continue
        constant += value / 4
        h[i] -= value / 4
        h[j] -= value / 4
        zz.append({"qubits": [i, j], "coefficient": value / 4})
    body = {
        "version": "hamiltonian-ir-v3",
        "problem_hash": spec.fingerprint(),
        "asset_qubits": spec.n,
        "qubits": len(linear),
        "linear_z": h.tolist(),
        "quadratic_zz": zz,
        "constant": constant,
        "objective_scale": scale,
        "penalty": penalty,
        "penalty_proof": "Integer residual squared >=1; penalty 2 exceeds normalized objective range bound 1.",
        "equalities": equalities,
        "slack": slack,
        "bit_order": "asset_i_is_bit_i_little_endian_then_slack",
        "phase": "exp(-i*gamma*H)",
        "post_allocation_constraints": [
            "sector_weight_caps",
            "position_bounds",
            "one_way_turnover",
        ],
        "construction": "direct_quadratic_coefficients_no_truth_table",
    }
    if constrained_subspace:
        body["version"] = "hamiltonian-ir-v3-subspace"
        body["certified_subspace"] = True
        body["omitted_zero_terms"] = ["cardinality", "include", "exclude"]
    body["hamiltonian_hash"] = digest(body)
    return body


def cost_values(h, indices):
    indices = np.asarray(indices, dtype=np.int64)
    values = np.full(indices.shape, h["constant"], dtype=float)
    for i, c in enumerate(h["linear_z"]):
        values += c * (1 - 2 * ((indices >> i) & 1))
    for term in h["quadratic_zz"]:
        i, j = term["qubits"]
        values += (
            term["coefficient"]
            * (1 - 2 * ((indices >> i) & 1))
            * (1 - 2 * ((indices >> j) & 1))
        )
    return values


def execute(ir, h, angles, max_qubits=16):
    if h["qubits"] > max_qubits:
        raise ValueError(
            "Statevector resource cap exceeded; compilation remains available."
        )
    values = parameter_values(ir, angles)
    state = np.zeros(1 << h["qubits"], complex)
    state[sum(b << q for q, b in enumerate(ir["initial_bits"]))] = 1
    if ir.get("preparation", {}).get("kind") == "dicke_reference":
        from .baselines import dicke_state

        state[:] = 0
        state[: 1 << h["asset_qubits"]] = dicke_state(ir)
    else:
        for gate in ir["initialization"]:
            apply_gate(state, gate, values)
    for q in range(h["asset_qubits"], h["qubits"]):
        apply_gate(state, {"op": "H", "qubits": [q], "angle": None}, values)
    energy = cost_values(h, np.arange(len(state)))
    for layer in ir["layers"]:
        state *= np.exp(-1j * values[layer["cost"]["parameter"]] * energy)
        for gate in layer["mixer"]:
            apply_gate(state, gate, values)
        for q in range(h["asset_qubits"], h["qubits"]):
            beta = next(
                g["angle"]["parameter"]
                for g in layer["mixer"]
                if g.get("angle") and g["angle"].get("parameter")
            )
            apply_gate(
                state,
                {
                    "op": "RX",
                    "qubits": [q],
                    "angle": {"parameter": beta, "scale": 2, "offset": 0},
                },
                values,
            )
    return state


def circuit(ir, h, angles=None):
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter

    qc = QuantumCircuit(h["qubits"])
    params = {p["id"]: Parameter(p["id"]) for p in ir["parameters"]}
    sources = []

    def mark(source):
        sources.append({"instruction": len(qc.data) - 1, "source": source})

    def add(gate):
        args = (
            gate["qubits"]
            if gate["angle"] is None
            else [angle_value(gate["angle"], params), *gate["qubits"]]
        )
        getattr(qc, gate["op"].lower())(*args)
        mark("llm_or_baseline_gate_program")

    if ir.get("preparation", {}).get("kind") == "dicke_reference":
        from .baselines import dicke_state
        from qiskit.circuit.library import StatePreparation

        qc.append(StatePreparation(dicke_state(ir)), range(h["asset_qubits"]))
        mark("compiler_dicke_dense_reference")
    else:
        for q, b in enumerate(ir["initial_bits"]):
            if b:
                qc.x(q)
                mark("compiler_basis")
        for gate in ir["initialization"]:
            add(gate)
    for q in range(h["asset_qubits"], h["qubits"]):
        qc.h(q)
        mark("compiler_slack_initialization")
    for layer in ir["layers"]:
        gamma = params[layer["cost"]["parameter"]]
        qc.global_phase -= h["constant"] * gamma
        for q, c in enumerate(h["linear_z"]):
            if c:
                qc.rz(2 * c * gamma, q)
                mark("compiler_cost")
        for term in h["quadratic_zz"]:
            qc.rzz(2 * term["coefficient"] * gamma, *term["qubits"])
            mark("compiler_cost")
        for gate in layer["mixer"]:
            add(gate)
        beta = next(
            g["angle"]["parameter"]
            for g in layer["mixer"]
            if g.get("angle") and g["angle"].get("parameter")
        )
        for q in range(h["asset_qubits"], h["qubits"]):
            qc.rx(2 * params[beta], q)
            mark("compiler_slack_mixer")
    if angles is not None:
        qc = qc.assign_parameters(
            {
                params[p["id"]]: float(a)
                for p, a in zip(ir["parameters"], angles, strict=True)
            }
        )
    return qc, sources


def verify(ir, spec, h, max_qubits=16):
    from qiskit import transpile
    from qiskit.quantum_info import Statevector

    start = perf_counter()
    core = {k: v for k, v in ir.items() if k != "preparation"}
    report = check_ir(core, spec, h)
    if "preparation" in ir:
        prep = ir["preparation"]
        if prep != {
            "kind": "dicke_reference",
            "free_qubits": [
                i
                for i, t in enumerate(spec.tickers)
                if t not in spec.include + spec.exclude
            ],
            "ones": spec.k - len(spec.include),
        }:
            return {
                "valid": False,
                "errors": [
                    {
                        "code": "preparation",
                        "message": "Unrecognized or altered Dicke domain.",
                    }
                ],
            }
    if h.get("certified_subspace"):
        from agqo.synthesis.ir import _preserves

        frozen = {spec.tickers.index(t) for t in spec.include + spec.exclude}
        gates = ir["initialization"] + [
            g for layer in ir["layers"] for g in layer["mixer"]
        ]
        certified = (
            ir["mode"] == "preserve_cardinality"
            and sum(ir["initial_bits"]) == spec.k
            and _preserves(ir["initialization"])[0]
        )
        certified &= all(
            ir["initial_bits"][spec.tickers.index(t)] == 1 for t in spec.include
        )
        certified &= all(
            ir["initial_bits"][spec.tickers.index(t)] == 0 for t in spec.exclude
        )
        certified &= all(
            g["op"] in ("RZ", "RZZ") or not frozen.intersection(g["qubits"])
            for g in gates
        )
        if not certified:
            return {
                "valid": False,
                "errors": [
                    {
                        "code": "subspace_certificate",
                        "message": "Omitted penalties require an analytic asset-subspace certificate.",
                    }
                ],
            }
    if not report["valid"]:
        return report
    if h != compile_cost(spec, constrained_subspace=h.get("certified_subspace", False)):
        return {
            "valid": False,
            "errors": [
                {
                    "code": "canonical_cost",
                    "message": "Hamiltonian differs from canonical financial compilation.",
                }
            ],
        }
    if ir["qubit_to_asset"] != list(range(spec.n)):
        return {
            "valid": False,
            "errors": [
                {
                    "code": "mapping",
                    "message": "V3 currently requires identity asset mapping.",
                }
            ],
        }
    if h["qubits"] > max_qubits:
        return {
            "valid": False,
            "status": "unsupported",
            "errors": [
                {
                    "code": "simulation_cap",
                    "message": "Verification exceeds simulator budget.",
                }
            ],
        }
    indices = np.arange(1 << h["qubits"])
    asset_bits = (indices[:, None] >> np.arange(spec.n)) & 1
    cardinal = asset_bits.sum(axis=1) == spec.k
    frozen = np.ones(len(indices), bool)
    for name in spec.include:
        frozen &= asset_bits[:, spec.tickers.index(name)] == 1
    for name in spec.exclude:
        frozen &= asset_bits[:, spec.tickers.index(name)] == 0
    fidelities = []
    leaks = []
    inactive = []
    test = np.random.default_rng(1701).uniform(-1, 1, (3, len(ir["parameters"])))
    try:
        for angles in test:
            state = execute(ir, h, angles, max_qubits)
            qc, _ = circuit(ir, h, angles)
            fidelity = float(
                abs(np.vdot(state, Statevector.from_instruction(qc).data)) ** 2
            )
            leak = float(np.sum(abs(state[~(cardinal & frozen)]) ** 2))
            fidelities.append(fidelity)
            leaks.append(leak)
            if (
                abs(np.linalg.norm(state) - 1) > 1e-9
                or fidelity < 1 - 1e-9
                or leak > 1e-9
            ):
                raise ValueError("Independent execution or conservation check failed.")
        for j, p in enumerate(ir["parameters"]):
            distances = []
            for angles in test[:2]:
                changed = angles.copy()
                changed[j] += 0.17
                distances.append(
                    1 - abs(np.vdot(execute(ir, h, angles), execute(ir, h, changed)))
                )
            if max(distances) < 1e-10:
                inactive.append(p["id"])
        symbolic, _ = circuit(ir, h)
        lowered = transpile(
            symbolic,
            basis_gates=["rz", "sx", "x", "cx"],
            optimization_level=1,
            seed_transpiler=11,
        )
        cx = int(lowered.count_ops().get("cx", 0))
        depth = lowered.depth()
        if cx > 40000 or depth > 80000:
            raise ValueError("Transpiled resource budget exceeded.")
        report.update(
            resources={
                "qubits": h["qubits"],
                "asset_qubits": spec.n,
                "slack_qubits": len(h["slack"]),
                "transpiled_cx": cx,
                "transpiled_depth": depth,
                "includes_cost_and_initialization": True,
            },
            inactive_parameters=inactive,
            active_parameters=len(ir["parameters"]) - len(inactive),
            crosscheck_state_fidelities=fidelities,
            maximum_cardinality_leak=max(leaks),
        )
        if any(p["id"] in inactive for p in ir["parameters"] if p["kind"] == "cost"):
            raise ValueError(
                "Numerically inactive cost parameter; diagnostic circuit is not qualified."
            )
    except Exception as exc:
        report["valid"] = False
        report["errors"].append({"code": "execution", "message": str(exc)})
    report["elapsed_seconds"] = perf_counter() - start
    report["reachability_scope"] = (
        "Asset exchange connectivity certifies cardinality-domain connectivity only; no certificate for all inequality-feasible portfolios."
    )
    return report


def evaluate(
    ir,
    spec,
    h,
    seed=11,
    evaluations=32,
    shots=128,
    exact_expectation=False,
    initial_angles=None,
):
    from scipy.optimize import minimize

    if evaluations < 1 or shots < 1:
        raise ValueError("Positive evaluation and shot budgets required.")
    start = perf_counter()
    rng = np.random.default_rng(seed)
    energy = cost_values(h, np.arange(1 << h["qubits"]))
    initial = (
        rng.uniform(-np.pi, np.pi, len(ir["parameters"]))
        if initial_angles is None
        else np.asarray(initial_angles, float)
    )
    calls = 0
    best = initial.copy()
    value = float("inf")

    class Exhausted(Exception):
        pass

    def loss(angles):
        nonlocal calls, best, value
        if calls >= evaluations:
            raise Exhausted
        calls += 1
        p = abs(execute(ir, h, angles)) ** 2
        p /= p.sum()
        sampled = rng.choice(len(p), size=shots, p=p)
        score = (
            float(p @ energy) if exact_expectation else float(energy[sampled].mean())
        )
        if score < value:
            best = angles.copy()
            value = score
        return score

    try:
        minimize(
            loss,
            initial,
            method="COBYLA",
            options={"maxiter": max(evaluations, len(initial) + 2), "rhobeg": 0.5},
        )
    except Exhausted:
        pass
    p = abs(execute(ir, h, best)) ** 2
    p /= p.sum()
    asset_p = np.bincount(
        np.arange(len(p)) & ((1 << spec.n) - 1), weights=p, minlength=1 << spec.n
    )
    bits = (np.arange(1 << spec.n)[:, None] >> np.arange(spec.n)) & 1
    feasible = np.array([spec.feasible(x) for x in bits])
    scores = np.array([spec.score(x) for x in bits])
    samples = rng.choice(len(asset_p), size=shots, p=asset_p)
    valid = samples[feasible[samples]]
    index = int(valid[np.argmin(scores[valid])]) if len(valid) else None
    probability = float(asset_p @ feasible)
    minimum = float(scores[feasible].min()) if feasible.any() else None
    expected = (
        float(asset_p[feasible] @ scores[feasible] / probability)
        if probability > 1e-15
        else None
    )
    return {
        "status": "feasible" if index is not None else "unknown",
        "feasible": index is not None,
        "bits": bits[index].tolist() if index is not None else None,
        "angles": best.tolist(),
        "seed": seed,
        "sampled_support_indices": samples.tolist(),
        "selection_proxy_objective": float(scores[index])
        if index is not None
        else None,
        "selection_feasible_probability": probability,
        "conditional_proxy_expectation": expected,
        "expected_proxy_regret": expected - minimum
        if expected is not None and minimum is not None
        else None,
        "probability_optimal": float(asset_p @ (feasible & (scores <= minimum + 1e-12)))
        if minimum is not None
        else None,
        "evaluations": calls,
        "total_shots": shots if exact_expectation else (calls + 1) * shots,
        "expectation_access": "exact_statevector"
        if exact_expectation
        else "finite_shots",
        "elapsed_seconds": perf_counter() - start,
        "execution": "ideal_cpu_statevector_with_finite_shot_optimization",
        "fallback_used": False,
    }


def export(ir, h, angles, verification, path):
    from pathlib import Path
    from qiskit import qasm3, qpy, transpile

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    symbolic, sources = circuit(ir, h)
    bound, _ = circuit(ir, h, angles)
    for name, qc in [("parameterized", symbolic), ("bound", bound)]:
        lowered = transpile(
            qc,
            basis_gates=["rz", "sx", "x", "cx"],
            optimization_level=1,
            seed_transpiler=11,
        )
        (path / f"{name}.qasm").write_text(qasm3.dumps(lowered))
        with (path / f"{name}.qpy").open("wb") as stream:
            qpy.dump(lowered, stream)
    for name, value in [
        ("gate_ir", ir),
        ("hamiltonian", h),
        ("verification", verification),
        ("source_map", sources),
        ("angles", angles),
    ]:
        (path / f"{name}.json").write_text(json.dumps(value, indent=2, allow_nan=False))
    (path / "load_circuit.py").write_text(
        'from pathlib import Path\nfrom qiskit import qpy\nwith Path(__file__).with_name("parameterized.qpy").open("rb") as stream:\n    circuit = qpy.load(stream)[0]\nprint(circuit)\n'
    )
