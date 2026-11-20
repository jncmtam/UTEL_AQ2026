"""Orchestration of the two V3.2 LLM experiments (called from the research notebook).

The LLM runs on the Modal H100 app `agqo-llm` through LLMClient (every call logged with prompts, raw text,
status and token counts); deterministic evaluation runs on Modal CPU through the functions passed in.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from ..mandate import Mandate, rule_clarification, rule_parse


# ================================================================== 3a. instruction parsing
def run_mandates(run, client, decide_fn, sector_of: dict[str, str]) -> dict:
    from ..llm.tasks import mandate_request, parse_mandate
    from .mandate_eval_v2 import ITEMS, PROMPT_VERSION, field_matches, question_quality, request_v32, status_of

    tickers = set(sector_of)
    reqs_v3 = [mandate_request(text, sector_of, seed=i) for i, (_, _, _, text, _, _) in enumerate(ITEMS)]
    reqs_v32 = [request_v32(text, sector_of, seed=i) for i, (_, _, _, text, _, _) in enumerate(ITEMS)]
    run.log(f"LLM: {len(ITEMS)} items x 2 prompts on {client.backend}")
    recs = client.generate(reqs_v3 + reqs_v32)
    rec_v3, rec_v32 = recs[:len(ITEMS)], recs[len(ITEMS):]
    run.step("llm_calls", calls=len(recs), invalid=sum(r["status"] != "ok" for r in recs),
             input_tokens=sum((r.get("usage") or {}).get("input_tokens", 0) for r in recs),
             output_tokens=sum((r.get("usage") or {}).get("output_tokens", 0) for r in recs))

    rows = []
    for i, (iid, cat, cap, text, gold, extra) in enumerate(ITEMS):
        gold_status = {"ambiguous": "needs_clarification", "conflicting": "conflict"}.get(cat, "ok")
        arms = {}
        m = rule_parse(text, tickers)
        clar, q = rule_clarification(text)
        arms["keyword"] = (m, "needs_clarification" if clar else "ok", q, [], None)
        for arm, rec, ver in (("qwen_v3_prompt", rec_v3[i], "v3"), ("qwen_v32_prompt", rec_v32[i], "v3.2")):
            parsed = rec["parsed"] if rec["status"] == "ok" else None
            st = status_of(parsed, ver)
            pm, _, errs = parse_mandate(parsed, tickers) if parsed is not None else (Mandate(), False, ["no valid JSON"])
            if errs:
                st = "invalid"
            arms[arm] = (pm, st, (parsed or {}).get("clarification_question_vi"), errs, parsed)
        for arm, (pm, st, q, errs, parsed) in arms.items():
            fm = field_matches(pm, gold)
            rows.append({"item": iid, "category": cat, "capital_million": cap, "instruction": text, "arm": arm,
                         "gold": gold.to_dict(), "gold_status": gold_status, "pred": pm.to_dict(), "status": st,
                         "blocked": st in ("needs_clarification", "conflict"), "errors": errs,
                         "question": q, "question_quality": question_quality(q, extra) if st != "ok" else None,
                         "fields_correct": sum(fm.values()), "mandate_exact": all(fm.values()),
                         **{f"field_{k}": v for k, v in fm.items()}, "extra": extra,
                         "raw": parsed if arm != "keyword" else None})
    df = pd.DataFrame(rows)

    # end-to-end: every unblocked, valid parse goes through the deterministic optimiser on Modal CPU
    jobs = [{"item": r.item, "arm": r.arm, "capital_million": r.capital_million, "mandate": r.pred, "gold": r.gold}
            for r in df.itertuples() if not r.blocked and r.status != "invalid"]
    batches = [jobs[i:i + 4] for i in range(0, len(jobs), 4)]
    run.log(f"end-to-end: {len(jobs)} decisions on Modal CPU")
    outs = [o for part in decide_fn(batches) for o in part]
    e2e = {(o["item"], o["arm"]): o for o in outs}
    run.step("end_to_end", decisions=len(outs), errors=sum(o["outcome"] == "error" for o in outs))

    def judge(r) -> tuple[bool, str]:
        if r.status == "invalid":
            return False, "invalid answer"
        if r.gold_status != "ok":
            return (True, "blocked as required") if r.blocked else (False, "traded although a question was needed")
        if r.blocked:
            return False, "asked although the instruction was clear"
        o = e2e.get((r.item, r.arm), {"outcome": "missing"})
        if r.category == "infeasible":
            ok = o["outcome"] == "infeasible" and r.extra["blocking"] in o.get("blocking", [])
            return ok, "infeasible with the right rule" if ok else f"outcome {o['outcome']} {o.get('blocking', '')}"
        if o["outcome"] != "decision":
            return False, f"outcome {o['outcome']} {o.get('blocking', o.get('errors', ''))}"
        return bool(o["gold_rules_ok"]), "trades obey the gold rules" if o["gold_rules_ok"] else f"violates {o['gold_failures']}"

    j = [judge(r) for r in df.itertuples()]
    df["e2e_correct"] = [a for a, _ in j]
    df["e2e_reason"] = [b for _, b in j]
    df["e2e_exact"] = df.e2e_correct & (df.mandate_exact | (df.gold_status != "ok"))
    df["e2e_outcome"] = [e2e.get((r.item, r.arm), {}).get("outcome") for r in df.itertuples()]

    score = {}
    for arm, g in df.groupby("arm"):
        clear = g[g.category == "clear"]
        need = g[g.gold_status != "ok"]
        asked = g[g.blocked]
        qq = [q["score"] for q in g.question_quality.dropna() if q and q.get("asked")]
        score[arm] = {
            "items": len(g), "invalid": int((g.status == "invalid").sum()),
            "field_accuracy_pct": float(100 * g.fields_correct.sum() / (6 * len(g))),
            "exact_mandate_clear_pct": float(100 * clear.mandate_exact.mean()),
            "status_accuracy_pct": float(100 * (g.status == g.gold_status).mean()),
            "block_decision_accuracy_pct": float(100 * (g.blocked == (g.gold_status != "ok")).mean()),
            "clarification_recall_pct": float(100 * need.blocked.mean()),
            "clarification_precision_pct": float(100 * (asked.gold_status != "ok").mean()) if len(asked) else None,
            "conflict_detected_pct": float(100 * (g[g.category == "conflicting"].status == "conflict").mean()),
            "question_quality_mean": float(np.mean(qq)) if qq else None,
            "e2e_correct_pct": float(100 * g.e2e_correct.mean()), "e2e_exact_pct": float(100 * g.e2e_exact.mean()),
            "e2e_by_category_pct": {c: float(100 * gg.e2e_correct.mean()) for c, gg in g.groupby("category")}}
    # McNemar (exact) on end-to-end correctness, V3.2 prompt vs keyword rules and vs the V3 prompt
    piv = df.pivot(index="item", columns="arm", values="e2e_correct")
    tests = {}
    for b in ("keyword", "qwen_v3_prompt"):
        a_only = int((piv["qwen_v32_prompt"] & ~piv[b]).sum())
        b_only = int((~piv["qwen_v32_prompt"] & piv[b]).sum())
        p = float(stats.binomtest(a_only, a_only + b_only, 0.5).pvalue) if a_only + b_only else 1.0
        tests[f"qwen_v32_prompt vs {b}"] = {"v32_only_correct": a_only, "other_only_correct": b_only, "mcnemar_exact_p": p}
    out = {"prompt_version": PROMPT_VERSION, "model": recs[0].get("model"), "revision": recs[0].get("revision"),
           "gpu": recs[0].get("gpu"), "score": score, "tests": tests,
           "note": "team-written evaluation set (50 items), not independent users"}
    run.save("mandate_eval_v2.json", out)
    run.save("mandate_eval_v2_rows.csv", df.drop(columns=["raw"]))
    run.save("mandate_eval_v2_raw.json", df[["item", "arm", "raw"]].to_dict("records"))
    return out


# ================================================================== 3b. circuit design
def _table_row(name: str, c: dict, res: dict) -> dict:
    keep = {k: v for k, v in c.items() if k != "rationale_en"}
    r = res.get(name, {})
    return {"name": name, **keep, **({"rejected": r["rejected"]} if "rejected" in r else
                                    {k: round(r[k], 4) if isinstance(r[k], float) else r[k]
                                     for k in ("mean_success", "feasible_mass", "evaluations", "two_qubit_gates")})}


def run_circuits(run, client, eval_fn, md, frozen_specs: dict) -> dict:
    """Two LLM rounds + random search on the design set, then the holdout comparison."""
    from .circuit_llm import N_CANDIDATES, PROMPT_VERSION, design_instances, random_candidate, request, summarise, validate
    from .instances import specs as instance_specs

    design = design_instances(md)

    def evaluate(specs: dict[str, dict], instances: list[dict]) -> list[dict]:
        jobs = [{"instances": [s], "specs": specs, "shots": 512, "seed": 7} for s in instances]
        return [r for part in eval_fn(jobs) for r in part]

    llm_specs, cands, rejected, history = {}, {}, {}, []
    for rnd in (1, 2):
        rec = client.generate([request(rnd, history, seed=rnd)])[0]
        props = (rec["parsed"] or {}).get("candidates", []) if rec["status"] == "ok" else []
        run.log(f"round {rnd}: LLM status {rec['status']}, {len(props)} candidates")
        names = []
        for i, c in enumerate(props):
            name = f"llm_r{rnd}_c{i + 1}"
            spec, errs = validate(c)
            cands[name] = c
            if errs:
                rejected[name] = errs
            else:
                llm_specs[name] = spec.to_dict()
                names.append(name)
        rows = evaluate({n: llm_specs[n] for n in names}, design) if names else []
        res = summarise(rows, names) | {n: {"rejected": e} for n, e in rejected.items() if n.startswith(f"llm_r{rnd}")}
        history = [_table_row(n, cands[n], res) for n in cands if n.startswith(f"llm_r{rnd}")]
        run.save(f"round{rnd}.json", {"request_user": rec.get("user"), "status": rec["status"], "candidates": cands,
                                      "results": res, "rejected": rejected})
        run.step(f"llm_round_{rnd}", valid=len(names), rejected=sum(n.startswith(f"llm_r{rnd}") for n in rejected),
                 best=max([v["mean_success"] for v in res.values() if "mean_success" in v], default=None))
    # random search: same space, same budget (16 evaluated candidates), 3 seeds
    rnd_specs = {}
    for seed in (0, 1, 2):
        g = np.random.default_rng(1000 + seed)
        for i in range(2 * N_CANDIDATES):
            rnd_specs[f"random_s{seed}_c{i + 1}"] = random_candidate(g).to_dict()
    rrows = evaluate(rnd_specs, design)
    rres = summarise(rrows, list(rnd_specs))
    design_scores = {}
    for rnd in (1, 2):
        design_scores |= json.loads((run.dir / f"round{rnd}.json").read_text())["results"]
    design_scores |= rres
    run.save("design_scores.json", design_scores)
    ok = lambda prefix: {n: v for n, v in design_scores.items() if n.startswith(prefix) and "mean_success" in v}
    pick = lambda d: max(d, key=lambda n: (round(d[n]["mean_success"], 6), -d[n]["two_qubit_gates"])) if d else None
    best_llm = pick(ok("llm_"))
    best_rnd = {s: pick(ok(f"random_s{s}_")) for s in (0, 1, 2)}
    run.step("design_selection", best_llm=best_llm, best_llm_score=design_scores.get(best_llm, {}).get("mean_success"),
             **{f"best_random_s{s}": n for s, n in best_rnd.items()})

    # holdout (examined once)
    final = {"llm_best": llm_specs[best_llm]} if best_llm else {}
    final |= {f"random_best_s{s}": rnd_specs[n] for s, n in best_rnd.items() if n}
    final |= frozen_specs
    hold = instance_specs(md, splits=("holdout",))
    hrows = evaluate(final, hold)
    hdf = pd.DataFrame(hrows)
    run.save("holdout_rows.csv", hdf)
    bad = hdf[hdf.errors.map(bool)] if "errors" in hdf else hdf.iloc[:0]
    good = hdf[~hdf.index.isin(bad.index)]
    pdd = good.pivot_table(index="date", columns="spec", values="success_prob")
    if all(f"random_best_s{s}" in pdd for s in (0, 1, 2)):
        pdd["random_best_mean"] = pdd[[f"random_best_s{s}" for s in (0, 1, 2)]].mean(1)
    tests = {}
    if "llm_best" in pdd:
        for b in [c for c in pdd.columns if c != "llm_best"]:
            d = pdd["llm_best"] - pdd[b]
            alt = "greater" if b == "random_best_mean" else "two-sided"
            tests[f"llm_best vs {b}"] = {"diff_pp": float(100 * d.mean()), "wins": int((d > 0).sum()), "n_dates": len(d),
                                         "wilcoxon_p": float(stats.wilcoxon(d, alternative=alt).pvalue), "alternative": alt}
    summ = good.groupby("spec").agg(success=("success_prob", "mean"), feasible_mass=("feasible_mass", "mean"),
                                    evaluations=("evaluations", "mean"), two_qubit_gates=("two_qubit_gates", "mean"),
                                    seconds=("seconds", "mean"))
    out = {"prompt_version": PROMPT_VERSION, "best_llm": best_llm, "best_llm_spec": llm_specs.get(best_llm),
           "best_llm_rationale": cands.get(best_llm, {}).get("rationale_en"), "best_random": best_rnd,
           "llm_valid": len(llm_specs), "llm_rejected": rejected, "holdout_summary": summ.reset_index().to_dict("records"),
           "holdout_tests": tests, "holdout_errors": len(bad)}
    run.save("circuit_llm.json", out)
    return out
