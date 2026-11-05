"""Run the preregistered weight-grid formulation diagnostic without model calls."""

import argparse
from dataclasses import replace
from itertools import combinations, product
from pathlib import Path
from time import perf_counter

import numpy as np
from qiskit import qasm3, qpy, transpile
from qiskit.quantum_info import Statevector

from agqo.problem import to_ising
from agqo.synthesis.profile import digest
from .data import sha, write_json
from .finance import allocate
from .improvement import decode, prepare_inputs
from .sources import capture_sources
from .weight_grid import UnsupportedGrid, compile_grid, cost_circuit, portfolios


RUN_ID = 'weight_grid_v2'


def exhaustive(grid):
    """Full small encoding check, independent financial and Ising evaluations."""
    if grid.n > 16:
        raise ValueError('Exhaustive gate/encoding validation is capped at 16 physical qubits.')
    h = to_ising(grid.qubo)
    financial_residual = ising_residual = penalty_residual = 0.0
    feasible, invalid_min, valid_min = 0, np.inf, np.inf
    for values in product((0, 1), repeat=grid.n):
        x = np.asarray(values)
        score = grid.qubo.energy(x)
        z = 1 - 2*x
        ising = h.constant + h.fields @ z + np.sum(h.couplings*np.outer(z, z))
        ising_residual = max(ising_residual, abs(score - ising))
        residual = grid.residual_penalty(x)
        raw = grid.objective.energy(x[:len(grid.registers)])
        penalty_residual = max(penalty_residual, abs(score - raw - grid.penalty*residual))
        if not residual:
            weights = grid.decode(x)
            if grid.spec.violations_weights(weights):
                raise ValueError('Zero-penalty state violates the financial mandate.')
            if not np.array_equal(grid.encode(weights), x):
                raise ValueError('Slack representation is not uniquely reproducible.')
            feasible += 1
            valid_min = min(valid_min, score)
            financial_residual = max(financial_residual, abs(score-grid.spec.metrics_weights(weights)['objective']))
        else:
            invalid_min = min(invalid_min, score)
    enumerated = list(portfolios(grid))
    if feasible != len(enumerated):
        raise ValueError('Feasible grid and zero-penalty encoded state counts disagree.')
    for w in enumerated:
        grid.encode(w)
    if feasible and invalid_min <= valid_min:
        raise ValueError('An invalid encoded state can minimize energy.')
    if max(financial_residual, ising_residual, penalty_residual) > 1e-10:
        raise ValueError('Numerical energy audit exceeds the frozen tolerance.')
    return {'states': 2**grid.n, 'physical_qubits': grid.n, 'zero_penalty_states': feasible,
            'financial_residual': financial_residual, 'ising_residual': ising_residual,
            'penalty_residual': penalty_residual,
            'invalid_min_minus_valid_min': float(invalid_min-valid_min) if feasible else None}


