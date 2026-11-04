"""Frozen resource-aware controls and real-US conditional budget curves."""

from copy import deepcopy
import hashlib
import json
import csv
from pathlib import Path
from time import perf_counter
import numpy as np

from .budget_search import search, prefix_rows, disjoint_schedule, resource_eligibility
from .cloud_pipeline import common_program, sampled_allocation_search
from .data import write_json
from .design import lower
from .finance import FinancialSpec, joint_reference
from .quantum import compile_cost, verify, export
from agqo.synthesis.profile import digest

VERSION = "cost-and-budget-controls-v1"


def decode(value):
    return FinancialSpec(
        **{k: v for k, v in value.items() if k in FinancialSpec.__dataclass_fields__}
    )


def prepare_inputs():
    from .published import load

    x, b, dates, labels, manifest = load("data/published_us")
    order = sorted(
        range(len(labels)),
        key=lambda i: hashlib.sha256(
            ("AGQO-improvement-family-v1:" + labels[i]).encode()
        ).hexdigest(),
    )
    cases = []
    for family in range(2):
        members = order[family * 20 : (family + 1) * 20]
        for n, k in [(12, 3), (20, 5)]:
            selected = members[:n]
            for scenario in ["base", "exit"]:
                spec = FinancialSpec(
                    tuple(f"ASSET_{i:02}" for i in range(n)),
                    tuple("policy_A" if i % 3 == 0 else "policy_B" for i in range(n)),
                    x[:126, selected],
                    b[:126],
                    np.r_[np.ones(k) / k, np.zeros(n - k)],
                    k,
                    str(dates[125].date()),
                    maximum_weight=0.6,
                    sector_weight_caps={"policy_A": 0.7},
                    exclude=("ASSET_00",) if scenario == "exit" else (),
                    provenance="published_conditional_development_not_investable",
                )
                cases.append(
                    {
                        "id": f"family{family}_n{n}_{scenario}",
                        "family": family,
                        "source_columns": selected,
                        "spec": spec.to_dict(),
                        "hash": spec.fingerprint(),
                    }
                )
    path = Path("results/research/modal_e2e_v1")
    original = json.loads((path / "evaluation/records.json").read_text())
    ablations = []
    for row in original:
        if row["method"] == "coder30":
            ablations.append(
                {
                    "case_id": row["case_id"],
                    "program": row["program"],
                    "original": row,
                    "spec": json.loads(
                        (
                            path / "inputs" / row["case_id"] / "financial_spec.json"
                        ).read_text()
                    ),
                }
            )
    return {
        "version": VERSION,
        "cases": cases,
        "ablations": ablations,
        "source_manifest": manifest,
        "source_cutoff": str(dates[125].date()),
        "inputs_hash": digest(cases),
        "new_inference_calls": 0,
    }


