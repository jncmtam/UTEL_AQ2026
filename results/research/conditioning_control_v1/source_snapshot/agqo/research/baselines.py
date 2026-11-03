"""Evidence-motivated controls with explicit classical evaluation accounting."""

from copy import deepcopy
from itertools import combinations
from pathlib import Path
from time import perf_counter
import numpy as np
from .design import baseline, lower
from .quantum import execute, cost_values, compile_cost, evaluate, verify, export
from .data import write_json


def dicke_state(ir):
    """Small exact reference, deliberately not the paper's O(kn) preparation."""
    prep = ir["preparation"]
    n = len(ir["initial_bits"])
    free = prep["free_qubits"]
    k = prep["ones"]
    if n > 12 or not 0 <= k <= len(free):
        raise ValueError("Dicke reference exceeds the declared domain.")
    fixed = sum(b << q for q, b in enumerate(ir["initial_bits"]) if q not in free)
    state = np.zeros(1 << n, complex)
    for chosen in combinations(free, k):
        state[fixed + sum(1 << q for q in chosen)] = 1
    state /= np.linalg.norm(state)
    return state


def with_dicke(ir, spec):
    value = deepcopy(ir)
    value["initialization"] = []
    value["preparation"] = {
        "kind": "dicke_reference",
        "free_qubits": [
            i
            for i, t in enumerate(spec.tickers)
            if t not in spec.include + spec.exclude
        ],
        "ones": spec.k - len(spec.include),
    }
    return value


def gradient_adaptive(spec, h, steps=3, angle_evaluations=16, seed=11):
    """Finite-difference ADAPT-inspired exchange selection, not a paper replication.

    Each operator gradient costs two exact statevector energy evaluations. Those
    costs are reported separately and cannot be compared to shot-only budgets.
    """
    from agqo.synthesis.builders import exchange

    ir = lower(baseline(spec), spec, h)
    ir["layers"][0]["mixer"] = []
    ir["parameters"] = [ir["parameters"][0]]
    free = [
        i for i, t in enumerate(spec.tickers) if t not in spec.include + spec.exclude
    ]
    pool = list(combinations(free, 2))
    energy = cost_values(h, np.arange(1 << h["qubits"]))
    angles = [0.3]
    history = []
    gradient_evaluations = 0
    used = set()
    start = perf_counter()
    for step in range(min(steps, len(pool))):
        candidates = []
        for edge in pool:
            if edge in used:
                continue
            candidate = deepcopy(ir)
            name = f"beta_adapt_{step}"
            candidate["parameters"].append(
                {"id": name, "kind": "mixer", "initial": None}
            )
            candidate["layers"][0]["mixer"] += exchange(*edge, parameter=name)
            values = []
            for shift in (-1e-4, 1e-4):
                probability = abs(execute(candidate, h, [*angles, shift])) ** 2
                values.append(float(probability @ energy))
            gradient_evaluations += 2
            candidates.append((abs((values[1] - values[0]) / 2e-4), edge, candidate))
        score, edge, ir = max(candidates, key=lambda row: (row[0], row[1]))
        used.add(edge)
        run = evaluate(
            ir,
            spec,
            h,
            seed + step,
            angle_evaluations,
            128,
            exact_expectation=True,
            initial_angles=[*angles, 0.05],
        )
        angles = run["angles"]
        history.append(
            {
                "edge": edge,
                "gradient_magnitude": score,
                "angle_evaluations": run["evaluations"],
            }
        )
    return ir, {
        "operator_pool_size": len(pool),
        "steps": history,
        "gradient_energy_evaluations": gradient_evaluations,
        "angle_energy_evaluations": sum(s["angle_evaluations"] for s in history),
        "seconds": perf_counter() - start,
        "access": "classical_exact_statevector_gradients",
        "paper_replication": False,
    }


def study(directory, evaluations=24):
    from .runner import cases

    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    protocol = {
        "version": "baseline-study-v1",
        "purpose": "development_only_non_LLM",
        "evidence": "docs/research/IMPLEMENTATION_PROTOCOL.md",
        "angle_evaluations": evaluations,
        "shots": 128,
        "seed": 11,
        "cases": [{"id": n, "hash": s.fingerprint()} for n, s in cases()],
        "comparators": [
            "exchange_full_penalty",
            "exchange_certified_subspace",
            "dicke_dense_reference",
            "gradient_adaptive_exchange",
        ],
        "claims": "Initialization/encoding diagnostics; no investment or hardware advantage.",
    }
    target = path / "protocol.json"
    if target.exists():
        import json

        if json.loads(target.read_text()) != protocol:
            raise ValueError("Frozen study differs; use another output directory.")
    write_json(target, protocol)
    records = []
    for name, spec in cases():
        for kind in protocol["comparators"]:
            h = compile_cost(spec, constrained_subspace=kind != "exchange_full_penalty")
            ir = lower(baseline(spec), spec, h)
            search = {}
            if kind == "dicke_dense_reference":
                ir = with_dicke(ir, spec)
            if kind == "gradient_adaptive_exchange":
                ir, search = gradient_adaptive(spec, h, angle_evaluations=evaluations)
            v = verify(ir, spec, h)
            row = {
                "case_id": name,
                "method": kind,
                "verification": v,
                "search_accounting": search,
            }
            if v["valid"]:
                run = evaluate(ir, spec, h, 11, evaluations, 128)
                row["evaluation"] = run
                export(ir, h, run["angles"], v, path / "circuits" / name / kind)
            records.append(row)
            write_json(path / "records.json", records)
    lines = [
        "# Non-LLM development study",
        "",
        "All resource counts include initialization and cost. Dicke synthesis is a dense small reference; gradient access is exact classical simulation.",
        "",
        "| Case | Method | Valid | CX | Feasible probability | Expected proxy regret |",
        "|---|---|---|---:|---:|---:|",
    ]
    for r in records:
        v = r["verification"]
        e = r.get("evaluation", {})
        lines.append(
            f"| {r['case_id']} | {r['method']} | {v['valid']} | {v.get('resources', {}).get('transpiled_cx')} | {e.get('selection_feasible_probability')} | {e.get('expected_proxy_regret')} |"
        )
    lines += [
        "",
        "This development study cannot qualify a model or a market strategy. Full-penalty and certified-subspace encodings are equivalent only on the proven asset subspace. See protocol and raw records for exact budgets.",
    ]
    (path / "RESULTS.md").write_text("\n".join(lines) + "\n")
    return {
        "output": str(path),
        "valid": sum(r["verification"]["valid"] for r in records),
        "total": len(records),
    }
