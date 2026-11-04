from pathlib import Path
from qiskit import qpy
with Path(__file__).with_name("parameterized.qpy").open("rb") as stream:
    circuit = qpy.load(stream)[0]
print(circuit)
