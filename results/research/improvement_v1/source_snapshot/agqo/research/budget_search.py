"""Budget curves with identical hard-bit constraints and explicit circuit costs."""

from copy import deepcopy
from time import perf_counter
import numpy as np
from scipy.optimize import minimize

from .finance import allocate
from .cloud_pipeline import objective_bound
from .conditioning import coordinates
from .symmetry import ConservedBasis
from .quantum import cost_values
from agqo.synthesis.typed import domain


def disjoint_schedule(program, spec):
    """A new gate order, not a unitary-equivalent optimization."""
    value = deepcopy(program)
    free = domain(spec)["free_qubits"]
    colors, used = [], {}
    for child in range(1, len(free)):
        a, b = free[value["parents"][f"p{child}"]], free[child]
        color = 0
        while color in used.get(a, set()) or color in used.get(b, set()):
            color += 1
        colors.append(color)
        used.setdefault(a, set()).add(color)
        used.setdefault(b, set()).add(color)
    value["schedule"] = sorted(range(len(colors)), key=lambda i: (colors[i], i))
    return value


def resource_eligibility(candidate, reference):
    """Reject resource overruns explicitly; never disguise a fallback as LLM."""
    keys = ("qubits", "transpiled_cx", "transpiled_depth")
    if any(k not in candidate or k not in reference for k in keys):
        raise ValueError("Missing independently compiled resource measurement.")
    exceeded = [k for k in keys if candidate[k] > reference[k]]
    return {
        "eligible": not exceeded,
        "exceeded": exceeded,
        "candidate_resources": candidate,
        "reference_budget": reference,
        "fallback_used": False,
        "attribution": "deterministic_resource_gate",
    }


def conditioned_draws(spec, rng, count):
    """Uniform on the fixed-bit/cardinality domain without universe enumeration."""
    fixed = {spec.tickers.index(t) for t in spec.include}
    excluded = {spec.tickers.index(t) for t in spec.exclude}
    free = sorted(set(range(spec.n)) - fixed - excluded)
    k = spec.k - len(fixed)
    if fixed & excluded or not 0 <= k <= len(free):
        raise ValueError("Empty conditioned sampling domain.")
    constant = sum(1 << q for q in fixed)
    return np.array(
        [
            constant + sum(1 << int(q) for q in rng.choice(free, k, replace=False))
            for _ in range(count)
        ],
        dtype=np.int64,
    )


class Observations:
    def __init__(self, spec):
        self.spec, self.cache, self.rows = spec, {}, []
        self.calls = 0
        self.start = perf_counter()
        self.bound = objective_bound(spec)
        self.best = None

    def score(self, samples):
        losses = []
        for index in map(int, samples):
            hit = index in self.cache
            if not hit:
                bits = [(index >> q) & 1 for q in range(self.spec.n)]
                self.calls += int(self.spec.feasible(bits))
                self.cache[index] = allocate(self.spec, bits)
            result = self.cache[index]
            if result.get("feasible"):
                if not -1e-7 <= result["objective"] <= self.bound * (1 + 1e-7):
                    raise ValueError("Frozen physical F bound violated.")
                if self.best is None or result["objective"] < self.best["objective"]:
                    self.best = result
                losses.append(result["objective"] / self.bound)
            else:
                losses.append(2.0)
            self.rows.append(
                {
                    "observation": len(self.rows) + 1,
                    "support_index": index,
                    "cache_hit": hit,
                    "allocation_calls": self.calls,
                    "allocation_status": result["status"],
                    "feasible": result.get("feasible", False),
                    "best_objective": self.best["objective"] if self.best else None,
                    "elapsed_seconds": perf_counter() - self.start,
                }
            )
        return float(np.mean(losses))


