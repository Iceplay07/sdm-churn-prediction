"""Фикстуры pytest. Один TestClient на сессию — startup (precompute) делается один раз."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
