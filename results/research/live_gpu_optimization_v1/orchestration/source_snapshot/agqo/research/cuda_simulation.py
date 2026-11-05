"""Optional CUDA state evolution over the independently certified conserved basis.

This is an ideal classical quantum simulator, never quantum hardware execution.
Support indexing and pair certification retain the NumPy reference implementation;
state preparation, phase application and exchange updates execute on the selected
torch device. The explicit ``device='cpu'`` mode exists only for unit crosschecks.
Production defaults to CUDA and fails rather than silently falling back to CPU.
"""

from time import perf_counter

import numpy as np

from agqo.synthesis.ir import angle_value
from .symmetry import ConservedBasis


class TorchConservedBasis(ConservedBasis):
    def __init__(self, spec, h, max_states=2_000_000, *, device="cuda"):
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("PyTorch is required for the explicit CUDA executor.") from exc

        self.torch = torch
        self.device = torch.device(device)
        if self.device.type not in {"cpu", "cuda"}:
            raise ValueError("Only explicit CUDA or CPU unit-crosscheck devices are supported.")
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA is required; no CPU simulation fallback is permitted.")
        super().__init__(spec, h, max_states=max_states)
        self.tensor_indices = torch.as_tensor(
            self.indices, dtype=torch.int64, device=self.device
        )
        self._tensor_pairs = {}
        self._z_products = {}
        self._energy_numpy = None
        self._energy_tensor = None
        self._hamiltonian_hash = h.get("hamiltonian_hash")
        self.execute_calls = 0
        self.gate_updates = 0
        self.cuda_stream_elapsed_ms = 0.0
        self.wall_seconds = 0.0

    def tensor_pair(self, q, r=None):
        key = (q, r)
        if key not in self._tensor_pairs:
            left, right = super().pair(q, r)
            self._tensor_pairs[key] = tuple(
                self.torch.as_tensor(v, dtype=self.torch.int64, device=self.device)
                for v in (left, right)
            )
        return self._tensor_pairs[key]

    def _scalar(self, value):
        return self.torch.as_tensor(
            float(value), dtype=self.torch.float64, device=self.device
        )

    def gates(self, state, gates, values):
        torch = self.torch
        i = 0
        while i < len(gates):
            gate = gates[i]
            op, targets = gate["op"], gate["qubits"]
            theta = angle_value(gate["angle"], values) if gate["angle"] else None
            if op in ("RZ", "RZZ"):
                key = tuple(targets)
                if key not in self._z_products:
                    z = torch.ones(len(state), dtype=torch.float64, device=self.device)
                    for q in targets:
                        z *= 1 - 2 * ((self.tensor_indices >> q) & 1)
                    self._z_products[key] = z
                state *= torch.exp(-0.5j * self._scalar(theta) * self._z_products[key])
                i += 1
                self.gate_updates += 1
                continue
            if op in ("RXX", "RYY") and i + 1 < len(gates):
                other = gates[i + 1]
                if (
                    {op, other["op"]} != {"RXX", "RYY"}
                    or sorted(targets) != sorted(other["qubits"])
                    or gate["angle"] != other["angle"]
                ):
                    raise ValueError("Unpaired exchange in CUDA conserved executor.")
                left, right = self.tensor_pair(*targets)
                a, b = state[left].clone(), state[right].clone()
                angle = self._scalar(theta)
                cosine, sine = torch.cos(angle), torch.sin(angle)
                state[left] = cosine * a - 1j * sine * b
                state[right] = cosine * b - 1j * sine * a
                i += 2
                self.gate_updates += 2
                continue
            raise ValueError(f"Gate {op} is not certified in the CUDA conserved executor.")

    def execute(self, ir, h, angles, energy=None):
        from .quantum import cost_values

        if h.get("hamiltonian_hash") != self._hamiltonian_hash:
            raise ValueError("CUDA executor is bound to the original Hamiltonian.")
        started = perf_counter()
        torch = self.torch
        start_event = end_event = None
        if self.device.type == "cuda":
            start_event, end_event = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
            start_event.record(torch.cuda.current_stream(self.device))
        values = {p["id"]: v for p, v in zip(ir["parameters"], angles, strict=True)}
        with torch.no_grad():
            state = torch.zeros(len(self.indices), dtype=torch.complex128, device=self.device)
            initial = sum(int(b) << q for q, b in enumerate(ir["initial_bits"]))
            index = int(np.searchsorted(self.indices, initial))
            if index >= len(self.indices) or self.indices[index] != initial:
                raise ValueError("Initial basis state is outside the declared subspace.")
            state[index] = 1
            prep = ir.get("preparation", {})
            if prep.get("kind") == "dicke_sequential_counter_v1":
                state.zero_()
                state[: self.asset_count] = 1 / np.sqrt(self.asset_count)
            elif prep:
                raise ValueError("Dense Dicke synthesis is a small full-state reference only.")
            else:
                self.gates(state, ir["initialization"], values)
            for q in range(self.n, h["qubits"]):
                left, right = self.tensor_pair(q)
                a, b = state[left].clone(), state[right].clone()
                state[left] = (a + b) / np.sqrt(2)
                state[right] = (a - b) / np.sqrt(2)

            energy = np.asarray(cost_values(h, self.indices) if energy is None else energy)
            if energy.shape != self.indices.shape or not np.all(np.isfinite(energy)):
                raise ValueError("Invalid conserved Hamiltonian energy vector.")
            if self._energy_numpy is None or not np.array_equal(energy, self._energy_numpy):
                self._energy_numpy = energy.copy()
                self._energy_tensor = torch.as_tensor(energy, dtype=torch.float64, device=self.device)
            for layer in ir["layers"]:
                gamma = self._scalar(values[layer["cost"]["parameter"]])
                state *= torch.exp(-1j * gamma * self._energy_tensor)
                self.gates(state, layer["mixer"], values)
                beta = next(
                    g["angle"]["parameter"]
                    for g in layer["mixer"]
                    if g.get("angle") and g["angle"].get("parameter")
                )
                for q in range(self.n, h["qubits"]):
                    left, right = self.tensor_pair(q)
                    a, b = state[left].clone(), state[right].clone()
                    angle = self._scalar(values[beta])
                    cosine, sine = torch.cos(angle), torch.sin(angle)
                    state[left] = cosine * a - 1j * sine * b
                    state[right] = cosine * b - 1j * sine * a
            if end_event is not None:
                end_event.record(torch.cuda.current_stream(self.device))
            result = state.cpu().numpy()
        if end_event is not None:
            end_event.synchronize()
            self.cuda_stream_elapsed_ms += start_event.elapsed_time(end_event)
        self.execute_calls += 1
        self.wall_seconds += perf_counter() - started
        return result

    def metadata(self):
        torch = self.torch
        cuda = self.device.type == "cuda"
        return {
            "executor": "torch_conserved_v1",
            "execution": "ideal_cuda_simulation" if cuda else "cpu_unit_crosscheck_only",
            "device": str(self.device),
            "gpu_name": torch.cuda.get_device_name(self.device) if cuda else None,
            "torch_version": torch.__version__,
            "cuda_runtime": torch.version.cuda,
            "state_dtype": "complex128",
            "simulation_states": len(self.indices),
            "execute_calls": self.execute_calls,
            "gate_updates": self.gate_updates,
            "cuda_stream_elapsed_ms": self.cuda_stream_elapsed_ms if cuda else None,
            "wall_seconds": self.wall_seconds,
            "cpu_fallback": False,
            "host_operations": ["basis_indexing", "pair_certification", "energy_coefficients", "sample_rng", "financial_allocation"],
            "gpu_operations": ["state_preparation", "cost_phase", "exchange_updates", "diagonal_rotations", "slack_updates"] if cuda else [],
            "quantum_hardware": False,
            "preparation_workspace": "Certified clean counter workspace is eliminated in ideal conserved simulation; exported circuits count it.",
        }

    def execution_metadata(self):
        """Shared-search runtime contract; CPU diagnostic mode is never CUDA."""
        return {"cuda": self.device.type == "cuda", **self.metadata()}


def crosscheck_cuda(spec, h, ir, angle_vectors, tolerance=1e-10):
    """Fail before search if actual CUDA amplitudes disagree with NumPy reference."""
    actual = TorchConservedBasis(spec, h)
    reference = ConservedBasis(spec, h)
    checks = []
    for angles in angle_vectors:
        expected = reference.execute(ir, h, angles)
        observed = actual.execute(ir, h, angles)
        residual = float(np.max(abs(observed - expected)))
        norm_residual = float(abs(np.vdot(observed, observed).real - 1))
        checks.append({"max_amplitude_residual": residual, "normalization_residual": norm_residual})
        if residual > tolerance or norm_residual > tolerance:
            raise ValueError(f"CUDA/NumPy crosscheck failed: {checks[-1]}")
    if not checks:
        raise ValueError("At least one CUDA amplitude crosscheck is required.")
    return {"status": "passed", "tolerance": tolerance, "checks": checks, "runtime": actual.metadata()}
