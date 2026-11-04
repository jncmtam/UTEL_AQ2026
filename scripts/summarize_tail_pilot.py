"""Independently audit and explain saved tail-fitting runs, without new search."""

from collections import Counter
from pathlib import Path
import argparse
import json
import shutil

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agqo.research.data import sha, write_json


METHODS = ["mean_f", "lower_tail_f", "uniform_conditioned", "allocation_swap"]
LABELS = {
    "mean_f": "Gated mean F",
    "lower_tail_f": "Gated lower-tail F",
    "uniform_conditioned": "Conditioned uniform",
    "allocation_swap": "Allocation-aware swap",
}
CHECKPOINTS = (64, 128, 256, 512, 576)


def load(path):
    return json.loads(path.read_text())


def support_feasible(index, spec):
    bits = np.array([(index >> i) & 1 for i in range(len(spec["tickers"]))])
    if bits.sum() != spec["k"]:
        return False
    if any(not bits[spec["tickers"].index(t)] for t in spec["include"]):
        return False
    if any(bits[spec["tickers"].index(t)] for t in spec["exclude"]):
        return False
    for sector, cap in spec["sector_count_caps"].items():
        if sum(bits[i] for i, s in enumerate(spec["sectors"]) if s == sector) > cap:
            return False
    limit = spec["max_replacements"]
    if (
        limit is not None
        and bits[np.array(spec["previous_weights"]) <= 1e-10].sum() > limit
    ):
        return False
    return True


def lower_tail(values, alpha):
    """Independent fractional empirical-tail calculation; no production helper."""
    ordered = sorted(values)
    mass = alpha * len(ordered)
    total = 0.0
    for i, value in enumerate(ordered):
        weight = max(0.0, min(1.0, mass - i))
        total += weight * value
    return total / mass


