# Urja Meter Ops Modern API Bridge

[![Tests](https://img.shields.io/badge/tests-21%20passed-10b981.svg)]()
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1.0-3b82f6.svg)](openapi.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-06b6d4.svg)]()
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)]()

A clean, resilient, fully documented REST API service and modern operational dashboard built over the legacy **Urja Meter Ops** internal smart-meter portal (`https://urja-ops.flockenergy.tech`).

This bridge transforms an ageing, click-only utility web portal into a developer-ready programmatic API service with sub-millisecond query performance, reconstructed 7-tier distribution hierarchy, geospatial proximity search, time-series telemetry analysis, and an interactive operational dashboard.

---

## Quick Links to Key Deliverables

- **[PROTOCOL.md](PROTOCOL.md)** — Comprehensive write-up on reverse-engineering the portal, authentication quirks, the cryptographic HMAC bulk export protocol, and schema variations.
- **[REFLECTION.md](REFLECTION.md)** — Architectural reflections, assumptions, lessons learned, and scaling limits analysis.
- **[openapi.json](openapi.json)** — Standard OpenAPI (3.1.0) specification describing all 14 endpoints and schemas.
- **Interactive Documentation** — Available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc).
- **Modern Web Dashboard** — Available at `http://localhost:8000/` (Fleet Explorer, Map, Telemetry Charts, Hierarchy).

---

## Table of Contents

