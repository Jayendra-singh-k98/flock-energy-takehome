# PROTOCOL.md — Reverse-Engineering Urja Meter Ops

This document provides a technical breakdown of the internal mechanics, authentication lifecycle, hidden data paths, cryptographic signing protocols, and data quirks discovered while reverse-engineering the **Urja Meter Ops** portal (`https://urja-ops.flockenergy.tech`).

---

## 1. System Architecture Overview

The Urja Meter Ops portal is built with **SvelteKit** and **Tailwind CSS**, operating as a hybrid server-rendered (SSR) and client-hydrated single-page application (SPA).

Inspection of the client bundle entrypoints (`start.Dtb6sIWb.js`, `app.03ZTmlg3.js`, and chunk `nodes/4.2Bgc2kUI.js` through `nodes/7.OkXSQ8CK.js`) revealed that while the human web interface appears to be a basic HTML web application, the portal communicates with several underlying REST and RPC endpoints under `/portal/*` and `/api/auth/*`.

---

## 2. Authentication & Session Lifecycle

### Login Flow
- **Endpoint:** `POST https://urja-ops.flockenergy.tech/login`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Body:** `email=operator@urja.local&password=urja-ops-2026`

### The CSRF Origin Quirk
Attempting a standard programmatic HTTP POST to `/login` immediately returns:
```http
HTTP/1.1 403 Forbidden
Content-Type: text/plain

Cross-site POST form submissions are forbidden
```
**Mechanism:** SvelteKit has built-in cross-site form submission protection. It validates that incoming POST requests contain an `Origin` (or `Referer`) header matching the host.

**Fix:** Every client request must explicitly supply:
```http
Origin: https://urja-ops.flockenergy.tech
Referer: https://urja-ops.flockenergy.tech/login
```

### Session Cookie
Upon valid credentials with the proper `Origin` header, the server responds with:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: __Secure-better-auth.session_token=...; Max-Age=3600; Path=/; HttpOnly; Secure; SameSite=Lax

{"type":"redirect","status":303,"location":"/meters"}
```
- **Cookie Name:** `__Secure-better-auth.session_token`
- **TTL:** 3,600 seconds (1 hour)
- **Sign-out Endpoint:** `POST /api/auth/sign-out`

---

## 3. Upstream Endpoints Catalog

Through static analysis of the immutable SvelteKit chunk bundles and route dictionaries, the following endpoints were identified:

| Endpoint | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/login` | `POST` | No (requires Origin) | Authenticates credentials and sets session cookie. |
| `/api/auth/sign-out` | `POST` | Cookie | Terminates active session. |
| `/portal/meters/search` | `GET` | Cookie | Meter search by query substring (`q`) and page (`page`). |
| `/portal/meters/{id}/geo` | `GET` | Cookie | Returns `{ "data": { "latitude": "...", "longitude": "..." } }`. |
| `/portal/meters/{id}/energy` | `GET` | Cookie | Returns 337 interval telemetry readings (`timestamp`, `kwh`, `kvah`, `voltR`). |
| `/portal/dts` | `GET` | Cookie | Paginated Distribution Transformers (`code`, `name`, `feederCode`, `capacityKva`). |
| `/portal/keys` | `GET` | Cookie | Returns active dynamic HMAC export signing secret. |
| `/portal/export` | `GET` | Cookie + HMAC | Bulk dataset export requiring signed cryptographic headers. |
| `/meters/{id}/__data.json` | `GET` | Cookie | SvelteKit SSR load hook containing nameplate details and raw hierarchy. |

---

## 4. Cryptographic Bulk Export Signing Protocol

The web interface features an **"Export all meters"** button on `/transformers` (compiled into `nodes/4.2Bgc2kUI.js`). Decompiling this chunk revealed a signed RPC pattern protecting the bulk export endpoint.

### Step 1: Obtain the Secret Key
A call to `GET /portal/keys` returns:
```json
{
  "data": {
    "signingSecret": "I3dZPPf5CgTp7JyGNMI8i6z8LFR7TmSR"
  }
}
```

