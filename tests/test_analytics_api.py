"""Integration tests for fleet analytics, anomalies, and health probes."""

from fastapi.testclient import TestClient


def test_fleet_overview(client: TestClient):
    """Test fleet overview metrics aggregation."""
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    overview = response.json()

    assert overview["total_meters"] == 403
    assert overview["total_transformers"] == 40
    assert overview["total_transformer_capacity_kva"] > 0
    assert "Installed" in overview["status_distribution"]
    assert "HPL" in overview["make_distribution"]
    assert "single" in overview["phase_distribution"]


def test_fleet_anomalies(client: TestClient):
    """Test fleet anomalies detection."""
    response = client.get("/api/v1/analytics/anomalies")
    assert response.status_code == 200
    anomalies = response.json()

    assert anomalies["faulty_meter_count"] == 90
    assert len(anomalies["faulty_meter_ids"]) == 90


def test_health_check(client: TestClient):
    """Test liveness probe endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sync_status(client: TestClient):
    """Test synchronization status and cache age."""
    response = client.get("/api/v1/sync/status")
    assert response.status_code == 200
    status = response.json()

    assert status["status"] == "healthy"
    assert status["indexed_meters"] == 403
    assert status["indexed_transformers"] == 40
