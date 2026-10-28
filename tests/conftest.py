"""Pytest configuration and test fixtures."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_meter_service


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Create test client for the FastAPI application."""
    # Pre-sync meter service before running tests
    meter_service = get_meter_service()
    meter_service.sync_all(force=False)
    with TestClient(app) as test_client:
        yield test_client