def run(output):
    path = Path(output)
    if (path/'completion.json').exists():
        print('Completed weight-grid diagnostic retained; no computation or model dispatch.')
        return
    if path.exists() and any(path.iterdir()):
        raise ValueError('Partial run retained; choose a new preregistered ID before retrying.')
    start = perf_counter()
    inputs = prepare_inputs()
    source = next(c for c in inputs['cases'] if c['id'] == 'family1_n20_base')
    manifest = inputs['source_manifest']  # Direct preparation retains the provider manifest.
    original = decode(source['spec'])
    if original.fingerprint() != source['hash']:
        raise ValueError('Source instance identity changed.')
    spec = replace(original, tickers=original.tickers[:3], sectors=('A', 'B', 'B'),
                   returns=original.returns[:126, :3], benchmark=original.benchmark[:126],
                   previous_weights=np.array([.5, .5, 0]), k=2, include=(), exclude=(),
                   sector_count_caps={}, sector_weight_caps={'A': .7}, turnover_cap=None,
                   max_replacements=None, minimum_weight=.02, maximum_weight=.7)
    path.mkdir(parents=True)
    write_json(path/'protocol.json', {'run_id': RUN_ID, 'spec_hash': spec.fingerprint(),
        'source_case': source['id'], 'source_spec_hash': original.fingerprint(),
        'grids': [6, 10, 20, 40], 'resource_grids': [6, 10, 20],
        'new_model_calls': 0, 'new_modal_calls': 0, 'registered_protocol': 'docs/research/WEIGHT_GRID_PROTOCOL.md',
        'tolerance': 1e-10, 'market_admitted': False, 'independent_test': False})
    snapshot = capture_sources(path)
    for file in ('docs/research/WEIGHT_GRID_PROTOCOL.md', 'tests/test_weight_grid.py'):
        dest = path/'source_snapshot'/file
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(file).read_bytes())
        snapshot['files'][file] = sha(dest)
    write_json(path/'source_snapshot/manifest.json', snapshot)
    write_json(path/'financial_spec.json', spec.to_dict())
    write_json(path/'source_financial_spec.json', original.to_dict())
    write_json(path/'dataset_manifest.json', manifest)
    reference = []
    for chosen in combinations(range(spec.n), spec.k):
        x = np.zeros(spec.n, int)
        x[list(chosen)] = 1
        reference.append(allocate(spec, x))
    write_json(path/'continuous_allocations.json', reference)
    if any(r['status'] not in ('optimal', 'infeasible') for r in reference):
        raise ValueError('Unresolved continuous reference; no approximation claim.')
    best = min((r for r in reference if r['feasible']), key=lambda r: r['objective'])
    rows = []
    for units in (6, 10, 20, 40):
        grid = compile_grid(spec, units)
        candidates = []
        for w in portfolios(grid):
            x = grid.encode(w)
            direct = spec.metrics_weights(w)
            energy = grid.objective.energy(x[:len(grid.registers)])
            if abs(energy-direct['objective']) > 1e-10:
                raise ValueError('Grid objective changed the financial cost.')
            candidates.append({'weights': w.tolist(), **direct, 'objective_residual': abs(energy-direct['objective'])})
        write_json(path/f'grid_{units}/encoding.json', grid.to_dict())
        write_json(path/f'grid_{units}/financial_candidates.json', candidates)
        if not candidates:
            rows.append({'units': units, 'status': 'grid_infeasible', 'qubits': grid.n})
            continue
        winner = min(candidates, key=lambda r: r['objective'])
        if winner['objective'] < best['objective']-1e-10:
            raise ValueError('Discrete result beats the continuous numerical reference beyond tolerance.')
        qc = cost_circuit(grid, .173)
        compiled = transpile(qc, basis_gates=['rz', 'sx', 'x', 'cx'], optimization_level=0, seed_transpiler=11)
        directory = path/f'grid_{units}'
        (directory/'cost.qasm').write_text(qasm3.dumps(qc))
        with (directory/'cost.qpy').open('wb') as file:
            qpy.dump(qc, file)
        validation = {'status': 'skipped', 'reason': '>16 physical qubits; no full-statevector claim'}
        if grid.n <= 16:
            validation = {'status': 'passed', **exhaustive(grid)}
            state = np.ones(2**grid.n, complex)/np.sqrt(2**grid.n)
            observed = Statevector(state).evolve(qc).data
            energies = np.array([grid.qubo.energy([(s>>q)&1 for q in range(grid.n)]) for s in range(2**grid.n)])
            residual = float(np.max(abs(observed-state*np.exp(-.173j*energies))))
            if residual > 1e-10:
                raise ValueError('Qiskit cost evolution disagrees with independent energy.')
            validation['statevector_residual'] = residual
        write_json(directory/'verification.json', validation)
        rows.append({'units': units, 'status': 'feasible', 'qubits': grid.n,
            'amount_qubits': len(grid.registers), 'slack_qubits': len(grid.slack),
            'feasible_grid_portfolios': len(candidates), 'best': winner,
            'continuous_reference': best['objective'],
            'relative_discretization_regret': winner['objective']/best['objective']-1,
            'penalty': grid.penalty, 'coefficient_range_bound': grid.range_bound,
            'cost_cx': compiled.count_ops().get('cx', 0), 'cost_depth': compiled.depth(),
            'full_state_validation': validation['status']})
    resources = []
    for units in (6, 10, 20):
        try:
            grid = compile_grid(original, units)
            qc = transpile(cost_circuit(grid, .173), basis_gates=['rz', 'sx', 'x', 'cx'], optimization_level=0, seed_transpiler=11)
            resources.append({'units': units, 'status': 'compiled_only', 'qubits': grid.n,
                'amount_qubits': len(grid.registers), 'slack_qubits': len(grid.slack),
                'cost_cx': qc.count_ops().get('cx', 0), 'cost_depth': qc.depth(),
                'simulation': 'not_attempted', 'penalty': grid.penalty})
        except UnsupportedGrid as exc:
            resources.append({'units': units, 'status': 'unsupported', 'reason': str(exc)})
    # Additional financially meaningful boundary controls are deliberately synthetic.
    controls = [replace(spec, returns=np.array([[.01,.02,0],[-.01,0,.01],[0,.01,-.01]]),
                        benchmark=np.array([.01,0,.005]), sector_weight_caps={}),
                replace(spec, returns=np.zeros((3,3)), benchmark=np.zeros(3),
                        previous_weights=np.array([.5,0,0]), turnover_cap=.5,
                        maximum_weight=.75, sector_weight_caps={}, include=(spec.tickers[0],),
                        exclude=(spec.tickers[2],), sector_count_caps={'B':1}, max_replacements=1)]
    control_records = []
    for i, control in enumerate(controls):
        grid = compile_grid(control, 3 if i == 0 else 4)
        record = {'id': i, 'provenance': 'synthetic_software_control', **exhaustive(grid)}
        control_records.append(record)
        write_json(path/f'controls/{i}_spec.json', control.to_dict())
        write_json(path/f'controls/{i}_encoding.json', grid.to_dict())
    write_json(path/'summary.json', {'rows': rows, 'original_n20_resources': resources,
        'controls': control_records, 'continuous_numerical_reference': best,
        'elapsed_seconds_including_input_preparation': perf_counter()-start,
        'new_model_calls': 0, 'new_modal_calls': 0, 'status': 'formulation_diagnostic_only'})
    manifest = {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
    write_json(path/'artifact_manifest.json', manifest)
    write_json(path/'completion.json', {'status': 'completed', 'manifest_hash': digest(manifest), 'spec_hash': spec.fingerprint()})
    print('Completed weight-grid formulation diagnostic; no LLM or Modal calls.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=f'results/research/{RUN_ID}')
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
