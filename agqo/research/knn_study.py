"""k-NN schedule selection as a standalone study (protocol §4).

Input: a `knn-table` run (meta.csv + success_table.npz): exact success of each of the 1,080 grid schedules on
every calibration / validation / holdout / main-test instance. This module only reads that table; it simulates
nothing. Selectors are fitted on calibration rows, compared on validation rows, and the chosen variant is
evaluated once on the holdout rows.

Arms on the same table
  frozen            schedule with the best mean calibration success
  stratum_frozen    best mean schedule per account size (calibration)
  knn_v3            main-study configuration: five features, z-score, Euclidean, uniform weights, k = 10, mean
  knn_selected      best variant on validation (search space of the protocol)
  knn_selected_fb   the same with the support fallback to frozen
  random_grid       expected success of a uniformly random admissible schedule
  best_of_B         best of B random schedules chosen on calibration (B = 24, 108), averaged over 200 draws
  oracle            best schedule of each target instance (upper bound)
  warm_start        the warm-start product state alone (epsilon of the frozen schedule), no circuit layers
"""

from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

V3 = ["warm_confidence", "decided_share", "log_field_to_coupling", "coupling_concentration", "lot_weight_pct"]
EXT = V3 + ["log_capital", "n_qubits", "has_cap", "has_exclusion"]
FEATURE_SETS = {"v3": V3, "ext": EXT}


@dataclass(frozen=True)
class Variant:
    features: str = "v3"
    scaling: str = "zscore"          # zscore | robust | rank
    distance: str = "euclid"         # euclid | manhattan | cosine
    weighting: str = "uniform"       # uniform | inverse | gaussian
    k: int = 10
    aggregation: str = "mean"        # mean | rank | shrunk
    fallback: bool = False

    def simplicity(self) -> tuple:
        """Smaller = simpler (tie-break of the protocol)."""
        return (len(FEATURE_SETS[self.features]), ["uniform", "inverse", "gaussian"].index(self.weighting), -self.k,
                ["mean", "shrunk", "rank"].index(self.aggregation), int(self.fallback),
                ["zscore", "robust", "rank"].index(self.scaling), ["euclid", "manhattan", "cosine"].index(self.distance))

    def label(self) -> str:
        return (f"{self.features}/{self.scaling}/{self.distance}/{self.weighting}/k={self.k}/{self.aggregation}"
                f"{'/fallback' if self.fallback else ''}")


VARIANTS = [Variant(*v) for v in itertools.product(
    ["v3", "ext"], ["zscore", "robust", "rank"], ["euclid", "manhattan", "cosine"], ["uniform", "inverse", "gaussian"],
    [3, 5, 10, 20, 40], ["mean", "rank", "shrunk"], [False, True])]
V3_VARIANT = Variant("v3", "zscore", "euclid", "uniform", 10, "mean", False)
_CACHE: dict = {}


# ------------------------------------------------------------------ data
@dataclass
class Table:
    meta: pd.DataFrame
    S: np.ndarray            # success, NaN where the schedule is over the two-qubit-gate budget
    cx: np.ndarray

    @classmethod
    def load(cls, run_dir: Path, cx_budget: int = 1500) -> "Table":
        meta = pd.read_csv(run_dir / "meta.csv")
        z = np.load(run_dir / "success_table.npz")
        S = z["success"].astype(float)
        S[(S < 0) | (z["cx"] > cx_budget)] = np.nan
        return cls(meta, S, z["cx"])

    def idx(self, split: str) -> np.ndarray:
        return np.flatnonzero(self.meta.split.to_numpy() == split)

    def X(self, rows, feats) -> np.ndarray:
        return self.meta.iloc[rows][[f"f_{f}" for f in feats]].to_numpy(float)


# ------------------------------------------------------------------ selectors
def _scale(Xc: np.ndarray, Xt: np.ndarray, how: str) -> tuple[np.ndarray, np.ndarray]:
    if how == "zscore":
        mu, sd = Xc.mean(0), Xc.std(0)
    elif how == "robust":
        mu = np.median(Xc, 0)
        sd = np.subtract(*np.percentile(Xc, [75, 25], axis=0))
    else:                                                   # empirical CDF of the calibration values
        srt = np.sort(Xc, 0)
        cdf = lambda X: np.column_stack([np.searchsorted(srt[:, j], X[:, j], side="right") / len(srt)
                                         for j in range(X.shape[1])])
        return cdf(Xc), cdf(Xt)
    sd = np.where(sd > 1e-12, sd, 1.0)
    return (Xc - mu) / sd, (Xt - mu) / sd


