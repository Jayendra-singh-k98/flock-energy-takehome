"""Integration tests for Distribution Transformer endpoints."""

from fastapi.testclient import TestClient


def test_list_transformers(client: TestClient):
    """Test retrieving list of all distribution transformers."""
    response = client.get("/api/v1/transformers")
    assert response.status_code == 200
    dts = response.json()

    assert len(dts) == 40
    first = dts[0]
    assert "code" in first
    assert "capacity_kva" in first
    assert "connected_meters_count" in first
    assert first["connected_meters_count"] > 0


def test_get_transformer_detail(client: TestClient):
    """Test retrieving detail of DT-001 with connected meters."""
    response = client.get("/api/v1/transformers/DT-001")
    assert response.status_code == 200
    dt = response.json()

    assert dt["code"] == "DT-001"
    assert "connected_meters" in dt
    assert len(dt["connected_meters"]) == dt["connected_meters_count"]


def test_get_transformer_not_found(client: TestClient):
    """Test 404 response for invalid transformer code."""
    response = client.get("/api/v1/transformers/DT-9999")
    assert response.status_code == 404
