"""Optional: sample an exported AGQO circuit on IBM Quantum hardware (Qiskit Runtime).

Not executed in this repository's results. Requires `pip install qiskit-ibm-runtime`,
an IBM Quantum account (the free Open Plan gives 10 QPU minutes per 28 days) and the
token in the environment variable IBM_QUANTUM_TOKEN. Nothing is submitted unless
`confirm=True` is passed explicitly.

    python -m agqo hardware --qasm results/baseline/circuits/evolve_2026-07-01.qasm \
        --backend ibm_kingston --shots 2000 --confirm
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def run_on_ibm(qasm_path: Path, backend_name: str, shots: int, confirm: bool, out: Path) -> dict:
    from qiskit import qasm2, transpile

    qc = qasm2.loads(Path(qasm_path).read_text(), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    if not confirm:
        return {"submitted": False, "reason": "dry run: pass --confirm to spend QPU time",
                "qubits": qc.num_qubits, "ops": dict(qc.count_ops())}
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=os.environ["IBM_QUANTUM_TOKEN"])
    backend = service.backend(backend_name)
    isa = transpile(qc, backend=backend, optimization_level=3)
    job = SamplerV2(mode=backend).run([isa], shots=shots)
    counts = job.result()[0].data.meas.get_counts()
    rec = {"submitted": True, "backend": backend_name, "job_id": job.job_id(), "shots": shots,
           "isa_two_qubit_gates": int(sum(v for k, v in isa.count_ops().items() if k in ("cz", "ecr", "cx"))),
           "isa_depth": isa.depth(), "counts": counts}
    out.write_text(json.dumps(rec, indent=2))
    return rec
