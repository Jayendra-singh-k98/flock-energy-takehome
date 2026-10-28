"""Unit tests for the Urja Portal HTTP Client and HMAC signing."""

import hashlib
import hmac
from unittest.mock import MagicMock, patch
from app.client.portal_client import PortalClient


def test_hmac_signature_generation():
    """Verify HMAC signature formatting and SHA256 correctness."""
    client = PortalClient(base_url="https://test-portal.local")
    secret = "test-secret-key-1234"
    path = "/portal/export"
    query = "page=1"

    timestamp, signature = client.create_hmac_signature("GET", path, query, secret)

    # Recreate expected signature
    expected_msg = f"GET\n{path}\n{query}\n{timestamp}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), expected_msg, hashlib.sha256).hexdigest()

    assert signature == expected_sig
    assert len(signature) == 64  # SHA256 hex length
    assert timestamp.isdigit()


def test_client_headers():
    """Verify mandatory Origin and User-Agent headers are set for CSRF compliance."""
    client = PortalClient(base_url="https://urja-ops.flockenergy.tech")
    headers = client._default_headers

    assert headers["Origin"] == "https://urja-ops.flockenergy.tech"
    assert headers["Referer"] == "https://urja-ops.flockenergy.tech/login"
    assert "UrjaOpsBridge" in headers["User-Agent"]
