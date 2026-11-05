"""Explicit numerical evidence for circuit decisions; no stock preselection.

Exchange sensitivity describes the equal-weight selection proxy B, not the
continuous allocated objective F or an ADAPT quantum energy gradient.
"""

from copy import deepcopy
from time import perf_counter
import numpy as np
from jsonschema import Draft202012Validator, ValidationError

from agqo.synthesis.profile import correlation, digest
from agqo.synthesis.typed import domain
from .budget_search import cost_aware_request, admit_cost_aware_program
from .design import COMMON_VERSION

VERSION = "data-guided-common-counter-v1"

PROCEDURE = """
Follow the supplied design procedure, not a fixed path template:
1. Read fixed bits, remaining cardinality and allowed parents. Never remove assets.
2. Compare candidate exchanges using measured RMS proxy-energy difference,
   signed mean difference, correlation and its half-window change. Large RMS is
   sensitivity, not evidence of a good direction or a better portfolio. Low-RMS
   near-degenerate transitions can matter too. Do not maximize correlation or RMS
   mechanically. Cost and benchmark exposure already enter the numerical proxy.
3. Choose a connected parent tree. Cite the actual EDGE_i_j for EVERY parent in
   evidence.parent_edges. Give a testable tradeoff in rationale. Sector/weight/
   turnover inequalities are not guaranteed by this tree or these edge features.
4. Order exchanges considering disjoint pairs and shared-qubit conflicts. Changing
   overlapping-edge order changes the unitary. Justify schedule in evidence.
5. Choose one or two beta groups considering channel heterogeneity AND the angle
   evaluation budget; explain what observation would disprove the benefit.
6. Use compiler-owned preparation, one cost/mixer layer and immutable cost. The
   compiler lowers each exchange to adjacent RXX(2*beta), RYY(2*beta). Return the
   new response version, all evidence fields and only schema-conforming JSON.
These statistics concern B under a neutral cardinality/fixed-bit reference, not
the allocated F landscape, an optimizer result, a quantum gradient, or a promise
of improvement. Independent measured F and compiled resources decide admission
and usefulness; citations alone do not prove either.
"""


