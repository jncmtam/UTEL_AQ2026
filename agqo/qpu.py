"""Cầu nối IBM Quantum Runtime; chỉ gửi mạch khi người dùng bật cờ xác nhận."""

from __future__ import annotations

import os
import json
import tomllib
import uuid
import fcntl
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.optimize import minimize

from .problem import PortfolioProblem, Qubo, build_qubo, to_ising


PLACEHOLDERS = {"FILL_IN_FROM_PROVIDER", "FILL_IN", "YOUR_BACKEND"}


@dataclass(frozen=True)
class QpuConfig:
    channel: str
    instance: str
    backend: str
    token_env: str
    shots: int
    max_evaluations: int
    max_shots: int
    allow_simulator: bool = False
    ledger_path: str = "outputs/qpu_shot_ledger.json"


def load_qpu_config(path: str | Path) -> QpuConfig:
    """Đọc cấu hình không bí mật; token chỉ được lấy từ biến môi trường."""
    with Path(path).open("rb") as file:
        raw = tomllib.load(file)
    values = raw.get("ibm", {})
    config = QpuConfig(
        channel=str(values.get("channel", "")),
        instance=str(values.get("instance", "")),
        backend=str(values.get("backend", "")),
        token_env=str(values.get("token_env", "IBM_QUANTUM_TOKEN")),
        shots=int(values.get("shots", 512)),
        max_evaluations=int(values.get("max_evaluations", 50)),
        max_shots=int(values.get("max_shots", 800_000)),
        allow_simulator=bool(values.get("allow_simulator", False)),
        ledger_path=str(values.get("ledger_path", "outputs/qpu_shot_ledger.json")),
    )
    validate_qpu_config(config)
    return config


def validate_qpu_config(config: QpuConfig) -> None:
    """Chặn cấu hình mẫu, thiếu token, hoặc ngân sách vượt đề nghị trước khi gọi dịch vụ."""
    required = {"channel": config.channel, "instance": config.instance, "backend": config.backend}
    missing = [key for key, value in required.items() if not value or value in PLACEHOLDERS]
    if missing:
        raise ValueError(f"Cần điền các trường cấu hình QPU: {', '.join(missing)}.")
    if config.shots != 512 or config.max_evaluations < 1 or not 1 <= config.max_shots <= 800_000:
        raise ValueError("Mặc định cần 512 shots, số đánh giá dương và tổng ngân sách không quá 800.000.")
    if not os.environ.get(config.token_env):
        raise ValueError(f"Chưa có khóa truy cập; hãy đặt biến môi trường {config.token_env}.")


def _update_ledger(path: str | Path, update) -> dict:
    """Khóa tệp khi đọc/sửa để hai lệnh chạy đồng thời không vượt ngân sách tổng."""
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger_path.with_suffix(ledger_path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"runs": []}
            update(ledger)
            temporary = ledger_path.with_suffix(ledger_path.suffix + f".{os.getpid()}.tmp")
            temporary.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, ledger_path)
            return ledger
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _reserve_shots(config: QpuConfig) -> str:
    """Dành chỗ theo số lần đo tối đa trước khi gửi; lỗi giữa chừng không giải phóng nhầm."""
    run_id = str(uuid.uuid4())
    planned = config.max_evaluations * config.shots

    def reserve(ledger: dict) -> None:
        used = sum(
            row["actual_shots"] if row["status"] == "complete" else row["reserved_shots"]
            for row in ledger["runs"]
        )
        if used + planned > config.max_shots:
            raise ValueError(
                f"Ngân sách QPU đã dùng/giữ chỗ {used:,}; thêm {planned:,} sẽ vượt trần {config.max_shots:,}."
            )
        ledger["runs"].append(
            {"run_id": run_id, "status": "reserved", "reserved_shots": planned, "actual_shots": None}
        )

    _update_ledger(config.ledger_path, reserve)
    return run_id


def _finalize_shots(config: QpuConfig, run_id: str, actual_shots: int) -> None:
    """Đổi phần giữ chỗ sang số lần đo thực tế sau khi toàn bộ job đã trả về."""
    def finalize(ledger: dict) -> None:
        row = next((item for item in ledger["runs"] if item["run_id"] == run_id), None)
        if row is None:
            raise ValueError("Không tìm thấy lượt chạy đã giữ chỗ trong sổ ngân sách.")
        row.update(status="complete", actual_shots=actual_shots)

    _update_ledger(config.ledger_path, finalize)


