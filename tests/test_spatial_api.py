"""Integration tests for spatial queries and Haversine proximity calculations."""

from fastapi.testclient import TestClient
from app.services.meter_service import haversine_distance_meters


def test_haversine_distance_calculation():
    """Verify accuracy of Haversine formula on known coordinates."""
    # Jaipur to Delhi (~238 km)
    jaipur_lat, jaipur_lng = 26.9124, 75.7873
    delhi_lat, delhi_lng = 28.6139, 77.2090
    dist_m = haversine_distance_meters(jaipur_lat, jaipur_lng, delhi_lat, delhi_lng)

    assert 230000 < dist_m < 250000


def test_nearby_meters_query(client: TestClient):
    """Test finding meters near Jaipur center."""
    response = client.get("/api/v1/spatial/nearby?latitude=26.9389&longitude=75.8309&radius_meters=3000&limit=10")
    assert response.status_code == 200
    results = response.json()

    assert len(results) > 0
    assert len(results) <= 10
    # Nearest should have smallest distance
    assert results[0]["distance_meters"] <= results[-1]["distance_meters"]
    assert results[0]["distance_meters"] <= 3000.0
    assert "meter" in results[0]
    assert "meter_id" in results[0]["meter"]