### Step 2: Formulate the Signature Payload
The payload string is composed of the HTTP method, the URI path, the query string, and the current Unix epoch timestamp in seconds, joined by newline characters:
```text
{METHOD}\n{PATH}\n{QUERY}\n{TIMESTAMP}
```

*Example for export page 1 at timestamp `1761648000`:*
```text
GET
/portal/export
page=1
1761648000
```

### Step 3: Compute HMAC-SHA256
The message is signed using HMAC-SHA256 with the UTF-8 encoded `signingSecret`:
```python
signature = hmac.new(
    signing_secret.encode("utf-8"),
    message.encode("utf-8"),
    hashlib.sha256
).hexdigest()
```

### Step 4: Dispatch Request with Custom Headers
```http
GET /portal/export?page=1 HTTP/1.1
Host: urja-ops.flockenergy.tech
Cookie: __Secure-better-auth.session_token=...
x-timestamp: 1761648000
x-signature: 8a4b6c... (64-character lowercase hex)
```

### Result
The export endpoint returns **all 403 meters in a single JSON response**, complete with normalized hierarchy structures and geographical coordinates.

---

## 5. Quirks, Surprises, and Inconsistencies

### 1. Legacy vs. Modern "v2" Data Representations
Inside the individual meter page server loads (`/meters/{id}/__data.json`), meters are split into two distinct schema formats:
- **Legacy Meters (238 units):** Nameplate fields are stored in a normalized key-value parameter list:
  ```json
  "detail": {
    "data": [
      {"parameterName": "Meter ID", "parameterValue": "J100000"},
      {"parameterName": "Serial No", "parameterValue": "SE33962"}
    ]
  }
  ```
- **Modern v2 Meters (165 units):** Nameplate fields are serialized as an escaped JSON string inside a `classData` field:
  ```json
  "detail": {
    "classData": "{\"installed_meter\":{\"MeterId\":\"J100004\",\"SerialNo\":\"SE65293\",\"Make\":\"Genus\"...}}"
  }
  ```
*Fortunately, the bulk `/portal/export` endpoint automatically normalizes both generations into unified JSON keys, providing a reliable source of truth.*

### 2. Stringified Telemetry Values
In `/portal/meters/{id}/energy`, electrical telemetry values (`kwh`, `kvah`, and `voltR`) are returned as strings rather than numeric types (e.g., `"kwh": "48439.16"`, `"voltR": "229"`). Our service handles numeric parsing and gracefully handles nulls or corrupted intervals.

### 3. Energy Telemetry Depth
Each meter in the system contains exactly **337 interval readings** sampled at 30-minute frequencies, spanning from `23/06/2026 23:30` to `30/06/2026 23:30` (7 full days of telemetry).

### 4. Network Hierarchy Completeness
The distribution grid topology maps strictly across 7 tiers:
```
Zone (3)
 └── Circle (6)
      └── Division (10)
           └── Subdivision (14)
                └── Substation (18)
                     └── Feeder (28)
                          └── Distribution Transformer (40)
                               └── Smart Meters (403)
```
- All 403 meters correspond to 40 valid Distribution Transformers (`DT-001` through `DT-040`).
- No orphan meters or missing DT references were detected in the fleet.

---

## 6. Long-Running Robustness & Session Maintenance

1. **Session Expiration:** The portal session token expires after 1 hour (3600 seconds). The `PortalClient` tracks session age and automatically re-authenticates if a request encounters an HTTP 401/403 or receives a redirect to `/login`.
2. **Secret Staleness:** The dynamic signing secret from `/portal/keys` is cached with a 5-minute TTL. If an export request fails with signature rejection, the client forces a fresh key lookup and retries.
3. **Thread Safety:** The client session is protected by a thread-safe mutex lock, ensuring concurrent API requests do not trigger race conditions during re-authentication.
