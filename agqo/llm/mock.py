"""Deterministic schema-valid stand-in for unit tests and dry runs.

It is NOT a language model and its outputs are never reported as LLM results:
every log record it produces carries execution="mock".
"""

from __future__ import annotations


def mock_response(req: dict) -> dict:
    return {"answer": 6, "why": "mock"}
