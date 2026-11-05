"""Independent numerical audit and explanation of frozen decision distributions."""

from collections import Counter
from math import comb
from pathlib import Path
import json
import shutil
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from agqo.research.data import sha, write_json

ROOT = Path("results/research/decision_audit_v1")


def expected_by_atoms(f, p, m, incumbent=None):
    values = np.minimum(f, incumbent) if incumbent is not None else np.asarray(f)
    order = np.argsort(values, kind="stable")
    survival = np.r_[1., 1-np.cumsum(np.asarray(p)[order])]
    survival[-1] = 0.
    survival = np.maximum(0., np.minimum(1., survival))
    return float(np.dot(values[order], survival[:-1]**m-survival[1:]**m))


def plots(root, curves, decisions, proxy_rows, case_summaries):
    cases = list(case_summaries)
    fig, axes = plt.subplots(1, len(cases), figsize=(12, 5), layout="constrained")
    for ax, cid in zip(np.atleast_1d(axes), cases):
        group = curves[curves.case_id == cid]
        reference = case_summaries[cid]["best_feasible_F"]
        for method in ("aggregate", "counterfactual", "teacher", "uniform_conditioned"):
            part = group[group.method == method].groupby("shots").expected_minimum.mean()
            ax.plot(part.index, part/reference, marker="o", label=method.replace("_", " "))
        ax.axhline(1, color="gray", linestyle="--")
        ax.axvline(64, color="gray", linestyle=":")
        ax.set(xscale="log", yscale="log", xlabel="Independent draws from fixed fitted angles", ylabel="Expected operational minimum / numerical feasible incumbent", title=cid)
        ax.grid(alpha=.2)
    np.atleast_1d(axes)[0].legend(fontsize=8)
    fig.suptitle("Exact best-of-budget curves under the exhaustive recorded allocation table\nTwo fitted seeds averaged; no adaptive-policy, market-return or speedup claim")
    fig.savefig(root / "best-of-budget.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(cases), figsize=(12, 4.8), layout="constrained")
    for ax, cid in zip(np.atleast_1d(axes), cases):
        part = decisions[(decisions.case_id == cid) & decisions.method.isin(["aggregate", "counterfactual", "teacher"])]
        names = [f"{r.method}\nseed {r.seed}" for r in part.itertuples()]
        reference = case_summaries[cid]["best_feasible_F"]
        x = np.arange(len(part))
        ax.scatter(x, part.observed_best_576/reference, marker="o", label="Recorded best of pooled576")
        ax.scatter(x, part.expected_final_with_incumbent/reference, marker="D", label="Conditional expectation after fitting")
        ax.set(xticks=x, xticklabels=names, ylabel="Decision F / numerical feasible incumbent", title=cid)
        ax.tick_params(axis="x", labelrotation=40, labelsize=8)
        ax.grid(alpha=.2)
    np.atleast_1d(axes)[0].legend(fontsize=8)
    fig.suptitle("Final decision quality after512 recorded fitting draws +64 future draws\nConditioning on the fitted history does not evaluate the unconditional adaptive policy")
    fig.savefig(root / "conditional-decisions.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(cases), figsize=(12, 5), layout="constrained")
    for ax, cid in zip(np.atleast_1d(axes), cases):
        q = proxy_rows[cid]
        ax.scatter(q["B"], q["F"], s=3, alpha=.12, rasterized=True)
        best = int(np.argmin(q["F"]))
        ax.scatter(q["B"][best], q["F"][best], marker="*", s=160, color="#145f51", label="Best recorded feasible F")
        b_best = int(np.argmin(q["B"]))
        ax.scatter(q["B"][b_best], q["F"][b_best], marker="D", s=55, color="#c27720", label="Allocated proxy optimum")
        ax.set(xlabel="Equal-weight support proxy B", ylabel="Continuous allocated F", title=f"{cid}\nSpearman {q['rank_correlation']:.3f}")
        ax.xaxis.set_major_locator(MaxNLocator(5))
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.ticklabel_format(axis="both", style="sci", scilimits=(0,0), useMathText=True)
        ax.grid(alpha=.2)
    np.atleast_1d(axes)[0].legend(fontsize=8)
    fig.suptitle("Exhaustive conditional-US support audit: B and allocated F are different\nAll numerical allocation queries and source-cache work remain charged diagnostic preprocessing")
    fig.savefig(root / "proxy-versus-allocation.png", dpi=170)
    plt.close(fig)


def main():
    root, e = ROOT, ROOT / "evaluation"
    if (root / "RESULTS.md").exists():
        raise ValueError("Existing audit retained; do not overwrite it.")
    read = lambda file: json.loads(file.read_text())
    manifest = read(root / "orchestration/download_manifest.json")
    for name, expected in manifest.items():
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert sha(e / name) == expected
    complete, table_summary = read(e / "completion.json"), read(e / "table_completion.json")
    assert complete == read(root / "orchestration/completed.json")
    assert complete["input_hash"] == table_summary["input_hash"]
    records, samplers = read(e / "distribution_records.json"), read(e / "frozen_samplers.json")
    source_lookup = {(s["case_id"], s["method"], s["seed"]): s for s in samplers}
    assert len(samplers) == 16 and len(records) == complete["logical_distributions"] == 18
    cases = {r["case_id"]: r for r in table_summary["cases"]}
    tables, proxy_rows = {}, {}
    rescored, residual = 0, 0.
    for cid, summary in cases.items():
        stat = read(e / "cases" / cid / "sufficient_statistics.json")
        spec, matrix, linear = stat["financial_spec_without_returns"], np.asarray(stat["matrix"]), np.asarray(stat["linear"])
        old = np.asarray(spec["previous_weights"])
        rows = [json.loads(line) for line in (e / "cases" / cid / "allocation_table.jsonl").read_text().splitlines()]
        indices = np.array([r["support_index"] for r in rows], dtype=np.int64)
        n, k = len(spec["tickers"]), spec["k"]
        fixed = [spec["tickers"].index(t) for t in spec["include"]]
        excluded = [spec["tickers"].index(t) for t in spec["exclude"]]
        expected_count = comb(n-len(fixed)-len(excluded), k-len(fixed))
        assert len(rows) == expected_count == summary["supports"]
        assert np.all(np.diff(indices)>0) and all(int(i).bit_count()==k for i in indices)
        assert all(all(i & (1<<q) for q in fixed) and all(not i & (1<<q) for q in excluded) for i in indices)
        assert Counter(r["allocation"]["status"] for r in rows) == summary["status_counts"]
        assert sum(r["origin"]["kind"] == "new_common_allocator_call" for r in rows) == summary["new_allocator_calls"]
        assert sum(r["origin"]["kind"] == "reused" for r in rows) == summary["reused_optimal_allocations"]
        F, B = [], []
        proxy = np.load(e / "cases" / cid / "proxy_scores.npy", allow_pickle=False)
        for number, row in enumerate(rows):
            index, allocation = row["support_index"], row["allocation"]
            bits = np.array([(index>>q)&1 for q in range(n)])
            equal = bits/k
            b = float(equal@matrix@equal + linear@equal + stat["offset"] + spec["cost_weight"]*spec["cost_rate"]*abs(equal-old).sum())
            assert abs(b-proxy[number]) < 1e-10
            if not allocation.get("feasible"):
                assert row["operational_score"] == 2*summary["objective_bound"]
                continue
            w = np.asarray(allocation["weights"])
            assert np.isfinite(w).all() and abs(w.sum()-1)<1e-7 and w.min()>=-1e-8
            assert np.max(abs(w[bits==0]), initial=0)<1e-8
            assert np.all(w[bits==1]>=spec["minimum_weight"]-1e-7) and np.all(w<=spec["maximum_weight"]+1e-7)
            for sector, cap in spec["sector_weight_caps"].items():
                assert sum(w[q] for q,s in enumerate(spec["sectors"]) if s==sector)<=cap+1e-7
            f = float(w@matrix@w + linear@w + stat["offset"] + spec["cost_weight"]*spec["cost_rate"]*abs(w-old).sum())
            error = abs(f-allocation["objective"])
            assert error<1e-10 and abs(f-row["operational_score"])<1e-10
            residual = max(residual, error)
            rescored += 1
            F.append(f)
            B.append(b)
        assert abs(min(F)-summary["best_feasible_F"])<1e-10
        tables[cid] = rows
        proxy_rows[cid] = {"B": np.asarray(B), "F": np.asarray(F), "rank_correlation": float(spearmanr(B,F).statistic)}
    curve_rows, decision_rows, numerical_errors = [], [], []
    physical = set()
    for record in records:
        cid = record["case_id"]
        table = tables[cid]
        f = np.array([r["operational_score"] for r in table])
        if record["method"] == "uniform_conditioned":
            p = np.ones(len(f))/len(f)
        else:
            source = source_lookup[(cid,record["method"],record["seed"])]
            assert sha(Path(source["source_file"])) == source["source_sha256"] == record["source_sha256"]
            old_result = read(Path(source["source_file"]))["result"]
            assert source["fit_incumbent"] == old_result["observations"][511]["best_objective"] == record["fit_incumbent"]
            assert source["observed_best_576"] == old_result["allocation"]["objective"] == record["observed_best_576"]
            data = np.load(e / "probabilities" / f"{record['sampler_signature']}.npz", allow_pickle=False)
            assert np.array_equal(data["indices"], [r["support_index"] for r in table])
            p = data["probabilities"]
            meta = record["execution"]
            assert meta["cuda"] and not meta["cpu_fallback"] and meta["execute_calls"]==1 and meta["cuda_stream_elapsed_ms"]>0
            physical.add(record["sampler_signature"])
        assert p.shape==f.shape and np.isfinite(p).all() and np.all(p>=0) and abs(p.sum()-1)<1e-10
        flags = np.array([r["allocation"].get("feasible", False) for r in table])
        feasible_mass = float(p[flags].sum())
        good_mass = float(p[flags & (f<=record["algorithmic_hit_threshold"])].sum())
        for row in record["curves"]:
            expected = expected_by_atoms(f,p,row["shots"])
            error = abs(row["expected_minimum"]-expected)
            assert error<1e-10
            assert abs(row["feasible_probability"]-feasible_mass)<1e-10
            assert abs(row["no_feasible_probability"]-(1-feasible_mass)**row["shots"])<1e-10
            assert abs(row["hit_probability"]-(1-(1-good_mass)**row["shots"]))<1e-10
            numerical_errors.append(error)
            if record["fit_incumbent"] is not None:
                clipped = expected_by_atoms(f,p,row["shots"],record["fit_incumbent"])
                assert abs(clipped-row["expected_with_incumbent"])<1e-10 and clipped<=record["fit_incumbent"]+1e-10
            curve_rows.append({"case_id":cid,"method":record["method"],"seed":record["seed"],**row})
        if record["fit_incumbent"] is not None:
            row = next(r for r in record["curves"] if r["shots"]==64)
            decision_rows.append({"case_id":cid,"method":record["method"],"seed":record["seed"],"fit_incumbent":record["fit_incumbent"],
                "observed_best_576":record["observed_best_576"], "expected_final_with_incumbent":row["expected_with_incumbent"],
                "expected_best_64_final_only":row["expected_minimum"], "exact_mean_score":row["mean_score"],
                "feasible_probability":row["feasible_probability"], "uncertain_probability":record["uncertain_probability"]})
    assert len(physical)==complete["unique_cuda_evaluations"]
    for cid in cases:
        check = read(e / "cases" / cid / "cuda_selfcheck.json")
        assert check["status"]=="passed" and all(c["max_amplitude_residual"]<=1e-10 for c in check["checks"])
    curves, decisions = pd.DataFrame(curve_rows), pd.DataFrame(decision_rows)
    pairs = []
    for cid in cases:
        for seed in (23,47):
            group=decisions[(decisions.case_id==cid)&(decisions.seed==seed)]
            a,b=[group[group.method==m].iloc[0] for m in ("counterfactual","aggregate")]
            pairs.append({"case_id":cid,"seed":seed,**{key:100*(a[key]/b[key]-1) for key in ("observed_best_576","expected_final_with_incumbent","expected_best_64_final_only","exact_mean_score")}})
    paired=pd.DataFrame(pairs)
    analysis={"hashes_verified":len(manifest),"supports":sum(c["supports"] for c in cases.values()),"feasible_allocations_rescored":rescored,
        "max_F_residual":residual,"max_order_statistic_crosscheck_residual":max(numerical_errors),
        "new_allocator_calls":table_summary["new_allocator_calls"],"unique_cuda_evaluations":len(physical),"logical_distributions":len(records),
        "case_summaries":cases,"proxy_rank_correlations":{k:v["rank_correlation"] for k,v in proxy_rows.items()},
        "paired_means_pct":paired.drop(columns=["case_id","seed"]).mean().to_dict(), "paired_records":pairs,
        "new_model_calls":0,"new_angle_optimizations":0,"financial_qualification":False,"scope":"Conditional expected final decision given recorded fit histories; not the unconditional adaptive optimizer or an investment test"}
    write_json(root/"analysis.json",analysis)
    curves.to_csv(root/"curves.csv",index=False)
    decisions.to_csv(root/"decisions.csv",index=False)
    paired.to_csv(root/"paired_differences.csv",index=False)
    plots(root,curves,decisions,proxy_rows,cases)
    cost=read(root/"orchestration/cost_report.json")
    lines=["# Decision-level audit results","",f"Full diagnostic supports:{analysis['supports']:,}; newly evaluated:{analysis['new_allocator_calls']:,}; independently rescored feasible allocations:{rescored:,}. Verified{len(manifest)} raw hashes. Logical fixed distributions:{len(records)}; unique actual CUDA evaluations:{len(physical)}. No new LLM calls, architecture search or angle fitting.","",
        "The F table is exhaustive, classical and exponential. It supplies a numerical reference, not a production financial oracle or quantum win. Cached source generation and all new allocation costs remain explicit. Historical source admission stays closed; the two opened2010 US cases have full-year membership conditioning and artificial policy buckets.","",
        "## What differs from the previous comparison","","Earlier results use the realized best from512 adaptive fitting draws +64 final draws. We now compute exact operational metrics for each fixed fitted sampler. The conditional final-decision expectation clips future64-draw scores at that run's recorded fitting incumbent. It is exact **given that realized history and this recorded allocator table**; it is not an unconditional expectation of the adaptive576-shot algorithm. Solver-status sensitivity intervals are numerical diagnostics, not formal joint certificates.","",
        "| Detailed versus aggregate, four related pairs | Mean difference |","|---|---:|"]
    for key,value in analysis["paired_means_pct"].items():lines.append(f"| {key} | {value:+.3f}% |")
    lines += ["","Negative favors detailed guidance. These are descriptive ratios over two cases/two fitted seeds; no significance or independent market claim.","","![Best-of-budget curves](best-of-budget.png)","","![Conditional final decisions](conditional-decisions.png)","","## Reference and proxy faithfulness","","| Case | Support count | Solver statuses | Numerical reference complete | B-optimum allocated regret |","|---|---:|---|---|---:|"]
    for cid,s in cases.items():
        regret=f"{s['proxy_best_allocated_regret_pct']:.3f}%" if s["proxy_best_allocated_regret_pct"] is not None else "not feasible/unknown"
        lines.append(f"| {cid} | {s['supports']} | {json.dumps(s['status_counts'])} | {s['numerical_reference_complete']} | {regret} |")
    lines += ["","A complete numerical reference reflects solver statuses, not a formal exact-arithmetic certificate. If the table is known, directly taking its minimum is the strongest trivial reference. Quantum curves do not receive free preprocessing credit.","","![Equal-weight proxy versus allocated objective](proxy-versus-allocation.png)","","## Limits and decision","",
        "This audit separates observed sampling outcomes, final-only distribution quality and the already-acquired fitting incumbent. It does not prove which mechanism caused an unconditional policy-level performance difference. No optimizer/default has been changed and no further paid/model sweep is scheduled by this report. Use these metrics to justify a separate fitting/formulation experiment, rather than interpreting four realized minima or a better mean as proof of financial value.","",
        f"Financial rescoring residual <= {residual:.3g}; independent atom-probability expectation check residual <= {max(numerical_errors):.3g}. Reservations USD{cost['reserved_usd_total']:.2f}, not an invoice. CPU table time:{table_summary['elapsed_seconds']:.2f}s; GPU audit stage:{complete['elapsed_gpu_stage_seconds']:.2f}s. Cache provenance, all statuses and partial-stage accounting are retained.","",
        "[Full curves](curves.csv) · [Conditional decisions](decisions.csv) · [Audit details](analysis.json) · [Exhaustive table summary](evaluation/table_completion.json) · [Cache provenance](evaluation/cache_provenance.json) · [Cost report](orchestration/cost_report.json)"]
    (root/"RESULTS.md").write_text("\n".join(lines)+"\n")
    (root/"PROGRESS.md").write_text("# Progress\n\nCPU table and real CUDA distribution audit completed, downloaded and independently checked. No new model/angle search or market test. Read RESULTS.md and analysis.json. No automatic repeat or new inference is scheduled.\n")
    shutil.copyfile(__file__,root/"report_generator.py")
    print(json.dumps(analysis,indent=2))


if __name__=="__main__":
    main()