def audit_run(record, sufficient, target, observations_per_run):
    result = record["result"]
    spec = sufficient["financial_spec_without_returns"]
    matrix = np.asarray(sufficient["matrix"])
    vector = np.asarray(sufficient["linear"])
    old = np.asarray(spec["previous_weights"])
    bound = float(
        abs(matrix).max()
        + abs(vector).max()
        + abs(sufficient["offset"])
        + 2 * spec["cost_weight"] * spec["cost_rate"]
        + 1e-8
    )
    allocations = result["allocation_results"]
    residual, rescored = 0.0, 0
    for key, allocation in allocations.items():
        if not allocation.get("feasible"):
            continue
        index = int(key)
        w = np.asarray(allocation["weights"])
        bits = np.array([(index >> i) & 1 for i in range(len(spec["tickers"]))])
        assert support_feasible(index, spec), (record["case_id"], index)
        assert allocation["support"] == bits.tolist()
        assert np.isfinite(w).all() and abs(w.sum() - 1) < 1e-6
        assert (w >= -1e-8).all() and (abs(w[bits == 0]) < 1e-8).all()
        assert (w <= spec["maximum_weight"] + 1e-7).all()
        assert (w[bits == 1] >= spec["minimum_weight"] - 1e-7).all()
        for sector, cap in spec["sector_weight_caps"].items():
            assert (
                sum(w[i] for i, s in enumerate(spec["sectors"]) if s == sector)
                <= cap + 1e-7
            )
        if spec["turnover_cap"] is not None:
            turnover = (abs(w - old).sum() + abs((1 - w.sum()) - (1 - old.sum()))) / 2
            assert turnover <= spec["turnover_cap"] + 1e-7
        value = float(
            w @ matrix @ w
            + vector @ w
            + sufficient["offset"]
            + spec["cost_weight"] * spec["cost_rate"] * abs(w - old).sum()
        )
        difference = abs(value - allocation["objective"])
        assert difference < 1e-10, (record["case_id"], difference)
        residual = max(residual, difference)
        rescored += 1
    rows = result["observations"]
    assert result["total_observations"] == len(rows) == observations_per_run
    seen, calls, best = set(), 0, None
    values, flags, statuses, hits = [], [], [], []
    for number, row in enumerate(rows, 1):
        index = row["support_index"]
        assert 0 <= index < (1 << len(spec["tickers"]))
        assert row["observation"] == number
        assert int(index).bit_count() == spec["k"]
        assert all(index & (1 << spec["tickers"].index(t)) for t in spec["include"])
        assert all(not index & (1 << spec["tickers"].index(t)) for t in spec["exclude"])
        assert row["cache_hit"] == (index in seen)
        if index not in seen:
            calls += int(support_feasible(index, spec))
        seen.add(index)
        assert row["allocation_calls"] == calls
        allocation = allocations[str(index)]
        feasible = allocation.get("feasible", False)
        assert row["allocation_status"] == allocation["status"]
        assert row["feasible"] == feasible
        if feasible:
            objective = allocation["objective"]
            best = objective if best is None else min(best, objective)
            values.append(objective / bound)
        else:
            values.append(2.0)
        flags.append(feasible)
        statuses.append(allocation["status"])
        hits.append(
            bool(feasible and target is not None and allocation["objective"] <= target)
        )
        assert (row["best_objective"] is None and best is None) or abs(
            row["best_objective"] - best
        ) < 1e-10
    assert result["allocation_queries"] == calls
    assert len(allocations) == len(seen)
    if best is None:
        assert result["allocation"] is None and result["status"] == "unknown"
    else:
        assert result["status"] == "feasible"
        assert abs(result["allocation"]["objective"] - best) < 1e-10
    fitting = result.get("fitting_record")
    if fitting:
        alpha = fitting["alpha"]
        threshold = fitting["minimum_feasible_fraction"]
        end = 0
        for batch in fitting["batches"]:
            start, stop = batch["observations_start"] - 1, batch["observations_end"]
            assert start == end and stop > start
            end = stop
            part, fraction = values[start:stop], float(np.mean(flags[start:stop]))
            tail, mean = lower_tail(part, alpha), float(np.mean(part))
            eligible = fraction >= threshold
            expected = (
                (mean if fitting["kind"] == "mean" else tail)
                if eligible
                else 2 + threshold - fraction
            )
            for key, expected_value in [
                ("mean_loss", mean),
                ("lower_tail_loss", tail),
                ("objective_loss", expected),
                ("feasible_fraction", fraction),
                ("tail_mass", len(part) * alpha),
            ]:
                assert np.isclose(batch[key], expected_value, rtol=1e-10, atol=1e-12), (
                    key
                )
            assert batch["eligible"] == eligible
            assert batch["observations"] == len(part)
            assert batch["status_counts"] == dict(Counter(statuses[start:stop]))
            prior_calls = rows[start - 1]["allocation_calls"] if start else 0
            assert (
                batch["allocation_calls"]
                == rows[stop - 1]["allocation_calls"] - prior_calls
            )
            assert batch["cache_hits"] == sum(r["cache_hit"] for r in rows[start:stop])
        assert end == len(rows)
        fits = [b for b in fitting["batches"] if b["phase"] == "fit"]
        finals = [b for b in fitting["batches"] if b["phase"] == "final"]
        assert len(fits) == 8 and len(finals) == 1
        assert fitting["best_fit_eligible"] == any(b["eligible"] for b in fits)
        assert fitting["final_eligible"] == finals[0]["eligible"]
    prefix = []
    for count in CHECKPOINTS:
        if count > len(rows):
            continue
        row = rows[count - 1]
        prefix.append(
            {
                "case_id": record["case_id"],
                "method": record["method"],
                "seed": record["seed"],
                "draws": count,
                "best_objective": row["best_objective"],
                "allocation_calls": row["allocation_calls"],
                "elapsed_seconds": row["elapsed_seconds"],
                "feasible_sample_fraction": float(np.mean(flags[:count])),
                "unknown_sample_count": statuses[:count].count("unknown"),
                "observed_hit_fraction": float(np.mean(hits[:count]))
                if target is not None
                else None,
            }
        )
    final_count = 64
    summary = {
        "case_id": record["case_id"],
        "method": record["method"],
        "seed": record["seed"],
        "best_objective": best,
        "observations": len(rows),
        "allocation_queries": calls,
        "cache_hits": sum(r["cache_hit"] for r in rows),
        "state_evaluations": result["state_evaluations"],
        "elapsed_seconds": result["elapsed_seconds"],
        "pooled_feasible_fraction": float(np.mean(flags)),
        "final64_feasible_fraction": float(np.mean(flags[-final_count:])),
        "sample_status_counts": dict(Counter(statuses)),
        "pooled_observed_hit_fraction": float(np.mean(hits))
        if target is not None
        else None,
        "final64_observed_hit_fraction": float(np.mean(hits[-final_count:]))
        if target is not None
        else None,
        "best_fit_eligible": fitting["best_fit_eligible"] if fitting else None,
        "final_eligible": fitting["final_eligible"] if fitting else None,
        "failed_fit_batches": sum(
            not b["eligible"] for b in fitting["batches"] if b["phase"] == "fit"
        )
        if fitting
        else None,
    }
    return prefix, summary, rescored, residual


