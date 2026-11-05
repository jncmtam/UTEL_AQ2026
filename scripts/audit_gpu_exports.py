"""Read-only independent QPY/QASM audit of a downloaded bounded GPU study.

No optimizer, LLM, simulator search, or paid service is invoked. The full-state
crosscheck retains the 16-physical-qubit cap, including preparation workspace.
Larger exports receive hash/identity checks and an explicit statevector skip.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from qiskit import qasm3, qpy
from qiskit.quantum_info import Statevector

from agqo.research.data import sha, write_json
from agqo.research.preparation import workspace_for
from agqo.research.quantum import execute
from agqo.synthesis.profile import digest


MAX_PHYSICAL_QUBITS = 16
TOLERANCE = 1e-9


def read(path):
    return json.loads(path.read_text())


def audit(directory):
    root = Path(directory)
    evaluation = root / "evaluation"
    manifest = read(root / "orchestration" / "download_manifest.json")
    checked, manifest_failures = 0, []
    for name, expected in manifest.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            manifest_failures.append({"file": name, "reason": "Unsafe relative path."})
            continue
        target = evaluation / relative
        if not target.is_file() or sha(target) != expected:
            manifest_failures.append({"file": name, "reason": "Missing file or SHA256 mismatch."})
        else:
            checked += 1
    if manifest_failures:
        return {
            "status": "failed",
            "downloaded_files_verified": checked,
            "manifest_failures": manifest_failures,
            "exports": [],
            "new_inference_or_optimizer_runs": 0,
        }

    exports = []
    for folder in sorted((evaluation / "circuits").glob("*/*")):
        if not folder.is_dir():
            continue
        relative = str(folder.relative_to(evaluation))
        row = {"circuit": relative, "status": "failed"}
        try:
            for name in (
                "gate_ir.json", "hamiltonian.json", "angles.json",
                "verification.json", "bound.qpy", "bound.qasm",
            ):
                key = str((folder / name).relative_to(evaluation))
                if key not in manifest:
                    raise ValueError(f"Export artifact is absent from download manifest: {key}")
            ir, h = read(folder / "gate_ir.json"), read(folder / "hamiltonian.json")
            angles, verification = read(folder / "angles.json"), read(folder / "verification.json")
            transport_path = evaluation / "cases" / folder.parent.name / "numerical_transport.json"
            if str(transport_path.relative_to(evaluation)) not in manifest:
                raise ValueError("Original Hamiltonian transport certificate is absent from manifest.")
            transport = read(transport_path)
            h_hash = digest({k: v for k, v in h.items() if k != "hamiltonian_hash"})
            if (
                h_hash != h.get("hamiltonian_hash")
                or ir.get("hamiltonian_hash") != h_hash
                or transport.get("canonical_hamiltonian_hash") != h_hash
                or not transport.get("executed_hamiltonian_bitwise_original")
                or ir.get("problem_hash") != h.get("problem_hash")
                or transport.get("problem_hash") != h.get("problem_hash")
            ):
                raise ValueError("Exported immutable Hamiltonian/source identity is inconsistent.")
            if verification.get("ir_hash") != digest({k: v for k, v in ir.items() if k != "preparation"}):
                raise ValueError("GateIR differs from its independent verification record.")
            if not verification.get("valid") or len(angles) != len(ir["parameters"]):
                raise ValueError("Export is not a verified, fully bound circuit.")
            physical_qubits = h["qubits"] + workspace_for(ir)
            with (folder / "bound.qpy").open("rb") as stream:
                loaded = qpy.load(stream)
            if len(loaded) != 1:
                raise ValueError("Expected exactly one bound QPY circuit.")
            qc = loaded[0]
            qasm_qc = qasm3.loads((folder / "bound.qasm").read_text())
            if (
                qc.num_qubits != physical_qubits
                or qasm_qc.num_qubits != physical_qubits
                or verification["resources"]["qubits"] != physical_qubits
                or qc.parameters or qasm_qc.parameters
            ):
                raise ValueError("Bound export register/parameter metadata is inconsistent.")
            row.update(
                hamiltonian_hash=h_hash,
                original_hamiltonian_identity="passed",
                bound_qpy_and_qasm_parse="passed",
                physical_qubits=physical_qubits,
                preparation_workspace_qubits=workspace_for(ir),
            )
            if physical_qubits > MAX_PHYSICAL_QUBITS:
                row.update(
                    status="skipped_statevector",
                    reason=f"{physical_qubits} physical qubits exceeds frozen full-state cap of {MAX_PHYSICAL_QUBITS}; no full state allocated.",
                    statevector_verified=False,
                )
                exports.append(row)
                continue
            reference = execute(ir, h, angles, max_qubits=MAX_PHYSICAL_QUBITS)
            qpy_state = np.asarray(Statevector.from_instruction(qc).data)
            qasm_state = np.asarray(Statevector.from_instruction(qasm_qc).data)
            # Compiler counter workspace occupies the high appended qubits and
            # must be clean: only its zero block contains the logical reference.
            qpy_leakage = float(np.sum(abs(qpy_state[len(reference):]) ** 2))
            qasm_leakage = float(np.sum(abs(qasm_state[len(reference):]) ** 2))
            qpy_fidelity = float(abs(np.vdot(reference, qpy_state[:len(reference)])) ** 2)
            qasm_fidelity = float(abs(np.vdot(reference, qasm_state[:len(reference)])) ** 2)
            cross_fidelity = float(abs(np.vdot(qpy_state, qasm_state)) ** 2)
            normalization_residual = max(
                float(abs(np.vdot(s, s).real - 1))
                for s in (reference, qpy_state, qasm_state)
            )
            passed = (
                min(qpy_fidelity, qasm_fidelity, cross_fidelity) >= 1 - TOLERANCE
                and max(qpy_leakage, qasm_leakage, normalization_residual) <= TOLERANCE
            )
            row.update(
                status="passed" if passed else "failed",
                statevector_verified=passed,
                qpy_numpy_fidelity=qpy_fidelity,
                qasm_numpy_fidelity=qasm_fidelity,
                qasm_qpy_fidelity=cross_fidelity,
                qpy_workspace_leakage=qpy_leakage,
                qasm_workspace_leakage=qasm_leakage,
                maximum_normalization_residual=normalization_residual,
            )
            if not passed:
                row["reason"] = "Independent bound QPY/QASM statevector comparison exceeded tolerance."
        except Exception as exc:
            row.update(status="failed", reason=f"{type(exc).__name__}: {exc}")
        exports.append(row)
    failures = sum(r["status"] == "failed" for r in exports)
    return {
        "status": "passed_with_explicit_skips" if not failures and exports else "failed",
        "downloaded_files_verified": checked,
        "manifest_hash": digest(manifest),
        "manifest_failures": [],
        "exports": exports,
        "export_count": len(exports),
        "statevectors_verified": sum(r["status"] == "passed" for r in exports),
        "statevectors_skipped": sum(r["status"] == "skipped_statevector" for r in exports),
        "failed_exports": failures,
        "maximum_physical_qubits_for_full_statevector": MAX_PHYSICAL_QUBITS,
        "tolerance": TOLERANCE,
        "new_inference_or_optimizer_runs": 0,
        "quantum_hardware": False,
        "scope": "Artifact and bounded ideal-state correctness only, not financial benefit or large-register full-state verification.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("results/research/live_gpu_optimization_v1"))
    args = parser.parse_args()
    destination = args.directory / "EXPORT_AUDIT.json"
    if destination.exists():
        raise ValueError("Existing export audit retained; use a separate revision for a new audit.")
    result = audit(args.directory)
    write_json(destination, result)
    print(json.dumps({k: v for k, v in result.items() if k != "exports"}, indent=2))
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