1. [Architecture & How It Works](#architecture--how-it-works)
2. [Project Structure](#project-structure)
3. [Prerequisites & Installation](#prerequisites--installation)
4. [Running the Application](#running-the-application)
5. [Running the Automated Tests](#running-the-automated-tests)
6. [Sample API Requests](#sample-api-requests)
7. [Features & Optional Extensions Implemented](#features--optional-extensions-implemented)
8. [Design Decisions & Trade-Offs](#design-decisions--trade-offs)
9. [What Was Intentionally Left Out](#what-was-intentionally-left-out)

---

## Architecture & How It Works

```
                                      +---------------------------------------------+
                                      |     Upstream Legacy Portal                  |
                                      |     https://urja-ops.flockenergy.tech       |
                                      +---------------------------------------------+
                                                 ▲                 ▲
                                  HMAC Signed    |                 |   Interval
                                  Bulk Export    |                 |   Telemetry
                                                 ▼                 ▼
+-----------------------------------------------------------------------------------+
|                        Urja Meter Ops API Service (FastAPI)                       |
|                                                                                   |
|  +------------------------+    +-----------------------+    +------------------+  |
|  |     PortalClient       |--->|      MeterService     |<---| AnalyticsService |  |
|  | - SvelteKit CSRF Bypass|    | - Memory Cache (TTL)  |    +------------------+  |
|  | - Cookie Jar Mgt       |    | - Spatial Proximity   |                          |
|  | - HMAC-SHA256 Signer   |    | - Inverted Indexing   |    +------------------+  |
|  | - Auto Re-auth Mutex   |    +-----------------------+--->| HierarchyService |  |
|  +------------------------+                |                | - 7-Tier Tree    |  |
|                                            ▼                +------------------+  |
|                          +-----------------------------------+                    |
|                          |     RESTful Router (/api/v1)      |                    |
|                          +-----------------------------------+                    |
+--------------------------------------------|--------------------------------------+
                                             ▼
                     +---------------------------------------+
                     | Downstream Consumers & Modern Web App |
                     | - Product & Data Teams (REST / JSON)  |
                     | - OpenAPI Docs (Swagger / ReDoc)      |
                     | - Interactive Leaflet & Chart Web UI  |
                     +---------------------------------------+
```

1. **Resilient Session Management:** The service transparently manages upstream authentication using the provided credentials (`operator@urja.local`). It handles SvelteKit's CSRF Origin header check, extracts the `__Secure-better-auth.session_token` cookie, and auto-renews expired sessions on 401/403 responses.
2. **Cryptographic Synchronization:** Instead of scraping 403 individual HTML pages, the service reverse-engineers the portal's HMAC-SHA256 signature algorithm against `/portal/keys` and ingests the complete 403-meter dataset in a single bulk export call.
3. **In-Memory Query & Spatial Engine:** The indexed dataset allows instantaneous multi-attribute filtering (make, phase, status, DT, feeder, zone) and spatial radius search via the Haversine formula.
4. **Data Normalization:** Unifies legacy parameter arrays and modern `v2` escaped JSON schemas into typed, validated Pydantic models.

---

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── config.py                 # Environment and application configuration
│   ├── dependencies.py           # Dependency injection container
│   ├── main.py                   # FastAPI app entry point, lifecycle, CORS, static mounts
│   ├── client/
│   │   ├── __init__.py
│   │   └── portal_client.py      # Resilient portal client (auth, CSRF origin, HMAC signing)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── common.py             # Pagination, envelope, and health check models
│   │   ├── meter.py              # Meter, Geo, Hierarchy, EnergyReading models
│   │   ├── transformer.py        # Distribution Transformer specifications
│   │   ├── hierarchy.py          # 7-tier distribution network tree models
│   │   └── analytics.py          # Fleet overview and anomaly models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── meter_service.py      # In-memory index, search, spatial radius, cache
│   │   ├── transformer_service.py# DT queries and asset load aggregation
│   │   ├── hierarchy_service.py  # Network tree reconstruction and navigation
│   │   └── analytics_service.py  # Grid health indicators and fleet summaries
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py         # API v1 aggregator
│   │       ├── meters.py         # Meter search, detail, energy, and geo routes
│   │       ├── transformers.py   # Transformer listing and detail routes
│   │       ├── hierarchy.py      # Network tree routes
│   │       ├── spatial.py        # Haversine proximity query routes
│   │       ├── analytics.py      # Fleet metrics and anomaly routes
│   │       └── sync.py           # On-demand refresh and health routes
│   └── static/
│       ├── index.html            # Modern web dashboard HTML
│       ├── styles.css            # Dark slate utility theme styling
│       └── app.js                # Dashboard client (Map, Charts, Tree, Search)
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Test client fixtures and startup configuration
│   ├── test_client.py            # PortalClient and HMAC signing unit tests
│   ├── test_meters_api.py        # Meter listing, filtering, detail, and energy tests
│   ├── test_transformers_api.py  # Transformer endpoint tests
│   ├── test_hierarchy_api.py     # Network tree reconstruction tests
│   ├── test_spatial_api.py       # Spatial Haversine distance and radius query tests
│   └── test_analytics_api.py     # Fleet analytics and health check tests
├── .env.example                  # Environment configuration template
├── .gitignore                    # Python git ignore rules
├── openapi.json                  # Exported OpenAPI 3.1.0 specification
├── pytest.ini                    # Pytest settings and pythonpath configuration
├── requirements.txt              # Production and test dependencies
├── PROTOCOL.md                   # Portal reverse-engineering technical write-up
├── REFLECTION.md                 # 5 reflection answers & scalability analysis
└── README.md                     # Main user guide and documentation
```

---

## Prerequisites & Installation

### Requirements
- Python 3.10+ (tested on Python 3.12)
- Network connectivity to `https://urja-ops.flockenergy.tech`

### 1. Clone the Repository
```bash
git clone <repository_url>
cd "Flock Energy Assignment"
```

### 2. Create and Activate Virtual Environment (Recommended)
```bash
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
The service operates with sensible defaults out of the box. To customize settings, copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration values:
- `PORTAL_BASE_URL`: `https://urja-ops.flockenergy.tech`
- `PORTAL_USERNAME`: `operator@urja.local`
- `PORTAL_PASSWORD`: `urja-ops-2026`
- `CACHE_TTL_SECONDS`: `900` (15 minutes)
- `PORT`: `8000`

---

## Running the Application

Start the service using `uvicorn`:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once running:
- **Web Dashboard:** Open `http://localhost:8000/` in your browser.
- **Interactive Swagger UI:** Open `http://localhost:8000/docs` in your browser.
- **ReDoc Documentation:** Open `http://localhost:8000/redoc` in your browser.
- **Raw OpenAPI Schema:** `http://localhost:8000/openapi.json`

---

## Running the Automated Tests

The test suite contains 21 unit, integration, and contract tests covering all API endpoints, authentication flows, HMAC signing, spatial mathematics, and edge cases.

Execute the test suite with:
```bash
python -m pytest -v
```

Expected output:
```text
============================= test session starts =============================
tests/test_analytics_api.py::test_fleet_overview PASSED                  [  4%]
tests/test_analytics_api.py::test_fleet_anomalies PASSED                 [  9%]
tests/test_analytics_api.py::test_health_check PASSED                    [ 14%]
tests/test_analytics_api.py::test_sync_status PASSED                     [ 19%]
tests/test_client.py::test_hmac_signature_generation PASSED              [ 23%]
tests/test_client.py::test_client_headers PASSED                         [ 28%]
tests/test_hierarchy_api.py::test_get_full_hierarchy PASSED              [ 33%]
tests/test_hierarchy_api.py::test_get_hierarchy_node PASSED              [ 38%]
tests/test_hierarchy_api.py::test_get_hierarchy_node_not_found PASSED    [ 42%]
tests/test_meters_api.py::test_list_meters_default PASSED                [ 47%]
tests/test_meters_api.py::test_list_meters_filtering PASSED              [ 52%]
tests/test_meters_api.py::test_list_meters_search PASSED                 [ 57%]
tests/test_meters_api.py::test_get_single_meter PASSED                   [ 61%]
tests/test_meters_api.py::test_get_meter_not_found PASSED                [ 66%]
tests/test_meters_api.py::test_get_meter_geo PASSED                      [ 71%]
tests/test_meters_api.py::test_get_meter_energy PASSED                   [ 76%]
tests/test_spatial_api.py::test_haversine_distance_calculation PASSED    [ 80%]
tests/test_spatial_api.py::test_nearby_meters_query PASSED               [ 85%]
tests/test_transformers_api.py::test_list_transformers PASSED            [ 90%]
tests/test_transformers_api.py::test_get_transformer_detail PASSED       [ 95%]
tests/test_transformers_api.py::test_get_transformer_not_found PASSED    [100%]

============================= 21 passed in 2.76s ==============================
```

---

## Sample API Requests

### 1. List & Filter Smart Meters
Search for Installed single-phase meters manufactured by HPL:
```bash
curl -X GET "http://localhost:8000/api/v1/meters?make=HPL&phase_type=single&install_status=Installed&page=1&page_size=5"
```
**Sample Response:**
```json
{
  "data": [
    {
      "meter_id": "J100008",
      "serial_no": "SE89764",
      "make": "HPL",
      "phase_type": "single",
      "install_status": "Installed",
      "install_type": "Whole Current",
      "build": "legacy",
      "dt_code": "DT-009",
      "geo": {
        "latitude": 26.91823,
        "longitude": 75.81245
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 5,
    "total_items": 52,
    "total_pages": 11,
    "has_next": true,
    "has_prev": false
  }
}
```

### 2. Inspect Single Meter with Hierarchy
```bash
curl -X GET "http://localhost:8000/api/v1/meters/J100000"
```
**Sample Response:**
```json
{
  "meter_id": "J100000",
  "serial_no": "SE33962",
  "make": "HPL",
  "phase_type": "single",
  "install_status": "Decommissioned",
  "install_type": "Whole Current",
  "build": "legacy",
  "dt_code": "DT-001",
  "geo": {
    "latitude": 26.938961,
    "longitude": 75.830956
  },
  "hierarchy": {
    "zone": { "name": "Jaipur Zone 1", "code": "Z-01" },
    "circle": { "name": "Circle 1", "code": "C-01" },
    "division": { "name": "Division 1", "code": "D-01" },
    "subdivision": { "name": "Subdivision 1", "code": "SD-01" },
    "substation": { "name": "Substation 1", "code": "SS-01" },
    "feeder": { "name": "Feeder 1", "code": "F-001" },
    "dt": { "name": "Malviya Nagar DT 1", "code": "DT-001" }
  },
  "latest_reading": {
    "timestamp": "30/06/2026 23:30",
    "kwh": 48580.79,
    "kvah": 52467.25,
    "volt_r": 220.0,
    "power_factor": 0.926
  }
}
```

### 3. Fetch Time-Series Telemetry & Analytics
```bash
curl -X GET "http://localhost:8000/api/v1/meters/J100001/energy"
```
**Sample Response:**
```json
{
  "meter_id": "J100001",
  "reading_count": 337,
  "oldest_reading": {
    "timestamp": "23/06/2026 23:30",
    "kwh": 42594.05,
    "kvah": 46001.58,
    "volt_r": 231.0,
    "power_factor": 0.926
  },
  "latest_reading": {
    "timestamp": "30/06/2026 23:30",
    "kwh": 42732.85,
    "kvah": 46151.48,
    "volt_r": 236.0,
    "power_factor": 0.926
  },
  "total_active_kwh_delta": 138.8,
  "avg_voltage_r": 230.1,
  "min_voltage_r": 218.0,
  "max_voltage_r": 242.0,
  "voltage_anomaly": false,
  "readings": [ ... ]
}
```

### 4. Geospatial Proximity Search ("What's near this location?")
Locate meters within 3km of Jaipur coordinates:
```bash
curl -X GET "http://localhost:8000/api/v1/spatial/nearby?latitude=26.9389&longitude=75.8309&radius_meters=3000&limit=3"
```
**Sample Response:**
```json
[
  {
    "meter": {
      "meter_id": "J100000",
      "serial_no": "SE33962",
      "make": "HPL",
      "phase_type": "single",
      "install_status": "Decommissioned",
      "dt_code": "DT-001"
    },
    "distance_meters": 0.0,
    "distance_km": 0.0
  },
  {
    "meter": {
      "meter_id": "J100142",
      "serial_no": "SE98201",
      "make": "Genus",
      "phase_type": "three",
      "install_status": "Installed",
      "dt_code": "DT-001"
    },
    "distance_meters": 412.35,
    "distance_km": 0.412
  }
]
```

### 5. Network Hierarchy Tree
```bash
curl -X GET "http://localhost:8000/api/v1/hierarchy"
```

### 6. Trigger On-Demand Upstream Cache Synchronization
```bash
curl -X POST "http://localhost:8000/api/v1/sync"
```

---

## Features & Optional Extensions Implemented

This project fulfills all core requirements and implements **all optional extensions**:

1. **Reconstructed Network Hierarchy:**
   - Automatically builds a complete 7-tier distribution hierarchy: `Zone -> Circle -> Division -> Subdivision -> Substation -> Feeder -> DT -> Meters`.
   - Aggregates downstream meter counts at every tier.
   - Endpoint: `GET /api/v1/hierarchy` and `GET /api/v1/hierarchy/{level}/{code}`.
2. **Local Index & Query Layer:**
   - Multi-attribute filtering across `make`, `phase_type`, `install_status`, `dt_code`, `feeder_code`, `zone_code`, and query substring.
   - Spatial proximity search answering *"what's near this location?"* via the Haversine formula.
   - Scalability analysis documented in [REFLECTION.md](REFLECTION.md).
3. **Freshness & Caching:**
   - Time-To-Live (TTL) caching with automatic staleness detection.
   - On-demand invalidation via `POST /api/v1/sync` and cache health metrics via `GET /api/v1/sync/status`.
4. **Resilient Session & Error Handling:**
   - Mutex-locked session re-authentication on 401/403 or login redirects.
   - Dynamic signing key caching with auto-retry.
5. **Cryptographic Bulk Dataset Integration:**
   - Uses the portal's HMAC-SHA256 export mechanism to synchronize all 403 meters in a single operation.
6. **Modern Web Client:**
   - A reactive dashboard built with vanilla CSS and modern components.
   - Integrated **Leaflet.js** map displaying color-coded meters across Jaipur.
   - **Chart.js** consumption and voltage curves over 337 interval points.
   - Live collapsible hierarchy tree explorer and transformer inventory.

---

## Design Decisions & Trade-Offs

1. **Python + FastAPI over Node.js / Go:**
   - FastAPI provides native Pydantic data validation, type hints, and automatic OpenAPI 3.1.0 generation.
   - Excellent fit for utility data modeling and analytics.
2. **In-Memory Cache vs. External Database:**
   - For a dataset of 403 meters and 40 DTs (~15MB RAM), an in-memory index eliminates external database dependencies (e.g., PostgreSQL, Redis), enabling zero-configuration local runs while delivering sub-millisecond response times.
   - Transition path to PostGIS at scale is documented in [REFLECTION.md](REFLECTION.md).
3. **Bulk Export over Granular Scraping:**
   - The `/portal/export` endpoint provides unified, normalized data across both legacy and v2 meters without hammering the upstream server with 403 individual HTTP requests.

---

## What Was Intentionally Left Out

1. **Persistent Relational Database:** Kept intentionally in-memory to ensure zero-setup local execution for evaluation as specified in the ground rules (*"Everything can be built and run locally"*).
2. **Write-Back Capabilities:** The assignment specifies the portal is strictly read-only; therefore, no write or update mutation endpoints were introduced.
3. **Consumer Authentication Layer:** We assume this service runs inside the utility's internal private VPC or behind an API Gateway, keeping internal service overhead minimal.