def _dist(Zc: np.ndarray, Zt: np.ndarray, how: str) -> np.ndarray:
    if how == "euclid":
        return np.sqrt(((Zt[:, None, :] - Zc[None]) ** 2).sum(-1))
    if how == "manhattan":
        return np.abs(Zt[:, None, :] - Zc[None]).sum(-1)
    nc = Zc / np.maximum(np.linalg.norm(Zc, axis=1, keepdims=True), 1e-12)
    nt = Zt / np.maximum(np.linalg.norm(Zt, axis=1, keepdims=True), 1e-12)
    return 1 - nt @ nc.T


def _wmean(W: np.ndarray, V: np.ndarray) -> np.ndarray:
    """Weighted mean over neighbours ignoring NaN: W (n_t, k), V (n_t, k, G) -> (n_t, G)."""
    m = ~np.isnan(V)
    num = np.einsum("tk,tkg->tg", W, np.where(m, V, 0.0))
    den = np.einsum("tk,tkg->tg", W, m.astype(float))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def _ranks(S: np.ndarray) -> np.ndarray:
    """Per-row percentile rank of each admissible schedule (NaN stays NaN)."""
    out = np.full_like(S, np.nan)
    for i, row in enumerate(S):
        ok = ~np.isnan(row)
        out[i, ok] = stats.rankdata(row[ok]) / ok.sum()
    return out


def frozen_choice(S_cal: np.ndarray) -> int:
    return int(np.nanargmax(np.nanmean(S_cal, 0)))


def _argmax_admissible(score: np.ndarray, S_target: np.ndarray) -> np.ndarray:
    """Pick the best-scored schedule among those admissible on each target (budget known before running)."""
    sc = np.where(np.isnan(S_target), -np.inf, np.where(np.isnan(score), -np.inf, score))
    return sc.argmax(1)


def knn_choose(t: Table, cal, tgt, v: Variant, tau: float | None = None, return_dist: bool = False):
    feats = FEATURE_SETS[v.features]
    Zc, Zt = _scale(t.X(cal, feats), t.X(tgt, feats), v.scaling)
    D = _dist(Zc, Zt, v.distance)
    k = min(v.k, len(cal))
    nn = np.argsort(D, 1)[:, :k]
    dk = np.take_along_axis(D, nn, 1)
    if v.weighting == "uniform":
        W = np.ones_like(dk)
    elif v.weighting == "inverse":
        W = 1 / np.maximum(dk, 1e-6)
    else:
        h = max(float(np.median(D)), 1e-6)
        W = np.exp(-(dk / h) ** 2)
    S_cal = t.S[cal]
    if v.aggregation == "rank":
        key = ("ranks", tuple(cal[:3]), len(cal))
        if key not in _CACHE:
            _CACHE[key] = _ranks(S_cal)
        V = _CACHE[key][nn]
    else:
        V = S_cal[nn]
    score = _wmean(W, V)
    if v.aggregation == "shrunk":
        score = 0.5 * score + 0.5 * np.nanmean(S_cal, 0)[None]
    choice = _argmax_admissible(score, t.S[tgt])
    if v.fallback and tau is not None:
        fz = _argmax_admissible(np.nanmean(S_cal, 0)[None].repeat(len(tgt), 0), t.S[tgt])
        far = dk[:, 0] > tau
        choice = np.where(far, fz, choice)
    return (choice, dk[:, 0]) if return_dist else choice


def support_threshold(t: Table, cal, val, v: Variant) -> float:
    """90th percentile of validation nearest-neighbour distances (protocol §4, K4)."""
    _, d = knn_choose(t, cal, val, Variant(**(asdict(v) | {"fallback": False})), return_dist=True)
    return float(np.percentile(d, 90))


# ------------------------------------------------------------------ evaluation helpers
def realised(t: Table, tgt, choice) -> np.ndarray:
    return t.S[tgt, choice]


def per_date(t: Table, tgt, values: np.ndarray) -> pd.Series:
    return pd.Series(values, index=t.meta.date.iloc[tgt].to_numpy()).groupby(level=0).mean()


