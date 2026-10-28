"""Integration and contract tests for smart meter endpoints."""

from fastapi.testclient import TestClient


def test_list_meters_default(client: TestClient):
    """Test listing meters with default pagination."""
    response = client.get("/api/v1/meters")
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) == 20
    assert data["pagination"]["total_items"] == 403
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["has_next"] is True


def test_list_meters_filtering(client: TestClient):
    """Test multi-attribute filtering (make and status)."""
    response = client.get("/api/v1/meters?make=HPL&install_status=Installed")
    assert response.status_code == 200
    data = response.json()

    for item in data["data"]:
        assert item["make"] == "HPL"
        assert item["install_status"] == "Installed"


def test_list_meters_search(client: TestClient):
    """Test substring search by meter ID."""
    response = client.get("/api/v1/meters?q=J100000")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1
    assert data["data"][0]["meter_id"] == "J100000"


def test_get_single_meter(client: TestClient):
    """Test retrieving detail of a specific meter."""
    response = client.get("/api/v1/meters/J100000")
    assert response.status_code == 200
    data = response.json()

    assert data["meter_id"] == "J100000"
    assert "hierarchy" in data
    assert "dt_code" in data
    assert data["hierarchy"]["zone"]["name"] == "Jaipur Zone 1"


def test_get_meter_not_found(client: TestClient):
    """Test 404 response for non-existent meter ID."""
    response = client.get("/api/v1/meters/NON_EXISTENT_ID")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_meter_geo(client: TestClient):
    """Test coordinates endpoint for a meter."""
    response = client.get("/api/v1/meters/J100000/geo")
    assert response.status_code == 200
    geo = response.json()
    assert "latitude" in geo
    assert "longitude" in geo
    assert isinstance(geo["latitude"], float)


def test_get_meter_energy(client: TestClient):
    """Test telemetry interval consumption for a meter."""
    response = client.get("/api/v1/meters/J100000/energy")
    assert response.status_code == 200
    energy = response.json()

    assert energy["meter_id"] == "J100000"
    assert energy["reading_count"] > 0
    assert len(energy["readings"]) > 0
    assert "kwh" in energy["readings"][0]
    assert "volt_r" in energy["readings"][0]
