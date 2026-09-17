# tests/conftest.py
"""
Pytest configuration and shared fixtures for SovereignForge tests.
"""
import sys
from pathlib import Path

# Add backend to Python path so test files can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest


@pytest.fixture(scope="session")
def backend_root():
    return Path(__file__).parent.parent / "backend"


@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).parent.parent


def make_llm_stream(responses: list[str]):
    """
    Build a stand-in for registry.generate_stream that returns the next canned
    response on each call (repeating the last one), split into a few chunks
    the way Ollama streams tokens.
    """
    calls = {"n": 0}

    async def _stream(*args, **kwargs):
        text = responses[min(calls["n"], len(responses) - 1)]
        calls["n"] += 1
        step = max(1, len(text) // 3)
        for i in range(0, len(text), step):
            yield text[i:i + step]

    _stream.calls = calls
    return _stream


@pytest.fixture
def allowed_path():
    """A file path inside the guardrail's allowed root (need not exist)."""
    from config import UPLOAD_DIR
    return lambda name: str(Path(UPLOAD_DIR) / name)
