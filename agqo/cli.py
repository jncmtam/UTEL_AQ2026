"""Lệnh chạy mẫu tổng hợp, bộ chuẩn 36 bài toán và nhánh QPU tùy chọn."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .ai import diagonal_shrinkage, regime_controls, risk_aversion_from_probability
from .market_data import analyze_market_dataset, summary_json, write_market_report
from .plots import create_market_figures
from .problem import PortfolioProblem, anneal_solve, exact_solve, greedy_solve, synthetic_problem
from .qpu import load_qpu_config, run_qpu
from .simulator import optimize_qaoa


def _save(records: list[dict], output: str | None) -> Path:
    path = Path(output or f"outputs/agqo_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _demo(args: argparse.Namespace) -> int:
    base_problem = synthetic_problem(args.seed, n=args.n, k=6)
    # Chỉ là xác suất minh họa trên dữ liệu tổng hợp, không phải dự báo thị trường.
    probability = 0.70
    rng = np.random.Generator(np.random.PCG64(args.seed + 1))
    previous_weights = np.zeros(base_problem.n, dtype=float)
    previous_weights[rng.choice(base_problem.n, base_problem.k, replace=False)] = 1 / base_problem.k
    versions = ("v0", "v1") if args.model_version == "compare" else (args.model_version,)
    records = []
    for version in versions:
        if version == "v0":
            risk_aversion, alpha = regime_controls(probability)
            cost_bps = 0.0
        else:
            # V1 tách AI khỏi co rút và tính phí đổi danh mục vào cùng mục tiêu.
            risk_aversion = risk_aversion_from_probability(probability)
            alpha = 0.40
            cost_bps = args.transaction_cost_bps
        problem = PortfolioProblem(
            base_problem.tickers,
            base_problem.mu,
            diagonal_shrinkage(base_problem.covariance, alpha),
            k=base_problem.k,
            risk_aversion=risk_aversion,
            previous_weights=previous_weights,
            transaction_costs=np.full(base_problem.n, cost_bps / 10_000),
            rebalances_per_year=12,
        )
        exact_bits, exact_value = exact_solve(problem)
        greedy_bits, greedy_value = greedy_solve(problem)
        anneal_bits, anneal_value = anneal_solve(problem, seed=args.seed, steps=2_000)
        records.append(
            {
                "kind": "demo",
                "model_version": version,
                "seed": args.seed,
                "data_source": "synthetic_only",
                "n": problem.n,
                "k": problem.k,
                "regime_probability_demo_only": probability,
                "risk_aversion_demo_only": risk_aversion,
                "diagonal_shrinkage_demo_only": alpha,
                "previous_weights": previous_weights.tolist(),
                "transaction_cost_bps": cost_bps,
                "exact_two_way_turnover": problem.two_way_turnover(exact_bits),
                "exact_annual_transaction_cost": problem.annual_transaction_cost(exact_bits),
                "exact": {"score": exact_value, "bits": exact_bits.tolist()},
                "greedy": {"score": greedy_value, "bits": greedy_bits.tolist()},
                "annealing": {"score": anneal_value, "bits": anneal_bits.tolist()},
            }
        )
        for mixer in ("X", "XY"):
            for seed in (11, 23, 47):
                result = optimize_qaoa(
                    problem, mixer=mixer, seed=seed, max_evaluations=args.max_evaluations, shots=512
                )
                records.append(
                    {
                        "kind": "qaoa",
                        "model_version": version,
                        "data_source": "synthetic_only",
                        **result.to_dict(),
                    }
                )
    path = _save(records, args.output)
    print(json.dumps({"results_file": str(path), "records": records}, ensure_ascii=False, indent=2))
    return 0


def _benchmark(args: argparse.Namespace) -> int:
    records = []
    for offset in range(args.limit):
        source_seed = 20261012 + offset
        full = synthetic_problem(source_seed, n=16, k=6)
        for n in (8, 12, 16):
            problem = type(full)(full.tickers[:n], full.mu[:n], full.covariance[:n, :n], k=6)
            exact_bits, exact_value = exact_solve(problem)
            for mixer in ("X", "XY"):
                runs = [
                    optimize_qaoa(
                        problem,
                        mixer=mixer,
                        seed=seed,
                        max_evaluations=args.max_evaluations,
                        shots=512,
                    )
                    for seed in (11, 23, 47)
                ]
                feasible_scores = [r.best_feasible_score for r in runs if r.best_feasible_score is not None]
                feasible_values = [
                    problem.score(np.fromiter(((i >> j) & 1 for j in range(n)), dtype=np.int8))
                    for i in range(1 << n)
                    if i.bit_count() == 6
                ]
                denominator = max(max(feasible_values) - min(feasible_values), 1e-12)
                gaps = [(value - exact_value) / denominator for value in feasible_scores]
                records.append(
                    {
                        "kind": "benchmark",
                        "source_seed": source_seed,
                        "data_source": "synthetic_only",
                        "n": n,
                        "k": 6,
                        "mixer": mixer,
                        "exact_objective": exact_value,
                        "exact_bits": exact_bits.tolist(),
                        "runs": [run.to_dict() for run in runs],
                        "median_normalized_gap": None if not gaps else float(np.median(gaps)),
                        "all_runs_feasible": len(feasible_scores) == 3,
                        "meets_case_threshold": len(feasible_scores) == 3 and float(np.median(gaps)) <= 0.05,
                    }
                )
                print(json.dumps(records[-1], ensure_ascii=False))
    path = _save(records, args.output)
    print(f"Kết quả đã lưu: {path}")
    print(f"Số bài toán đã chạy: {len(records)} / mục tiêu đầy đủ 36")
    return 0


def _qpu(args: argparse.Namespace) -> int:
    # Không mở dịch vụ/tiêu hạn mức nếu người dùng chưa bật cờ gửi rõ ràng.
    if not args.submit:
        print("Chưa gửi job. Điền config/qpu.toml, đặt khóa trong biến môi trường, rồi thêm --submit.")
        return 0
    config = load_qpu_config(args.config)
    problem = synthetic_problem(args.seed, n=args.n, k=6)
    record = run_qpu(problem, config, mixer=args.mixer, seed=args.seed)
    path = _save([{"kind": "qpu", "data_source": "synthetic_only", **record}], args.output)
    print(json.dumps({"results_file": str(path), "result": record}, ensure_ascii=False, indent=2))
    return 0


def _market_data(args: argparse.Namespace) -> int:
    summary = analyze_market_dataset(
        args.data,
        args.members,
        lookback=args.lookback,
        k=args.k,
        transaction_cost_bps=args.transaction_cost_bps,
    )
    figures = create_market_figures(args.data, args.members, summary, args.figures, args.benchmark)
    report = write_market_report(summary, args.report, figures, args.benchmark)
    print(
        json.dumps(
            {"report_file": str(report), "figure_files": [str(path) for path in figures], "summary": summary},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="agqo", description="Thử nghiệm nghiên cứu AGQO.")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Chạy đối chứng cổ điển và QAOA trên một mẫu tổng hợp.")
    demo.add_argument("--n", type=int, choices=(8, 12, 16), default=8)
    demo.add_argument("--seed", type=int, default=20261012)
    demo.add_argument("--max-evaluations", type=int, default=50)
    demo.add_argument("--model-version", choices=("v0", "v1", "compare"), default="v0")
    demo.add_argument("--transaction-cost-bps", type=float, default=25.0)
    demo.add_argument("--output")
    demo.set_defaults(func=_demo)
    benchmark = commands.add_parser("benchmark", help="Chạy H2 trên tối đa 12×3 bài toán.")
    benchmark.add_argument("--limit", type=int, choices=range(1, 13), default=12)
    benchmark.add_argument("--max-evaluations", type=int, default=50)
    benchmark.add_argument("--output")
    benchmark.set_defaults(func=_benchmark)
    qpu = commands.add_parser("qpu", help="Chạy nhánh IBM Runtime; cần cờ --submit.")
    qpu.add_argument("--config", default="config/qpu.toml")
    qpu.add_argument("--n", type=int, choices=(8, 12), default=8)
    qpu.add_argument("--seed", type=int, default=20261012)
    qpu.add_argument("--mixer", choices=("X", "XY"), default="XY")
    qpu.add_argument("--submit", action="store_true")
    qpu.add_argument("--output")
    qpu.set_defaults(func=_qpu)
    market = commands.add_parser(
        "market-data",
        help="Phân tích snapshot OHLCV VN30 và VN-Index đã lưu trong dự án.",
    )
    market.add_argument(
        "--data",
        default="data/vn30_snapshot_20261002/ohlcv_daily.csv",
        help="Tệp OHLCV chuẩn hóa đã tải.",
    )
    market.add_argument(
        "--members",
        default="data/vn30_snapshot_20261002/members.csv",
        help="Danh sách 30 thành phần tại ngày chụp.",
    )
    market.add_argument("--lookback", type=int, default=252)
    market.add_argument("--k", type=int, default=6)
    market.add_argument("--transaction-cost-bps", type=float, default=25.0)
    market.add_argument("--report", default="results/BAO_CAO_KET_QUA.md")
    market.add_argument("--figures", default="results/figures/vn30")
    market.add_argument(
        "--benchmark",
        default="results/qaoa_h2_20261013.jsonl",
        help="Tệp kết quả QAOA tổng hợp; bỏ qua phần đối chiếu nếu đường dẫn không tồn tại.",
    )
    market.set_defaults(func=_market_data)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
