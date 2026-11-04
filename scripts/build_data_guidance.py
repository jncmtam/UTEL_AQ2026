"""Prepare auditable feature-guided requests locally; never call an LLM or Modal."""

from pathlib import Path
import json
import csv
import shutil
from time import perf_counter
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agqo.research.data import write_json, sha
from agqo.research.guidance import exchange_features, guided_request
from agqo.research.improvement import prepare_inputs, decode
from agqo.research.quantum import compile_cost


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / "results/research/data_guidance_v1"
    if (out / "completion.json").exists():
        print("Completed offline artifacts retained; no inference or new computation.")
        return
    if out.exists():
        raise ValueError("Partial artifact directory retained; review before resuming.")
    started = perf_counter()
    inputs = prepare_inputs()
    old = json.loads(
        (root / "results/research/improvement_v1/records.json").read_text()
    )
    budgets = {
        r["case_id"]: r["verification"]["resources"]
        for r in old
        if r["method"] == "fixed"
    }
    protocol = {
        "version": "data-guidance-offline-v1",
        "source_inputs_hash": inputs["inputs_hash"],
        "source_cutoff": inputs["source_cutoff"],
        "source_manifest": inputs["source_manifest"],
        "source_scope": "Opened conditional US development cases; no financial holdout scored",
        "llm_calls": 0,
        "modal_calls": 0,
        "new_quality_searches": 0,
        "protocol_sha256": sha(root / "docs/research/DATA_GUIDANCE_PROTOCOL.md"),
        "acceptance": "Exact small-case moments, traceable requests and unchanged compiler objective; no quality claim",
    }
    write_json(out / "protocol.json", protocol)
    rows, pairs, features_by_id = [], [], {}
    for case in inputs["cases"]:
        spec = decode(case["spec"])
        features = exchange_features(spec)
        h = compile_cost(spec, True)
        request = guided_request(spec, h, budgets[case["id"]])
        folder = out / "cases" / case["id"]
        write_json(folder / "exchange_features.json", features)
        write_json(folder / "request.json", request)
        strongest = max(features["edges"], key=lambda e: e["rms_delta_B"])
        rows.append(
            {
                "case_id": case["id"],
                "problem_hash": spec.fingerprint(),
                "hamiltonian_hash": h["hamiltonian_hash"],
                "feature_hash": features["feature_hash"],
                "request_hash": request["request_hash"],
                "allowed_pairs": len(features["edges"]),
                "strongest_sensitivity_edge": strongest["id"],
                "strongest_sensitivity_correlation": strongest["correlation"],
                "max_rms_delta_B": strongest["rms_delta_B"],
                "serialized_request_bytes_not_tokens": len(
                    json.dumps(request).encode()
                ),
                "construction_seconds": features["construction_seconds"],
            }
        )
        pairs.extend({"case_id": case["id"], **e} for e in features["edges"])
        features_by_id[case["id"]] = features
    write_json(out / "request_audit.json", rows)
    with (out / "exchange_features.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(pairs)
    features = features_by_id["family0_n20_base"]
    n = len(features["free_qubits"])
    corr, sensitivity = np.eye(n), np.zeros((n, n))
    scale = np.median([e["rms_delta_B"] for e in features["edges"]]) or 1
    for edge in features["edges"]:
        i, j = edge["qubits"]
        corr[i, j] = corr[j, i] = edge["correlation"]
        sensitivity[i, j] = sensitivity[j, i] = edge["rms_delta_B"] / scale
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), layout="constrained")
    im = axes[0].imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    fig.colorbar(im, ax=axes[0], shrink=0.76, label="Correlation")
    im = axes[1].imshow(sensitivity, cmap="viridis", vmin=0)
    fig.colorbar(im, ax=axes[1], shrink=0.76, label="RMS delta B / median")
    axes[0].set_title("Asset returns: correlation")
    axes[1].set_title("Locked proxy: exchange sensitivity")
    for ax in axes[:2]:
        ax.set_xlabel("Asset qubit")
        ax.set_ylabel("Asset qubit")
    axes[2].scatter(
        [e["correlation"] for e in features["edges"]],
        [e["rms_delta_B"] / scale for e in features["edges"]],
        s=18,
        alpha=0.75,
    )
    axes[2].set(
        xlabel="Pair correlation",
        ylabel="RMS delta B / median",
        title="Different evidence for circuit design",
    )
    axes[2].grid(alpha=0.2)
    fig.suptitle(
        "N20/K5 US development case — descriptors, not circuit-quality results",
        fontsize=12,
    )
    fig.savefig(out / "features-to-circuit.png", dpi=180)
    plt.close(fig)
    table = "\n".join(
        f"| {r['case_id']} | {r['allowed_pairs']} | {r['strongest_sensitivity_edge']} | "
        f"{r['strongest_sensitivity_correlation']:.3f} | {r['serialized_request_bytes_not_tokens']:,} |"
        for r in rows
    )
    (out / "RESULTS.md").write_text(
        "# Explicit data-to-circuit guidance: offline evidence\n\n"
        "The previous prompt supplied data but did not require a specific feature-to-gate link. "
        "The new optional API supplies exact exchange-difference statistics and requires every "
        "chosen tree connection to cite the matching pair. No new model was run.\n\n"
        "![Correlation and exchange evidence](features-to-circuit.png)\n\n"
        "Correlation describes returns; exchange sensitivity additionally reflects benchmark "
        "and cost terms in the locked selection proxy. Neither implies that a pair is a good "
        "mixer edge. The figure has no measured quantum or financial performance claim.\n\n"
        f"Prepared {len(rows)} requests covering {len(pairs)} permitted pair records; "
        "no stock filtering, allocation queries, new optimization or holdout scoring. "
        "Requests include every allowed pair, in rounded compact rows, and preserve the "
        "compiler-owned objective. Byte sizes below are not tokenizer counts or a context-fit "
        "certificate; actual tokenization must precede any future inference.\n\n"
        "| Opened development case | Pair records | Largest RMS pair | Pair correlation | Request bytes |\n"
        "|---|---:|---|---:|---:|\n" + table + "\n\n"
        "## What the LLM must decide\n\n"
        "1. Which permitted exchange connections offer a testable tradeoff, using both "
        "sensitivity and stability rather than mechanically ranking correlation.\n"
        "2. How to order overlapping/disjoint exchanges within compiled resource limits.\n"
        "3. Whether one or two shared beta groups earn their additional fitting cost.\n\n"
        "Compiler-owned preparation and cost remain locked. The response adapter rejects "
        "missing or unrelated pair citations, then independently verifies quantum semantics "
        "and resources. Explanation validity cannot substitute for measured allocated F.\n\n"
        "## Limits and next decision\n\n"
        "Statistics are exact for equal-weight B under cardinality/fixed bits, not for the "
        "continuous allocated objective F or all mandate inequalities. The 2010 corpus has "
        "full-year membership conditioning and artificial policy buckets. These are opened "
        "algorithm-development cases; independent financial value remains unqualified.\n\n"
        "Compare an identical LLM with/without guidance, a deterministic feature rule, random "
        "and adaptive classical circuit search, and strong allocation-aware local search "
        "under a frozen matched total budget on untouched cases. Gate changes and plausible "
        "explanations alone are insufficient. No new paid experiment is scheduled.\n\n"
        "Protocol: [DATA_GUIDANCE_PROTOCOL](../../../docs/research/DATA_GUIDANCE_PROTOCOL.md). "
        "API: agqo.research.guidance.guided_request / admit_guided_program. "
        "Legacy Modal request paths are unchanged; these prepared requests are not deployed "
        "live-model results.\n"
    )
    (out / "PROGRESS.md").write_text(
        "# Progress\n\nImplemented exact exchange descriptors, explicit prompt procedure, "
        "per-edge evidence schema and independent admission adapter. Prepared eight US "
        "development examples and visualization. No new inference or quality experiment. "
        "Remaining: tokenized runtime preflight, frozen guidance ablation and independent "
        "financial qualification after data admission.\n"
    )
    write_json(
        out / "cost_report.json",
        {
            "execution": "local CPU only",
            "modal_calls": 0,
            "llm_calls": 0,
            "new_paid_reservation_usd": 0,
            "wall_seconds": perf_counter() - started,
            "not_an_invoice": True,
        },
    )
    for name in [
        "agqo/research/guidance.py",
        "agqo/research/design.py",
        "agqo/research/budget_search.py",
        "agqo/research/finance.py",
        "agqo/research/improvement.py",
        "agqo/synthesis/profile.py",
        "agqo/synthesis/typed.py",
        "scripts/build_data_guidance.py",
        "tests/test_guidance.py",
        "docs/research/DATA_GUIDANCE_PROTOCOL.md",
    ]:
        target = out / "source_snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    files = {
        str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()
    }
    write_json(
        out / "completion.json",
        {
            "status": "offline_requests_prepared_not_model_qualified",
            "requests": len(rows),
            "pair_records": len(pairs),
            "llm_calls": 0,
            "modal_calls": 0,
            "sha256_files": files,
        },
    )
    print(
        json.dumps(
            {
                "requests": len(rows),
                "pairs": len(pairs),
                "output": str(out),
                "new_inference": False,
            }
        )
    )


if __name__ == "__main__":
    main()
