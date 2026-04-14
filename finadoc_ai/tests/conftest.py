"""Shared fixtures for finadoc_ai tests."""
import sys
import os

# Make the finadoc_ai package importable when pytest is run from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous FastAPI test client — no live network calls required."""
    return TestClient(app)
