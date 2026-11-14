"""Additional visual evidence for the final AGQO report."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from .simulator import mixer_edges_for_problem


COLORS = {
    "ink": "#263542",
    "blue": "#3979A8",
    "orange": "#E18D45",
    "green": "#3B8C72",
    "red": "#B95754",
    "purple": "#7967A7",
    "gray": "#7D8994",
    "grid": "#DDE3E8",
}


def _save(fig: plt.Figure, directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _draw_circuit_panel(ax, mixer: str, n: int = 8, k: int = 6) -> None:
    ys = np.arange(n)[::-1]
    x0, x1 = 0.25, 9.7
    for index, y in enumerate(ys):
        ax.plot([x0, x1], [y, y], color=COLORS["ink"], linewidth=0.9, zorder=1)
        ax.text(x0 - 0.12, y, f"q{index}", ha="right", va="center", fontsize=8)

    def block(x: float, label: str, subtitle: str, color: str, width: float = 0.82):
        y0, y1 = ys.min() - 0.42, ys.max() + 0.42
        rect = plt.Rectangle(
            (x - width / 2, y0), width, y1 - y0,
            facecolor=color, alpha=0.12, edgecolor=color, linewidth=1.2,
            linestyle="--" if width > 1 else "-", zorder=0,
        )
        ax.add_patch(rect)
        ax.text(x, y1 + 0.18, label, ha="center", va="bottom", fontsize=8, weight="bold", color=color)
        ax.text(x, y0 - 0.18, subtitle, ha="center", va="top", fontsize=7, color=COLORS["ink"])

    ax.text(0.75, ys.max() + 0.2, "Initial state", ha="center", fontsize=8, weight="bold")
    if mixer == "X":
        for y in ys:
            ax.add_patch(plt.Rectangle((0.58, y - 0.17), 0.34, 0.34, facecolor="white", edgecolor=COLORS["gray"]))
            ax.text(0.75, y, "H", ha="center", va="center", fontsize=7)
        mixer_text = "RX(2β) on each qubit"
        mixer_color = COLORS["blue"]
    else:
        for y in ys[:k]:
            ax.add_patch(plt.Rectangle((0.58, y - 0.17), 0.34, 0.34, facecolor="white", edgecolor=COLORS["gray"]))
            ax.text(0.75, y, "X", ha="center", va="center", fontsize=7)
        mixer_text = "RXX(2β) + RYY(2β) per XY edge"
        mixer_color = COLORS["orange"]

    block(2.0, "RZ", "single-qubit cost terms", COLORS["purple"])
    block(4.1, "RZZ", f"all covariance pairs: {n * (n - 1) // 2}", COLORS["red"], 1.35)
    block(6.45, "MIXER", mixer_text, mixer_color, 1.4)
    block(8.7, "MEASURE", "computational basis", COLORS["green"])
    if mixer == "X":
        for y in ys:
            ax.add_patch(plt.Rectangle((1.84, y - 0.17), 0.32, 0.34, facecolor="white", edgecolor=COLORS["purple"]))
            ax.text(2.0, y, "Rz", ha="center", va="center", fontsize=6)
            ax.add_patch(plt.Rectangle((6.29, y - 0.17), 0.32, 0.34, facecolor="white", edgecolor=mixer_color))
            ax.text(6.45, y, "Rx", ha="center", va="center", fontsize=6)
    else:
        for y in ys:
            ax.add_patch(plt.Rectangle((1.84, y - 0.17), 0.32, 0.34, facecolor="white", edgecolor=COLORS["purple"]))
            ax.text(2.0, y, "Rz", ha="center", va="center", fontsize=6)
        # The mixer block denotes repeated pair gates on the displayed topology.
        for y in ys[::2]:
            ax.scatter([6.45], [y], color=mixer_color, s=12, zorder=3)
        for y1, y2 in zip(ys[:-1], ys[1:]):
            ax.plot([6.45, 6.45], [y1, y2], color=mixer_color, alpha=0.5, linewidth=1.1, zorder=2)
        ax.text(6.45, ys.min() - 0.08, "edge gates", ha="center", fontsize=6, color=mixer_color)
    for y in ys:
        ax.add_patch(plt.Rectangle((8.54, y - 0.17), 0.32, 0.34, facecolor="white", edgecolor=COLORS["green"]))
        ax.text(8.7, y, "M", ha="center", va="center", fontsize=6)
    ax.set_xlim(0.0, 10.0)
    ax.set_ylim(ys.min() - 1.35, ys.max() + 0.85)
    ax.axis("off")


def _draw_topology(ax, layout: str, n: int = 8) -> None:
    angles = np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, n, endpoint=False)
    positions = np.column_stack([np.cos(angles), np.sin(angles)])
    if layout == "correlation":
        edges = set(mixer_edges_for_problem(np.eye(n), "ring"))
        edges.update(tuple(sorted((i, (i + 2) % n))) for i in range(n))
    else:
        edges = set(mixer_edges_for_problem(np.eye(n), layout))
    for i, j in sorted(edges):
        ax.plot(
            [positions[i, 0], positions[j, 0]],
            [positions[i, 1], positions[j, 1]],
            color=COLORS["gray"], alpha=0.42, linewidth=0.8, zorder=1,
        )
    ax.scatter(positions[:, 0], positions[:, 1], s=54, color=COLORS["blue"], edgecolor="white", linewidth=0.8, zorder=2)
    for i, (x, y) in enumerate(positions):
        ax.text(x, y, str(i), ha="center", va="center", fontsize=7, color="white", weight="bold", zorder=3)
    ax.set_title(f"{layout.title()} · {len(edges)} edges", fontsize=8, weight="bold")
    ax.set_aspect("equal")
    ax.axis("off")


def build_quantum_design_plot(output_dir: str | Path) -> Path:
    """Draw the logical cost/mixer gate pattern and four tested mixer graphs."""
    directory = Path(output_dir)
    fig = plt.figure(figsize=(16, 9))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.6, 1.0], height_ratios=[1, 1], wspace=0.12, hspace=0.30)
    ax_x = fig.add_subplot(grid[0, 0])
    ax_xy = fig.add_subplot(grid[1, 0])
    _draw_circuit_panel(ax_x, "X")
    _draw_circuit_panel(ax_xy, "XY")
    ax_x.set_title("X mixer: penalty-based cardinality", loc="left", weight="bold", pad=8)
    ax_xy.set_title("XY mixer: cardinality-preserving exchanges", loc="left", weight="bold", pad=8)
    topology_grid = grid[:, 1].subgridspec(2, 2, wspace=0.04, hspace=0.22)
    for cell, layout in zip(topology_grid, ("ring", "linear", "complete", "correlation")):
        _draw_topology(fig.add_subplot(cell), layout)
    fig.suptitle("QAOA logical gates and mixer layouts (N=8, K=6 schematic; p=1 layer)", x=0.04, ha="left", weight="bold", fontsize=15)
    fig.text(
        0.04, 0.012,
        "RZ/RZZ encode the portfolio cost Hamiltonian; RX is the X mixer; RXX+RYY are XY edge gates. "
        "The RZZ panel groups all pair terms and is not a single physical gate. Correlation graph is illustrative; "
        "backtests build it from each covariance matrix. Logical diagrams are not hardware layouts.",
        fontsize=8, color=COLORS["gray"],
    )
    return _save(fig, directory, "09_qaoa_gate_and_mixer_design.png")


def build_policy_tradeoff_plot(result_json: str | Path, output_dir: str | Path) -> Path:
    """Compare measured logical gate counts against objective regret per policy."""
    result = json.loads(Path(result_json).read_text(encoding="utf-8"))
    policies = result.get("agqo_guidance", {}).get("policy_catalog", [])
    summary = result.get("qaoa", {}).get("quality_summary", {})
    rows = []
    for policy in policies:
        key = f"POLICY:{policy['policy_id']}"
        quality = summary.get(key, {})
        records = [
            row for row in result["qaoa"]["monthly_runs"]
            if row.get("variant") == key
        ]
        gate_values = [
            row.get("logical_cost_two_qubit_gate_count", 0)
            + row.get("logical_mixer_two_qubit_gate_count", 0)
            for row in records
        ]
        regret = quality.get("mean_normalized_regret")
        if gate_values and regret is not None:
            rows.append({
                "id": policy["policy_id"],
                "n": policy["n_qubits"],
                "mixer": policy["mixer"],
                "depth": policy["depth"],
                "gates": float(np.mean(gate_values)),
                "regret": float(regret) * 100,
                "feasible": quality.get("mean_best_seed_feasible_probability"),
            })
    fig = plt.figure(figsize=(16, 8.5))
    layout = fig.add_gridspec(1, 2, width_ratios=[3.1, 1.4], wspace=0.10)
    ax = fig.add_subplot(layout[0, 0])
    key_ax = fig.add_subplot(layout[0, 1])
    palette = {8: COLORS["green"], 12: COLORS["blue"], 16: COLORS["purple"]}
    label_offsets = [(6, 6), (7, -11), (-12, 7), (-12, -11), (2, 12), (2, -16), (12, 2)]
    for index, row in enumerate(rows):
        marker = "o" if row["mixer"] == "X" else "D"
        ax.scatter(row["gates"], row["regret"], s=76 if row["depth"] == 1 else 102, marker=marker,
                   color=palette.get(row["n"], COLORS["gray"]), edgecolor="white", linewidth=0.7, zorder=3)
        ax.annotate(
            str(index + 1), (row["gates"], row["regret"]),
            xytext=label_offsets[index % len(label_offsets)], textcoords="offset points",
            fontsize=7, weight="bold", color=COLORS["ink"],
            bbox={"boxstyle": "circle,pad=0.18", "fc": "white", "ec": COLORS["gray"], "lw": 0.55},
        )
    key_ax.axis("off")
    key_ax.set_xlim(0, 1)
    key_ax.set_ylim(0, max(15, len(rows) + 2))
    key_ax.text(0, max(15, len(rows) + 2) - 0.2, "Mã chính sách", fontsize=10, weight="bold", va="top")
    for index, row in enumerate(rows):
        y = max(15, len(rows) + 2) - 1.15 - index
        color = palette.get(row["n"], COLORS["gray"])
        marker = "o" if row["mixer"] == "X" else "D"
        key_ax.scatter([0.04], [y], marker=marker, color=color, s=32, edgecolor="white", linewidth=0.5)
        key_ax.text(0.1, y, f"{index + 1}. {row['id']}", fontsize=7.5, va="center", color=COLORS["ink"])
    key_ax.text(0, 0.2, "Màu: N=8/12/16 · Hình: X/XY · Kích thước: p=1/2", fontsize=7, va="bottom", color=COLORS["gray"])
    ax.set_xlabel("Mean logical two-qubit gate proxy per instance")
    ax.set_ylabel("Mean normalized regret vs exact optimum (%) · lower is better")
    ax.set_title("Quality and logical circuit cost across QAOA policies", loc="left", weight="bold")
    ax.axhline(5, color=COLORS["red"], linestyle="--", linewidth=1, label="Regret 5% threshold")
    ax.grid(color=COLORS["grid"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right")
    fig.text(0.11, 0.012, "Marker size grows with p. Gate counts are logical simulation proxies, not transpiled hardware counts.", fontsize=8, color=COLORS["gray"])
    return _save(fig, Path(output_dir), "10_qaoa_quality_vs_gate_cost.png")


def build_agqo_decision_audit_plot(result_json: str | Path, output_dir: str | Path) -> Path:
    """Show the LLM proposal, guardrail execution, and any override by signal date."""
    result = json.loads(Path(result_json).read_text(encoding="utf-8"))
    decisions = result.get("agqo_guidance", {}).get("decisions", [])
    fig, ax = plt.subplots(figsize=(13, max(4.8, 0.48 * len(decisions) + 1.8)))
    if not decisions:
        ax.text(0.5, 0.5, "No AGQO LLM decisions recorded", ha="center", va="center")
        ax.axis("off")
    else:
        y = np.arange(len(decisions))
        for i, row in enumerate(decisions):
            proposed = row.get("proposed_policy_id", row["decision"]["policy_id"])
            executed = row.get("executed_policy_id", row.get("policy", {}).get("policy_id", proposed))
            overridden = proposed != executed
            color = COLORS["red"] if overridden else COLORS["green"]
            ax.plot([0.8, 2.5], [i, i], color=COLORS["grid"], linewidth=1, zorder=1)
            ax.scatter([0.8], [i], color=COLORS["blue"], marker="o", s=46, zorder=3)
            ax.scatter([2.5], [i], color=color, marker="D", s=46, zorder=3)
            reason = row.get("guardrail_reason") or ""
            if "fewer than" in reason:
                note = "insufficient history"
            elif "feasible-shot" in reason:
                note = "feasibility guard"
            elif "regret" in reason:
                note = "regret guard"
            elif "utility" in reason:
                note = "risk-adjusted guard"
            else:
                note = "accepted"
            short_executed = executed.replace("n08_", "8:").replace("n12_", "12:").replace("n16_", "16:")
            ax.text(2.68, i, f"{short_executed} · {note}", va="center", fontsize=8, color=COLORS["ink"])
            ax.text(-0.08, i, f"{row['signal_date']}  {proposed}", ha="right", va="center", fontsize=8, color=COLORS["ink"])
        ax.set_ylim(len(decisions) - 0.4, -0.6)
        ax.set_xlim(-2.2, 4.6)
        ax.set_xticks([0.8, 2.5], ["LLM proposal", "Executed after guardrail"])
        ax.grid(axis="x", color=COLORS["grid"])
        ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax.tick_params(axis="y", left=False, labelleft=False)
    ax.set_title("AGQO decision audit: proposal and executed policy", loc="left", weight="bold")
    fig.text(0.12, 0.012, "Blue circles are Qwen3.8-27B proposals; green diamonds are accepted; red diamonds show numeric guardrail overrides.", fontsize=8, color=COLORS["gray"])
    return _save(fig, Path(output_dir), "11_agqo_decision_audit.png")


def build_final_visuals(result_json: str | Path, output_dir: str | Path) -> list[Path]:
    return [
        build_quantum_design_plot(output_dir),
        build_policy_tradeoff_plot(result_json, output_dir),
        build_agqo_decision_audit_plot(result_json, output_dir),
    ]
