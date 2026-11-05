"""GateIR schema, safe angle AST, and free-form gate schedule validation."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json
import numpy as np
from jsonschema import Draft202012Validator

from .profile import digest


@dataclass(frozen=True)
class Limits:
    max_qubits: int = 12
    max_layers: int = 4
    max_parameters: int = 16
    max_synthesis_gates: int = 512
    max_two_qubit_gates: int = 40000
    max_transpiled_depth: int = 80000


ANGLE = {"type": "object", "additionalProperties": False, "properties": {
    "parameter": {"anyOf": [{"type": "string", "pattern": "^[a-z][a-z0-9_]{0,31}$"}, {"type": "null"}]},
    "scale": {"type": "number", "minimum": -16, "maximum": 16},
    "offset": {"type": "number", "minimum": -6.284, "maximum": 6.284}}, "required": ["parameter", "scale", "offset"]}
GATE = {"type": "object", "additionalProperties": False, "properties": {
    "op": {"type": "string", "enum": ["H", "X", "RX", "RY", "RZ", "CX", "RXX", "RYY", "RZZ"]},
    "qubits": {"type": "array", "items": {"type": "integer", "minimum": 0}, "minItems": 1, "maxItems": 2, "uniqueItems": True},
    "angle": {"anyOf": [ANGLE, {"type": "null"}]}}, "required": ["op", "qubits", "angle"]}
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "version": {"const": "gate-ir-v1"}, "problem_hash": {"type": "string"}, "hamiltonian_hash": {"type": "string"},
    "qubit_to_asset": {"type": "array", "items": {"type": "integer", "minimum": 0}, "uniqueItems": True, "minItems": 1, "maxItems": 12},
    "mode": {"enum": ["preserve_cardinality", "penalty"]},
    "initial_bits": {"type": "array", "items": {"type": "integer", "enum": [0, 1]}, "minItems": 1, "maxItems": 12},
    "parameters": {"type": "array", "minItems": 1, "maxItems": 16, "items": {
        "type": "object", "additionalProperties": False, "properties": {
            "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,31}$"}, "kind": {"enum": ["cost", "mixer", "initialization"]},
            "initial": {"anyOf": [{"type": "number", "minimum": -6.284, "maximum": 6.284}, {"type": "null"}]}}, "required": ["id", "kind", "initial"]}},
    "initialization": {"type": "array", "maxItems": 128, "items": GATE},
    "layers": {"type": "array", "minItems": 1, "maxItems": 4, "items": {
        "type": "object", "additionalProperties": False, "properties": {
            "cost": {"type": "object", "additionalProperties": False, "properties": {
                "op": {"const": "COST"}, "parameter": {"type": "string"}, "hamiltonian_hash": {"type": "string"}},
                "required": ["op", "parameter", "hamiltonian_hash"]},
            "mixer": {"type": "array", "minItems": 1, "maxItems": 256, "items": GATE}}, "required": ["cost", "mixer"]}},
    "rationale": {"type": "array", "maxItems": 8, "items": {"type": "object", "additionalProperties": False,
        "properties": {"feature_ids": {"type": "array", "items": {"type": "string"}}, "decision": {"type": "string", "maxLength": 500}},
        "required": ["feature_ids", "decision"]}}},
    "required": ["version", "problem_hash", "hamiltonian_hash", "qubit_to_asset", "mode", "initial_bits", "parameters", "initialization", "layers", "rationale"]}


def angle_value(angle, parameters):
    return angle["offset"] + angle["scale"] * (0.0 if angle["parameter"] is None else parameters[angle["parameter"]])


def _preserves(gates):
    """Conservation certificate from trusted commuting diagonal / XX+YY primitives."""
    i = 0
    while i < len(gates):
        gate = gates[i]
        if gate["op"] in {"RZ", "RZZ"}:
            i += 1; continue
        if gate["op"] in {"RXX", "RYY"} and i + 1 < len(gates):
            other = gates[i + 1]
            if {gate["op"], other["op"]} == {"RXX", "RYY"} and sorted(gate["qubits"]) == sorted(other["qubits"]) and gate["angle"] == other["angle"]:
                i += 2; continue
        return False, i
    return True, None


def check_ir(ir, problem, hamiltonian, limits=Limits(), schema=None):
    errors, warnings = [], []
    for error in Draft202012Validator(SCHEMA if schema is None else schema).iter_errors(ir):
        errors.append({"code": "schema", "path": "/".join(map(str, error.path)), "message": error.message[:400]})
    if errors:
        return {"valid": False, "errors": errors[:16], "warnings": []}
    # JSON numeric infinities are rejected even when supplied as in-memory Python values.
    try:
        json.dumps(ir, allow_nan=False)
    except (TypeError, ValueError):
        errors.append({"code": "nonfinite", "path": "", "message": "All constants must be finite JSON numbers."})
    def fail(code, path, message):
        errors.append({"code": code, "path": path, "message": message})
    n = problem.n
    if n > limits.max_qubits or len(ir["layers"]) > limits.max_layers:
        fail("budget", "layers", "Qubit/layer budget exceeded.")
    if ir["problem_hash"] != problem.fingerprint() or ir["hamiltonian_hash"] != hamiltonian["hamiltonian_hash"]:
        fail("identity", "problem_hash", "Financial or Hamiltonian identity changed.")
    if sorted(ir["qubit_to_asset"]) != list(range(n)) or len(ir["initial_bits"]) != n:
        fail("mapping", "qubit_to_asset", "Register must map each asset exactly once.")
    params = {p["id"]: p["kind"] for p in ir["parameters"]}
    if len(params) != len(ir["parameters"]) or len(params) > limits.max_parameters:
        fail("parameters", "parameters", "Duplicate parameter or parameter budget exceeded.")
    used = set()
    all_stages = [("initialization", ir["initialization"], "initialization")]
    for index, layer in enumerate(ir["layers"]):
        cost = layer["cost"]
        if cost["hamiltonian_hash"] != hamiltonian["hamiltonian_hash"] or params.get(cost["parameter"]) != "cost":
            fail("cost", f"layers/{index}/cost", "COST requires the canonical Hamiltonian and declared cost parameter.")
        used.add(cost["parameter"])
        all_stages.append((f"layers/{index}/mixer", layer["mixer"], "mixer"))
        if ir["mode"] == "preserve_cardinality":
            ok, position = _preserves(layer["mixer"])
            if not ok:
                fail("conservation", f"layers/{index}/mixer/{position}", "Unproven cardinality preservation. Use adjacent RXX/RYY with identical angle/qubits, or diagonal RZ/RZZ.")
    gate_count = 0
    for path, gates, kind in all_stages:
        gate_count += len(gates)
        for index, gate in enumerate(gates):
            op, targets, angle = gate["op"], gate["qubits"], gate["angle"]
            expected = 2 if op in {"CX", "RXX", "RYY", "RZZ"} else 1
            if len(targets) != expected or any(type(q) is not int or q >= n for q in targets):
                fail("gate_target", f"{path}/{index}", "Wrong arity or qubit outside register.")
            if op in {"H", "X", "CX"}:
                if angle is not None:
                    fail("gate_angle", f"{path}/{index}", "Nonrotation gate must have angle=null.")
            elif angle is None:
                fail("gate_angle", f"{path}/{index}", "Rotation requires an angle AST.")
            elif angle["parameter"] is not None:
                used.add(angle["parameter"])
                if params.get(angle["parameter"]) != kind:
                    fail("parameter_kind", f"{path}/{index}", "Gate may reference only a parameter for its stage.")
    if ir["mode"] == "preserve_cardinality":
        # Constant initialization is checked numerically on its actual state. A
        # parameterized initialization needs an analytic certificate as well.
        if any(g.get("angle") and g["angle"]["parameter"] for g in ir["initialization"]):
            certified, _ = _preserves(ir["initialization"])
            if not certified:
                fail("initialization_conservation", "initialization", "Uncertified parameterized preparation.")
    if gate_count > limits.max_synthesis_gates:
        fail("budget", "gates", "LLM gate budget exceeded; cost gates are counted after lowering too.")
    if set(params) != used:
        fail("unused_parameter", "parameters", "Every declaration must be referenced; unknown references are forbidden.")
    known_features = {"CORRELATION", "CLUSTERS", "SPECTRUM", "OBJECTIVE_TERMS", "INCUMBENT", "STABILITY"}
    for index, rationale in enumerate(ir["rationale"]):
        if not set(rationale["feature_ids"]) <= known_features:
            fail("feature_reference", f"rationale/{index}", "Unknown data feature identifier.")
    if ir["mode"] == "preserve_cardinality" and any(g.get("angle") and g["angle"]["parameter"] for g in ir["initialization"]):
        certified, _ = _preserves(ir["initialization"])
        if not certified or sum(ir["initial_bits"]) != problem.k:
            fail("initialization_conservation", "initialization", "Parameterized initialization must carry an analytic conservation certificate.")
    if len(ir["layers"]) == 1 and not ir["initialization"]:
        warnings.append({"code": "inactive_first_cost", "message": "Basis initialization: first COST is only a global phase; p=1 is a diagnostic baseline."})
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "conservation_certificate": "trusted_diagonal_and_paired_exchange" if ir["mode"] == "preserve_cardinality" and not errors else None,
            "synthesis_gate_count": gate_count, "declared_parameters": len(params),
            "ir_hash": None if any(e["code"] == "nonfinite" for e in errors) else digest(ir), "limits": asdict(limits)}
