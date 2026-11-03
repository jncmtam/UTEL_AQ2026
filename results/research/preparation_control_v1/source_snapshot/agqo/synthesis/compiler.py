"""Independent NumPy executor, Qiskit lowering, and executable GateIR verifier."""
from __future__ import annotations

from time import perf_counter
import numpy as np

from .ir import Limits, angle_value, check_ir


def apply_gate(state, gate, values):
    op, qubits = gate["op"], gate["qubits"]
    indices = np.arange(len(state), dtype=np.int64)
    q = qubits[0]; bit = 1 << q
    theta = None if gate["angle"] is None else angle_value(gate["angle"], values)
    if op in {"H", "X", "RX", "RY"}:
        left = indices[(indices & bit) == 0]; right = left | bit
        a, b = state[left].copy(), state[right].copy()
        if op == "H":
            state[left], state[right] = (a + b) / np.sqrt(2), (a - b) / np.sqrt(2)
        elif op == "X":
            state[left], state[right] = b, a
        else:
            c, s = np.cos(theta / 2), np.sin(theta / 2)
            state[left], state[right] = (c * a - 1j * s * b, c * b - 1j * s * a) if op == "RX" else (c * a - s * b, s * a + c * b)
    elif op == "RZ":
        z = 1 - 2 * ((indices >> q) & 1)
        state *= np.exp(-0.5j * theta * z)
    elif op == "CX":
        target = 1 << qubits[1]
        left = indices[((indices & bit) != 0) & ((indices & target) == 0)]
        right = left | target
        a = state[left].copy(); state[left] = state[right]; state[right] = a
    else:
        second = qubits[1]
        zz = (1 - 2 * ((indices >> q) & 1)) * (1 - 2 * ((indices >> second) & 1))
        if op == "RZZ":
            state *= np.exp(-0.5j * theta * zz)
        else:
            flipped = indices ^ bit ^ (1 << second)
            phase = 1 if op == "RXX" else -zz
            state[:] = np.cos(theta / 2) * state - 1j * np.sin(theta / 2) * phase * state[flipped]


def mapped_indices(ir):
    indices = np.arange(1 << len(ir["qubit_to_asset"]), dtype=np.int64)
    original = np.zeros_like(indices)
    for q, asset in enumerate(ir["qubit_to_asset"]):
        original |= ((indices >> q) & 1) << asset
    return original


def parameter_values(ir, angles):
    return dict(zip((p["id"] for p in ir["parameters"]), angles, strict=True))


def execute(ir, energies, angles, initialization_only=False):
    values = parameter_values(ir, angles)
    state = np.zeros(len(energies), dtype=complex)
    state[sum(bit << q for q, bit in enumerate(ir["initial_bits"]))] = 1
    for gate in ir["initialization"]:
        apply_gate(state, gate, values)
    if initialization_only:
        return state
    diagonal = energies[mapped_indices(ir)]
    for layer in ir["layers"]:
        state *= np.exp(-1j * values[layer["cost"]["parameter"]] * diagonal)
        for gate in layer["mixer"]:
            apply_gate(state, gate, values)
    return state


def qiskit_lower(ir, energies, angles):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import DiagonalGate
    qc = QuantumCircuit(len(ir["qubit_to_asset"]))
    values, provenance = parameter_values(ir, angles), []
    for q, bit in enumerate(ir["initial_bits"]):
        if bit:
            qc.x(q); provenance.append({"instruction": len(qc.data) - 1, "source": "gate_ir_initial_bits", "qubit": q})

    def add(gate, stage, index):
        op, targets = gate["op"].lower(), gate["qubits"]
        if gate["angle"] is None:
            getattr(qc, op)(*targets)
        else:
            getattr(qc, op)(angle_value(gate["angle"], values), *targets)
        provenance.append({"instruction": len(qc.data) - 1, "source": "gate_ir", "stage": stage, "gate_index": index})

    for i, gate in enumerate(ir["initialization"]):
        add(gate, "initialization", i)
    diagonal = energies[mapped_indices(ir)]
    for layer_index, layer in enumerate(ir["layers"]):
        qc.append(DiagonalGate(np.exp(-1j * values[layer["cost"]["parameter"]] * diagonal)), range(qc.num_qubits))
        provenance.append({"instruction": len(qc.data) - 1, "source": "canonical_compiler_cost", "layer": layer_index,
                           "hamiltonian_hash": ir["hamiltonian_hash"]})
        for i, gate in enumerate(layer["mixer"]):
            add(gate, f"layer_{layer_index}_mixer", i)
    return qc, provenance