def paired(a: pd.Series, b: pd.Series, alternative: str = "greater", boot: int = 10000, seed: int = 0) -> dict:
    d = (a - b).to_numpy()
    rng = np.random.default_rng(seed)
    bs = rng.choice(d, size=(boot, len(d)), replace=True).mean(1)
    try:
        p = float(stats.wilcoxon(d, alternative=alternative, zero_method="zsplit").pvalue)
    except ValueError:
        p = float("nan")
    return {"n_dates": len(d), "mean_a": float(a.mean()), "mean_b": float(b.mean()), "diff_pp": float(100 * d.mean()),
            "ci95_pp": [float(100 * np.percentile(bs, 2.5)), float(100 * np.percentile(bs, 97.5))],
            "wins": int((d > 0).sum()), "losses": int((d < 0).sum()), "wilcoxon_p": p, "alternative": alternative}


def arms_on(t: Table, cal, tgt, selected: Variant, tau: float, seed: int = 0) -> dict[str, np.ndarray]:
    """Realised success of every arm on the target rows."""
    S_cal, S_t = t.S[cal], t.S[tgt]
    fz = frozen_choice(S_cal)
    out = {"frozen": np.where(np.isnan(S_t[:, fz]), np.nan, S_t[:, fz])}
    caps = t.meta.capital_vnd.to_numpy()
    strat = np.empty(len(tgt), int)
    for c in np.unique(caps[tgt]):
        rows = cal[caps[cal] == c]
        strat[caps[tgt] == c] = frozen_choice(t.S[rows]) if len(rows) else fz
    out["stratum_frozen"] = S_t[np.arange(len(tgt)), strat]
    out["knn_v3"] = realised(t, tgt, knn_choose(t, cal, tgt, V3_VARIANT))
    out["knn_selected"] = realised(t, tgt, knn_choose(t, cal, tgt, selected, tau))          # exactly as chosen
    out["knn_selected_nofb"] = realised(t, tgt, knn_choose(t, cal, tgt, Variant(**(asdict(selected) | {"fallback": False}))))
    out["knn_selected_fb"] = realised(t, tgt, knn_choose(t, cal, tgt, Variant(**(asdict(selected) | {"fallback": True})), tau))
    out["random_grid"] = np.nanmean(S_t, 1)
    rng = np.random.default_rng(seed)
    G = t.S.shape[1]
    for B in (24, 108):
        acc = np.zeros(len(tgt))
        for _ in range(200):
            pick = rng.choice(G, size=B, replace=False)
            j = pick[np.nanargmax(np.nanmean(S_cal[:, pick], 0))]
            acc += np.nan_to_num(S_t[:, j], nan=0.0)
        out[f"best_of_{B}"] = acc / 200
    out["oracle"] = np.nanmax(S_t, 1)
    eps = 0.02
    out["warm_start"] = t.meta.iloc[tgt][f"warm_{eps}"].to_numpy(float) if f"warm_{eps}" in t.meta else np.full(len(tgt), np.nan)
    return out


