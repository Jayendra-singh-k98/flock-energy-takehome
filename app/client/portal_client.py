"""Resilient HTTP client for the Urja Meter Ops legacy portal."""

import hashlib
import hmac
import logging
import threading
import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException

from app.config import settings

logger = logging.getLogger("urja.client")


class PortalAuthError(Exception):
    """Raised when authentication to the Urja Meter Ops portal fails."""
    pass


class PortalAPIError(Exception):
    """Raised when an upstream portal API request fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class PortalClient:
    """Client for interacting with the legacy Urja Meter Ops portal.

    Handles session lifecycle, CSRF origin requirements, dynamic HMAC-SHA256
    signing for bulk export, and automatic session re-establishment.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.portal_base_url).rstrip("/")
        self.username = username or settings.portal_username
        self.password = password or settings.portal_password

        self._session = requests.Session()
        self._lock = threading.Lock()
        self._last_auth_time: float = 0.0
        self._cached_signing_secret: Optional[str] = None
        self._secret_cached_at: float = 0.0

        # Standard headers required by SvelteKit's CSRF protection
        self._default_headers = {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/login",
            "User-Agent": "UrjaOpsBridge/1.0 (Flock Energy Integration)",
            "Accept": "application/json, text/html, */*",
        }

    def authenticate(self, force: bool = False) -> None:
        """Authenticate against the portal and store the session token.

        Urja Meter Ops requires an Origin header matching the portal host to
        pass SvelteKit's cross-site POST form check.
        """
        with self._lock:
            # If authenticated recently (within 45 minutes) and not forced, reuse session
            now = time.time()
            if not force and (now - self._last_auth_time < 2700):
                return

            logger.info("Authenticating with Urja Meter Ops portal as %s...", self.username)
            login_url = f"{self.base_url}/login"
            payload = {
                "email": self.username,
                "password": self.password,
            }

            try:
                response = self._session.post(
                    login_url,
                    data=payload,
                    headers=self._default_headers,
                    allow_redirects=False,
                    timeout=15,
                )
            except RequestException as exc:
                raise PortalAuthError(f"Network error connecting to login endpoint: {exc}") from exc

            # The portal responds with 200 and JSON {"type":"redirect","status":303,"location":"/meters"}
            # while setting '__Secure-better-auth.session_token'
            if response.status_code not in (200, 302, 303):
                logger.error(
                    "Login failed with status %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                raise PortalAuthError(
                    f"Authentication failed with HTTP {response.status_code}: {response.text[:100]}"
                )

            token_found = any(
                "session_token" in cookie.name for cookie in self._session.cookies
            )
            if not token_found:
                logger.warning(
                    "Session cookie not detected in cookie jar after login. Response: %s",
                    response.text[:200],
                )

            self._last_auth_time = now
            logger.info("Authentication successful. Session token established.")

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = 1,
    ) -> requests.Response:
        """Execute an authenticated request with automatic retry on session expiry."""
        self.authenticate()

        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        req_headers = dict(self._default_headers)
        if headers:
            req_headers.update(headers)

        try:
            resp = self._session.request(
                method=method,
                url=url,
                params=params,
                headers=req_headers,
                timeout=20,
            )
        except RequestException as exc:
            raise PortalAPIError(f"Upstream network failure for {path}: {exc}") from exc

        # If session expired or redirected to login, re-authenticate and retry
        if (resp.status_code in (401, 403) or "/login" in resp.url) and retries > 0:
            logger.warning(
                "Request to %s indicated unauthorized/forbidden (status %d). Re-authenticating...",
                path,
                resp.status_code,
            )
            self.authenticate(force=True)
            return self._request(method, path, params=params, headers=headers, retries=retries - 1)

        if not resp.ok:
            raise PortalAPIError(
                f"Upstream request {method} {path} failed with status {resp.status_code}: {resp.text[:150]}",
                status_code=resp.status_code,
            )

        return resp

    def get_signing_secret(self, force_refresh: bool = False) -> str:
        """Fetch the dynamic HMAC signing secret used for bulk exports."""
        now = time.time()
        if not force_refresh and self._cached_signing_secret and (now - self._secret_cached_at < 300):
            return self._cached_signing_secret

        resp = self._request("GET", "/portal/keys")
        data = resp.json()
        secret = data.get("data", {}).get("signingSecret")
        if not secret:
            raise PortalAPIError("Failed to extract signingSecret from /portal/keys response")

        self._cached_signing_secret = secret
        self._secret_cached_at = now
        return secret

    def create_hmac_signature(self, method: str, path: str, query: str, secret: str) -> tuple[str, str]:
        """Generate the required HMAC-SHA256 signature and timestamp for export.

        Format:
            Signature String: "{METHOD}\n{PATH}\n{QUERY}\n{TIMESTAMP}"
            Algorithm: HMAC-SHA256
        """
        timestamp = str(int(time.time()))
        message = f"{method}\n{path}\n{query}\n{timestamp}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return timestamp, signature

    def fetch_all_meters_export(self, page: int = 1) -> Dict[str, Any]:
        """Fetch bulk export of all meters with signed HMAC-SHA256 authentication."""
        path = "/portal/export"
        query = f"page={page}"
        secret = self.get_signing_secret()
        timestamp, signature = self.create_hmac_signature("GET", path, query, secret)

        headers = {
            "x-timestamp": timestamp,
            "x-signature": signature,
        }

        resp = self._request("GET", f"{path}?{query}", headers=headers)
        return resp.json()

    def search_meters(self, query: str = "", page: int = 1) -> Dict[str, Any]:
        """Query the portal search endpoint for meters."""
        resp = self._request(
            "GET",
            "/portal/meters/search",
            params={"q": query, "page": page},
        )
        return resp.json()

    def fetch_meter_geo(self, meter_id: str) -> Dict[str, Any]:
        """Fetch geographic location for a specific meter."""
        resp = self._request("GET", f"/portal/meters/{meter_id}/geo")
        return resp.json()

    def fetch_meter_energy(self, meter_id: str) -> Dict[str, Any]:
        """Fetch 30-minute interval energy consumption readings for a meter."""
        resp = self._request("GET", f"/portal/meters/{meter_id}/energy")
        return resp.json()

    def fetch_dts_page(self, page: int = 1) -> Dict[str, Any]:
        """Fetch a single page of Distribution Transformers."""
        resp = self._request("GET", "/portal/dts", params={"page": page})
        return resp.json()

    def fetch_all_dts(self) -> List[Dict[str, Any]]:
        """Page through all Distribution Transformers until complete."""
        all_dts: List[Dict[str, Any]] = []
        page = 1
        while True:
            result = self.fetch_dts_page(page=page)
            items = result.get("data", [])
            total = result.get("total", 0)
            all_dts.extend(items)

            if len(all_dts) >= total or not items:
                break
            page += 1

        return all_dts