def build_parameterized_circuit(
    qubo: Qubo, mixer: str, depth: int, initial_bits: np.ndarray | None = None
):
    """Tạo mạch Qiskit tham số hóa bằng đúng các hệ số Ising đã kiểm thử."""
    try:
        from qiskit import QuantumCircuit
        from qiskit.circuit import ParameterVector
    except ImportError as exc:
        raise RuntimeError("Cài nhánh QPU bằng pip install -e .[qpu].") from exc

    ising = to_ising(qubo)
    beta = ParameterVector("beta", depth)
    gamma = ParameterVector("gamma", depth)
    circuit = QuantumCircuit(qubo.n)
    if mixer == "X":
        circuit.h(range(qubo.n))
    else:
        if initial_bits is None or int(np.sum(initial_bits)) == 0:
            raise ValueError("XY cần một trạng thái đầu khả thi có K bit bật.")
        for q, bit in enumerate(initial_bits):
            if bit:
                circuit.x(q)
    for layer in range(depth):
        # RZ/RZZ thực hiện e^(-i gamma H_C); hằng số Ising chỉ là pha toàn cục.
        for q, field in enumerate(ising.fields):
            if abs(field) > 1e-14:
                circuit.rz(2 * gamma[layer] * field, q)
        for i in range(qubo.n):
            for j in range(i + 1, qubo.n):
                coupling = ising.couplings[i, j]
                if abs(coupling) > 1e-14:
                    circuit.rzz(2 * gamma[layer] * coupling, i, j)
        if mixer == "X":
            circuit.rx(2 * beta[layer], range(qubo.n))
        else:
            # Tích Trotter bậc nhất theo thứ tự vòng; từng cạnh thực hiện exp(-i beta(XX+YY)).
            for i in range(qubo.n):
                j = (i + 1) % qubo.n
                circuit.rxx(2 * beta[layer], i, j)
                circuit.ryy(2 * beta[layer], i, j)
    circuit.measure_all()
    return circuit, tuple(beta) + tuple(gamma)


def _counts_energy(counts: dict[str, int], qubo: Qubo, k: int) -> tuple[float, float, tuple[int, ...] | None]:
    """Chuyển bit đo của Qiskit về chỉ số tài sản và chấm trên cùng hàm QUBO."""
    total, energy, feasible_shots = sum(counts.values()), 0.0, 0
    best_bits, best_score = None, float("inf")
    for bitstring, count in counts.items():
        bits = np.fromiter((int(bit) for bit in bitstring.replace(" ", "")[::-1]), dtype=np.int8)
        energy += qubo.energy(bits) * count
        if int(bits.sum()) == k:
            feasible_shots += count
            score = qubo.energy(bits)
            if score < best_score:
                best_score, best_bits = score, tuple(int(x) for x in bits)
    return energy / total, feasible_shots / total, best_bits


def _two_qubit_gate_metrics(circuit) -> tuple[int, int]:
    """Đếm cổng hai qubit và độ sâu của lớp cổng hai qubit sau biên dịch."""
    qubit_depths = [0] * circuit.num_qubits
    gate_count = 0
    for item in circuit.data:
        if item.operation.num_qubits != 2:
            continue
        gate_count += 1
        qubits = [circuit.find_bit(qubit).index for qubit in item.qubits]
        layer = 1 + max(qubit_depths[index] for index in qubits)
        for index in qubits:
            qubit_depths[index] = layer
    return gate_count, max(qubit_depths, default=0)