def paired_summary(frame, comparison):
    baseline = frame[frame.method == comparison][
        ["case_id", "seed", "best_objective"]
    ].rename(columns={"best_objective": "baseline"})
    paired = frame.merge(baseline, on=["case_id", "seed"])
    paired = paired[
        paired.best_objective.notna() & paired.baseline.notna() & (paired.baseline > 0)
    ].copy()
    paired["difference_pct"] = 100 * (paired.best_objective / paired.baseline - 1)
    rows = []
    for (n, method), group in paired.groupby(["n", "method"]):
        difference = group.best_objective - group.baseline
        rows.append(
            {
                "n": int(n),
                "method": method,
                "reference": comparison,
                "pairs": len(group),
                "mean_paired_difference_pct": float(group.difference_pct.mean()),
                "median_paired_difference_pct": float(group.difference_pct.median()),
                "wins_ties_losses": [
                    int((difference < -1e-10).sum()),
                    int((abs(difference) <= 1e-10).sum()),
                    int((difference > 1e-10).sum()),
                ],
            }
        )
    return rows


def plot_results(path, prefix, final, pairs):
    selected = prefix[prefix.n == 20]
    cases = selected.case_id.unique()
    if len(cases):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
        for ax, case in zip(axes.flat, cases):
            for method in METHODS:
                group = selected[
                    (selected.case_id == case) & (selected.method == method)
                ]
                mean = group.groupby("draws").best_objective.mean() * 1e6
                if len(mean):
                    ax.plot(
                        mean.index,
                        mean.values,
                        marker="o",
                        markersize=3,
                        label=LABELS[method],
                    )
            ax.set(
                title=case,
                xlabel="Observed supports, optimizer + final",
                ylabel="Best allocated training F ×10⁶",
            )
            ax.grid(alpha=0.2)
        for ax in axes.flat[len(cases) :]:
            ax.set_visible(False)
        handles, labels = axes.flat[0].get_legend_handles_labels()
        if handles:
            fig.legend(handles, labels, loc="outside lower center", ncol=2, fontsize=9)
        fig.suptitle(
            "Opened N20 development cases — matched observations, measured unequal total cost"
        )
        fig.savefig(path / "quality-by-budget.png", dpi=160)
        plt.close(fig)
    tail_pairs = [
        r for r in pairs if r["reference"] == "mean_f" and r["method"] == "lower_tail_f"
    ]
    if tail_pairs:
        fig, ax = plt.subplots(figsize=(7.4, 4.4), layout="constrained")
        bars = ax.bar(
            [f"N{r['n']} ({r['pairs']} pairs)" for r in tail_pairs],
            [r["mean_paired_difference_pct"] for r in tail_pairs],
            color="#387d88",
        )
        ax.bar_label(bars, fmt="%+.2f%%", padding=5)
        ax.axhline(0, color="#26384d", lw=1)
        low, high = ax.get_ylim()
        pad = max((high - low) * 0.22, 0.05)
        ax.set_ylim(low - pad, high + pad)
        ax.set(
            ylabel="Mean paired F difference (%)\nnegative means lower-tail fitting is better",
            title="Lower-tail versus mean fitting, final pooled decision",
        )
        fig.savefig(path / "tail-versus-mean.png", dpi=160)
        plt.close(fig)
    if len(final):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
        means = final.groupby("method")
        methods = [m for m in METHODS if m in means.groups]
        x = np.arange(len(methods))
        pooled = means.pooled_feasible_fraction.mean().reindex(methods).to_numpy()
        held = means.final64_feasible_fraction.mean().reindex(methods).to_numpy()
        axes[0].bar(x - 0.18, pooled * 100, 0.35, label="All observed supports")
        axes[0].bar(x + 0.18, held * 100, 0.35, label="Final64 observations")
        axes[0].set(
            xticks=x,
            xticklabels=[LABELS[m] for m in methods],
            ylim=(0, 110),
            ylabel="Observed feasible samples (%)",
            title="Pooled and final feasibility remain separate",
        )
        axes[0].legend(fontsize=8)
        calls = means.allocation_queries.mean().reindex(methods).to_numpy()
        bars = axes[1].bar(x, calls, color="#977547")
        axes[1].bar_label(bars, fmt="%.1f", padding=3)
        axes[1].set(
            xticks=x,
            xticklabels=[LABELS[m] for m in methods],
            ylabel="Mean unique convex allocation attempts",
            title="Equal observations do not imply equal solve cost",
        )
        axes[1].set_ylim(0, max(calls) * 1.18 if max(calls) else 1)
        for ax in axes:
            ax.tick_params(axis="x", rotation=18, labelsize=8)
        fig.savefig(path / "feasibility-and-allocations.png", dpi=160)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path", type=Path, default=Path("results/research/tail_fitting_v1")
    )
    args = parser.parse_args()
    path = args.path
    if (path / "RESULTS.md").exists():
        raise ValueError(
            "Preserve the completed derived report; use a separate revision for new presentation."
        )
    protocol = load(path / "protocol.json")
    completion = load(path / "completion.json")
    expected_hashes = completion.get("raw_sha256_files", completion.get("sha256_files"))
    if not expected_hashes:
        raise ValueError(
            "Completed pilot must supply its frozen raw-file hash manifest."
        )
    raw_hashes = {**expected_hashes, "completion.json": sha(path / "completion.json")}
    for name, expected in raw_hashes.items():
        assert sha(path / name) == expected, name
    case_info = {c["id"]: c for c in protocol["cases"]}
    expected_keys = {
        (c, m, s)
        for c in case_info
        for m in protocol["methods"]
        for s in protocol["seeds"]
    }
    rows, summaries, failures, completed_keys = [], [], [], set()
    rescored, maximum_residual, setups = 0, 0.0, []
    for case in case_info:
        setup_file = path / "setup" / f"{case}.json"
        if setup_file.exists():
            setup = load(setup_file)
            assert setup["verification"]["valid"], case
            setups.append({"case_id": case, **setup})
    for filename in sorted((path / "runs").glob("*.json")):
        record = load(filename)
        key = (record["case_id"], record["method"], record["seed"])
        assert key in expected_keys and key not in completed_keys, key
        if record.get("status") != "completed":
            failures.append(
                {
                    "case_id": key[0],
                    "method": key[1],
                    "seed": key[2],
                    "status": record.get("status"),
                    "reason": record.get("reason", record.get("error")),
                }
            )
            continue
        info = case_info[key[0]]
        sufficient = load(path / "cases" / key[0] / "sufficient_statistics.json")
        assert sufficient["source_spec_hash"] == info["hash"] == record["problem_hash"]
        setup = load(path / "setup" / f"{key[0]}.json")
        assert setup["hamiltonian_hash"] == record["hamiltonian_hash"]
        target = info.get("target", info.get("quality_target"))
        prefix, summary, count, residual = audit_run(
            record, sufficient, target, protocol["observations_per_run"]
        )
        for item in prefix + [summary]:
            item.update(n=info["n"], family=info["family"])
        rows.extend(prefix)
        summaries.append(summary)
        rescored += count
        maximum_residual = max(maximum_residual, residual)
        completed_keys.add(key)
    failed_keys = {(r["case_id"], r["method"], r["seed"]) for r in failures}
    pending = [
        dict(case_id=c, method=m, seed=s, status="not_completed")
        for c, m, s in sorted(expected_keys - completed_keys - failed_keys)
    ]
    prefix, final = pd.DataFrame(rows), pd.DataFrame(summaries)
    assert completion["completed_runs"] == len(completed_keys)
    assert completion["observations"] == sum(r["observations"] for r in summaries)
    assert completion["allocation_calls"] == sum(
        r["allocation_queries"] for r in summaries
    )
    pairs = []
    if len(final):
        for reference in ("mean_f", "uniform_conditioned", "allocation_swap"):
            pairs.extend(paired_summary(final, reference))
        prefix.to_csv(path / "prefix_metrics.csv", index=False)
        final.to_csv(path / "run_metrics.csv", index=False)
        plot_results(path, prefix, final, pairs)
    write_json(
        path / "analysis.json",
        {
            "study_status": completion.get("status"),
            "expected_runs": len(expected_keys),
            "completed_runs": len(completed_keys),
            "failed_runs": failures,
            "pending_runs": pending,
            "paired_comparisons": pairs,
            "run_summaries": summaries,
            "audited_feasible_allocations": rescored,
            "max_objective_residual": maximum_residual,
            "observations": sum(r["observations"] for r in summaries),
            "allocation_queries": sum(r["allocation_queries"] for r in summaries),
            "setup_seconds": sum(s["seconds"] for s in setups),
            "all_attempt_run_seconds": completion.get("cumulative_run_seconds"),
            "partial_failed_allocation_accounting": "Unknown on failed/interrupted runs; completed totals do not silently include them",
            "observation_status_counts": dict(
                sum((Counter(r["sample_status_counts"]) for r in summaries), Counter())
            ),
            "source_hashes": raw_hashes,
            "new_search_or_inference_calls": 0,
        },
    )
    lines = [
        "# Feasibility-gated tail-fitting results",
        "",
        "Opened US-return development pilot, local CPU simulation/classical controls. "
        "No new LLM, GPU or quantum hardware execution; no independent financial qualification.",
        "",
        f"Study status: **{completion.get('status')}**. Audited {len(completed_keys)}/{len(expected_keys)} "
        f"completed runs; {len(failures)} recorded failures and {len(pending)} uncompleted slots. "
        "Failures and uncompleted work are not successful runs.",
        "",
        "## What changed",
        "",
        "The same compact, verified circuit is fitted using either mean allocated F or its lower-tail "
        "mean, with a separate all-shot empirical feasibility gate. COST still represents equal-weight "
        "B. This experiment tests aggregation, not a coherent F oracle or the new LLM guidance contract.",
        "",
        "Each completed run receives576 observations (8×64 fitting plus64 final). Uniform and swap "
        "have the same observation budget. Actual allocator attempts, simulation evaluations and "
        "runtime differ; this is not matched complete cost. All observed supports enter the decision pool.",
        "",
        "![Quality by observation budget](quality-by-budget.png)",
        "",
        "**Figure 1.** Best allocated training F versus all observed supports for N20 cases. Lower is "
        "better. Curves average available seeds; related families/mandates/seeds are not independent "
        "market samples. No significance or return interpretation.",
        "",
        "## Paired final portfolio quality",
        "",
        "Positive differences mean a worse allocated training objective. Values below are means of "
        "paired percentage differences, not ratios of aggregate means. Only pairs with both feasible "
        "decisions and a positive reference objective enter this descriptive table; failure counts remain above.",
        "",
        "| Size | Method | Reference | Pairs | Mean F difference | Median | Wins/ties/losses |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for r in pairs:
        if r["method"] == r["reference"]:
            continue
        lines.append(
            f"| N{r['n']} | {LABELS[r['method']]} | {LABELS[r['reference']]} | {r['pairs']} | "
            f"{r['mean_paired_difference_pct']:+.2f}% | {r['median_paired_difference_pct']:+.2f}% | {r['wins_ties_losses']} |"
        )
    lines += [
        "",
        "![Tail versus mean](tail-versus-mean.png)",
        "",
        "**Figure 2.** Lower-tail minus mean fitting at the pooled final decision. Any benefit "
        "is an aggregation result on opened data, not LLM benefit or quantum advantage.",
        "",
        "## Feasibility and complete accounting",
        "",
        "A run can retain a feasible observed portfolio even if its fitted sampling distribution "
        "fails the empirical95% gate. Training best-batch eligibility and final64-shot eligibility "
        "are recorded separately; neither is a population-feasibility certificate.",
        "",
        "| Method | Completed | Mean pooled feasibility | Mean final64 feasibility | Best-fit gate passed | Final gate passed | Allocation attempts | Search seconds |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if len(final):
        for method in METHODS:
            group = final[final.method == method]
            if not len(group):
                continue
            fitted = method in ("mean_f", "lower_tail_f")
            best = (
                f"{int(group.best_fit_eligible.sum())}/{len(group)}"
                if fitted
                else "not applicable"
            )
            held = (
                f"{int(group.final_eligible.sum())}/{len(group)}"
                if fitted
                else "not applicable"
            )
            lines.append(
                f"| {LABELS[method]} | {len(group)} | {group.pooled_feasible_fraction.mean():.2%} | "
                f"{group.final64_feasible_fraction.mean():.2%} | {best} | {held} | "
                f"{int(group.allocation_queries.sum()):,} | {group.elapsed_seconds.sum():.2f} |"
            )
    lines += [
        "",
        "![Feasibility and allocation effort](feasibility-and-allocations.png)",
        "",
        "**Figure 3.** Pooled/final sample feasibility and actual convex allocation attempts. "
        "Classical final64 means its last64 observations, not a held-out circuit distribution. "
        "Allocator caching is local to each run. Simulation and setup costs are additional.",
        "",
        "The hit target is1.05 times a previously saved feasible5s SCIP incumbent. "
        "This is an opened-data algorithmic target, not global optimality or an economic margin. "
        "Pooled/final observed hit fractions and unknown/infeasible counts are in run_metrics.csv "
        "and analysis.json; adaptive observations are not independent Bernoulli trials.",
        "",
        "## Independent audit",
        "",
        f"- Rescored {rescored:,} feasible cached allocations from sufficient statistics; "
        f"maximum absolute objective residual {maximum_residual:.3g}.",
        f"- Captured hashes for {len(raw_hashes)} input/run/setup/source files before derived reporting; "
        "raw files remain unchanged.",
        "- Checked sample/cache/solver counters, support constraints, portfolio bounds, pooled best "
        "decisions and every recorded fitting/final aggregation and gate.",
        "- Setup verification/resource records are retained. Conserved CPU simulation is "
        "exponential classical simulation, not hardware evidence.",
        "",
        "## Interpretation and stop rule",
        "",
        "Tail fitting is useful only if downstream quality and actual cost support it against "
        "strong controls. A win over mean fitting alone does not justify an LLM sweep. "
        "If allocation-aware swap still leads the useful frontier, preserve that result and "
        "investigate formulation/sampler limits before model escalation.",
        "",
        "The corpus has full-year membership conditioning and artificial policy buckets. "
        "Only first126 estimation observations were used. No untouched financial test was opened; "
        "security/action/sector reconciliation remains required for investment evidence.",
    ]
    details = [
        "## Target hits and compiled resources",
        "",
        "| Method | Mean pooled observed hit fraction | Mean final64 observed hit fraction | Simulation state evaluations |",
        "|---|---:|---:|---:|",
    ]
    if len(final):
        for method in METHODS:
            group = final[final.method == method]
            if not len(group):
                continue
            pooled = group.pooled_observed_hit_fraction.mean()
            held = group.final64_observed_hit_fraction.mean()
            pooled_text = f"{pooled:.2%}" if pd.notna(pooled) else "target unavailable"
            held_text = f"{held:.2%}" if pd.notna(held) else "target unavailable"
            details.append(
                f"| {LABELS[method]} | {pooled_text} | {held_text} | {int(group.state_evaluations.sum()):,} |"
            )
    details += [
        "",
        "The common circuit resources below include compiler-owned COST and counted "
        "counter-Dicke preparation. Both fitting arms use the same structure; changing the "
        "aggregation does not reduce its gates. Values are compiler resources, not noisy hardware measurements.",
        "",
        "| Case | Physical/workspace-counted qubits | CX | Depth | Setup/verification seconds |",
        "|---|---:|---:|---:|---:|",
    ]
    for setup in setups:
        resources = setup["verification"]["resources"]
        details.append(
            f"| {setup['case_id']} | {resources['qubits']} | {resources['transpiled_cx']} | "
            f"{resources['transpiled_depth']} | {setup['seconds']:.2f} |"
        )
    details += [
        "",
        f"Total recorded setup/verification time: {sum(s['seconds'] for s in setups):.2f}s. "
        f"All attempted run time: {completion.get('cumulative_run_seconds')}s. "
        "Completed-run allocation totals exclude unknown partial work on failed/interrupted "
        "runs; no zero-cost assumption is made for that work. Local CPU only, with no new "
        "paid reservation or isolated cloud invoice.",
        "",
    ]
    position = lines.index("## Independent audit")
    lines[position:position] = details
    if failures or pending:
        lines += [
            "",
            "## Incomplete or failed work",
            "",
            "```json",
            json.dumps({"failures": failures, "uncompleted": pending}, indent=2),
            "```",
        ]
    for i, line in enumerate(lines):
        if line.startswith("!["):
            image_name = line.split("](", 1)[1].removesuffix(")")
            if not (path / image_name).exists():
                lines[i] = "No plot generated: no completed data for this comparison."
    (path / "RESULTS.md").write_text("\n".join(lines) + "\n")
    (path / "REPORT_PROGRESS.md").write_text(
        f"# Progress\n\nAudited {len(completed_keys)}/{len(expected_keys)} completed development runs. "
        f"Recorded failures:{len(failures)}; uncompleted:{len(pending)}. Study status:{completion.get('status')}. "
        "No new search or inference in this reporting step. Read RESULTS.md for measured comparisons "
        "and limits. No model, independent financial value or quantum advantage qualified.\n"
    )
    generator = path / "report_generator.py"
    shutil.copyfile(Path(__file__), generator)
    derived_names = [
        "analysis.json",
        "RESULTS.md",
        "REPORT_PROGRESS.md",
        "report_generator.py",
        "prefix_metrics.csv",
        "run_metrics.csv",
        "quality-by-budget.png",
        "tail-versus-mean.png",
        "feasibility-and-allocations.png",
    ]
    write_json(
        path / "report_manifest.json",
        {
            "raw_files_unchanged": all(
                sha(path / name) == expected for name, expected in raw_hashes.items()
            ),
            "derived_files": {
                name: sha(path / name)
                for name in derived_names
                if (path / name).exists()
            },
            "scope": "Read-only audit and derived reporting; no new optimization or inference",
        },
    )
    print(
        json.dumps(
            {
                "completed_runs": len(completed_keys),
                "failed": len(failures),
                "uncompleted": len(pending),
                "rescored_allocations": rescored,
                "maximum_residual": maximum_residual,
            }
        )
    )


if __name__ == "__main__":
    main()
