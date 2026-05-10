"""Regression tests for web auth and CSRF behavior."""

from __future__ import annotations

from fastapi.testclient import TestClient

from rakkib.state import State
from rakkib.web.app import create_app
from rakkib.web.host_auth import HostAuthStatus
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


def test_logout_revokes_session_and_clears_cookie(tmp_path):
    client = _client(tmp_path)
    bootstrap = client.post("/api/session/bootstrap", json={"token": "setup-token"})
    csrf_token = bootstrap.json()["csrf_token"]

    logout = client.post("/api/session/logout", headers={"X-CSRF-Token": csrf_token})
    session = client.get("/api/session")

    assert logout.status_code == 200
    assert logout.json()["ok"] is True
    assert "rakkib_session=" in logout.headers["set-cookie"]
    assert session.status_code == 401


def test_run_status_returns_internal_deployed_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "rakkib.web.api.check_host_auth_readiness",
        lambda: HostAuthStatus(True, "ready", "ready", command=None),
    )
    (tmp_path / ".fss-state.yaml").write_text(
        "confirmed: true\n"
        "deployed:\n  exists: true\n"
        "exposure_mode: internal\n"
        "lan_ip: 192.168.1.50\n"
        "foundation_services:\n  - homepage\n"
        "selected_services: []\n"
    )
    client = _client(tmp_path)
    client.post("/api/session/bootstrap", json={"token": "setup-token"})

    response = client.get("/api/run")

    assert response.status_code == 200
    assert {item["url"] for item in response.json()["deployed_urls"]} == {"http://192.168.1.50:13000/"}


def test_run_status_blocks_start_when_host_auth_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(State, "resume_phase", lambda self: 7)
    monkeypatch.setattr(
        "rakkib.web.api.check_host_auth_readiness",
        lambda: HostAuthStatus(False, "sudo_required", "Run `rakkib auth` first."),
    )
    (tmp_path / ".fss-state.yaml").write_text("confirmed: true\n")
    client = _client(tmp_path)
    bootstrap = client.post("/api/session/bootstrap", json={"token": "setup-token"})

    status_response = client.get("/api/run")
    start_response = client.post(
        "/api/run/start",
        headers={"X-CSRF-Token": bootstrap.json()["csrf_token"]},
        json={"mode": "full_setup"},
    )

    status_payload = status_response.json()
    assert status_response.status_code == 200
    assert status_payload["can_start"] is False
    assert status_payload["host_auth"]["code"] == "sudo_required"
    assert start_response.status_code == 409
    assert start_response.json()["detail"]["host_auth"]["command"] == "rakkib auth"
