"""Frozen development/test protocol, paired solver runs and explicit LLM ablations."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import hashlib
import json
import platform
import numpy as np
import scipy

from .circuits import CATALOG, CircuitSpec, rule_spec, run_qaoa
from .data import make_window
from .llm import QwenClient
from .mandates import MandateSpec, normalize_rules
from .model import heldout_metrics
from .solvers import anneal_solve, exact_solve, hold_result, milp_solve


@dataclass(frozen=True)
class Protocol:
    version: str = "repair-benchmark-v1"
    n: int = 8
    k: int = 4
    train: int = 60
    horizon: int = 20
    development_starts: tuple[int, ...] = (0, 20)
    test_starts: tuple[int, ...] = (100, 120)
    seeds: tuple[int, ...] = (11, 23, 47)
    evaluations: int = 32
    shots: int = 256
    anneal_evaluations: int = 800
    cost_weight: float = 0.01
    cost_bps: float = 25.0
    threshold_tracking_rmse: float = 0.01

    def __post_init__(self):
        if not 3 <= self.n <= 12 or not 1 <= self.k <= self.n or self.evaluations < 8 or self.shots < 1 or not self.seeds:
            raise ValueError("Invalid protocol dimensions or budget.")
        # Held-out outcomes may not overlap development outcomes or one another.
        def intervals(starts):
            return [set(range(s + self.train, s + self.train + self.horizon)) for s in starts]
        dev, test = intervals(self.development_starts), intervals(self.test_starts)
        if any(a & b for a in dev for b in test) or any(a & b for i, a in enumerate(test) for b in test[i + 1:]):
            raise ValueError("Development and test outcomes overlap.")
        if min(self.test_starts, default=0) + self.train <= max((s + self.train + self.horizon - 1 for s in self.development_starts), default=-1):
            raise ValueError("Test must follow development.")


def semantic_key(m):
    return (m.k, tuple(sorted(m.include)), tuple(sorted(m.exclude)), tuple(sorted(m.sector_caps.items())), m.turnover_cap, m.cost_weight, m.status)


def mandate_corpus(tickers, sectors, k=4):
    """Authored labels independent of parser predictions; public text is not a real mandate."""
    a, z = tickers[0], tickers[-1]
    sector = sectors[0]
    examples = [
        ("canonical_en", f"Hold {k} assets; Exclude {a}", {"k": k, "exclude": (a,)}, "ready"),
        ("canonical_vi", f"Giữ {k} mã; Loại mã {a}", {"k": k, "exclude": (a,)}, "ready"),
        ("paraphrase", f"Please select exactly {k} stocks; Exclude {a}", {"k": k, "exclude": (a,)}, "ready"),
        ("include", f"Hold {k} assets; Must hold {z}", {"k": k, "include": (z,)}, "ready"),
        ("sector", f"Hold {k} assets; Sector {sector} at most 25%", {"k": k, "sector_caps": {sector: 0.25}}, "ready"),
        ("turnover", f"Hold {k} assets; Turnover at most 12.5%", {"k": k, "turnover_cap": 0.125}, "ready"),
        ("decimal", f"Hold {k} assets; Cost weight 0.01", {"k": k, "cost_weight": 0.01}, "ready"),
        ("conflict", f"Hold {k} assets; Must hold {a}; Exclude {a}", {"k": k, "include": (a,), "exclude": (a,)}, "conflict"),
        ("missing_k", f"Exclude {a}", {"exclude": (a,)}, "needs_clarification"),
        ("unsupported", f"Hold {k} assets; Avoid risky companies", {"k": k}, "needs_clarification"),
        ("negation", f"Hold {k} assets; Do not exclude {a}", {"k": k}, "needs_clarification"),
        ("inequality", f"Hold at most {k} assets", {}, "needs_clarification"),
    ]
    rows = []
    for name, text, gold, status in examples:
        reference = MandateSpec(text, **gold, status=status, origin="authored_gold")
        rows.append({"id": name, "text": text, "gold": asdict(reference),
                     "label_provenance": "authored_synthetic_mandate_not_real_client_instruction"})
    return rows


def evaluate_language(corpus, tickers, sectors, client):
    output = []
    for case in corpus:
        gold = MandateSpec(**case["gold"])
        for method in ("rules", "qwen"):
            start = perf_counter()
            trace = None
            try:
                if method == "rules":
                    parsed = normalize_rules(case["text"], tickers, sectors)
                else:
                    parsed, trace = client.normalize(case["text"], tickers, sectors)
                predicted = None if parsed is None else parsed.to_dict()
                # For unsafe cases, refusal is the target; extracted partial fields need not match.
                correct = parsed is not None and (semantic_key(parsed) == semantic_key(gold) if gold.status == "ready" else parsed.status == gold.status)
                output.append({"case_id": case["id"], "method": method, "correct": correct if parsed is not None else None if trace["status"] == "not_run" else False,
                               "status": "evaluated" if parsed is not None else trace["status"],
                               "prediction": predicted, "trace": trace, "elapsed_seconds": perf_counter() - start})
            except (ValueError, TypeError) as exc:
                output.append({"case_id": case["id"], "method": method, "status": "invalid", "correct": False, "reason": str(exc)})
    return output


def _scenario_texts(data, protocol, test):
    prefix = f"Hold {protocol.k} assets"
    yield "unchanged_mandate", prefix
    yield "new_exclusion", prefix + f"; Exclude {data.tickers[0]}"
    if test:
        yield "unseen_combination", prefix + f"; Exclude {data.tickers[0]}; Must hold {data.tickers[protocol.n - 1]}; Turnover at most 120%"
        yield "infeasible_turnover", prefix + f"; Exclude {data.tickers[0]}; Turnover at most 1%"
        if data.provenance.get("sector_source") != "unavailable":
            yield "unseen_sector_combination", prefix + f"; Sector {data.sectors[0]} at most 25%; Exclude {data.tickers[0]}"


def _window(data, protocol, start, text):
    return make_window(data, start, protocol.train, protocol.horizon, protocol.n, protocol.k, text,
                       protocol.cost_weight, protocol.cost_bps)


def _attach(record, p, future_r, future_b, reference=None):
    if record.get("bits") is not None:
        w = np.asarray(record["bits"]) / p.k
    elif "weights" in record:
        w = record["weights"]
    else:
        w = None
    if w is not None:
        record.update(heldout_metrics(p, w, future_r, future_b))
    if reference and reference.get("status") == "optimal" and record.get("feasible") and record.get("bits") is not None:
        record["objective_gap_absolute"] = record["objective"] - reference["objective"]
    return record


def _search(p, protocol, seed):
    start = perf_counter()
    # Four final measurements are charged against the same total shot budget as one run.
    per = max(1, (protocol.evaluations + 1) // len(CATALOG) - 1)
    candidates = [run_qaoa(p, s, seed, per, protocol.shots) for s in CATALOG]
    good = [r for r in candidates if r["feasible"]]
    chosen = min(good, key=lambda r: r["objective"]) if good else candidates[0]
    return {**chosen, "method": "classical_circuit_search", "elapsed_seconds": perf_counter() - start,
            "total_shots": sum(r["total_shots"] for r in candidates),
            "evaluations": sum(r["evaluations"] for r in candidates),
            "search_candidates": [{k: r.get(k) for k in ("circuit_spec", "objective", "feasible", "total_shots")} for r in candidates]}


def run_benchmark(data, directory, protocol=Protocol(), client=None, progress=None):
    client = client or QwenClient()
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    corpus = mandate_corpus(data.tickers[:protocol.n], tuple(sorted(set(data.sectors[:protocol.n]))), protocol.k)
    planned = []
    for split, starts in (("development", protocol.development_starts), ("test", protocol.test_starts)):
        for start in starts:
            for family, text in _scenario_texts(data, protocol, split == "test"):
                p, _, _ = _window(data, protocol, start, text)
                planned.append({"split": split, "start": start, "family": family, "text": text, "problem_hash": p.fingerprint()})
    source_hash = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))).hexdigest()
    frozen = {"protocol": asdict(protocol), "cases": planned, "data_provenance": data.provenance,
              "llm_mode": client.mode, "source_sha256": source_hash,
              "primary_metrics": ["heldout_tracking_rmse", "transaction_cost", "two_way_turnover", "feasible"],
              "quantum_budget": "(evaluations+1)*shots per seed, including final measurements; classical search charged for every candidate",
              "cost_weight_policy": "Ex-ante fixed protocol default, no test tuning; cost frontier is descriptive sensitivity only.",
              "test_isolation": "chronological held-out outcomes plus unseen mandate combinations; historical benchmark not a prospective live holdout"}
    protocol_text = json.dumps(frozen, ensure_ascii=False, sort_keys=True, indent=2)
    protocol_hash = hashlib.sha256(protocol_text.encode()).hexdigest()
    # Persist experiment definition before looking at any test result.
    (directory / "protocol.json").write_text(protocol_text, encoding="utf-8")
    (directory / "mandates_gold.json").write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    development, ratings = [], []
    for spec in CATALOG:
        scores = []
        for case in [c for c in planned if c["split"] == "development"]:
            p, _, _ = _window(data, protocol, case["start"], case["text"])
            reference = exact_solve(p)
            for seed in protocol.seeds:
                record = run_qaoa(p, spec, seed, protocol.evaluations, protocol.shots)
                scores.append(1.0 if not record["feasible"] else max(0.0, record["objective"] - reference["objective"]))
                development.append({"case": case, "result": record})
        ratings.append((float(np.mean(scores)), spec))
        if progress:
            progress("Development " + str(spec.to_dict()))
    fixed = min(ratings, key=lambda pair: pair[0])[1]
    records = []
    trace_log = []
    for case in [c for c in planned if c["split"] == "test"]:
        p, future_r, future_b = _window(data, protocol, case["start"], case["text"])
        ref = exact_solve(p)
        base = [ref, milp_solve(p), hold_result(p)]
        incumbent = base[-1]
        threshold = dict(incumbent if incumbent["feasible"] and incumbent["tracking_rmse"] <= protocol.threshold_tracking_rmse else ref)
        threshold.update(method="threshold_rebalance", threshold_tracking_rmse=protocol.threshold_tracking_rmse,
                         policy="Keep compliant incumbent below fixed training-window RMSE threshold; otherwise solve original repair problem.")
        base.append(threshold)
        # Stateless fixed-time target reconstruction is a separate business comparator,
        # checked against the ORIGINAL mandate, not relabeled feasible after relaxation.
        rebuild_p = replace(p, mandate=replace(p.mandate, turnover_cap=None, cost_weight=None), cost_weight=0.0)
        rebuilt = exact_solve(rebuild_p)
        if rebuilt["bits"] is not None:
            from .solvers import result
            base.append(result(p, "periodic_rebuild", rebuilt["bits"], "evaluated", perf_counter(),
                               reconstruction_seconds=rebuilt["elapsed_seconds"]))
            base[-1]["elapsed_seconds"] += rebuilt["elapsed_seconds"]
        else:
            base.append({"method": "periodic_rebuild", "status": rebuilt["status"], "feasible": False,
                         "problem_hash": p.fingerprint(), "elapsed_seconds": rebuilt["elapsed_seconds"]})
        for record in base:
            records.append({"case": case, "result": _attach(record, p, future_r, future_b, ref)})
        spec, circuit_trace = client.propose(p)
        parsed, mandate_trace = client.normalize(case["text"], p.tickers, tuple(sorted(set(p.sectors))))
        full_spec, full_trace = (None, {"status": "not_run"})
        if parsed is not None and parsed.status == "ready":
            full_spec, full_trace = client.propose(replace(p, mandate=parsed))
        trace_log.append({"case": case, "circuit": circuit_trace, "mandate": mandate_trace, "full_circuit": full_trace})
        for seed in protocol.seeds:
            runs = [anneal_solve(p, seed, protocol.anneal_evaluations)]
            for name, candidate in (("qaoa_fixed", fixed), ("qaoa_rule", rule_spec(p)),
                                    ("qaoa_random", CATALOG[int(np.random.default_rng(seed).integers(len(CATALOG)))]),
                                    ("qaoa_warm_start", CircuitSpec("XY", "ring", 1, "previous")),
                                    ("qaoa_random_init", CircuitSpec("XY", "ring", 1, "random"))):
                r = run_qaoa(p, candidate, seed, protocol.evaluations, protocol.shots)
                r["method"] = name; runs.append(r)
            runs.append(_search(p, protocol, seed))
            if spec is not None:
                r = run_qaoa(p, spec, seed, protocol.evaluations, protocol.shots)
                r.update(method="qwen_circuit", llm_trace=circuit_trace)
                r["elapsed_seconds"] += circuit_trace.get("elapsed_seconds", 0)
                runs.append(r)
            else:
                runs.append({"method": "qwen_circuit", "seed": seed, "status": circuit_trace["status"], "feasible": False, "llm_trace": circuit_trace, "problem_hash": p.fingerprint(), "elapsed_seconds": circuit_trace.get("elapsed_seconds", 0)})
            if seed == protocol.seeds[0]:
                for name, proposed_spec in (("qwen_mandate_classical", None), ("qwen_full_pipeline", full_spec)):
                    if parsed is None or parsed.status != "ready" or (name == "qwen_full_pipeline" and proposed_spec is None):
                        failed_status = mandate_trace["status"] if parsed is None else parsed.status if parsed.status != "ready" else full_trace["status"]
                        runs.append({"method": name, "status": failed_status,
                                     "feasible": False, "llm_trace": mandate_trace, "full_circuit_trace": full_trace,
                                     "problem_hash": p.fingerprint(), "elapsed_seconds": mandate_trace.get("elapsed_seconds", 0) + (full_trace.get("elapsed_seconds", 0) if name == "qwen_full_pipeline" else 0)})
                        continue
                    pp = replace(p, mandate=parsed)
                    r = milp_solve(pp) if proposed_spec is None else run_qaoa(pp, proposed_spec, seed, protocol.evaluations, protocol.shots)
                    r["method"] = name
                    r["normalized_problem_hash"] = pp.fingerprint()
                    r["semantic_match_gold"] = semantic_key(parsed) == semantic_key(p.mandate)
                    r["llm_trace"] = mandate_trace
                    # Evaluate original requirements, even if LLM silently dropped a constraint.
                    if r.get("bits") is not None:
                        original = np.asarray(r["bits"])
                        r.update(feasible=p.feasible(original), violations=p.violations(original), **p.metrics_weights(original / p.k))
                    r["problem_hash"] = p.fingerprint()
                    r["elapsed_seconds"] += mandate_trace.get("elapsed_seconds", 0) + (full_trace.get("elapsed_seconds", 0) if proposed_spec else 0)
                    runs.append(r)
            for record in runs:
                records.append({"case": case, "result": _attach(record, p, future_r, future_b, ref)})
        if progress:
            progress("Test " + str(case["start"]) + " " + case["family"])
    language = evaluate_language(corpus, data.tickers[:protocol.n], tuple(sorted(set(data.sectors[:protocol.n]))), client)
    screening = []
    if len(data.tickers) > protocol.n:
        for case in [c for c in planned if c["split"] == "test"]:
            restricted, _, _ = _window(data, protocol, case["start"], case["text"])
            full = replace(restricted, tickers=data.tickers, sectors=data.sectors,
                           returns=data.returns[case["start"]:case["start"] + protocol.train],
                           previous_weights=np.pad(restricted.previous_weights, (0, len(data.tickers) - protocol.n)),
                           cost_rates=np.full(len(data.tickers), protocol.cost_bps / 10000))
            full_result, restricted_result = milp_solve(full), exact_solve(restricted)
            gap = None
            if full_result["status"] == restricted_result["status"] == "optimal":
                gap = restricted_result["objective"] - full_result["objective"]
            screening.append({"case": case, "full_universe_n": full.n, "restricted_n": restricted.n,
                              "full_reference": full_result, "restricted_reference": restricted_result,
                              "objective_loss_from_fixed_subset": gap,
                              "note": "Separate universe audit, not a fair head-to-head QAOA comparison."})
    output = {"version": protocol.version, "protocol_sha256": protocol_hash, "protocol": frozen,
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "platform": platform.platform()},
              "selected_fixed_spec": fixed.to_dict(), "development": development, "records": records,
              "language": language, "llm_traces": trace_log, "screening_audit": screening,
              "claims": {"quantum_advantage": "not_established", "llm_value": "requires_paired_evidence",
                         "business_value": "benchmark_only_not_live_fund_savings", "research_gap": "candidate_not_uniqueness_proof"}}
    (directory / "benchmark.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return output