def walsh_coefficients(energies):
    """Exact diagonal Pauli-Z expansion via Walsh transform, O(N*2^N)."""
    coefficients=np.array(energies,dtype=float,copy=True)
    step=1
    while step<len(coefficients):
        blocks=coefficients.reshape(-1,2*step)
        left,right=blocks[:,:step].copy(),blocks[:,step:].copy()
        blocks[:,:step],blocks[:,step:]=left+right,left-right
        step*=2
    return coefficients/len(coefficients)


def qiskit_parameterized(ir, energies):
    """Symbolic COST lowered to commuting Z strings; no symbolic DiagonalGate fiction."""
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter
    qc=QuantumCircuit(len(ir['qubit_to_asset']))
    parameters={p['id']:Parameter(p['id']) for p in ir['parameters']}
    for q,bit in enumerate(ir['initial_bits']):
        if bit: qc.x(q)
    def add(gate):
        if gate['angle'] is None:
            getattr(qc,gate['op'].lower())(*gate['qubits'])
        else:
            getattr(qc,gate['op'].lower())(angle_value(gate['angle'],parameters),*gate['qubits'])
    for gate in ir['initialization']:add(gate)
    coefficients=walsh_coefficients(energies[mapped_indices(ir)])
    for layer in ir['layers']:
        gamma=parameters[layer['cost']['parameter']]
        qc.global_phase-=float(coefficients[0])*gamma
        for mask,coefficient in enumerate(coefficients[1:],1):
            if abs(coefficient)<1e-14:continue
            targets=[q for q in range(qc.num_qubits) if (mask>>q)&1]
            for a,b in zip(targets,targets[1:]):qc.cx(a,b)
            qc.rz(2*float(coefficient)*gamma,targets[-1])
            for a,b in reversed(list(zip(targets,targets[1:]))):qc.cx(a,b)
        for gate in layer['mixer']:add(gate)
    return qc,parameters


