"""Bounded cloud integration: real LLM designs, sampled F feedback, honest gates."""

from dataclasses import replace
from itertools import combinations
from pathlib import Path
from time import perf_counter
import json
import numpy as np
from scipy.optimize import minimize

from agqo.synthesis.profile import digest
from .data import write_json
from .design import COMMON_VERSION, baseline, lower, request
from .finance import FinancialSpec, allocate, diagnose, Account, joint_reference
from .quantum import compile_cost, execute, verify, export
from .workflow import artifact_bundle, swap_allocate

RUN_VERSION = "modal-e2e-v1"


def contexts():
    from .runner import cases

    base = dict(cases())
    spec = base["development_n6"]
    return [
        ("n6_base", spec),
        ("n6_exit", replace(spec, exclude=(spec.tickers[0],))),
        ("n8_base", base["development_n8"]),
    ]


def common_program(spec, mode="fixed"):
    value = baseline(spec, mode)
    value.update(version=COMMON_VERSION, preparation="compiler_counter_dicke_v1")
    return value


def objective_bound(spec):
    """Conservative bound on F for feasible long-only, fully invested weights."""
    matrix, vector, offset = spec.quadratic()
    return float(
        abs(matrix).max()
        + abs(vector).max()
        + abs(offset)
        + 2 * spec.cost_weight * spec.cost_rate
        + 1e-8
    )


def sampled_allocation_search(
    spec,
    ir,
    h,
    *,
    seed=11,
    evaluations=6,
    shots=32,
    final_shots=64,
    uniform=False,
    uniform_conditioned=False,
):
    """Every observed support counts; no financial optimum is used in fitting."""
    if any(type(v) is not int or v < 1 for v in (evaluations, shots, final_shots)):
        raise ValueError("Positive integer budgets required.")
    start = perf_counter()
    rng = np.random.default_rng(seed)
    cache, history, observed = {}, [], []
    hits = 0
    allocator_calls = 0
    bound = objective_bound(spec)
    if not uniform:
        from .conditioning import coordinates

        scales, conditioning = coordinates(ir, h, "paper_rms_v1")
        initial = rng.uniform(-np.pi, np.pi, len(ir["parameters"]))
        best, best_loss = initial.copy(), float("inf")

    def score_samples(samples):
        nonlocal hits, allocator_calls
        values = []
        feasible_count = 0
        for index in samples:
            index = int(index)
            observed.append(index)
            if index not in cache:
                bits = [(index >> q) & 1 for q in range(spec.n)]
                allocator_calls += int(spec.feasible(bits))
                cache[index] = allocate(spec, bits)
            else:
                hits += 1
            result = cache[index]
            if result.get("feasible"):
                feasible_count += 1
                if not -1e-7 <= result["objective"] <= bound * (1 + 1e-7):
                    raise ValueError("F is outside the frozen physical loss bound.")
                values.append(result["objective"] / bound)
            else:
                values.append(2.0)
        history.append(
            {
                "samples": list(map(int, samples)),
                "mean_normalized_allocated_loss": float(np.mean(values)),
                "allocation_feasible_samples": feasible_count,
            }
        )
        return float(np.mean(values))

    def samples_at(angles, count):
        probabilities = abs(execute(ir, h, np.asarray(angles) * scales)) ** 2
        probabilities /= probabilities.sum()
        # Statevector indices include slack; project only the measured asset bits.
        return rng.choice(len(probabilities), count, p=probabilities) & (
            (1 << spec.n) - 1
        )

    if uniform:
        if uniform_conditioned:
            from .budget_search import conditioned_draws

            samples = conditioned_draws(spec, rng, evaluations * shots + final_shots)
        else:
            all_k = np.array(
                [
                    sum(1 << q for q in chosen)
                    for chosen in combinations(range(spec.n), spec.k)
                ]
            )
            samples = rng.choice(all_k, evaluations * shots + final_shots)
        score_samples(samples)
        physical_angles = None
    else:
        calls = 0

        class Exhausted(Exception):
            pass

        def loss(angles):
            nonlocal calls, best, best_loss
            if calls >= evaluations:
                raise Exhausted
            calls += 1
            value = score_samples(samples_at(angles, shots))
            if value < best_loss:
                best, best_loss = np.asarray(angles).copy(), value
            return value

        try:
            minimize(
                loss,
                initial,
                method="COBYLA",
                options={"maxiter": max(evaluations, len(initial) + 2), "rhobeg": 0.5},
            )
        except Exhausted:
            pass
        # Some optimizers terminate early; spend the frozen residual budget at best.
        while calls < evaluations:
            loss(best)
        score_samples(samples_at(best, final_shots))
        physical_angles = (best * scales).tolist()
    feasible = [r for r in cache.values() if r.get("feasible")]
    selected = (
        min(feasible, key=lambda r: (r["objective"], r["support"]))
        if feasible
        else None
    )
    return {
        "status": "feasible" if selected else "unknown",
        "allocation": selected,
        "angles": physical_angles,
        "history": history,
        "allocation_results": {str(k): v for k, v in cache.items()},
        "allocation_queries": allocator_calls,
        "unique_support_checks": len(cache),
        "cache_hits": hits,
        "allocation_failures": sum(not r.get("feasible") for r in cache.values()),
        "allocation_feasible_sample_fraction": sum(
            cache[i].get("feasible", False) for i in observed
        )
        / len(observed),
        "total_shots": len(observed),
        "optimizer_evaluations": 0 if uniform else evaluations,
        "pooling": "all_optimizer_and_final_samples_in_first_observed_order",
        "loss": "F_over_physical_bound_if_feasible_else_2",
        "physical_objective_bound": bound,
        "conditioning": None if uniform else conditioning,
        "execution": "modal_cpu_ideal_simulation"
        if not uniform
        else "classical_uniform_cardinality",
        "elapsed_seconds": perf_counter() - start,
        "fallback_used": False,
    }