def run_qpu(
    problem: PortfolioProblem,
    config: QpuConfig,
    mixer: str = "XY",
    depth: int = 1,
    seed: int = 11,
) -> dict:
    """Tối ưu bằng COBYLA lấy mẫu thật; chỉ gọi sau khi config và backend đã được kiểm tra."""
    validate_qpu_config(config)
    if config.max_evaluations * config.shots > config.max_shots:
        raise ValueError("Một lần chạy vượt ngân sách shots trong cấu hình.")
    try:
        from qiskit.transpiler import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except ImportError as exc:
        raise RuntimeError("Cài nhánh QPU bằng pip install -e .[qpu].") from exc

    mixer = mixer.upper()
    rng = np.random.Generator(np.random.PCG64(seed))
    initial_bits = None
    if mixer == "XY":
        asset_order = rng.permutation(problem.n)
        ordered_problem = PortfolioProblem(
            tuple(problem.tickers[i] for i in asset_order),
            problem.mu[asset_order],
            problem.covariance[np.ix_(asset_order, asset_order)],
            k=problem.k,
            risk_aversion=problem.risk_aversion,
            previous_weights=problem.previous_weights[asset_order],
            transaction_costs=problem.transaction_costs[asset_order],
            rebalances_per_year=problem.rebalances_per_year,
        )
        initial_bits = np.zeros(problem.n, dtype=np.int8)
        initial_bits[: problem.k] = 1
    else:
        asset_order = np.arange(problem.n)
        ordered_problem = problem
    qubo = build_qubo(ordered_problem, mixer=mixer)
    circuit, parameters = build_parameterized_circuit(qubo, mixer, depth, initial_bits)
    service = QiskitRuntimeService(
        channel=config.channel,
        token=os.environ[config.token_env],
        instance=config.instance,
    )
    backend = service.backend(config.backend)
    if backend.num_qubits < problem.n:
        raise ValueError(f"Thiết bị có {backend.num_qubits} qubit, cần {problem.n}.")
    if getattr(backend, "simulator", False) and not config.allow_simulator:
        raise ValueError("Cấu hình đang yêu cầu QPU thật nhưng backend được chọn là máy mô phỏng.")
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pass_manager.run(circuit)
    two_qubit_count, two_qubit_depth = _two_qubit_gate_metrics(isa_circuit)
    sampler = SamplerV2(mode=backend)
    ledger_run_id = _reserve_shots(config)
    start, calls, jobs = perf_counter(), 0, []
    best_bits, best_score, feasible_rates = None, float("inf"), []

    def objective(angles: np.ndarray) -> float:
        nonlocal calls, best_bits, best_score
        calls += 1
        values = {parameter: float(value) for parameter, value in zip(parameters, angles)}
        bound = isa_circuit.assign_parameters(values)
        job = sampler.run([bound], shots=config.shots)
        jobs.append(job.job_id())
        counts = job.result()[0].data.meas.get_counts()
        mean_energy, feasible_rate, candidate = _counts_energy(counts, qubo, problem.k)
        feasible_rates.append(feasible_rate)
        if candidate is not None:
            candidate_array = np.asarray(candidate)
            original_candidate = np.zeros(problem.n, dtype=np.int8)
            original_candidate[asset_order] = candidate_array
            score = problem.score(original_candidate)
            if score < best_score:
                best_bits, best_score = tuple(int(x) for x in original_candidate), score
        return mean_energy

    initial_angles = rng.uniform(-np.pi, np.pi, size=2 * depth)
    result = minimize(
        objective,
        initial_angles,
        method="COBYLA",
        options={"maxiter": config.max_evaluations, "rhobeg": 0.5, "tol": 1e-3},
    )
    _finalize_shots(config, ledger_run_id, calls * config.shots)
    return {
        "backend": config.backend,
        "mixer": mixer,
        "depth": depth,
        "seed": seed,
        "n": problem.n,
        "k": problem.k,
        "risk_aversion": problem.risk_aversion,
        "previous_weights": problem.previous_weights.tolist(),
        "transaction_cost_rates": problem.transaction_costs.tolist(),
        "rebalances_per_year": problem.rebalances_per_year,
        "asset_order": asset_order.tolist(),
        "evaluations": calls,
        "shots_used": calls * config.shots,
        "budget_ledger_run_id": ledger_run_id,
        "mean_feasible_probability": float(np.mean(feasible_rates)),
        "best_feasible_bits": best_bits,
        # Giữ khóa cũ để tương thích nhật ký; giá trị này là mục tiêu danh mục,
        # không phải năng lượng QUBO có thể chứa hạng phạt.
        "best_feasible_qubo_energy": None if best_bits is None else float(best_score),
        "best_feasible_score": None if best_bits is None else float(best_score),
        "best_parameters": [float(value) for value in result.x],
        "job_ids": jobs,
        "elapsed_seconds": perf_counter() - start,
        "circuit_depth": isa_circuit.depth(),
        "two_qubit_gate_count": two_qubit_count,
        "two_qubit_depth": two_qubit_depth,
        "swap_gate_count": int(isa_circuit.count_ops().get("swap", 0)),
        "circuit_operations": {str(key): int(value) for key, value in isa_circuit.count_ops().items()},
    }