def verify(ir, problem, hamiltonian, compiled, limits=Limits(), crosscheck=True):
    start = perf_counter()
    report = check_ir(ir, problem, hamiltonian, limits)
    if not report["valid"]:
        report["elapsed_seconds"] = perf_counter() - start
        return report
    from agqo.repair.circuits import compile_diagonal
    from .profile import digest
    canonical = compile_diagonal(problem)
    identity = {k: v for k, v in hamiltonian.items() if k not in {"hamiltonian_hash", "construction_seconds", "classical_states", "limitation"}}
    if digest(identity) != hamiltonian["hamiltonian_hash"] or hamiltonian["problem_hash"] != problem.fingerprint() or not np.allclose(canonical["energies"], compiled["energies"], atol=1e-12, rtol=0) or not np.allclose(hamiltonian["energies"], compiled["energies"], atol=1e-12, rtol=0):
        report["valid"] = False
        report["errors"].append({"code": "canonical_cost", "path": "hamiltonian", "message": "Oracle differs from the financial problem or its recorded hash."})
        return report
    from qiskit import transpile
    from qiskit.quantum_info import Statevector
    rng = np.random.default_rng(173)
    test_angles = [rng.uniform(-1.2, 1.2, len(ir["parameters"])) for _ in range(3)]
    original = mapped_indices(ir)
    cardinal = compiled["bits"][original].sum(axis=1) == problem.k
    overlaps, leaks = [], []
    try:
        for angles in test_angles:
            state = execute(ir, compiled["energies"], angles)
            prepared = execute(ir, compiled["energies"], angles, initialization_only=True)
            leaks.append(float((np.abs(state[~cardinal])**2).sum()))
            if not np.isclose(np.linalg.norm(state), 1, atol=1e-10, rtol=0):
                raise ValueError("State is not normalized.")
            if ir["mode"] == "preserve_cardinality" and (leaks[-1] > 1e-9 or (np.abs(prepared[~cardinal])**2).sum() > 1e-9):
                index = int(np.argmax(np.where(~cardinal, np.abs(state)**2, -1)))
                raise ValueError(f"Cardinality counterexample: qubit_basis_index={index}, asset_bits={compiled['bits'][original[index]].tolist()}")
            qc, source_map = qiskit_lower(ir, compiled["energies"], angles)
            if crosscheck:
                actual = Statevector.from_instruction(qc).data
                overlap = float(abs(np.vdot(actual, state))**2)
                overlaps.append(overlap)
                if not np.isclose(overlap, 1, atol=1e-9, rtol=0):
                    raise ValueError(f"NumPy/Qiskit disagree (overlap={overlap}).")
        lowered = transpile(qc, basis_gates=["rz", "sx", "x", "cx"], optimization_level=1, seed_transpiler=11)
        gates, depth = int(lowered.count_ops().get("cx", 0)), lowered.depth()
        if gates > limits.max_two_qubit_gates or depth > limits.max_transpiled_depth:
            raise ValueError(f"Lowered resource budget exceeded: cx={gates}, depth={depth}. COST is not counted as one gate.")
        inactive = []
        for i, parameter in enumerate(ir["parameters"]):
            distances = []
            for angles in test_angles[:2]:
                shifted = angles.copy(); shifted[i] += 0.17
                distances.append(1 - abs(np.vdot(execute(ir, compiled["energies"], angles), execute(ir, compiled["energies"], shifted))))
            if max(distances) < 1e-10:
                inactive.append(parameter["id"])
        report.update(active_parameters=len(ir["parameters"]) - len(inactive), inactive_parameters=inactive,
                      maximum_cardinality_leak=max(leaks), crosscheck_state_fidelities=overlaps,
                      resources={"transpiled_cx": gates, "transpiled_depth": depth, "target": "generic_rz_sx_x_cx_not_qpu",
                                 "includes_lowered_cost": True}, source_map=source_map)
        if inactive:
            report["warnings"].append({"code": "inactive_parameters", "parameters": inactive,
                                       "message": "Numerical global-phase/inactivity diagnostic, not a proof over all angles."})
    except Exception as exc:
        report["valid"] = False
        report["errors"].append({"code": "execution", "path": "circuit", "message": f"{type(exc).__name__}: {exc}"})
    report["elapsed_seconds"] = perf_counter() - start
    report["business_check"] = "All measured assets are decoded and checked against the original mandate; XY alone certifies only cardinality."
    return report


def export_artifacts(ir, compiled, angles, directory, verification):
    from pathlib import Path
    import json
    from qiskit import qasm3, transpile, qpy
    path = Path(directory); path.mkdir(parents=True, exist_ok=True)
    qc, source_map = qiskit_lower(ir, compiled["energies"], angles)
    lowered = transpile(qc, basis_gates=["rz", "sx", "x", "cx"], optimization_level=1, seed_transpiler=11)
    (path / "circuit.qasm").write_text(qasm3.dumps(lowered))
    parameterized,parameters=qiskit_parameterized(ir,compiled['energies'])
    symbolic=transpile(parameterized,basis_gates=['rz','sx','x','cx'],optimization_level=1,seed_transpiler=11)
    (path/'circuit_parameterized.qasm').write_text(qasm3.dumps(symbolic))
    with (path/'circuit_parameterized.qpy').open('wb') as handle:qpy.dump(symbolic,handle)
    (path/'symbolic_resources.json').write_text(json.dumps({'parameters':list(parameters),
        'cx':int(symbolic.count_ops().get('cx',0)),'depth':symbolic.depth(),
        'cost_lowering':'exact_commuting_Z_strings_from_Walsh_transform',
        'note':'Symbolic decomposition may be larger than optimized bound DiagonalGate; both counts are explicit.'},indent=2))
    (path / "gate_ir.json").write_text(json.dumps(ir, ensure_ascii=False, indent=2))
    (path / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2, allow_nan=False))
    (path / "source_map.json").write_text(json.dumps(source_map, indent=2))
    (path / "angles.json").write_text(json.dumps(dict(zip((p["id"] for p in ir["parameters"]), map(float, angles))), indent=2))
    (path / "circuit.txt").write_text(str(qc.draw(output="text", fold=120)))