def prepare(directory, data_directory, cost_aware=False):
    from .pipeline import execute_pipeline
    from .sources import capture_sources

    path = Path(directory)
    context = contexts()
    requests = [
        request(spec, compile_cost(spec, True), seed=100, common_preparation=True)
        for _, spec in context
    ]
    if cost_aware:
        from .budget_search import cost_aware_request

        requests = []
        for _, spec in context:
            h = compile_cost(spec, True)
            ir = lower(common_program(spec), spec, h, common_preparation=True)
            report = verify(ir, spec, h)
            if not report["valid"]:
                raise ValueError("Reference circuit did not verify.")
            budget = {
                k: report["resources"][k]
                for k in ("qubits", "transpiled_cx", "transpiled_depth")
            }
            requests.append(cost_aware_request(spec, h, budget))
    protocol = {
        "version": "modal-e2e-cost-aware-v1" if cost_aware else RUN_VERSION,
        "purpose": "live_cloud_integration_not_qualification",
        "evidence": "docs/research/MODAL_E2E_PROTOCOL.md",
        "cases": [{"id": name, "hash": spec.fingerprint()} for name, spec in context],
        "request_hashes": [r["request_hash"] for r in requests],
        "seeds": [11, 23],
        "evaluations": 6,
        "shots": 32,
        "final_shots": 64,
        "source_hash": digest(
            {p.name: p.read_text() for p in sorted(Path(__file__).parent.glob("*.py"))}
        ),
        "model_key": "coder30",
        "common_preparation": "compiler_counter_dicke_v1",
        "cost_aware": cost_aware,
        "financial_claims_allowed": False,
        "raw_market_inputs_mounted": False,
    }
    existing = path / "prepared.json"
    if existing.exists():
        saved = json.loads(existing.read_text())
        if saved["protocol"] != protocol:
            raise ValueError("Prepared run changed; use a new run ID.")
        return saved
    write_json(path / "protocol.json", protocol)
    capture_sources(path)
    stage = execute_pipeline(
        path / "software_pipeline",
        mode="offline",
        data_directory=data_directory,
        periods=2,
    )
    for name, spec in context:
        write_json(path / "inputs" / name / "financial_spec.json", spec.to_dict())
        write_json(
            path / "inputs" / name / "hamiltonian.json", compile_cost(spec, True)
        )
    result = {
        "protocol": protocol,
        "requests": requests,
        "software_pipeline": stage,
        "prepared_hash": digest({"protocol": protocol, "requests": requests}),
    }
    write_json(existing, result)
    return result


