"""Integration tests for Network Hierarchy reconstruction."""

from fastapi.testclient import TestClient


def test_get_full_hierarchy(client: TestClient):
    """Test full 7-tier distribution grid reconstruction."""
    response = client.get("/api/v1/hierarchy")
    assert response.status_code == 200
    data = response.json()

    assert data["total_zones"] == 3
    assert data["total_transformers"] == 40
    assert data["total_meters"] == 403
    assert len(data["root_zones"]) == 3

    # Check top-level zone
    zone1 = next(z for z in data["root_zones"] if z["code"] == "Z-01")
    assert zone1["name"] == "Jaipur Zone 1"
    assert zone1["meter_count"] > 0
    assert len(zone1["children"]) > 0  # Circles


def test_get_hierarchy_node(client: TestClient):
    """Test retrieving subtree for a specific division."""
    response = client.get("/api/v1/hierarchy/division/D-01")
    assert response.status_code == 200
    node = response.json()

    assert node["code"] == "D-01"
    assert node["level"] == "division"
    assert node["meter_count"] > 0
    assert len(node["children"]) > 0  # Subdivisions


def test_get_hierarchy_node_not_found(client: TestClient):
    """Test 404 response for non-existent hierarchy node."""
    response = client.get("/api/v1/hierarchy/division/INVALID_CODE")
    assert response.status_code == 404