def exchange_features(spec):
    """Exact swap-difference moments, in polynomial time without support search."""
    started = perf_counter()
    d = domain(spec)
    free, fixed = d["free_qubits"], d["frozen_one"]
    remaining = spec.k - len(fixed)
    q = spec.objective_qubo()
    interactions = q.quadratic + q.quadratic.T
    c, _, _ = correlation(spec.returns)
    recent, _, _ = correlation(spec.returns[-max(2, len(spec.returns) // 2) :])
    edges = []
    for child in range(1, len(free)):
        j = free[child]
        for parent in range(child):
            i = free[parent]
            others = [t for t in free if t not in (i, j)]
            a = interactions[j, others] - interactions[i, others]
            size, chosen = len(others), remaining - 1
            mean = float(q.linear[j] - q.linear[i])
            mean += float(np.sum(interactions[j, fixed] - interactions[i, fixed]))
            if size:
                mean += chosen / size * float(a.sum())
            variance = (
                chosen
                * (size - chosen)
                / (size * (size - 1))
                * float(np.sum((a - a.mean()) ** 2))
                if size > 1
                else 0.0
            )
            edges.append(
                {
                    "id": f"EDGE_{i}_{j}",
                    "parent_key": f"p{child}",
                    "parent_index": parent,
                    "qubits": [i, j],
                    "mean_delta_B_i_to_j": mean,
                    "variance_delta_B": variance,
                    "rms_delta_B": float(np.sqrt(mean * mean + variance)),
                    "correlation": float(c[i, j]),
                    "correlation_half_window_abs_change": float(
                        abs(recent[i, j] - c[i, j])
                    ),
                    "same_policy_bucket": spec.sectors[i] == spec.sectors[j],
                }
            )
    result = {
        "version": "exchange-evidence-v1",
        "problem_hash": spec.fingerprint(),
        "cutoff": spec.cutoff,
        "free_qubits": free,
        "frozen_one": fixed,
        "frozen_zero": d["frozen_zero"],
        "remaining_cardinality": remaining,
        "reference": "uniform fixed-bit/cardinality states conditioned on x_i=1,x_j=0",
        "not_conditioned_on": "other support inequalities or continuous allocation feasibility",
        "objective": "unscaled equal-weight proxy B including its cost terms",
        "units": "same as B; variance has squared units",
        "formula_reference": "docs/research/DATA_GUIDANCE_PROTOCOL.md",
        "allocation_queries": 0,
        "support_enumerations": 0,
        "edges": edges,
    }
    result["feature_hash"] = digest(result)
    result["construction_seconds"] = perf_counter() - started
    return result


def _table(features):
    scale = float(np.median([e["rms_delta_B"] for e in features["edges"]]))
    if scale == 0:
        scale = max(e["rms_delta_B"] for e in features["edges"]) or 1.0
    rows = {}
    for edge in features["edges"]:
        rows.setdefault(edge["parent_key"], []).append(
            [
                float(format(v, ".6g"))
                for v in (
                    edge["mean_delta_B_i_to_j"] / scale,
                    edge["rms_delta_B"] / scale,
                    edge["correlation"],
                    edge["correlation_half_window_abs_change"],
                )
            ]
        )
    return {
        "feature_hash": features["feature_hash"],
        "problem_hash": features["problem_hash"],
        "cutoff": features["cutoff"],
        "free_qubits": features["free_qubits"],
        "remaining_cardinality": features["remaining_cardinality"],
        "columns": [
            "mean_delta_B/scale",
            "rms_delta_B/scale",
            "correlation",
            "abs_half_window_change",
        ],
        "scale": scale,
        "rounding": "6 significant digits, descriptors only; cost coefficients are unchanged",
        "row_rule": "rows[pChild][parent] describes EDGE_free[parent]_free[Child]; every allowed pair is present",
        "reference": features["reference"],
        "not_conditioned_on": features["not_conditioned_on"],
        "rows": rows,
    }


def guided_request(spec, h, resource_budget, seed=100):
    """Opt-in, bounded prompt with per-gate evidence; legacy paths unchanged."""
    if h.get("problem_hash") != spec.fingerprint():
        raise ValueError("Hamiltonian and financial instance disagree.")
    features = exchange_features(spec)
    if len(features["free_qubits"]) > 20:
        raise ValueError(
            "Data-guided development contract supports at most 20 free assets."
        )
    value = cost_aware_request(spec, h, resource_budget, seed)
    contract = value["schema"]
    contract["properties"]["version"] = {"const": VERSION}
    links = {}
    for edge in features["edges"]:
        links.setdefault(edge["parent_key"], {"enum": []})["enum"].append(edge["id"])
    explanation = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "feature_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {
                    "enum": ["EXCHANGE_TABLE", "MANDATE_DOMAIN", "RESOURCE_BUDGET"]
                },
            },
            "hypothesis": {"type": "string", "minLength": 1, "maxLength": 240},
            "falsifier": {"type": "string", "minLength": 1, "maxLength": 240},
        },
        "required": ["feature_ids", "hypothesis", "falsifier"],
    }
    contract["properties"]["evidence"] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "parent_edges": {
                "type": "object",
                "additionalProperties": False,
                "properties": links,
                "required": list(links),
            },
            "schedule": deepcopy(explanation),
            "sharing": deepcopy(explanation),
        },
        "required": ["parent_edges", "schedule", "sharing"],
    }
    contract["required"].append("evidence")
    contract["properties"]["rationale"]["minItems"] = 1
    payload = value["payload"]
    # Avoid duplicate dense matrices in the prompt; no change to the compiler.
    profile = payload["data_profile"]
    payload["data_profile"] = {
        k: profile[k]
        for k in (
            "version",
            "problem_hash",
            "cutoff",
            "numerical_rank",
            "condition_number",
            "previous_weights",
            "current_violations",
            "zero_variance_assets",
        )
        if k in profile
    }
    payload["exchange_table"] = _table(features)
    payload["prompt_version"] = VERSION
    payload["schema_contract"] = (
        "The full response schema is supplied through structured decoding. "
        "Return per-parent evidence links plus schedule/sharing hypotheses and falsifiers."
    )
    payload["evidence_scope"] = (
        "Traceability only; neither citation validity nor RMS proves better allocated F."
    )
    value["system"] += PROCEDURE
    value["max_tokens"] = 4096
    value.pop("request_hash", None)
    value["request_hash"] = digest(value)
    return value


def check_evidence(program, request):
    """Check actual gate-to-feature links, not the truth of free-text reasoning."""
    Draft202012Validator(request["schema"]).validate(program)
    free = request["payload"]["exchange_table"]["free_qubits"]
    checked = []
    for child in range(1, len(free)):
        key = f"p{child}"
        expected = f"EDGE_{free[program['parents'][key]]}_{free[child]}"
        if program["evidence"]["parent_edges"][key] != expected:
            raise ValueError(
                f"Evidence for {key} does not describe its selected exchange {expected}."
            )
        checked.append(expected)
    return {
        "valid_links": True,
        "checked_edges": checked,
        "feature_hash": request["payload"]["exchange_table"]["feature_hash"],
        "scope": "Schema and exact gate-to-feature linkage; free-text explanations are unproven.",
    }


def admit_guided_program(program, spec, h, resource_budget):
    """Evidence admission precedes independent quantum and resource checks."""
    request = guided_request(spec, h, resource_budget)
    try:
        evidence = check_evidence(program, request)
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        return {
            "status": "rejected_evidence",
            "reason": str(exc),
            "fallback_used": False,
        }
    compiled = deepcopy(program)
    compiled.pop("evidence")
    compiled["version"] = COMMON_VERSION
    result = admit_cost_aware_program(compiled, spec, h, resource_budget)
    result["evidence_check"] = evidence
    result["source_response_hash"] = digest(program)
    return result