def finish(directory, answers, prepared_hash, cost_context=None):
    path = Path(directory)
    prepared = json.loads((path / "prepared.json").read_text())
    source_hash = digest(
        {p.name: p.read_text() for p in sorted(Path(__file__).parent.glob("*.py"))}
    )
    if source_hash != prepared["protocol"]["source_hash"]:
        raise ValueError("Execution source differs from the prepared request snapshot.")
    if prepared["prepared_hash"] != prepared_hash:
        raise ValueError("Remote preparation identity mismatch.")
    if (
        len(answers) != len(prepared["requests"])
        or [a.get("request_hash") for a in answers]
        != prepared["protocol"]["request_hashes"]
    ):
        raise ValueError("Inference responses do not match prepared requests.")
    output = path / "evaluation"
    if (output / "completion.json").exists():
        saved = json.loads((output / "completion.json").read_text())
        if saved["answers_hash"] != digest(answers):
            raise ValueError("Completed response batch changed.")
        return saved
    saved_answers = path / "inference_answers.json"
    if saved_answers.exists() and json.loads(saved_answers.read_text()) != answers:
        raise ValueError("Partial run response batch changed.")
    write_json(saved_answers, answers)
    decisions, metrics, records, references = [], [], [], {}
    for case, item, answer in zip(
        prepared["protocol"]["cases"], prepared["requests"], answers, strict=True
    ):
        name = case["id"]
        raw = json.loads((path / "inputs" / name / "financial_spec.json").read_text())
        spec = FinancialSpec(
            **{k: v for k, v in raw.items() if k in FinancialSpec.__dataclass_fields__}
        )
        h = compile_cost(spec, True)
        if spec.fingerprint() != case["hash"]:
            raise ValueError("Financial specification changed after inference.")
        exact = []
        for chosen in combinations(range(spec.n), spec.k):
            bits = [int(q in chosen) for q in range(spec.n)]
            result = allocate(spec, bits)
            exact.append(result)
        valid = [r for r in exact if r.get("feasible")]
        best = min(valid, key=lambda r: r["objective"]) if valid else None
        references[name] = {
            "exact_support_allocation": best,
            "exhaustive_queries": len(exact),
            "joint_scip": joint_reference(spec, time_limit=15),
            "allocation_swap": swap_allocate(spec),
            "infeasible_control": diagnose(
                replace(spec, include=(spec.tickers[0],), exclude=(spec.tickers[0],))
            ),
        }
        for method in ("fixed", "rules", "uniform", "coder30"):
            record = {"case_id": name, "method": method, "runs": []}
            ir = None
            if method != "uniform":
                try:
                    if method == "coder30":
                        if answer.get("status") != "ok":
                            raise ValueError(answer.get("reason", answer.get("status")))
                        program = answer["response"]
                        if prepared["protocol"].get("cost_aware"):
                            from .budget_search import admit_cost_aware_program

                            admitted = admit_cost_aware_program(
                                program,
                                spec,
                                h,
                                item["payload"]["compiled_resource_budget"],
                            )
                            if admitted["status"] != "accepted":
                                raise ValueError(str(admitted))
                    else:
                        program = common_program(spec, method)
                    ir = lower(program, spec, h, common_preparation=True)
                    checked = verify(ir, spec, h)
                    record.update(program=program, verification=checked)
                    if not checked["valid"]:
                        raise ValueError(str(checked.get("errors")))
                except Exception as exc:
                    record.update(
                        status="rejected", error=f"{type(exc).__name__}: {exc}"
                    )
                    records.append(record)
                    metrics.append(
                        {"case_id": name, "method": method, "status": "rejected"}
                    )
                    continue
            for seed in prepared["protocol"]["seeds"]:
                run = sampled_allocation_search(
                    spec,
                    ir,
                    h,
                    seed=seed,
                    uniform=method == "uniform",
                    uniform_conditioned=prepared["protocol"].get("cost_aware", False),
                )
                record["runs"].append(run)
                allocation = run["allocation"]
                decision = {
                    "case_id": name,
                    "method": method,
                    "seed": seed,
                    "status": run["status"],
                    "allocation": allocation,
                    "problem_hash": spec.fingerprint(),
                    "hamiltonian_hash": h["hamiltonian_hash"],
                    "execution": "synthetic_common_state_decision_not_market_or_trajectory",
                }
                if allocation:
                    account = Account(100000 * spec.previous_weights)
                    decision["trade"] = account.rebalance(
                        allocation["weights"], spec.cost_rate
                    )
                decisions.append(decision)
                metrics.append(
                    {
                        "case_id": name,
                        "method": method,
                        "seed": seed,
                        "status": run["status"],
                        "allocated_objective": allocation["objective"]
                        if allocation
                        else None,
                        "regret_to_exhaustive": allocation["objective"]
                        - best["objective"]
                        if allocation and best
                        else None,
                        "allocation_queries": run["allocation_queries"],
                        "total_shots": run["total_shots"],
                        "feasible_sample_fraction": run[
                            "allocation_feasible_sample_fraction"
                        ],
                        "elapsed_seconds": run["elapsed_seconds"],
                    }
                )
            if ir is not None:
                export(
                    ir,
                    h,
                    record["runs"][0]["angles"],
                    record["verification"],
                    output / "circuits" / name / method,
                )
            record["status"] = "evaluated"
            records.append(record)
        write_json(output / "records.json", records)
        write_json(output / "references.json", references)
    accepted = sum(
        r["method"] == "coder30" and r["status"] == "evaluated" for r in records
    )
    result = artifact_bundle(
        output,
        prepared["protocol"],
        {
            "dataset_kind": "synthetic_integration_cases",
            "financial_evaluation_allowed": False,
        },
        decisions,
        metrics,
        status="completed_with_data_blockers" if accepted else "failed",
        reason=f"Live model designs evaluated: {accepted}/3. Synthetic cloud integration only; historical market admission remains blocked. COST is B; sampled optimizer feedback is allocated F. No model/financial/quantum advantage qualified.",
        cost=cost_context or {"reservation_is_not_invoice": True},
    )
    result.update(
        live_model_circuits_accepted=accepted,
        model_proposals=3,
        decisions=len(decisions),
        answers_hash=digest(answers),
    )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3), layout="constrained")
    for ax, case in zip(axes, prepared["protocol"]["cases"]):
        for position, method in enumerate(("fixed", "rules", "uniform", "coder30")):
            values = [
                r["allocated_objective"] * 1e6
                for r in metrics
                if r["case_id"] == case["id"]
                and r["method"] == method
                and r.get("allocated_objective") is not None
            ]
            if values:
                ax.bar(
                    position,
                    np.mean(values),
                    color=["#47759a", "#519388", "#a18c45", "#8c659d"][position],
                )
                ax.scatter(
                    position + np.linspace(-0.04, 0.04, len(values)),
                    values,
                    color="#24354b",
                    s=18,
                )
            else:
                ax.text(position, 0, "rejected", rotation=90, va="bottom", ha="center")
        ax.set(
            xticks=range(4),
            xticklabels=["Fixed", "Rules", "Uniform", "LLM"],
            title=case["id"],
            ylabel="Allocated training objective ×10⁶",
        )
    fig.suptitle(
        "Modal integration: synthetic cases, two seeds; no financial or model superiority claim"
    )
    fig.savefig(output / "allocated-objective.png", dpi=160)
    plt.close(fig)
    with (output / "RESULTS.md").open("a") as stream:
        stream.write(
            "\n## Connected cloud stages\n\n"
            "Cloud CPU prepared the financial/data profiles, live Modal GPU responses designed exchange gates, and cloud CPU verified, optimized sampled F, allocated supports and accounted trades.\n\n"
            "The software_pipeline directory separately contains continuous synthetic accounts and explicit blocked market artifacts. The allocation-aware decisions here are state-matched cases, not a continuous market backtest.\n\n"
            "![Allocated objective](allocated-objective.png)\n\n"
            "**Figure 1. Allocated training objective.** Source: this run's metrics.csv. Lower is better. Dots are two seeds per synthetic case, not independent market observations. Rejected designs remain in records and do not receive fabricated scores.\n\n"
            "All optimizer and final samples enter the financial candidate pool. COST remains the equal-weight proxy B; F is evaluated classically. Full accounting is in the local orchestration/cost_report.json after download; reservations are not invoices.\n"
        )
    write_json(output / "completion.json", result)
    return result
