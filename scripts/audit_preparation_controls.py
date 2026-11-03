"""Explicitly post-hoc adversarial classical control; no rescore of circuit rows."""

from pathlib import Path
from time import perf_counter
import json
import sys
import numpy as np
from agqo.research.data import write_json, sha
from agqo.research.published import load, family_indices
from agqo.research.finance import FinancialSpec
from agqo.research.quantum import compile_cost, cost_values
from agqo.research.symmetry import ConservedBasis
from agqo.research.runner import postprocess_samples


def main(directory):
    path = Path(directory)
    output = path / "postrun_control_audit"
    if output.exists():
        raise ValueError("Preserve the previous control audit.")
    protocol = json.loads((path / "protocol.json").read_text())
    x, b, dates, labels, _ = load()
    rows = []
    phase = []
    for n, k in protocol["cases"]:
        indices = family_indices(labels, n)
        spec = FinancialSpec(
            tuple(labels[i] for i in indices),
            tuple("policy_A" if i % 3 == 0 else "policy_B" for i in range(n)),
            x[:126, indices],
            b[:126],
            np.r_[np.ones(k) / k, np.zeros(n - k)],
            k,
            str(dates[125].date()),
            sector_weight_caps={"policy_A": 0.7},
            maximum_weight=0.6,
            provenance="published_selection_conditioned_us_2010",
        )
        h = compile_cost(spec, constrained_subspace=True)
        basis = ConservedBasis(spec, h)
        energy = cost_values(h, basis.indices)
        phase.append(
            {
                "n": n,
                "states_scored": len(energy),
                "normalized_cost_range": float(np.ptp(energy)),
                "normalized_cost_std": float(np.std(energy)),
                "phase_span_at_abs_gamma_pi": float(np.pi * np.ptp(energy)),
                "scope": "Exact classical diagnostic, not supplied to the completed angle optimizer.",
            }
        )
        for seed in protocol["seeds"]:
            start = perf_counter()
            rng = np.random.default_rng(seed)
            count = (protocol["evaluations"] + 1) * protocol["shots"]
            samples = [
                sum(1 << int(i) for i in rng.choice(n, k, replace=False))
                for _ in range(count)
            ]
            allocation = postprocess_samples(spec, samples, 32)
            rows.append(
                {
                    "n": n,
                    "k": k,
                    "seed": seed,
                    "method": "uniform_total_shots",
                    "draws": count,
                    "allocation": allocation,
                    "elapsed_seconds": perf_counter() - start,
                }
            )
    write_json(
        output / "audit.json",
        {
            "scope": "Post-hoc adversarial development control; not preregistered or held-out evidence.",
            "input_hashes": {
                name: sha(path / name)
                for name in ["protocol.json", "decisions.jsonl", "metrics.csv"]
            },
            "script_sha256": sha(__file__),
            "rows": rows,
            "phase_diagnostics": phase,
            "new_inference_calls": 0,
        },
    )
    original = [
        json.loads(s) for s in (path / "decisions.jsonl").read_text().splitlines()
    ]
    text = [
        "# Post-run matched-draw classical audit",
        "",
        "This comparator was added after opening results, to challenge rather than promote the quantum finding. It does not change the frozen circuit rows.",
        "",
        "| N | Method | Mean allocated training objective | Support draws | Allocator cap |",
        "|---:|---|---:|---:|---:|",
    ]
    for n, _ in protocol["cases"]:
        for mode in ["three_pair", "counter_dicke", "uniform"]:
            subset = [r for r in original if r["n"] == n and r["method"] == mode]
            value = np.mean(
                [r["allocation"]["objective"] for r in subset if r["feasible"]]
            )
            text.append(
                f"| {n} | {mode} | {value:.8g} | 128 final; circuit methods also use up to2048 optimizer shots | 32 |"
            )
        subset = [r for r in rows if r["n"] == n]
        value = np.mean(
            [
                r["allocation"]["objective"]
                for r in subset
                if r["allocation"]["feasible"]
            ]
        )
        text.append(f"| {n} | uniform_total_shots | {value:.8g} | 2176 | 32 |")
    text += [
        "",
        "The total-draw comparator uses the same maximum draw count as the circuit evaluation, while circuit postprocessing used only128 final samples. Optimizer bitstrings were not pooled in the frozen method. This is a protocol limitation, not a quantum advantage.",
        "",
        "Means over three seeds on each opened case are descriptive. Instances, not seeds, are the independent research units. No significance test or model selection is justified.",
        "",
        "## Cost-phase diagnostic",
        "",
    ]
    for r in phase:
        text.append(
            f"- N={r['n']}: normalized cost range={r['normalized_cost_range']:.6g}; standard deviation={r['normalized_cost_std']:.6g}; phase span at |gamma|=pi is {r['phase_span_at_abs_gamma_pi']:.6g} radians."
        )
    text += [
        "",
        "Any cost rescaling must be a declared optimizer-conditioning study: rescaling H and inversely rescaling gamma leaves the physical unitary unchanged. It cannot be sold as a new quantum algorithm or repair the allocated-objective distortion.",
        "",
        "Next comparisons should predeclare how all observed optimizer/final samples are used, retain matched total-draw and time references, and fix the financial formulation before spending on models.",
    ]
    (output / "ANALYSIS.md").write_text("\n".join(text) + "\n")
    print(output)


if __name__ == "__main__":
    main(
        sys.argv[1] if len(sys.argv) > 1 else "results/research/preparation_control_v1"
    )