def search(
    spec,
    ir=None,
    h=None,
    *,
    method="circuit",
    target="allocation",
    seed=11,
    evaluations=10,
    shots=8,
    final_shots=8,
):
    if method not in ("circuit", "uniform", "swap") or target not in (
        "allocation",
        "proxy",
    ):
        raise ValueError("Unsupported frozen search method/feedback.")
    if any(type(v) is not int or v <= 0 for v in (evaluations, shots, final_shots)):
        raise ValueError("Positive integer budgets required.")
    start = perf_counter()
    rng = np.random.default_rng(seed)
    oracle = Observations(spec)
    total = evaluations * shots + final_shots
    angles = None
    state_calls = 0
    basis = None
    if method == "uniform":
        oracle.score(conditioned_draws(spec, rng, total))
    elif method == "swap":
        prohibited = set(spec.exclude)
        required = set(spec.include)
        ordered = [
            i
            for i in np.argsort(-spec.previous_weights, kind="stable")
            if spec.tickers[i] not in prohibited | required
        ]
        chosen = {spec.tickers.index(t) for t in required}
        chosen.update(map(int, ordered[: spec.k - len(chosen)]))
        oracle.score([sum(1 << q for q in chosen)])
        attempted = {oracle.rows[-1]["support_index"]}
        while len(oracle.rows) < total:
            incumbent = (
                oracle.best["support"]
                if oracle.best
                else [(q in chosen) for q in range(spec.n)]
            )
            candidates = []
            for q in range(spec.n):
                if not incumbent[q] or spec.tickers[q] in required:
                    continue
                for r in range(spec.n):
                    if incumbent[r] or spec.tickers[r] in prohibited:
                        continue
                    index = (
                        sum(int(b) << j for j, b in enumerate(incumbent))
                        ^ (1 << q)
                        ^ (1 << r)
                    )
                    if index not in attempted:
                        candidates.append(index)
            if not candidates:
                # Explicit restart uses the same conditioned domain and counts draws.
                candidates = conditioned_draws(spec, rng, 1).tolist()
            for index in candidates:
                if len(oracle.rows) >= total:
                    break
                attempted.add(index)
                oracle.score([index])
    else:
        scales, coordinate_record = coordinates(ir, h, "paper_rms_v1")
        basis = ConservedBasis(spec, h)
        energies = cost_values(h, basis.indices)
        initial = rng.uniform(-np.pi, np.pi, len(ir["parameters"]))
        best, value, calls = initial.copy(), float("inf"), 0

        class Exhausted(Exception):
            pass

        def sample(values, count):
            nonlocal state_calls
            state_calls += 1
            state = basis.execute(ir, h, values * scales, energies)
            probability = abs(state) ** 2
            probability /= probability.sum()
            indices = rng.choice(len(probability), count, p=probability)
            return basis.indices[indices] & ((1 << spec.n) - 1), energies[indices]

        def loss(values):
            nonlocal calls, best, value
            if calls >= evaluations:
                raise Exhausted
            calls += 1
            samples, observed_energy = sample(np.asarray(values), shots)
            allocated_loss = oracle.score(samples)
            result = (
                allocated_loss
                if target == "allocation"
                else float(observed_energy.mean())
                * coordinate_record["optimizer_loss_scale"]
            )
            if result < value:
                best, value = np.asarray(values).copy(), result
            return result

        try:
            minimize(
                loss,
                initial,
                method="COBYLA",
                options={"maxiter": max(evaluations, len(initial) + 2), "rhobeg": 0.5},
            )
        except Exhausted:
            pass
        while calls < evaluations:
            loss(best)
        oracle.score(sample(best, final_shots)[0])
        angles = (best * scales).tolist()
    return {
        "status": "feasible" if oracle.best else "unknown",
        "allocation": oracle.best,
        "observations": oracle.rows,
        "allocation_results": {str(k): v for k, v in oracle.cache.items()},
        "angles": angles,
        "allocation_queries": oracle.calls,
        "total_observations": len(oracle.rows),
        "state_evaluations": state_calls,
        "simulation_states": len(basis.indices) if basis else None,
        "feedback_target": target if method == "circuit" else None,
        "elapsed_seconds": perf_counter() - start,
        "cache_shared_between_runs": False,
        "sampling_domain": "fixed_bits_and_cardinality",
        "fallback_used": False,
    }


def prefix_rows(run, checkpoints=(8, 24, 48, 88)):
    result = []
    for count in checkpoints:
        if count > len(run["observations"]):
            continue
        row = run["observations"][count - 1]
        result.append(
            {
                "draws": count,
                "best_objective": row["best_objective"],
                "allocation_calls": row["allocation_calls"],
                "elapsed_seconds": row["elapsed_seconds"],
                "feasible_sample_fraction": sum(
                    r["feasible"] for r in run["observations"][:count]
                )
                / count,
            }
        )
    return result
