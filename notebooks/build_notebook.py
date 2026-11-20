"""Generate notebooks/AGQO_V3_2_Research_Modal.ipynb from the cells below (keeps the notebook reviewable).

    python notebooks/build_notebook.py

Execute (from the repository root; the notebook only submits work, Modal runs it):
    papermill notebooks/AGQO_V3_2_Research_Modal.ipynb results/runs/notebook_<date>.ipynb -p TASKS '["reproduce"]'
or open it in Jupyter / Modal Notebooks and run the cells in order.
"""

from pathlib import Path

import nbformat as nbf

MD, CODE = "markdown", "code"
CELLS = [
    (MD, """# AGQO V3.2 research runs on Modal

This notebook is the entry point for every quantum simulation, benchmark rerun and live LLM experiment of
V3.2. It submits work to Modal and keeps a local copy of each run directory under `results/runs/`.
No circuit is simulated in this kernel: the functions live in `modal_research.py` (Modal CPU) and
`modal_app.py` (Qwen3.8-27B on a Modal H100).

Prerequisites: `modal token new` once (credentials stay in `~/.modal.toml`), the price snapshot at
`data/vn30/ohlcv_daily.csv`, and for LLM tasks the deployed `agqo-llm` app. Vietnamese guide:
`docs/vi/NGHIEN_CUU_MODAL.md`.

Set `TASKS` in the next cell (papermill parameter) to choose what runs."""),
    (CODE, """# Parameters (papermill)
TASKS = ["smoke"]          # any of: smoke, reproduce, pytest, knn_table, knn_study, knn_refine, llm_mandates, llm_circuits, presets, account_benchmark,
                           #         llm_circuits, knn_table, knn_study
PYTEST_ARGS = []
LLM_MODEL_APP = "agqo-llm"
RUN_TAG = \"\""""),
    (CODE, """import json, os, sys, time
from pathlib import Path

ROOT = Path.cwd()
while not (ROOT / "modal_research.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import modal
import modal_research as mr
from agqo.research.orchestrate import keep, revision, show

REV = revision()
print("revision", REV)
kept = {}"""),
    (MD, "## Smoke test: image, data snapshot and Volume"),
    (CODE, """if "smoke" in TASKS:
    with mr.app.run():
        res = mr.smoke.remote(REV)
    kept["smoke"] = keep(res); show(kept["smoke"])"""),
    (MD, """## Product failure reproduction

Runs the decision pipeline on the edge cases reported against V3.1 and audits every result on the
post-trade NAV (cash after fees + holdings). Output: `product_failures.json`."""),
    (CODE, """if "reproduce" in TASKS:
    with mr.app.run():
        res = mr.reproduce.remote(REV)
    kept["reproduce"] = keep(res); show(kept["reproduce"])
    pf = json.loads((kept["reproduce"] / "product_failures.json").read_text())
    for c in pf["cases"]:
        a = c.get("audit", {})
        print(f"{c['case'][:58]:58s} {c['outcome']:9s} status={c.get('status')} app_ok={c.get('app_all_ok')} audit_ok={a.get('all_ok')}")
    print("verifier accepts swapped numbers:", pf["verifier_swap"]["swapped"]["check"]["ok"])"""),
    (MD, "## Test suite (including the circuit-simulating tests) on Modal CPU"),
    (CODE, """if "pytest" in TASKS:
    with mr.app.run():
        res = mr.pytest_suite.remote(REV, PYTEST_ARGS)
    kept["pytest"] = keep(res); show(kept["pytest"])
    print((kept["pytest"] / "pytest.txt").read_text()[-3000:])"""),
    (MD, """## k-NN study: success table (protocol §4)

Builds every calibration, validation, holdout and V3-test instance (5 account sizes × 3 constraint types) in
Modal containers and scores all 1,080 grid schedules on each with an exact statevector. The caller only
collects rows. Output: `meta.csv` (spec, features, baselines), `success_table.npz` (success, two-qubit gates)."""),
    (CODE, """if "knn_table" in TASKS:
    import numpy as np, pandas as pd
    from agqo.data import MarketData
    from agqo.research.instances import specs
    from agqo.research.orchestrate import local_run, push
    md = MarketData.load()
    sp = specs(md) + specs(md, splits=("v3_test",))
    run = local_run("knn-table", {"n_specs": len(sp), "grid": "V3 DesignConfig (1080 schedules)", "batch": 3,
                                  "account": "fresh cash", "sizes": sorted({s["capital_vnd"] for s in sp})})
    batches = [sp[i:i + 3] for i in range(0, len(sp), 3)]
    from agqo.research.orchestrate import fanout
    with mr.app.run():
        parts = fanout(mr.schedule_rows, batches,
                       on_item=lambda i, r: i % 30 == 0 and run.log(f"{3 * i}/{len(sp)} instances"))
        rows = [r for part in parts for r in part]
        ok = [r for r in rows if "error" not in r]
        bad = [r for r in rows if "error" in r]
        for r in bad:
            run.manifest["errors"].append({"where": f"{r['split']} {r['date']} {r['capital_vnd']:.0f} {r['constraint']}",
                                           "error": r["error"], "traceback": ""})
        key = lambda r: (r["split"], r["date"], r["capital_vnd"], r["constraint"])
        ok.sort(key=key)
        meta = pd.DataFrame([{k: v for k, v in r.items() if k not in ("features", "success", "cx", "warm_success")}
                             | {f"f_{k}": v for k, v in r["features"].items()}
                             | {f"warm_{k}": v for k, v in r["warm_success"].items()} for r in ok])
        run.save("meta.csv", meta)
        np.savez_compressed(run.dir / "success_table.npz", success=np.array([r["success"] for r in ok], dtype=np.float32),
                            cx=np.array([r["cx"] for r in ok], dtype=np.int32))
        run.step("table", instances=len(ok), errors=len(bad), cpu_seconds=float(meta.seconds.sum()))
        run.finish(instances=len(ok), errors=len(bad), cpu_hours=round(float(meta.seconds.sum()) / 3600, 2))
        push(run, mr.archive)
    kept["knn_table"] = run.dir; show(run.dir)"""),
    (MD, """## k-NN study: diagnosis, validation search, holdout (protocol §4)

Reads the newest `knn-table` run; it only analyses the stored success table (no simulation), so it runs in
this kernel. Validation chooses the variant before the holdout rows are scored."""),
    (CODE, """if "knn_study" in TASKS:
    from agqo.research.knn_study import run_study
    from agqo.research.orchestrate import local_run, push
    from agqo.research.runlog import RUNS_DIR
    table = sorted(p for p in RUNS_DIR.glob("*-knn-table") if json.loads((p / "run.json").read_text())["status"] == "ok")[-1]
    run = local_run("knn-study", {"table_run": table.name, "protocol": "docs/research/PROTOCOL_V3_2.md §4"})
    try:
        out = run_study(table, run)
        run.finish(selected=out["selection"]["label"],
                   holdout_knn=out["results"]["holdout"]["arms"]["knn_selected"]["mean_success"],
                   holdout_frozen=out["results"]["holdout"]["arms"]["frozen"]["mean_success"],
                   K2_p=out["results"]["holdout"]["tests"]["K2 knn_selected vs frozen"]["wilcoxon_p"])
    except Exception as e:
        run.error("knn_study", e); run.finish("failed")
    with mr.app.run():
        push(run, mr.archive)
    kept["knn_study"] = run.dir; show(run.dir)"""),
    (MD, """## k-NN study: local refinement ablation on the holdout (protocol §4)

Each holdout instance runs four circuits in a Modal container: the frozen schedule and the selected k-NN
schedule, each without and with 40 COBYLA steps on CVaR(0.1). 512 shots, seed 7. Measures success, feasible
mass, best-of-512 gap, circuit evaluations and wall time."""),
    (CODE, """if "knn_refine" in TASKS:
    import pandas as pd
    from agqo.extras import load_config
    from agqo.config import RESULTS_DIR
    from agqo.quantum.design import schedule_grid, spec_of
    from agqo.research.orchestrate import fanout, local_run, push
    from agqo.research.runlog import RUNS_DIR
    study = sorted(p for p in RUNS_DIR.glob("*-knn-study") if json.loads((p / "run.json").read_text())["status"] == "ok")[-1]
    plan = json.loads((study / "refine_plan.json").read_text())
    ec = load_config(RESULTS_DIR); grid = schedule_grid(ec.design); dc = ec.design
    sd = lambda i, pol: spec_of(grid.iloc[i], dc.polish_iters if pol else 0, dc.polish_cvar_alpha).to_dict()
    jobs = [{"instances": [{k: r[k] for k in ("split", "date", "capital_vnd", "constraint")}], "shots": 512, "seed": 7,
             "specs": {"frozen": sd(r["frozen_schedule"], False), "frozen+polish": sd(r["frozen_schedule"], True),
                       "knn": sd(r["knn_schedule"], False), "knn+polish": sd(r["knn_schedule"], True)}} for r in plan]
    run = local_run("knn-refine", {"study_run": study.name, "instances": len(jobs), "polish_iters": dc.polish_iters,
                                   "cvar_alpha": dc.polish_cvar_alpha, "shots": 512, "seed": 7})
    with mr.app.run():
        parts = fanout(mr.evaluate_specs, jobs, on_item=lambda i, r: i % 60 == 0 and run.log(f"{i}/{len(jobs)} instances"))
        rows = [r for part in parts for r in part]
        df = pd.DataFrame(rows)
        run.save("refine_rows.csv", df)
        bad = df[df.get("errors", pd.Series([[]] * len(df))).map(bool)] if "errors" in df else df.iloc[:0]
        for r in bad.itertuples():
            run.manifest["errors"].append({"where": f"{r.date} {r.capital_vnd} {r.constraint} {r.spec}", "error": str(r.errors), "traceback": ""})
        ok = df[~df.index.isin(bad.index)]
        g = ok.groupby("spec").agg(success=("success_prob", "mean"), feasible_mass=("feasible_mass", "mean"),
                                   best_gap=("best_sample_gap", "mean"), evaluations=("evaluations", "mean"),
                                   seconds=("seconds", "mean"), cx=("two_qubit_gates", "mean"))
        run.save("refine_summary.csv", g.reset_index())
        run.finish(**{f"{k}_success": round(float(v), 4) for k, v in g.success.items()})
        push(run, mr.archive)
    kept["knn_refine"] = run.dir; show(run.dir)"""),
    (MD, """## LLM experiment 1: Vietnamese instructions → constraints (protocol §3a)

Qwen3.8-27B on the Modal H100 app `agqo-llm` parses the 50 V3.2 evaluation instructions twice (V3 prompt and the
English V3.2 prompt); the keyword rules are the baseline. Every unblocked parse then runs through the
deterministic optimiser on Modal CPU and is judged against the gold constraints."""),
    (CODE, """if "llm_mandates" in TASKS:
    from agqo.data import MarketData
    from agqo.llm.client import LLMClient
    from agqo.research.llm_runs import run_mandates
    from agqo.research.orchestrate import fanout, local_run, push
    md = MarketData.load()
    run = local_run("llm-mandates", {"model_app": LLM_MODEL_APP, "items": 50, "temperature": 0.0, "decoding": "JSON schema"})
    client = LLMClient("modal", run.dir / "llm_log.jsonl", app_name=LLM_MODEL_APP)
    with mr.app.run():
        try:
            out = run_mandates(run, client, lambda b: fanout(mr.decide_items, b), {t: md.sector(t) for t in md.close.columns})
            run.finish(**{f"{a}_e2e_pct": round(s["e2e_correct_pct"], 1) for a, s in out["score"].items()})
        except Exception as e:
            run.error("llm_mandates", e); run.finish("failed")
        push(run, mr.archive)
    kept["llm_mandates"] = run.dir; show(run.dir)"""),
    (MD, """## LLM experiment 2: circuit design and optimisation (protocol §3b)

Two rounds of 8 structured candidates from Qwen3.8 (English prompt with the problem specification, components,
budgets and objective), validated before simulation and scored on 24 design instances on Modal CPU; random search
over the same space with the same budget (3 seeds); then the best of each on the 330 holdout instances."""),
    (CODE, """if "llm_circuits" in TASKS:
    from agqo.config import RESULTS_DIR
    from agqo.data import MarketData
    from agqo.extras import load_config
    from agqo.llm.client import LLMClient
    from agqo.quantum.design import spec_of
    from agqo.research.llm_runs import run_circuits
    from agqo.research.orchestrate import fanout, local_run, push
    md = MarketData.load(); ec = load_config(RESULTS_DIR)
    fz = json.loads((RESULTS_DIR / "run_manifest.json").read_text())["frozen_schedule"]
    frozen = {"frozen_grid": spec_of(fz).to_dict(),
              "frozen_grid+polish": spec_of(fz, ec.design.polish_iters, ec.design.polish_cvar_alpha).to_dict()}
    run = local_run("llm-circuits", {"model_app": LLM_MODEL_APP, "rounds": 2, "candidates_per_round": 8,
                                     "random_seeds": [1000, 1001, 1002], "design_instances": 24, "frozen_schedule": fz})
    client = LLMClient("modal", run.dir / "llm_log.jsonl", app_name=LLM_MODEL_APP)
    with mr.app.run():
        try:
            out = run_circuits(run, client, lambda jobs: fanout(mr.evaluate_specs, jobs), md, frozen)
            run.finish(best_llm=out["best_llm"], llm_valid=out["llm_valid"],
                       **{k: round(v["diff_pp"], 2) for k, v in out["holdout_tests"].items()})
        except Exception as e:
            run.error("llm_circuits", e); run.finish("failed")
        push(run, mr.archive)
    kept["llm_circuits"] = run.dir; show(run.dir)"""),
    (MD, """## Product presets (protocol §6) and small-account benchmark (protocol §5)

Presets: the latest-date decision of every preset (kept for the app's replay) and 12-quarter walks with AGQO and
nearest-lot rounding under the preset's rules. Benchmark: 20M and the price-level bound (18.2M, 16M, 13.3M =
historical lot costs understated by 10%, 25%, 50%) for rounding, greedy, exact and AGQO."""),
    (CODE, """if "presets" in TASKS or "account_benchmark" in TASKS:
    import shutil
    from agqo.research.orchestrate import fanout, local_run, push
    from agqo.research.product_runs import run_account_benchmark, run_presets
    with mr.app.run():
        if "presets" in TASKS:
            run = local_run("presets", {"quarters": "V3 test (12)", "account": "fresh cash, then walk"})
            try:
                res = run_presets(run, lambda ps: fanout(mr.preset_job, ps), lambda js: fanout(mr.walk_job, js))
                (ROOT / "results" / "v32").mkdir(parents=True, exist_ok=True)
                shutil.copy(run.dir / "presets.json", ROOT / "results" / "v32" / "presets.json")
                run.finish(**{p["id"]: p["outcome"] for p in res["presets"]})
            except Exception as e:
                run.error("presets", e); run.finish("failed")
            push(run, mr.archive); kept["presets"] = run.dir; show(run.dir)
        if "account_benchmark" in TASKS:
            run = local_run("account-benchmark", {"capitals": [20e6, 18.18e6, 16e6, 13.33e6], "quarters": "V3 test (12)"})
            try:
                res = run_account_benchmark(run, lambda js: fanout(mr.walk_job, js))
                run.finish(**{f"{int(t['capital_vnd'] / 1e5) / 10:g}M {t['comparison']}": round(t["diff_pp"], 2)
                              for t in res["tests"] if t["comparison"] == "agqo vs practitioner"})
            except Exception as e:
                run.error("account_benchmark", e); run.finish("failed")
            push(run, mr.archive); kept["account_benchmark"] = run.dir; show(run.dir)"""),
    (MD, "## Summary of this notebook execution"),
    (CODE, """print(json.dumps({k: str(v) for k, v in kept.items()}, indent=1))"""),
]


def build(path: Path = Path(__file__).with_name("AGQO_V3_2_Research_Modal.ipynb")) -> Path:
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    for kind, src in CELLS:
        cell = nbf.v4.new_markdown_cell(src) if kind == MD else nbf.v4.new_code_cell(src)
        if kind == CODE and src.startswith("# Parameters"):
            cell.metadata["tags"] = ["parameters"]
        nb.cells.append(cell)
    nbf.write(nb, path)
    return path


if __name__ == "__main__":
    print(build())
