from copy import deepcopy
from scripts.summarize_counterfactual_editor import family_signature


def fixture():
    return {"initial_bits": [1, 0, 0], "initialization": [],
        "preparation": {"kind": "dicke_sequential_counter_v1"},
        "layers": [{"cost": {"parameter": "gamma"}, "mixer": [
            {"op": "RXX", "qubits": [0, 1], "angle": {"parameter": "beta", "scale": 2}},
            {"op": "RYY", "qubits": [0, 1], "angle": {"parameter": "beta", "scale": 2}},
            {"op": "RXX", "qubits": [1, 2], "angle": {"parameter": "beta", "scale": 2}},
            {"op": "RYY", "qubits": [1, 2], "angle": {"parameter": "beta", "scale": 2}},
        ]}]}


def test_parameter_renaming_is_not_misreported_as_architecture_discovery():
    old = fixture()
    new = deepcopy(old)
    new["layers"][0]["cost"]["parameter"] = "g_renamed"
    for gate in new["layers"][0]["mixer"]:
        gate["angle"]["parameter"] = "b_renamed"
    assert family_signature(new) == family_signature(old)


def test_changed_sharing_or_overlapping_order_is_a_different_family():
    old = fixture()
    split = deepcopy(old)
    for gate in split["layers"][0]["mixer"][2:]:
        gate["angle"]["parameter"] = "independent_beta"
    assert family_signature(split) != family_signature(old)
    reordered = deepcopy(old)
    pairs = reordered["layers"][0]["mixer"]
    reordered["layers"][0]["mixer"] = pairs[2:] + pairs[:2]
    assert family_signature(reordered) != family_signature(old)
