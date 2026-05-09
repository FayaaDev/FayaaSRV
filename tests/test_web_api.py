"""Regression tests for web auth and CSRF behavior."""

from __future__ import annotations

from fastapi.testclient import TestClient

from rakkib.web.app import create_app
from rakkib.web.models import WebRuntimeConfig


def _client(tmp_path):
    app = create_app(
        WebRuntimeConfig(
            host="127.0.0.1",
            port=3737,
            repo_dir=tmp_path,
            token_auth_enabled=True,
            startup_token="setup-token",
        )
    )
    return TestClient(app)


def test_setup_route_rejects_query_string_token(tmp_path):
    client = _client(tmp_path)

    response = client.get("/setup?token=setup-token")

    assert response.status_code == 401


def test_setup_route_accepts_bearer_token(tmp_path):
    client = _client(tmp_path)

    response = client.get("/setup", headers={"Authorization": "Bearer setup-token"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_bootstrap_sets_strict_cookie_and_returns_csrf_token(tmp_path):
    client = _client(tmp_path)

    response = client.post("/api/session/bootstrap", json={"token": "setup-token"})


    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["csrf_token"]
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=strict" in response.headers["set-cookie"].lower()


def test_cookie_authenticated_patch_requires_csrf_token(tmp_path):
    client = _client(tmp_path)
    bootstrap = client.post("/api/session/bootstrap", json={"token": "setup-token"})

    response = client.patch("/api/state", json={"state": {"domain": "example.com"}})

    assert bootstrap.status_code == 200
    assert response.status_code == 403


def test_cookie_authenticated_patch_accepts_csrf_token(tmp_path):
    client = _client(tmp_path)
    bootstrap = client.post("/api/session/bootstrap", json={"token": "setup-token"})
    csrf_token = bootstrap.json()["csrf_token"]

    response = client.patch(
        "/api/state",
        headers={"X-CSRF-Token": csrf_token},
        json={"state": {"domain": "example.com"}},
    )

    assert response.status_code == 200
    assert response.json()["state"]["domain"] == "example.com"
