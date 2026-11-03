"""Bounded specialist interface probes: declarative QASM, never generated Python."""

from pathlib import Path
import json, re
import numpy as np
from agqo.synthesis.budget import MODEL_CATALOG, configured_budget, billing_snapshot
from agqo.synthesis.client import SynthesisClient
from agqo.synthesis.profile import digest
from .data import write_json


def check_native(text, task):
    """Reference semantics are computed independently of generated source."""
    from qiskit import qasm3, transpile
    from qiskit.quantum_info import Statevector

    source = text.strip()
    if source.startswith("```"):
        source = re.sub(r"^```[^\n]*\n", "", source)
        source = re.sub(r"\n```\s*$", "", source)
    if len(source) > 16000 or re.search(
        r"\b(while|for|extern|defcal|def|reset|measure)\b", source
    ):
        raise ValueError("Unsupported native program construct or size.")
    if any(v != "stdgates.inc" for v in re.findall(r'include\s+"([^"]+)"', source)):
        raise ValueError("Only the standard gate library is admitted.")
    qc = qasm3.loads(source)
    if qc.num_qubits != 2 or qc.num_clbits or len(qc.data) > 200:
        raise ValueError(
            "Native probe register or gate budget differs from the contract."
        )
    if any(
        item.operation.name not in ("h", "x", "rx", "ry", "rz", "cx", "rzz", "barrier")
        for item in qc.data
    ):
        raise ValueError("Unsupported native probe gate.")
    actual = Statevector.from_instruction(qc).data
    if task == "bell":
        expected = np.array([1, 0, 0, 1], complex) / np.sqrt(2)
    elif task == "cost":
        indices = np.arange(4)
        z0 = 1 - 2 * (indices & 1)
        z1 = 1 - 2 * ((indices >> 1) & 1)
        expected = np.exp(-0.3j * (0.25 * z0 - 0.5 * z1 + 0.75 * z0 * z1)) / 2
    else:
        raise ValueError("Unknown native task.")
    fidelity = float(abs(np.vdot(expected, actual)) ** 2)
    lowered = transpile(
        qc,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=1,
        seed_transpiler=11,
    )
    return {
        "valid": fidelity >= 1 - 1e-9,
        "fidelity": fidelity,
        "cx": int(lowered.count_ops().get("cx", 0)),
        "depth": lowered.depth(),
        "source": source,
    }


