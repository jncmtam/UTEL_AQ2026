"""Vietnamese figures for the contest submission (slides: dark theme, report: light theme).

    python -m agqo.figures_vi            # writes docs/figures_vi/{dark,light}/*.png

Every figure reads the frozen results in results/final; nothing is re-estimated. Figures carry no
title: the slide or the report gives the title and the caption underneath.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from .config import RESULTS_DIR, ROOT

THEMES = {
    "dark": {"bg": "#0b1220", "ink": "#e6edf7", "muted": "#8b9ab3", "grid": "#1e2b44", "panel": "#111a2e",
             "agqo": "#38bdf8", "near": "#ef4444", "greedy": "#f59e0b", "warm": "#34d399", "text": "#a78bfa",
             "rand": "#64748b", "ideal": "#94a3b8", "up": "#22c55e", "ai": "#38bdf8", "q": "#a78bfa", "cl": "#34d399",
             "data": "#94a3b8", "accent": "#facc15"},
    "light": {"bg": "#ffffff", "ink": "#111827", "muted": "#6b7280", "grid": "#e5e7eb", "panel": "#f8fafc",
              "agqo": "#0284c7", "near": "#dc2626", "greedy": "#d97706", "warm": "#059669", "text": "#7c3aed",
              "rand": "#9ca3af", "ideal": "#9ca3af", "up": "#16a34a", "ai": "#0284c7", "q": "#7c3aed", "cl": "#059669",
              "data": "#6b7280", "accent": "#ca8a04"},
}
SECTOR_VI = {"Banking": "Ngân hàng", "Insurance": "Bảo hiểm", "Technology": "Công nghệ", "Energy": "Năng lượng",
             "Materials": "Nguyên vật liệu", "Real estate": "Bất động sản", "Consumer": "Tiêu dùng",
             "Brokerage": "Chứng khoán", "Aviation": "Hàng không"}
BINS = ["optimal", "within 5%", "5–25%", "25–100%", "worse than typical", "over budget"]
BIN_VI = ["tối ưu", "trong 5%", "5–25%", "25–100%", "tệ hơn trung bình", "vượt ngân sách"]


FS = 1.0          # figure-size scale: the report (light theme) uses smaller canvases, i.e. relatively larger text


def _fs(w, h):
    return (w * FS, h * FS)


def _style(T: dict) -> None:
    plt.rcParams.update({
        "font.family": ["Arial", "DejaVu Sans"], "font.size": 11, "figure.facecolor": T["bg"], "axes.facecolor": T["bg"],
        "savefig.facecolor": T["bg"], "axes.edgecolor": T["grid"], "axes.labelcolor": T["muted"], "text.color": T["ink"],
        "xtick.color": T["muted"], "ytick.color": T["muted"], "axes.grid": True, "grid.color": T["grid"],
        "grid.linewidth": 0.7, "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
        "legend.labelcolor": T["ink"], "axes.axisbelow": True})


def _save(fig, path: Path) -> str:
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path.name


def _pct(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


# ------------------------------------------------------------------ figures
def lot_cost(T, out, run, md, ec):
    d = md.rebalance_dates(ec.test_start, ec.test_end)[-1]
    uni, _ = md.universe(d, ec.problem.lookback_days, ec.problem.min_history)
    px = md.px.loc[d, uni]
    pct = (100 * 100 * px / 20e6).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=_fs(12, 4.6))
    cols = [T["near"] if v > 100 else T["greedy"] if v > 10 else T["up"] for v in pct]
    ax.bar(pct.index, pct.values, color=cols, width=0.7)
    for y, lab, c in [(100, "toàn bộ tài khoản", T["near"]), (10, "10% tài khoản", T["greedy"])]:
        ax.axhline(y, color=c, linestyle="--", linewidth=1.2)
        ax.text(len(pct) - 0.5, y * 1.12, lab, color=c, ha="right", fontsize=10)
    ax.set_yscale("log")
    ax.set_yticks([1, 3, 10, 30, 100], ["1%", "3%", "10%", "30%", "100%"])
    ax.set_ylabel("giá 1 lô / 20 triệu đồng")
    ax.tick_params(axis="x", rotation=60, labelsize=9.5)
    ax.grid(axis="x", visible=False)
    for i, (t, v) in enumerate(pct.items()):
        if v > 10 and (i % 2 == 0 or v > 60):
            ax.text(i, v * 1.08, f"{v:.0f}%", ha="center", fontsize=8, color=T["ink"])
    return _save(fig, out / "01_lot_cost.png"), {"date": str(d.date()), "over10": int((pct > 10).sum()),
                                                 "over100": int((pct > 100).sum()), "max": float(pct.max()),
                                                 "max_ticker": pct.index[0], "min": float(pct.min())}


def _box(ax, x, y, w, h, title, body, c, T):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15", facecolor=T["panel"],
                                edgecolor=c, linewidth=2))
    ax.text(x + w / 2, y + h - 0.32, title, ha="center", va="top", fontsize=12.5, weight="bold", color=c)
    ax.text(x + w / 2, y + h - 0.82, body, ha="center", va="top", fontsize=9.6, color=T["ink"], linespacing=1.35)


def _arrow(ax, a, b, T, text=None):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=16, color=T["muted"], linewidth=1.6))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.14, text, ha="center", fontsize=8.8, color=T["muted"], style="italic")


def pipeline(T, out):
    fig, ax = plt.subplots(figsize=(15, 6.6))
    ax.set_xlim(0, 16.2)
    ax.set_ylim(0.1, 7.8)
    ax.axis("off")
    W, H = 2.95, 1.85
    _box(ax, 0.15, 5.8, W, H, "Dữ liệu thị trường", "OHLCV ngày 2022–2026 (DNSE)\n40 mã từng thuộc VN30\nthành phần theo thời điểm\nVN30, VN-Index, 3 ETF", T["data"], T)
    _box(ax, 0.15, 1.3, W, H, "Nhà đầu tư", "“Không mua bất động sản,\nngân hàng tối đa 30%”\nsố vốn, danh mục hiện có", T["data"], T)
    _box(ax, 3.65, 5.8, W, H, "1a · AI đọc thị trường", "tương quan, nhân tố thị trường\nsố cược độc lập, cụm mã\ngiá lô, chi phí làm tròn\n(thống kê)", T["ai"], T)
    _box(ax, 3.65, 1.3, W, H, "1b · LLM dịch yêu cầu", "Qwen3.8-27B · vLLM · H100\nđầu ra JSON theo lược đồ\nloại mã/ngành, trần, số mã,\ntiền mặt → mã nguồn kiểm tra", T["ai"], T)
    _box(ax, 7.15, 3.55, W, H, "Bài toán lô chẵn", "QP liên tục có trần\n→ thanh ghi 16 qubit an toàn\nQUBO = sai số bám² +\nvòng quay + ngân sách", T["cl"], T)
    _box(ax, 7.15, 5.8, W, H, "2a · Đặc trưng bài toán", "nghiệm nới lỏng x*\nnguồn & khối lượng tương tác\nthang RMS năng lượng\n5 đặc trưng mỗi quý", T["ai"], T)
    _box(ax, 10.65, 5.8, W, H, "2b · AI dẫn dắt mạch", "mô hình k-NN học trên\n48 bài toán năm 2023\nchọn p, ε, khối lượng, Δγ, Δβ\ntừ 1.080 lịch ứng viên", T["ai"], T)
    _box(ax, 10.65, 3.55, W, H, "Mạch QAOA", "R1 khởi động ấm · R2 trộn căn chỉnh\nR3 tỉa tương tác · R4 thang RMS\nR5 dốc tuyến tính · 512 lần đo\nmô phỏng / Qiskit / IBM", T["q"], T)
    _box(ax, 10.65, 1.3, W, H, "Kiểm chứng chính xác", "tiền, phí, thuế, trần từng mẫu\nliệt kê đủ 2^16 tổ hợp\n→ quyết định tốt nhất\nđủ tiền, đúng quy tắc", T["cl"], T)
    _box(ax, 14.05, 3.55, 2.05, H, "Lệnh", "danh sách lệnh\ntheo lô chẵn,\nphí và thuế", T["data"], T)
    _box(ax, 14.05, 1.3, 2.05, H, "LLM giải thích", "tiếng Việt,\nmọi con số\nđược đối chiếu", T["ai"], T)
    _arrow(ax, (3.1, 6.72), (3.65, 6.72), T)
    _arrow(ax, (3.1, 2.22), (3.65, 2.22), T)
    _arrow(ax, (6.6, 6.1), (7.15, 4.85), T, "trọng số, rủi ro")
    _arrow(ax, (6.6, 2.4), (7.15, 4.0), T, "ràng buộc")
    _arrow(ax, (8.62, 5.4), (8.62, 5.8), T)
    _arrow(ax, (10.1, 6.72), (10.65, 6.72), T, "đặc trưng")
    _arrow(ax, (12.12, 5.8), (12.12, 5.4), T, "lịch mạch")
    _arrow(ax, (10.1, 4.45), (10.65, 4.45), T, "Hamiltonian")
    _arrow(ax, (12.12, 3.55), (12.12, 3.15), T, "mẫu đo")
    _arrow(ax, (13.6, 2.5), (14.05, 4.1), T, "quyết định")
    _arrow(ax, (15.07, 3.55), (15.07, 3.15), T)
    for c, lab, x in [(T["ai"], "AI (thống kê, mô hình học, LLM)", 0.3), (T["q"], "lượng tử", 4.6),
                      (T["cl"], "cổ điển, tính chính xác", 6.3), (T["data"], "dữ liệu và đầu ra", 9.0)]:
        ax.add_patch(FancyBboxPatch((x, 0.3), 0.35, 0.3, boxstyle="round,pad=0.02", facecolor=T["panel"], edgecolor=c, linewidth=2))
        ax.text(x + 0.5, 0.45, lab, va="center", fontsize=10, color=T["ink"])
    return _save(fig, out / "02_pipeline.png")


def market(T, out, run):
    ins = pd.DataFrame(json.loads((run / "insight.json").read_text()))
    q = [d[:7] for d in ins.date]
    fig, a1 = plt.subplots(figsize=_fs(11, 4.2))
    a1.bar(q, ins.effective_bets, color=T["ai"], width=0.6, label="số “cược” độc lập (trên ~30 mã)")
    a1.set_ylabel("số cược độc lập")
    a1.set_ylim(0, 30)
    a1.axhline(30, color=T["muted"], linestyle=":")
    a1.text(0, 28.3, "nếu 30 mã độc lập hoàn toàn", fontsize=9, color=T["muted"])
    a2 = a1.twinx()
    a2.plot(q, 100 * ins.market_factor_share, "o-", color=T["accent"], linewidth=2.4, label="% phương sai do nhân tố thị trường")
    a2.set_ylim(0, 80)
    a2.set_ylabel("% phương sai", color=T["accent"])
    a2.grid(False)
    a2.spines["right"].set_visible(True)
    a1.tick_params(axis="x", rotation=45)
    h1, l1 = a1.get_legend_handles_labels()
    h2, l2 = a2.get_legend_handles_labels()
    a1.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=9.5)
    return _save(fig, out / "03_market.png"), {"bets": float(ins.effective_bets.mean()),
                                               "factor": float(100 * ins.market_factor_share.mean())}


def hamiltonian(T, out, run):
    ex = json.loads((run / "extras" / "examples.json").read_text())["20000000"]
    reg = ex["register"]
    J = np.array(ex["J"])
    h = np.array(ex["h"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=_fs(13, 5.4), gridspec_kw={"width_ratios": [1.15, 1]})
    m = np.abs(J).max()
    Jd = J.copy()
    np.fill_diagonal(Jd, 0.0)
    im = a1.imshow(Jd / m, cmap="RdBu_r", vmin=-1, vmax=1)
    a1.set_xticks(range(len(reg)), reg, rotation=70, fontsize=9)
    a1.set_yticks(range(len(reg)), reg, fontsize=9)
    a1.grid(False)
    cb = fig.colorbar(im, ax=a1, fraction=0.046)
    cb.set_label("J_ij (chuẩn hoá): đỏ = thay thế nhau, xanh = bổ sung nhau", color=T["muted"], fontsize=9)
    cb.ax.tick_params(colors=T["muted"])
    o = np.argsort(-np.abs(h))
    a2.barh(np.array(reg)[o][::-1], (h[o] / np.abs(h).max())[::-1],
            color=[T["near"] if v > 0 else T["agqo"] for v in h[o][::-1]])
    a2.set_xlabel("trường h_i (chuẩn hoá): âm = nên mua thêm lô")
    a2.tick_params(axis="y", labelsize=9)
    return _save(fig, out / "04_hamiltonian.png")


def circuit(T, out, run):
    from .quantum.design import spec_of
    from .quantum.simulator import initial_angles

    ins = json.loads((run / "insight.json").read_text())
    row = ins[-1]["chosen_schedule"]
    spec = spec_of(row)
    a = initial_angles(spec)
    p = spec.layers
    fig = plt.figure(figsize=(14, 5.2))
    ax = fig.add_axes([0.01, 0.02, 0.66, 0.96])
    ax.set_xlim(0, 12.6)
    ax.set_ylim(-0.6, 5.0)
    ax.axis("off")
    qs = ["VIC", "VHM", "FPT", "HPG"]
    ys = [4.0, 3.0, 2.0, 1.0]
    for q, y in zip(qs, ys):
        ax.plot([0.9, 12.4], [y, y], color=T["muted"], linewidth=1)
        ax.text(0.8, y, f"{q}  |0⟩", ha="right", va="center", fontsize=11, color=T["ink"])

    def gate(x, y, w, label, c):
        ax.add_patch(FancyBboxPatch((x, y - 0.3), w, 0.6, boxstyle="round,pad=0.02", facecolor=T["panel"], edgecolor=c, linewidth=1.8))
        ax.text(x + w / 2, y, label, ha="center", va="center", fontsize=10.5, color=T["ink"], weight="bold")

    for y in ys:
        gate(1.1, y, 1.2, "Ry(θ_k)", T["cl"])
    ax.add_patch(FancyBboxPatch((2.7, 0.45), 6.6, 4.1, boxstyle="round,pad=0.02", facecolor="none", edgecolor=T["muted"],
                                linestyle="--", linewidth=1.2))
    for y in ys:
        gate(2.9, y, 1.2, "Rz(2γh_k)", T["q"])
    for x, (i, j) in zip([4.5, 4.95, 5.4, 5.85], [(0, 1), (0, 2), (1, 3), (2, 3)]):
        ax.plot([x, x], [ys[i], ys[j]], color=T["q"], linewidth=2)
        ax.plot([x, x], [ys[i], ys[j]], "o", color=T["q"], markersize=7)
    for y in ys:
        gate(6.4, y, 2.7, "Ry(θ)·Rz(−2β)·Ry(−θ)", T["ai"])
    for y in ys:
        gate(9.7, y, 0.7, "…", T["muted"])
        gate(10.8, y, 1.2, "đo", T["accent"])
    for x, lab, c in [(1.7, "R1 khởi động ấm", T["cl"]), (3.5, "trường h (R4)", T["q"]), (5.2, "ZZ(2γJ_kl) (R3)", T["q"]),
                      (7.75, "R2 bộ trộn căn chỉnh", T["ai"]), (11.4, "512 lần đo", T["accent"])]:
        ax.text(x, 4.75, lab, ha="center", fontsize=10, color=c, weight="bold")
    ax.text(6.0, -0.25, f"một lớp QAOA, lặp p = {p} lần: γ tăng dần, β giảm dần (R5)", ha="center", fontsize=10.5,
            color=T["muted"], style="italic")
    a2 = fig.add_axes([0.72, 0.16, 0.26, 0.74])
    L = np.arange(1, p + 1)
    a2.plot(L, a[:p], "o-", color=T["q"], linewidth=2.6, label="γ (bài toán)")
    a2.plot(L, a[p:], "s-", color=T["ai"], linewidth=2.6, label="β (bộ trộn)")
    a2.set_xlabel("lớp")
    a2.set_xticks(L)
    a2.legend(fontsize=10)
    a2.set_title("lịch góc dốc tuyến tính", fontsize=11, color=T["ink"])
    return _save(fig, out / "05_circuit.png"), {"p": p, "row": row}


def schedules(T, out, run):
    g = pd.read_csv(run / "schedule_grid.csv")
    n_all = len(g)
    g = g[~g.over_budget]                    # schedules over the two-qubit gate budget are never run
    man = json.loads((run / "run_manifest.json").read_text())
    fz = man["frozen_schedule"]
    s = 100 * g.train_success
    fig, ax = plt.subplots(figsize=_fs(11, 4.2))
    ax.hist(s, bins=60, color=T["ai"], alpha=0.85)
    ax.set_xlabel("tỷ lệ lượt đo gần tối ưu trên 48 bài toán huấn luyện 2023 (%)")
    ax.set_ylabel("số lịch mạch")
    best = g[(g.layers == fz["layers"]) & (g.epsilon == fz["epsilon"]) & (g.coupling_mass == fz["coupling_mass"]) &
             (g.dgamma == fz["dgamma"]) & (g.dbeta == fz["dbeta"])].train_success.iloc[0] * 100
    ax.axvline(best, color=T["accent"], linewidth=2.2)
    ax.text(best, ax.get_ylim()[1] * 0.9, f"  lịch tốt nhất trung bình\n  {_pct(best)}%", color=T["accent"], fontsize=10, va="top")
    med = float(np.median(s))
    ax.axvline(med, color=T["muted"], linestyle=":")
    ax.text(med, ax.get_ylim()[1] * 0.55, f" trung vị {_pct(med)}%", color=T["muted"], fontsize=10)
    return _save(fig, out / "06_schedules.png"), {"n": n_all, "in_budget": len(g), "best": best, "median": med}


def prob_flow(T, out, run):
    d = pd.read_csv(run / "extras" / "distributions.csv")
    order = ["random guessing", "warm start only", "textbook QAOA", "AGQO"]
    lab = ["đoán ngẫu nhiên", "khởi động ấm (cổ điển)", "QAOA sách giáo khoa", "AGQO"]
    m = d.groupby("arm")[BINS].mean().reindex(order) * 100
    cols = ["#15803d", "#4ade80", "#a3e635", "#f59e0b", "#ef4444", T["grid"] if T["bg"] != "#ffffff" else "#d1d5db"]
    fig, ax = plt.subplots(figsize=_fs(12, 4.2))
    left = np.zeros(len(m))
    for c, cl, nm in zip(BINS, cols, BIN_VI):
        ax.barh(range(len(m)), m[c], left=left, color=cl, height=0.62, label=nm, edgecolor=T["bg"])
        for i, v in enumerate(m[c]):
            if v > 4:
                ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=9.5,
                        color="white" if cl in ("#15803d", "#ef4444") or nm == "vượt ngân sách" and T["bg"] != "#ffffff" else "#0b1220")
        left += m[c].to_numpy()
    ax.set_yticks(range(len(m)), lab, fontsize=11)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% xác suất đo, trung bình 12 quý kiểm định")
    ax.legend(ncol=6 if FS == 1 else 3, loc="upper center", bbox_to_anchor=(0.5, -0.24), fontsize=9.5)
    ax.grid(False)
    a = m.loc["AGQO"]
    return _save(fig, out / "07_probability.png"), {"agqo_good": float(a["optimal"] + a["within 5%"]),
                                                    "rand_good": float(m.loc["random guessing", "optimal"] + m.loc["random guessing", "within 5%"])}


def quarters(T, out, run):
    q = pd.read_csv(run / "quantum_test.csv")
    q["arm"] = q.arm.str.replace(r"^random_s\d+$", "random", regex=True)
    p = q.pivot_table(index="date", columns="arm", values="success_prob") * 100
    lab = [d[:7] for d in p.index]
    fig, ax = plt.subplots(figsize=_fs(12, 4.3))
    x = np.arange(len(p))
    ax.bar(x, p["agqo"], color=T["agqo"], width=0.55, label="AGQO", zorder=2)
    for k, c, nm, mk in [("warm_start_only", T["warm"], "khởi động ấm (cổ điển)", "o"), ("random", T["greedy"], "tìm kiếm ngẫu nhiên thiết kế mạch", "s"),
                         ("textbook", T["text"], "QAOA sách giáo khoa", "^")]:
        ax.plot(x, p[k], mk + "-", color=c, label=nm, linewidth=2, markersize=7, zorder=3)
    ax.set_xticks(x, lab, rotation=45)
    ax.set_ylabel("% lượt đo gần tối ưu (trong 5%)")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13), fontsize=9.5)
    return _save(fig, out / "08_quarters.png")


def accounts(T, out, run):
    rb = pd.read_csv(run / "extras" / "robustness.csv")
    b = rb[rb.scenario.str.startswith("base")].set_index("capital_vnd")
    fig, ax = plt.subplots(figsize=_fs(9.5, 4.6))
    x = np.arange(len(b))
    for off, k, c, nm in [(-0.27, "te_practitioner", T["near"], "làm tròn lô gần nhất"), (0, "te_greedy", T["greedy"], "tham lam (thêm từng lô)"),
                          (0.27, "te_whole_lot_optimum", T["agqo"], "AGQO")]:
        ax.bar(x + off, b[k], 0.26, color=c, label=nm)
        for i, v in enumerate(b[k]):
            ax.text(x[i] + off, v + 0.2, _pct(v), ha="center", fontsize=11, color=T["ink"], weight="bold" if k.endswith("optimum") else None)
    ax.set_xticks(x, [f"tài khoản {c / 1e6:.0f} triệu" for c in b.index], fontsize=11.5)
    ax.set_ylabel("sai số bám VN30 thực tế (%/năm)")
    ax.set_ylim(0, b.te_practitioner.max() * 1.22)
    ax.legend(fontsize=10, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    r20 = b.loc[20e6]
    ax.annotate(f"−{_pct(-r20.diff_pp)} điểm %\nKTC 95%: {_pct(r20.ci_low)} đến {_pct(r20.ci_high)}", xy=(0.27, r20.te_whole_lot_optimum),
                xytext=(0.75, r20.te_practitioner * 0.62), color=T["up"], fontsize=10.5,
                arrowprops=dict(arrowstyle="->", color=T["up"]))
    return _save(fig, out / "09_accounts.png")


def one_decision(T, out, run):
    ex = json.loads((run / "extras" / "examples.json").read_text())["20000000"]
    t = np.array(ex["tickers"])
    c, p, g, a = (np.array(ex[k]) * 100 for k in ("continuous", "practitioner", "greedy", "agqo"))
    top = np.argsort(-c)[:16]
    fig, ax = plt.subplots(figsize=_fs(13, 4.8))
    x = np.arange(len(top))
    w = 0.2
    for off, v, col, lab in [(-1.5, c, T["ideal"], f"lý tưởng, cổ phiếu lẻ (sai số {_pct(ex['te']['continuous'])}%)"),
                             (-0.5, p, T["near"], f"làm tròn lô gần nhất (sai số {_pct(ex['te']['practitioner'])}%, {100 - p.sum():.0f}% tiền mặt)"),
                             (0.5, g, T["greedy"], f"tham lam (sai số {_pct(ex['te']['greedy'])}%)"),
                             (1.5, a, T["agqo"], f"AGQO (sai số {_pct(ex['te']['agqo'])}%)")]:
        ax.bar(x + off * w, v[top], w, color=col, label=lab)
    ax.set_xticks(x, [f"{t[j]}\n{ex['lot_pct'][j]:.0f}%" for j in top], fontsize=9.5)
    ax.set_xlabel("mã cổ phiếu (và giá một lô theo % tài khoản)")
    ax.set_ylabel("tỷ trọng trong tài khoản 20 triệu (%)")
    ax.legend(fontsize=9.5, ncol=2, loc="upper right")
    ax.set_ylim(0, max(c[top].max(), a[top].max(), g[top].max()) * 1.5)
    return _save(fig, out / "10_one_decision.png"), {"te": ex["te"], "cash_naive": float(100 - p.sum()), "date": ex["date"]}


def mandates(T, out, run):
    m = pd.read_csv(run / "mandates.csv")
    m = m[m.strategy.str.startswith("AGQO")]
    lab = ["(không có yêu cầu)" if s == "(none)" else s for s in m.instruction]
    fig, ax = plt.subplots(figsize=_fs(12, 3.9))
    y = np.arange(len(m))[::-1]
    ax.barh(y, m.tracking_error_ann_pct, color=T["agqo"], height=0.55)
    for yi, v, cst, vi in zip(y, m.tracking_error_ann_pct, m.te_cost_vs_unconstrained_pp, m.rule_violations_at_rebalance):
        ax.text(v + 0.05, yi, f"{_pct(v, 2)}%   chi phí quy tắc +{_pct(cst, 2)} đ%   ✔ {vi} vi phạm", va="center", fontsize=10.5, color=T["ink"])
    ax.set_yticks(y, ["\n".join([s[i:i + 48] for i in range(0, len(s), 48)]) for s in lab], fontsize=10)
    ax.set_xlabel("sai số bám VN30 thực tế qua 12 quý (%/năm), tài khoản 100 triệu")
    ax.set_xlim(0, m.tracking_error_ann_pct.max() * 2.0)
    ax.grid(axis="y", visible=False)
    return _save(fig, out / "11_mandates.png")


def hardware(T, out, run):
    h = pd.read_csv(run / "extras" / "hardware.csv")
    ha = pd.read_csv(run / "extras" / "hardware_aware.csv")
    g = h.groupby("circuit").mean(numeric_only=True)
    na = ha[ha.date.isin(h.date)].mean(numeric_only=True)
    rows = [("khởi động\nấm", g.loc["warm start only"], T["warm"]),
            ("QAOA sách\ngiáo khoa", g.loc["textbook QAOA"], T["text"]),
            ("AGQO sâu\np=6", g.loc["AGQO (chosen schedule)"], T["near"])]
    lab = [r[0] for r in rows] + ["AGQO theo\nnhiễu p=2"]
    two = [r[1].native_2q for r in rows] + [na.native_2q]
    ideal = [r[1].ideal_success for r in rows] + [na.ideal_success]
    noisy = [r[1].esp_model_success for r in rows] + [na.esp_fit * na.ideal_success + (1 - na.esp_fit) * na.uniform]
    cols = [r[2] for r in rows] + [T["agqo"]]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=_fs(13, 4.6))
    x = np.arange(len(lab))
    a1.bar(x, np.maximum(two, 1), color=cols, width=0.6)
    for i, v in enumerate(two):
        a1.text(i, max(v, 1) * 1.25, f"{v:,.0f} CZ".replace(",", "."), ha="center", fontsize=10, color=T["ink"])
    a1.set_yscale("log")
    a1.set_ylim(0.5, 5e4)
    a1.set_ylabel("cổng 2 qubit sau khi định tuyến (log)")
    a1.set_xticks(x, lab, fontsize=9.5)
    a2.bar(x - 0.2, 100 * np.array(ideal), 0.38, color=T["grid"], edgecolor=T["muted"], label="không nhiễu")
    a2.bar(x + 0.2, 100 * np.array(noisy), 0.38, color=cols, label="nhiễu IBM Heron (mô hình ESP)")
    a2.set_xticks(x, lab, fontsize=9.5)
    a2.set_ylabel("% lượt đo gần tối ưu")
    a2.legend(fontsize=9.5)
    return _save(fig, out / "12_hardware.png"), {"cz": float(na.native_2q)}


def scaling(T, out, run):
    s = pd.read_csv(run / "extras" / "scaling.csv")
    g = s.groupby("qubits").mean(numeric_only=True)
    r = g.frozen_success / g.warm_success
    fig, a1 = plt.subplots(figsize=_fs(10, 4.3))
    x = np.arange(len(g))
    a1.bar(x - 0.2, 100 * g.frozen_success, 0.38, color=T["agqo"], label="mạch AGQO (lịch học năm 2023)")
    a1.bar(x + 0.2, 100 * g.warm_success, 0.38, color=T["warm"], label="khởi động ấm (cổ điển)")
    a1.set_yscale("log")
    a1.set_ylabel("% lượt đo gần tối ưu (log)")
    a1.set_xticks(x, [f"{q} qubit\n{2 ** q:,} tổ hợp".replace(",", ".") for q in g.index])
    a2 = a1.twinx()
    a2.plot(x, r, "D-", color=T["accent"], linewidth=2.6, markersize=9, label="gấp bao nhiêu lần")
    for i, v in enumerate(r):
        a2.text(i, v + 0.8, f"{_pct(v)}×", ha="center", color=T["accent"], fontsize=12, weight="bold")
    a2.set_ylim(0, r.max() * 1.35)
    a2.grid(False)
    a2.set_ylabel("lần", color=T["accent"])
    h1, l1 = a1.get_legend_handles_labels()
    h2, l2 = a2.get_legend_handles_labels()
    a1.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=3, fontsize=9.5)
    return _save(fig, out / "13_scaling.png"), {"ratio": r.round(1).to_dict()}


def llm(T, out, run):
    me = json.loads((run / "llm" / "mandate_eval.json").read_text())["score"]
    ex = json.loads((run / "llm" / "explanations.json").read_text())["score"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=_fs(12, 3.9))
    a1.barh([1, 0], [me["llm_effective_pct"], me["rule_effective_pct"]], color=[T["ai"], T["muted"]], height=0.55)
    a1.set_yticks([1, 0], ["Qwen3.8-27B", "quy tắc từ khóa"], fontsize=11)
    for y, v in zip([1, 0], [me["llm_effective_pct"], me["rule_effective_pct"]]):
        a1.text(v - 2, y, f"{_pct(v)}%", va="center", ha="right", fontsize=13, weight="bold", color="#0b1220")
    a1.set_xlim(0, 100)
    a1.set_xlabel("% trong 35 yêu cầu tiếng Việt dịch đúng ràng buộc")
    a1.grid(axis="y", visible=False)
    n = ex["explanations"]
    ok_mean = round(ex["faithful_pct"] * n / 100)
    vals = [[n, n], [0, ok_mean]]
    x = np.arange(2)
    a2.bar(x - 0.18, vals[0], 0.34, color=T["muted"], label="lời nhắc ban đầu")
    a2.bar(x + 0.18, [n, ok_mean], 0.34, color=T["ai"], label="lời nhắc có nhãn ý nghĩa")
    a2.set_xticks(x, ["mọi con số đúng", "đúng cả ý nghĩa"], fontsize=11)
    a2.set_ylim(0, 14.5)
    a2.set_ylabel(f"số lời giải thích (trên {n})")
    for xi, v0, v1 in zip(x, [n, 0], [n, ok_mean]):
        a2.text(xi - 0.18, v0 + 0.3, f"{v0}/{n}", ha="center", fontsize=11, color=T["ink"])
        a2.text(xi + 0.18, v1 + 0.3, f"{v1}/{n}", ha="center", fontsize=11, color=T["ink"], weight="bold")
    a2.legend(fontsize=9.5, loc="upper right", bbox_to_anchor=(1, 1.16), ncol=2)
    return _save(fig, out / "14_llm.png")


def backtest(T, out, run):
    dv = pd.read_csv(run / "daily_values.csv", parse_dates=["date"]).set_index("date") / 1e6
    fig, ax = plt.subplots(figsize=_fs(12, 4.3))
    for k, c, lw, nm in [("VN30 index (scaled)", T["accent"], 1.6, "chỉ số VN30"), ("ETF E1VFVN30", T["muted"], 1.3, "ETF E1VFVN30"),
                         ("Practitioner: nearest-lot rounding", T["near"], 1.3, "làm tròn lô gần nhất"),
                         ("AGQO: AI-guided QAOA rounding", T["agqo"], 2.4, "AGQO")]:
        ax.plot(dv.index, dv[k], color=c, linewidth=lw, label=nm)
    ax.set_ylabel("giá trị tài khoản (triệu đồng)")
    ax.legend(fontsize=10, ncol=4, loc="upper left")
    return _save(fig, out / "15_backtest.png")


def build(out_root: Path = ROOT / "docs" / "figures_vi", run: Path = RESULTS_DIR) -> dict:
    from .data import MarketData
    from .extras import load_config

    md, ec = MarketData.load(), load_config(run)
    facts = {}
    global FS
    for name, T in THEMES.items():
        FS = 1.0 if name == "dark" else 0.62
        out = out_root / name
        out.mkdir(parents=True, exist_ok=True)
        _style(T)
        facts["lot"] = lot_cost(T, out, run, md, ec)[1]
        pipeline(T, out)
        facts["market"] = market(T, out, run)[1]
        hamiltonian(T, out, run)
        facts["circuit"] = circuit(T, out, run)[1]
        facts["schedules"] = schedules(T, out, run)[1]
        facts["prob"] = prob_flow(T, out, run)[1]
        quarters(T, out, run)
        accounts(T, out, run)
        facts["decision"] = one_decision(T, out, run)[1]
        mandates(T, out, run)
        facts["hardware"] = hardware(T, out, run)[1]
        facts["scaling"] = scaling(T, out, run)[1]
        llm(T, out, run)
        backtest(T, out, run)
    (out_root / "facts.json").write_text(json.dumps(facts, indent=1, default=str, ensure_ascii=False))
    return facts


if __name__ == "__main__":
    print(json.dumps(build(), indent=1, default=str, ensure_ascii=False))