# ------------------------------------------------------------------ K1 diagnosis
def diagnose(t: Table, cal, val) -> dict:
    S = t.S[cal]
    srt = -np.sort(-np.nan_to_num(S, nan=-1), 1)
    top_spread = srt[:, 0] - srt[:, 9]
    near_best = (np.nan_to_num(S, nan=-1) >= 0.9 * srt[:, :1]).sum(1)
    # winner's curse: in-sample estimate of the chosen schedule vs realised success (validation)
    out = {"calibration_top1_minus_top10_pp": float(100 * top_spread.mean()),
           "calibration_schedules_within_90pct_of_best": float(near_best.mean()),
           "schedules_admissible": int((~np.isnan(S)).all(0).sum())}
    for name, v in (("knn_v3", V3_VARIANT), ("knn_3", Variant(k=3)), ("knn_40", Variant(k=40))):
        feats = FEATURE_SETS[v.features]
        Zc, Zt = _scale(t.X(cal, feats), t.X(val, feats), v.scaling)
        nn = np.argsort(_dist(Zc, Zt, v.distance), 1)[:, :v.k]
        score = _wmean(np.ones(nn.shape), t.S[cal][nn])
        ch = _argmax_admissible(score, t.S[val])
        est = score[np.arange(len(val)), ch]
        real = t.S[val, ch]
        out[f"{name}_in_sample_estimate"] = float(np.nanmean(est))
        out[f"{name}_realised"] = float(np.nanmean(real))
    fz = frozen_choice(S)
    out["frozen_in_sample_estimate"] = float(np.nanmean(S[:, fz]))
    out["frozen_realised"] = float(np.nanmean(t.S[val, fz]))
    # do feature distances predict which schedules work? (calibration pairs)
    Z, _ = _scale(t.X(cal, V3), t.X(cal, V3), "zscore")
    D = _dist(Z, Z, "euclid")
    P = np.ma.corrcoef(np.ma.masked_invalid(S))
    iu = np.triu_indices(len(cal), 1)
    rho = stats.spearmanr(D[iu], 1 - np.asarray(P)[iu], nan_policy="omit")
    out["spearman_feature_distance_vs_profile_dissimilarity"] = float(rho.statistic)
    # nearest-neighbour transfer: success of the nearest calibration neighbour's best schedule, as a share of own best
    nn1 = np.argsort(_dist(*_scale(t.X(cal, V3), t.X(val, V3), "zscore"), "euclid"), 1)[:, 0]
    best_nb = np.nanargmax(np.nan_to_num(t.S[cal], nan=-1), 1)[nn1]
    out["nn1_transfer_share_of_own_best"] = float(np.nanmean(t.S[val, best_nb] / np.nanmax(t.S[val], 1)))
    out["frozen_share_of_own_best_validation"] = float(np.nanmean(t.S[val, fz] / np.nanmax(t.S[val], 1)))
    out["oracle_minus_frozen_validation_pp"] = float(100 * (np.nanmean(np.nanmax(t.S[val], 1)) - np.nanmean(t.S[val, fz])))
    return out


