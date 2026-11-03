"""Research figures, machine-readable summary and Vietnamese evidence report."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import csv
import html
import json
import numpy as np


def summarize(output):
    groups = defaultdict(list)
    for row in output["records"]:
        groups[row["result"]["method"]].append(row["result"])
    summary = []
    for method, records in groups.items():
        executed = [r for r in records if r["status"] != "not_run"]
        feasible = [r for r in executed if r.get("feasible")]
        means = {}
        for metric in ("tracking_rmse", "heldout_tracking_rmse", "transaction_cost", "two_way_turnover", "objective_gap_absolute", "elapsed_seconds", "total_shots"):
            values = [r[metric] for r in feasible if metric in r]
            means[metric] = None if not values else float(np.mean(values))
        summary.append({"method": method, "records": len(records), "executed": len(executed),
                        "failures": sum(r["status"] in {"error", "invalid", "unknown", "needs_clarification"} for r in records),
                        "feasible": len(feasible), "feasible_rate": None if not executed else len(feasible) / len(executed),
                        "mean_elapsed_attempted": None if not executed else float(np.mean([r.get("elapsed_seconds", 0) for r in executed])),
                        "total_shots_attempted": sum(r.get("total_shots", 0) for r in executed),
                        **means})
    # Differences are paired by case AND seed. Deterministic comparators are not
    # duplicated as independent observations. Collapse seeds before describing cases.
    pairs = []
    case_groups = defaultdict(lambda: defaultdict(list))
    for row in output["records"]:
        case = row["case"]
        case_groups[(case["start"], case["family"])][row["result"]["method"]].append(row["result"])
    for key, methods in case_groups.items():
        baseline = methods.get("qaoa_fixed", [])
        for method, records in methods.items():
            if method in {"qaoa_fixed", "hold", "exact", "milp_highs", "periodic_rebuild"}:
                continue
            matches = []
            for r in records:
                b = next((b for b in baseline if b.get("seed") == r.get("seed")), None)
                if b and b.get("feasible") and r.get("feasible") and r.get("problem_hash") == b.get("problem_hash"):
                    matches.append(r["objective"] - b["objective"])
            if matches:
                pairs.append({"start": key[0], "family": key[1], "method": method,
                              "mean_objective_difference_vs_fixed": float(np.mean(matches)), "paired_seeds": len(matches)})
    return {"methods": summary, "paired_case_differences": pairs,
            "interpretation": "Descriptive benchmark. Conditional means exclude failed solutions; feasibility/failures shown separately. Cases share market windows and are dependent. Seeds are repetitions, not independent financial samples. No significance or live-savings claim."}


def create_report(output, directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    directory = Path(directory); figures = directory / "figures"; figures.mkdir(parents=True, exist_ok=True)
    summary = summarize(output)
    (directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    with (directory / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary["methods"][0])); writer.writeheader(); writer.writerows(summary["methods"])
    plt.rcParams.update({"figure.facecolor": "#f6f4ed", "axes.facecolor": "#f6f4ed", "font.size": 9})
    catalog = []
    valid = [m for m in summary["methods"] if m["executed"]]

    def save(fig, filename, title, caption, fields):
        fig.tight_layout(); fig.savefig(figures / filename, dpi=160); plt.close(fig)
        catalog.append({"file": "figures/" + filename, "title": title, "caption": caption,
                        "source": output["protocol"]["data_provenance"]["kind"], "fields": fields})

    fig, ax = plt.subplots(figsize=(9, 5))
    for m in valid:
        if m["two_way_turnover"] is not None:
            ax.scatter(m["two_way_turnover"] * 100, m["heldout_tracking_rmse"] * 100, s=45)
            ax.annotate(m["method"], (m["two_way_turnover"] * 100, m["heldout_tracking_rmse"] * 100), fontsize=7, xytext=(4, 3), textcoords="offset points")
    ax.set(xlabel="Two-way turnover (%)", ylabel="Held-out tracking RMSE per period (%)")
    save(fig, "01_tracking_turnover.png", "Hình 1. Đánh đổi tracking–turnover", "Mỗi điểm là trung bình có điều kiện trên những nghiệm hợp lệ. Đọc cùng tỷ lệ khả thi ở Hình 2; đây không phải đường biên hiệu quả đã được chứng minh.", ["two_way_turnover", "heldout_tracking_rmse"])
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh([m["method"] for m in valid], [100 * m["feasible_rate"] for m in valid], color="#246a65")
    ax.set(xlabel="Feasible records (%)", xlim=(0, 100))
    save(fig, "02_feasibility.png", "Hình 2. Tỷ lệ phương án đáp ứng yêu cầu", "Tất cả giới hạn được kiểm tra bằng mô hình gốc. Case không có nghiệm vẫn xuất hiện trong mẫu; bộ giải báo infeasible không phải là lỗi.", ["feasible", "status"])
    fig, ax = plt.subplots(figsize=(10, 5))
    selected = [m for m in valid if m["objective_gap_absolute"] is not None]
    ax.barh([m["method"] for m in selected], [m["objective_gap_absolute"] for m in selected], color="#c66c35")
    ax.set(xlabel="Absolute objective gap to proven optimum (lower is better)")
    save(fig, "03_objective_gap.png", "Hình 3. Khoảng cách tới nghiệm tối ưu", "Khoảng cách tuyệt đối trên đúng cùng hàm mục tiêu; không chia cho giá trị tối ưu có thể gần 0. Phương án không hợp lệ được báo riêng.", ["objective_gap_absolute"])
    fig, ax = plt.subplots(figsize=(9, 4))
    language = output["language"]
    for i, method in enumerate(("rules", "qwen")):
        rows = [r for r in language if r["method"] == method and r["correct"] is not None]
        if rows:
            ax.bar(i, 100 * np.mean([r["correct"] for r in rows]), color=("#246a65", "#c66c35")[i])
        else:
            ax.text(i, 5, "not run", ha="center")
    ax.set(xticks=[0, 1], xticklabels=["rules", "Qwen"], ylim=(0, 105), ylabel="Correct semantic/status targets (%)")
    save(fig, "04_language_ablation.png", "Hình 4. Kiểm tra chuẩn hóa yêu cầu", "Bộ yêu cầu tự biên soạn có nhãn chuẩn độc lập gồm diễn đạt lại, mâu thuẫn, phủ định và thiếu thông tin; kết quả nhỏ mang tính chẩn đoán.", ["language.correct", "language.status"])
    # Cost sensitivity uses exact optima on a fixed single instance, without test tuning.
    from dataclasses import replace
    from .data import synthetic_data, make_window
    from .solvers import exact_solve
    p, _, _ = make_window(synthetic_data(), text="Hold 4 assets; Exclude S00")
    frontier = []
    for weight in (0.0, 0.001, 0.01, 0.1, 1.0):
        candidate = replace(p, cost_weight=weight)
        r = exact_solve(candidate)
        frontier.append({"cost_weight": weight, "problem_hash": candidate.fingerprint(), "result": r})
    (directory / "cost_frontier.json").write_text(json.dumps({"source": "separate_synthetic_sensitivity_not_test_tuning", "rows": frontier}, indent=2))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot([r["result"]["transaction_cost"] * 10000 for r in frontier], [r["result"]["tracking_rmse"] * 100 for r in frontier], "o-", color="#246a65")
    ax.set(xlabel="Modeled trading cost (bps of NAV)", ylabel="In-sample tracking RMSE (%)")
    save(fig, "05_cost_frontier.png", "Hình 5. Độ nhạy tracking–chi phí", "Nghiệm exact trên một fixture tổng hợp riêng, thay hệ số chi phí đã khai báo. Biểu đồ minh họa đánh đổi của mô hình, không dùng để chọn cấu hình từ tập test.", ["cost_frontier.rows"])
    catalog[-1]["source"] = "separate_synthetic_fixture"
    fig, ax = plt.subplots(figsize=(9, 5))
    for m in valid:
        if m["elapsed_seconds"] is not None and m["objective_gap_absolute"] is not None:
            ax.scatter(m["elapsed_seconds"], m["objective_gap_absolute"], s=45)
            ax.annotate(m["method"], (m["elapsed_seconds"], m["objective_gap_absolute"]), fontsize=7, xytext=(4, 3), textcoords="offset points")
    ax.set(xlabel="End-to-end seconds on feasible records (CPU + charged selector latency)", ylabel="Absolute objective gap")
    ax.set_xscale("log")
    save(fig, "06_quality_resources.png", "Hình 6. Chất lượng và tài nguyên", "Thời gian gồm dựng oracle và tối ưu; nhánh LLM tính thêm latency chọn mạch. Điểm trung bình có điều kiện không thay thế phân tích thất bại hay chứng minh speedup.", ["elapsed_seconds", "objective_gap_absolute"])
    families = sorted({r["case"]["family"] for r in output["records"]})
    fig, ax = plt.subplots(figsize=(10, 5))
    for method in ("qaoa_fixed", "qaoa_rule", "qwen_circuit"):
        values = []
        for family in families:
            records = [row["result"] for row in output["records"] if row["case"]["family"] == family and row["result"]["method"] == method and row["result"]["status"] != "not_run"]
            values.append(float(np.mean([r["feasible"] for r in records])) if records else np.nan)
        if any(np.isfinite(values)):
            ax.plot(range(len(families)), values, "o-", label=method)
    ax.set(xticks=range(len(families)), xticklabels=families, ylabel="Feasible rate", ylim=(-0.03, 1.03))
    ax.tick_params(axis="x", labelrotation=20); ax.legend()
    save(fig, "07_unseen_structure.png", "Hình 7. Khả năng thích nghi theo nhóm yêu cầu", "Nhóm unseen là tổ hợp giới hạn không dùng để chọn cấu hình cố định. Nhóm không có nghiệm được giữ lại để kiểm tra phản hồi; không kỳ vọng tỷ lệ khả thi dương.", ["case.family", "feasible", "status"])
    (directory / "figure_catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
    lines = ["# AGQO — bằng chứng tái cân bằng theo mandate", "", "Nguồn: " + output["protocol"]["data_provenance"]["kind"],
             "", "Protocol SHA-256: `" + output["protocol_sha256"] + "`", "", "Kết quả là benchmark nghiên cứu; chưa chứng minh lợi thế lượng tử hoặc tiết kiệm thực tế cho quỹ.",
             "", "Các kỳ của nguồn OR-Library chưa được xác minh tần suất; chỉ báo số liệu mỗi kỳ, không năm hóa.",
             "", "| Phương pháp | Đã chạy | Hợp lệ | RMSE ngoài mẫu (%) | Turnover hai chiều (%) |", "|---|---:|---:|---:|---:|"]
    for m in summary["methods"]:
        fmt = lambda v: "—" if v is None else f"{v * 100:.3f}"
        lines.append(f"| {m['method']} | {m['executed']}/{m['records']} | {m['feasible']} | {fmt(m['heldout_tracking_rmse'])} | {fmt(m['two_way_turnover'])} |")
    lines += ["", "Giá trị trung bình chỉ gồm nghiệm hợp lệ; tỷ lệ thất bại phải được đọc cùng. Các seed không phải các mẫu tài chính độc lập.",
              "", "## Bằng chứng và giới hạn", "", "- Exact và MILP cùng mô hình; các nhánh QAOA không được đổi universe, K hoặc mục tiêu.",
              "- Oracle pha chéo được dựng đầy đủ trên 2^N trạng thái; đây là chi phí cổ điển tăng theo hàm mũ và giới hạn quan trọng của prototype.",
              "- Khởi tạo previous bảo toàn số tài sản khi dùng XY; không bảo đảm mọi giới hạn ngành/turnover.",
              "- LLM disabled/error/invalid được ghi đúng trạng thái, không thay bằng quy tắc rồi gắn nhãn Qwen.",
              "- Chuỗi benchmark đã được mở trong quá trình phát triển; tập test là tách theo giao thức, không phải dữ liệu tương lai mới thu.",
              "- Gap phương pháp là giả thuyết; không khẳng định tính mới tuyệt đối từ việc tích hợp."]
    for item in catalog:
        lines += ["", f"![{item['title']}]({item['file']})", "", f"**{item['title']}.** {item['caption']} Nguồn: {item['source']}."]
    lines += ["", "## Tái lập", "", "Xem protocol.json, benchmark.json, mandates_gold.json, summary.csv và figure_catalog.json trong cùng thư mục."]
    (directory / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    cards = "".join(f"<figure><img src='{item['file']}' alt='{html.escape(item['title'])}'><figcaption><b>{html.escape(item['title'])}.</b> {html.escape(item['caption'])}</figcaption></figure>" for item in catalog)
    (directory / "report.html").write_text("<!doctype html><html lang='vi'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>AGQO · Bằng chứng</title><style>body{font:16px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:24px;background:#f6f4ed;color:#172d39}img{max-width:100%}figure{margin:35px 0}a{color:#246a65}</style><h1>AGQO · Bằng chứng nghiên cứu</h1><p>Benchmark có đối chứng; chưa xác lập ưu thế lượng tử hoặc tiết kiệm thực tế.</p><p><a href='summary.json'>Số liệu tổng hợp</a> · <a href='benchmark.json'>Kết quả đầy đủ</a> · <a href='protocol.json'>Giao thức</a></p>" + cards + "</html>", encoding="utf-8")
    return summary