def run(directory, inputs):
    from .sources import capture_sources

    path = Path(directory)
    if inputs["version"] != VERSION or inputs["inputs_hash"] != digest(inputs["cases"]):
        raise ValueError("Input identity mismatch.")
    if (path / "completion.json").exists():
        saved = json.loads((path / "completion.json").read_text())
        if saved["inputs_hash"] != inputs["inputs_hash"]:
            raise ValueError("Completed input changed.")
        return saved
    if (path / "protocol.json").exists():
        raise ValueError(
            "Partial frozen run retained; do not automatically overwrite/retry."
        )
    protocol = {
        "version": VERSION,
        "inputs_hash": inputs["inputs_hash"],
        "evidence": "docs/research/IMPROVEMENT_PROTOCOL.md",
        "cases": [
            {k: c[k] for k in ("id", "family", "source_columns", "hash")}
            for c in inputs["cases"]
        ],
        "seeds": [11, 23, 47],
        "evaluations": 10,
        "shots": 8,
        "final_shots": 8,
        "checkpoints": [8, 24, 48, 88],
        "financial_claims_allowed": False,
        "source_cutoff": inputs["source_cutoff"],
        "new_inference_calls": 0,
        "methods": [
            "fixed",
            "rules",
            "scheduled",
            "depth2_pattern",
            "proxy_feedback",
            "uniform_conditioned",
            "allocation_swap",
        ],
    }
    write_json(path / "protocol.json", protocol)
    write_json(
        path / "dataset_manifest.json",
        {
            "source": inputs["source_manifest"],
            "scope": "First126 rows of pinned US corpus, conditioned membership, anonymous private case matrices.",
            "investment_universe_approved": False,
            "raw_or_case_return_matrices_published": False,
        },
    )
    capture_sources(path)
    ablations = []
    for item in inputs["ablations"]:
        spec = decode(item["spec"])
        h = compile_cost(spec, True)
        reference_ir = lower(common_program(spec), spec, h, common_preparation=True)
        reference_resources = verify(reference_ir, spec, h)["resources"]
        for name in ("depth1_edit", "depth1_scheduled_edit"):
            program = deepcopy(item["program"])
            program["depth"] = 1
            if name == "depth1_scheduled_edit":
                program = disjoint_schedule(program, spec)
            ir = lower(program, spec, h, common_preparation=True)
            verification = verify(ir, spec, h)
            if not verification["valid"]:
                raise ValueError(verification)
            runs = [
                sampled_allocation_search(spec, ir, h, seed=seed) for seed in (11, 23)
            ]
            ablations.append(
                {
                    "case_id": item["case_id"],
                    "method": name,
                    "attribution": "deterministic_classical_edit_of_recorded_LLM_program",
                    "program": program,
                    "verification": verification,
                    "runs": runs,
                    "original_resources": item["original"]["verification"]["resources"],
                    "original_objectives": [
                        r["allocation"]["objective"] for r in item["original"]["runs"]
                    ],
                    "original_eligibility": resource_eligibility(
                        item["original"]["verification"]["resources"],
                        reference_resources,
                    ),
                    "edited_eligibility": resource_eligibility(
                        verification["resources"], reference_resources
                    ),
                }
            )
            export(
                ir,
                h,
                runs[0]["angles"],
                verification,
                path / "circuits/ablation" / item["case_id"] / name,
            )
    write_json(path / "ablation.json", ablations)
    records, rows, references = [], [], {}
    for case in inputs["cases"]:
        spec = decode(case["spec"])
        if spec.fingerprint() != case["hash"]:
            raise ValueError("Financial case fingerprint mismatch.")
        h = compile_cost(spec, True)
        matrix, vector, offset = spec.quadratic()
        write_json(
            path / "cases" / case["id"] / "sufficient_statistics.json",
            {
                "matrix": matrix.tolist(),
                "linear": vector.tolist(),
                "offset": offset,
                "financial_spec_without_returns": {
                    k: v
                    for k, v in case["spec"].items()
                    if k not in ("returns", "benchmark")
                },
                "source_spec_hash": case["hash"],
            },
        )
        reference = joint_reference(spec, time_limit=5)
        references[case["id"]] = reference
        write_json(path / "references.json", references)
        for method in protocol["methods"]:
            ir, verification, overhead = None, None, 0.0
            if method not in ("uniform_conditioned", "allocation_swap"):
                begin = perf_counter()
                program = common_program(
                    spec, "rules" if method == "rules" else "fixed"
                )
                if method == "scheduled":
                    program = disjoint_schedule(program, spec)
                if method == "depth2_pattern":
                    program["depth"] = 2
                ir = lower(program, spec, h, common_preparation=True)
                verification = verify(ir, spec, h)
                overhead = perf_counter() - begin
                if not verification["valid"]:
                    raise ValueError(verification)
            for seed in protocol["seeds"]:
                result = search(
                    spec,
                    ir,
                    h,
                    seed=seed,
                    method="uniform"
                    if method == "uniform_conditioned"
                    else "swap"
                    if method == "allocation_swap"
                    else "circuit",
                    target="proxy" if method == "proxy_feedback" else "allocation",
                )
                record = {
                    "case_id": case["id"],
                    "method": method,
                    "seed": seed,
                    "verification": verification,
                    "compile_verify_seconds_once_per_method": overhead
                    if seed == 11
                    else 0,
                    "result": result,
                }
                records.append(record)
                for prefix in prefix_rows(result):
                    rows.append(
                        {
                            "case_id": case["id"],
                            "family": case["family"],
                            "n": spec.n,
                            "method": method,
                            "seed": seed,
                            **prefix,
                            "signed_difference_to_scip_incumbent": prefix[
                                "best_objective"
                            ]
                            - reference["allocation"]["objective"]
                            if prefix["best_objective"] is not None
                            and reference.get("feasible")
                            else None,
                            "reference_status": reference["status"],
                        }
                    )
                if ir is not None and seed == 11:
                    export(
                        ir,
                        h,
                        result["angles"],
                        verification,
                        path / "circuits" / case["id"] / method,
                    )
                write_json(path / "records.json", records)
                print(
                    case["id"],
                    method,
                    seed,
                    result["allocation"]["objective"]
                    if result["allocation"]
                    else "unknown",
                    flush=True,
                )
        with (path / "metrics.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "status": "completed_development_controls",
        "inputs_hash": inputs["inputs_hash"],
        "cases": len(inputs["cases"]),
        "runs": len(records),
        "ablation_variants": len(ablations),
        "new_inference_calls": 0,
        "investment_universe_approved": False,
    }
    write_json(path / "completion.json", summary)
    return summary
