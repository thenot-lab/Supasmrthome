"""Tests for authentication endpoints and token-based access control."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated_users(tmp_path, monkeypatch):
    """Each test gets its own empty users file."""
    users_file = tmp_path / "users.json"
    monkeypatch.setenv("NEUROAROUSAL_USERS_FILE", str(users_file))
    monkeypatch.setenv("NEUROAROUSAL_SECRET_KEY", "test-secret-key-fixed")
    # Reload auth module to pick up env vars
    import neuro_arousal.auth as auth_mod
    auth_mod.USERS_FILE = users_file
    auth_mod.SECRET_KEY = "test-secret-key-fixed"


@pytest.fixture
def client():
    from neuro_arousal.api import app
    return TestClient(app)


def _register(client, username="testuser", password="testpass123"):
    return client.post("/auth/register", json={
        "username": username,
        "password": password,
        "display_name": f"Test {username}",
    })


def _login(client, username="testuser", password="testpass123"):
    return client.post("/auth/login", data={
        "username": username,
        "password": password,
    })


def _auth_header(client, username="testuser", password="testpass123"):
    _register(client, username, password)
    r = _login(client, username, password)
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_register_success(self, client):
        r = _register(client)
        assert r.status_code == 201
        body = r.json()
        assert body["username"] == "testuser"
        assert body["display_name"] == "Test testuser"
        assert "created_at" in body

    def test_register_duplicate(self, client):
        _register(client)
        r = _register(client)
        assert r.status_code == 409

    def test_register_short_username(self, client):
        r = client.post("/auth/register", json={
            "username": "ab",
            "password": "testpass123",
        })
        assert r.status_code == 422

    def test_register_short_password(self, client):
        r = client.post("/auth/register", json={
            "username": "testuser",
            "password": "short",
        })
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_success(self, client):
        _register(client)
        r = _login(client)
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_wrong_password(self, client):
        _register(client)
        r = _login(client, password="wrongpass")
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = _login(client, username="nobody", password="nope")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Token-based access
# ---------------------------------------------------------------------------

class TestTokenAccess:
    def test_me_endpoint(self, client):
        headers = _auth_header(client)
        r = client.get("/auth/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"

    def test_me_no_token(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_me_bad_token(self, client):
        r = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Protected POST endpoints require auth
# ---------------------------------------------------------------------------

class TestProtectedEndpoints:
    def test_run_scenario_requires_auth(self, client):
        r = client.post("/run/scenario/resting_state")
        assert r.status_code == 401

    def test_run_custom_requires_auth(self, client):
        r = client.post("/run/custom", json={})
        assert r.status_code == 401

    def test_set_adapter_requires_auth(self, client):
        r = client.post("/adapters/poetic")
        assert r.status_code == 401

    def test_run_scenario_with_auth(self, client):
        headers = _auth_header(client)
        r = client.post("/run/scenario/resting_state", headers=headers)
        assert r.status_code == 200

    def test_run_custom_with_auth(self, client):
        headers = _auth_header(client)
        r = client.post("/run/custom", json={}, headers=headers)
        assert r.status_code == 200

    def test_set_adapter_with_auth(self, client):
        headers = _auth_header(client)
        r = client.post("/adapters/poetic", headers=headers)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Public GET endpoints remain open
# ---------------------------------------------------------------------------

class TestPublicEndpoints:
    def test_root_no_auth(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_scenarios_no_auth(self, client):
        r = client.get("/scenarios")
        assert r.status_code == 200

    def test_adapters_list_no_auth(self, client):
        r = client.get("/adapters")
        assert r.status_code == 200

    def test_nullclines_no_auth(self, client):
        r = client.get("/nullclines")
        assert r.status_code == 200
