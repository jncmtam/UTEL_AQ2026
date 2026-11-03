"""Post-run diagnostic analysis; no inference and no alteration of frozen results."""

from pathlib import Path
from time import perf_counter
import json
import sys
import numpy as np
from sklearn.covariance import LedoitWolf
from agqo.research.data import write_json, sha
from agqo.research.published import load, family_indices
from agqo.research.finance import FinancialSpec, audit_proxy, allocate
from agqo.research.quantum import compile_cost, cost_values
from agqo.research.symmetry import ConservedBasis


def main(directory):
    path = Path(directory)
    output = path / "postrun_analysis"
    if output.exists():
        raise ValueError("Preserve earlier diagnostics; use a new development run.")
    start = perf_counter()
    x, b, dates, labels, _ = load()
    protocol = json.loads((path / "protocol.json").read_text())
    records = [
        json.loads(s) for s in (path / "decisions.jsonl").read_text().splitlines()
    ]
    training = x[:126]
    centered = training - training.mean(axis=0)
    singular = np.linalg.svd(centered, compute_uv=False)
    eigen = singular**2 / (len(training) - 1)
    raw_rank = int(np.sum(eigen > eigen.max() * 1e-10))
    shrunk = np.linalg.eigvalsh(LedoitWolf().fit(training).covariance_)
    diagnostics = {
        "scope": "Post-run opened development diagnosis; not a new qualification test.",
        "input_hashes": {
            f: sha(path / f)
            for f in ("protocol.json", "decisions.jsonl", "metrics.csv")
        },
        "source_assets": len(labels),
        "training_rows": len(training),
        "raw_training_covariance_rank": raw_rank,
        "raw_covariance_condition_number": None,
        "condition_policy": "null for rank-deficient covariance; rank cutoff=max_eigenvalue*1e-10",
        "ledoit_wolf_condition_number": float(shrunk.max() / shrunk.min()),
        "covariance_participation_ratio": float(eigen.sum() ** 2 / (eigen @ eigen)),
        "proxy_audits": {},
        "new_inference_calls": 0,
    }
    for n, k, scenario in protocol["cases"]:
        case = f"n{n}_k{k}_{scenario}"
        indices = family_indices(labels, n)
        spec = FinancialSpec(
            tuple(labels[i] for i in indices),
            tuple("policy_A" if i % 3 == 0 else "policy_B" for i in range(n)),
            training[:, indices],
            b[:126],
            np.r_[np.ones(k) / k, np.zeros(n - k)],
            k,
            str(dates[125].date()),
            exclude=(labels[indices[0]],) if scenario == "exclude_incumbent" else (),
            sector_weight_caps={"policy_A": 0.7},
            maximum_weight=0.6,
            provenance="published_selection_conditioned_us_2010",
        )
        if n == 10:
            result = audit_proxy(spec)
            diagnostics["proxy_audits"][case] = {
                key: value for key, value in result.items() if key != "supports"
            }
            write_json(output / f"{case}_all_supports.json", result)
        else:
            clock = perf_counter()
            h = compile_cost(spec, constrained_subspace=True)
            basis = ConservedBasis(spec, h)
            energy = cost_values(h, basis.indices)
            index = int(basis.indices[np.argmin(energy)])
            bits = (index >> np.arange(n)) & 1
            allocation = allocate(spec, bits)
            reference = next(
                r for r in records if r["case"] == case and r["method"] == "joint_scip"
            )
            incumbent = reference["allocation"]["objective"]
            lower = reference["reference"]["lower_bound"]
            diagnostics["proxy_audits"][case] = {
                "status": "exhaustive_proxy_only_allocation_optimum_unproven",
                "proxy_supports_scored": len(basis.indices),
                "proxy_optimum": spec.score(bits),
                "proxy_optimal_support": bits.tolist(),
                "allocation_of_proxy_optimum": allocation,
                "joint_scip_incumbent": incumbent,
                "joint_scip_lower_bound": lower,
                "joint_scip_relative_bound_gap": (incumbent - lower)
                / max(abs(incumbent), 1e-12),
                "proxy_allocation_minus_scip_incumbent": allocation.get("objective", 0)
                - incumbent
                if allocation["feasible"]
                else None,
                "elapsed_seconds": perf_counter() - clock,
            }
    diagnostics["elapsed_seconds"] = perf_counter() - start
    write_json(output / "analysis.json", diagnostics)
    text = [
        "# Data, support proxy and circuit diagnosis",
        "",
        "These diagnostics were defined after opening the development results. They cannot become held-out qualification evidence.",
        "",
        f"The full source universe has 386 assets but only 126 training returns. Raw training covariance rank is {raw_rank}, so its condition number is undefined under the declared policy. Ledoit–Wolf shrinkage condition number is {diagnostics['ledoit_wolf_condition_number']:.2f}. The covariance participation ratio is {diagnostics['covariance_participation_ratio']:.2f}.",
        "",
        "Tracking MSE uses a positive semidefinite return Gram matrix without inverting covariance. Shrinkage is useful for risk-transfer experiments; it does not repair full-year membership conditioning, stale identifiers or publisher return uncertainty.",
        "",
        "## Proxy versus allocated financial objective",
        "",
    ]
    for case, report in diagnostics["proxy_audits"].items():
        if "rank_correlation" in report:
            text.append(
                f"- {case}: all small supports allocated; Spearman={report['rank_correlation']:.4f}; proxy-optimal support allocation regret={report['proxy_optimum_allocation_regret']}; feasible allocation fraction={report['feasible_allocation_fraction']:.4f}."
            )
        else:
            text.append(
                f"- {case}: exact proxy search over {report['proxy_supports_scored']:,} supports; full allocation optimum remains unproven. Proxy-optimal allocated objective={report['allocation_of_proxy_optimum'].get('objective')}; SCIP incumbent={report['joint_scip_incumbent']}; lower bound={report['joint_scip_lower_bound']}; relative incumbent/bound gap={report['joint_scip_relative_bound_gap']:.2%}."
            )
    text += [
        "",
        "## Engineering consequence",
        "",
        "The current shallow fixed circuit explores very few supports at meaningful probability. The data-conditioned rule changes depth/schedule resources but does not beat uniform draws on the N=30 training objective. Do not infer a general topology benefit from correlation alone.",
        "The support proxy must qualify on rank/regret before using energy improvement as evidence of financial value. Keep the common allocator and a full support/weight classical reference. A support-proxy optimum is not a portfolio-allocation optimum.",
        "A next circuit study should compare scalable broad-support preparation and multiple exchange sweeps, with a fixed non-LLM control at matched resources, before a large model sweep. Existing dense Dicke synthesis is only a small reference. Any efficient Dicke implementation needs independent equivalence and resource tests.",
        "Do not spend on a larger model merely to make this opened development score improve. Freeze a new protocol, including preparation/angle-search accounting, before a new inference study.",
    ]
    (output / "ANALYSIS.md").write_text("\n".join(text) + "\n")
    print(
        json.dumps(
            {"output": str(output), "elapsed_seconds": diagnostics["elapsed_seconds"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main(
        sys.argv[1]
        if len(sys.argv) > 1
        else "results/research/published_development_v2"
    )
