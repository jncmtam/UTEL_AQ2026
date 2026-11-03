"""Decoder compatibility adapter; semantic validator retains the full schema."""
from copy import deepcopy


def decoder_schema(schema):
    """uniqueItems is not supported by vLLM's grammar backends in this runtime.

    Removing it affects token masking only. Duplicate wires/assets are still
    rejected by jsonschema plus the independent quantum verifier before execution.
    """
    def lower(node):
        if isinstance(node, dict):
            return {key: lower(value) for key, value in node.items() if key != "uniqueItems"}
        if isinstance(node, list):
            return [lower(value) for value in node]
        return node
    return lower(deepcopy(schema))