def run_probe(directory, mode="modal", model="quasar4"):
    from .runner import cases, evaluate_design
    from .quantum import compile_cost
    from .design import request

    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    prompts = [
        (
            "bell",
            "Prepare (|00>+|11>)/sqrt(2) on exactly two qubits starting in |00>. Use H on qubit 0 then CX from 0 to 1. Omit measurements and classical bits.",
        ),
        (
            "cost",
            "On exactly two qubits starting in |00>, apply H to each then exp(-i*0.3*(0.25 Z0 - 0.5 Z1 + 0.75 Z0 Z1)). Use RZ and CX for the diagonal unitary. Omit measurements and classical bits. Angles are radians. Global phase is irrelevant.",
        ),
    ]
    requests = []
    for task, prompt in prompts:
        item = {
            "system": "Return only a complete OpenQASM 3.0 program, including stdgates.inc. No Python or explanation.",
            "payload": prompt,
            "schema": None,
            "max_tokens": 2048,
            "seed": 11,
            "temperature": 0.0,
        }
        item["request_hash"] = digest(item)
        requests.append(item)
    name, spec = cases()[0]
    h = compile_cost(spec, True)
    requests.append(request(spec, h, seed=11))
    # Positive controls establish the parser and independent state checks before inference.
    assert check_native(
        'OPENQASM 3.0; include "stdgates.inc"; qubit[2] q; h q[0]; cx q[0],q[1];',
        "bell",
    )["valid"]
    assert check_native(
        'OPENQASM 3.0; include "stdgates.inc"; qubit[2] q; h q[0]; h q[1]; rz(0.15) q[0]; rz(-0.3) q[1]; cx q[0],q[1]; rz(0.45) q[1]; cx q[0],q[1];',
        "cost",
    )["valid"]
    protocol = {
        "version": "specialist-interface-v1",
        "model": MODEL_CATALOG[model],
        "tasks": ["native_bell", "native_cost", "gate_ir_transfer_n6"],
        "requests": requests,
        "repairs": 0,
        "purpose": "native_interface_and_transfer_diagnostic_not_paper_replication_or_model_qualification",
        "evidence_protocol": "docs/research/IMPLEMENTATION_PROTOCOL.md",
        "inference_dtype": "bfloat16",
    }
    if (path / "protocol.json").exists() and json.loads(
        (path / "protocol.json").read_text()
    ) != protocol:
        raise ValueError("Frozen probe differs; use another directory.")
    write_json(path / "protocol.json", protocol)
    before = billing_snapshot() if mode == "modal" else None
    client = SynthesisClient(
        model,
        mode,
        path / "inference",
        ledger=configured_budget(ledger_path=str(path / "budget.json")),
        prefetch=True,
    )
    answers = client.batch(requests)
    records = []
    for index, answer in enumerate(answers):
        record = {"task": protocol["tasks"][index], "inference": answer, "valid": False}
        if answer.get("status") == "ok":
            try:
                if index < 2:
                    record.update(check_native(answer["response"], prompts[index][0]))
                    target = path / "circuits" / record["task"]
                    target.mkdir(parents=True, exist_ok=True)
                    (target / "program.qasm").write_text(record["source"])
                else:
                    result = evaluate_design(
                        spec,
                        h,
                        answer["response"],
                        (11,),
                        12,
                        128,
                        path / "circuits" / record["task"],
                    )
                    record.update(result)
                    record["valid"] = result["verification"]["valid"]
            except Exception as exc:
                record["error"] = str(exc)
        else:
            record["error"] = answer.get("reason", answer.get("status"))
        records.append(record)
    write_json(path / "records.json", records)
    write_json(
        path / "cost_report.json",
        {
            "billing_before": before,
            "billing_after": billing_snapshot() if mode == "modal" else None,
            "reservation_is_not_invoice": True,
            "failed_proposals_included": True,
        },
    )
    lines = [
        "# Specialist interface probe",
        "",
        "This is a three-request interface diagnostic. Native code and GateIR transfer are different tasks. No production model is qualified.",
        "",
        "| Task | Valid | Error |",
        "|---|---|---|",
    ]
    for row in records:
        lines.append(f"| {row['task']} | {row['valid']} | {row.get('error', '')} |")
    (path / "RESULTS.md").write_text("\n".join(lines) + "\n")
    complete_probe_contract(path)
    return {
        "model": model,
        "valid": sum(r["valid"] for r in records),
        "total": len(records),
        "output": str(path),
    }


def complete_probe_contract(directory):
    """Derive common artifacts from saved evidence, without inference or rescoring."""
    import csv

    path = Path(directory)
    protocol = json.loads((path / "protocol.json").read_text())
    records = json.loads((path / "records.json").read_text())
    write_json(
        path / "dataset_manifest.json",
        {
            "version": "specialist-probe-data-v1",
            "dataset_kind": "analytic_quantum_and_synthetic_finance",
            "financial_claims_allowed": False,
            "protocol_hash": digest(protocol),
            "tasks": protocol["tasks"],
        },
    )
    decisions = [
        {
            "task": r["task"],
            "status": "valid" if r["valid"] else "failed",
            "financial_decision": r.get("runs", [{}])[0].get("allocation")
            if r.get("runs")
            else None,
        }
        for r in records
    ]
    (path / "decisions.jsonl").write_text(
        "".join(json.dumps(r, allow_nan=False) + "\n" for r in decisions)
    )
    with (path / "metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["task", "valid", "fidelity", "error"]
        )
        writer.writeheader()
        writer.writerows({k: r.get(k) for k in writer.fieldnames} for r in records)
    (path / "circuits").mkdir(exist_ok=True)
    (path / "PROGRESS.md").write_text(
        "# Specialist probe progress\n\nBounded batch complete; no production model is qualified. All raw responses and failures are preserved. No automatic repair or model-size escalation is scheduled.\n"
    )