# ------------------------------------------------------------------ the study
def run_study(table_dir: Path, run) -> dict:
    t = Table.load(table_dir)
    cal, val, hold, v3t = t.idx("calibration"), t.idx("validation"), t.idx("holdout"), t.idx("v3_test")
    run.log(f"table: calibration {len(cal)}, validation {len(val)}, holdout {len(hold)}, v3_test {len(v3t)}")

    # stage 1: diagnosis (calibration + validation only)
    diag = diagnose(t, cal, val)
    run.save("k1_diagnosis.json", diag)
    run.step("k1_diagnosis", **{k: round(v, 4) if isinstance(v, float) else v for k, v in diag.items()})

    # stage 2: variant search on validation only
    fz_val = per_date(t, val, realised(t, val, np.full(len(val), frozen_choice(t.S[cal]))))
    rows = []
    tau_cache = {}
    for v in VARIANTS:
        key = (v.features, v.scaling, v.distance, v.weighting, v.k, v.aggregation)
        if v.fallback and key not in tau_cache:
            tau_cache[key] = support_threshold(t, cal, val, v)
        ch = knn_choose(t, cal, val, v, tau_cache.get(key))
        pdv = per_date(t, val, realised(t, val, ch))
        rows.append(asdict(v) | {"label": v.label(), "val_success": float(pdv.mean()),
                                 "val_minus_frozen_pp": float(100 * (pdv.mean() - fz_val.mean()))})
    vs = pd.DataFrame(rows)
    vs["simplicity"] = [v.simplicity() for v in VARIANTS]
    best = vs.val_success.max()
    tied = vs[vs.val_success >= best - 1e-12].sort_values("simplicity")
    sel = VARIANTS[int(tied.index[0])]
    sel_nofb = Variant(**(asdict(sel) | {"fallback": False}))
    tau = support_threshold(t, cal, val, sel_nofb)
    run.save("validation_search.csv", vs.drop(columns="simplicity").sort_values("val_success", ascending=False))
    selection = {"selected": asdict(sel), "label": sel.label(), "val_success": float(best),
                 "val_frozen": float(fz_val.mean()), "support_threshold": tau, "n_variants": len(VARIANTS),
                 "n_tied_at_best": int(len(tied))}
    run.save("selection.json", selection)
    run.step("validation_selection", label=sel.label(), val_success=round(best, 4), val_frozen=round(float(fz_val.mean()), 4))

    # stage 3: holdout, examined once
    res = {}
    for split, tgt in (("holdout", hold), ("v3_test", v3t)):
        A = arms_on(t, cal, tgt, sel, tau)
        pdd = {k: per_date(t, tgt, v) for k, v in A.items()}
        summary = {k: {"mean_success": float(s.mean()), "per_date_sd": float(s.std())} for k, s in pdd.items()}
        tests = {"K2 knn_selected vs frozen": paired(pdd["knn_selected"], pdd["frozen"]),
                 "knn_v3 vs frozen": paired(pdd["knn_v3"], pdd["frozen"], "two-sided"),
                 "K4 knn_selected_fb vs frozen (non-inferiority, margin 0.5pp)": paired(pdd["knn_selected_fb"], pdd["frozen"], "two-sided"),
                 "stratum_frozen vs frozen": paired(pdd["stratum_frozen"], pdd["frozen"], "two-sided"),
                 "knn_selected vs stratum_frozen": paired(pdd["knn_selected"], pdd["stratum_frozen"], "two-sided"),
                 "knn_v3 vs stratum_frozen": paired(pdd["knn_v3"], pdd["stratum_frozen"], "two-sided"),
                 "frozen vs best_of_24": paired(pdd["frozen"], pdd["best_of_24"]),
                 "frozen vs random_grid": paired(pdd["frozen"], pdd["random_grid"]),
                 "oracle vs frozen": paired(pdd["oracle"], pdd["frozen"])}
        k4 = tests["K4 knn_selected_fb vs frozen (non-inferiority, margin 0.5pp)"]
        k4["non_inferior"] = bool(k4["ci95_pp"][0] > -0.5)
        # K3 strata
        m = t.meta.iloc[tgt]
        strata = []
        for col in ("capital_vnd", "constraint"):
            for val_ in sorted(m[col].unique()):
                mask = (m[col] == val_).to_numpy()
                a = per_date(t, tgt[mask], A["knn_selected"][mask])
                b = per_date(t, tgt[mask], A["frozen"][mask])
                strata.append({"by": col, "value": val_, "knn_selected": float(a.mean()), "frozen": float(b.mean()),
                               "diff_pp": float(100 * (a.mean() - b.mean()))})
        st = pd.DataFrame(strata)
        k3 = {"sizes_positive": int((st[st.by == "capital_vnd"].diff_pp > 0).sum()),
              "constraints_positive": int((st[st.by == "constraint"].diff_pp > 0).sum())}
        k3["persists"] = bool(k3["sizes_positive"] >= 4 and k3["constraints_positive"] == 3)
        # cost: two-qubit gates of the chosen schedules
        cx = {"frozen": float(np.mean(t.cx[tgt, frozen_choice(t.S[cal])])),
              "knn_selected": float(np.mean(t.cx[tgt, knn_choose(t, cal, tgt, sel, tau)]))}
        sec_per_circuit = float((m.sim_seconds / (~np.isnan(t.S[tgt])).sum(1)).mean())
        res[split] = {"arms": summary, "tests": tests, "K3": k3, "strata": strata, "two_qubit_gates_mean": cx,
                      "seconds_per_circuit_evaluation": sec_per_circuit}
        run.save(f"{split}_per_date.csv", pd.DataFrame(pdd).reset_index(names="date"))
        run.save(f"{split}_strata.csv", st)
        run.step(split, knn_selected=round(summary["knn_selected"]["mean_success"], 4),
                 frozen=round(summary["frozen"]["mean_success"], 4), oracle=round(summary["oracle"]["mean_success"], 4),
                 K2_p=round(tests["K2 knn_selected vs frozen"]["wilcoxon_p"], 4))
    run.save("holdout_results.json", res)
    # per-instance choices for the refinement ablation (Modal job): frozen and selected schedule per holdout row
    fz = frozen_choice(t.S[cal])
    ch = knn_choose(t, cal, hold, sel, tau)
    ch3 = knn_choose(t, cal, hold, V3_VARIANT)
    plan = [{"split": "holdout", "date": r.date, "capital_vnd": float(r.capital_vnd), "constraint": r.constraint,
             "frozen_schedule": int(fz), "knn_schedule": int(c), "knn_v3_schedule": int(c3)}
            for r, c, c3 in zip(t.meta.iloc[hold].itertuples(), ch, ch3)]
    run.save("refine_plan.json", plan)
    return {"diagnosis": diag, "selection": selection, "results": res}
