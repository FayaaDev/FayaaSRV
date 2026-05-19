"""Tests for shared service-catalog side effects."""

from __future__ import annotations

from rakkib.service_catalog import (
    apply_service_catalog_selection,
    caddy_enabled,
    cloudflare_enabled,
    deployed_service_urls,
    service_fqdn,
    service_url,
    validate_registry_internal_access,
    validate_subdomain_map,
    mark_deployment_stale,
)
from rakkib.state import State


def test_apply_service_catalog_selection_sets_shared_state_shape():
    registry = {
        "services": [
            {"id": "postgres", "state_bucket": "always"},
            {"id": "nocodb", "state_bucket": "foundation_services", "default_subdomain": "nocodb"},
            {"id": "n8n", "state_bucket": "selected_services", "default_subdomain": "n8n"},
        ]
    }
    state = State({"subdomains": {"n8n": "workflow"}})

    apply_service_catalog_selection(state, registry, {"nocodb", "n8n"})

    assert state.get("foundation_services") == ["nocodb"]
    assert state.get("selected_services") == ["n8n"]
    assert state.get("admin_email") == "admin@nocodb.com"
    assert state.get("subdomains") == {"nocodb": "nocodb", "n8n": "workflow"}
    assert state.get("NOCODB_SUBDOMAIN") == "nocodb"
    assert state.get("N8N_SUBDOMAIN") == "workflow"


def test_mark_deployment_stale_matches_web_and_cli_behavior():
    state = State({"confirmed": True, "web_deployment": {"status": "succeeded"}})

    mark_deployment_stale(state)

    assert state.get("confirmed") is False
    assert state.get("web_deployment.status") == "stale"


def test_validate_subdomain_map_rejects_duplicates_and_invalid_labels():
    errors = validate_subdomain_map({"a": "files", "b": "files", "c": "bad.label"})

    assert any("duplicates" in error for error in errors)
    assert any("full domain" in error for error in errors)


def test_cloudflare_enabled_defaults_existing_cloudflare_installs_to_true():
    assert cloudflare_enabled(State({"cloudflare": {"auth_method": "browser_login"}})) is True
    assert (
        cloudflare_enabled(State({"exposure_mode": "internal", "cloudflare": {"auth_method": "browser_login"}}))
        is False
    )


def test_caddy_enabled_only_skips_explicit_internal_mode():
    assert caddy_enabled(State({})) is True
    assert caddy_enabled(State({"exposure_mode": "cloudflare"})) is True
    assert caddy_enabled(State({"exposure_mode": "internal"})) is False


def test_service_fqdn_uses_custom_or_default_subdomain():
    state = State({"domain": "example.com", "subdomains": {"webdav": "dav"}})

    assert service_fqdn(state, {"id": "webdav", "default_subdomain": "webdav"}) == "dav.example.com"
    assert service_fqdn(state, {"id": "vaultwarden", "default_subdomain": "vault"}) == "vault.example.com"


def test_service_url_uses_internal_access_for_internal_mode():
    state = State({"exposure_mode": "internal", "lan_ip": "192.168.1.50"})
    svc = {"id": "homepage", "internal_access": {"enabled": True, "host_port": 13000, "container_port": 3000}}

    assert service_url(state, svc) == "http://192.168.1.50:13000/"


def test_deployed_service_urls_keep_registry_order_for_internal_mode():
    state = State(
        {"exposure_mode": "internal", "lan_ip": "192.168.1.50", "foundation_services": ["homepage", "nocodb"]}
    )
    registry = {
        "services": [
            {"id": "homepage", "internal_access": {"enabled": True, "host_port": 13000, "container_port": 3000}},
            {"id": "nocodb", "internal_access": {"enabled": True, "host_port": 13001, "container_port": 8080}},
        ]
    }

    assert [row["url"] for row in deployed_service_urls(state, registry)] == [
        "http://192.168.1.50:13000/",
        "http://192.168.1.50:13001/",
    ]


def test_deployed_service_urls_use_openclaw_special_url_only():
    registry = {
        "services": [
            {"id": "homepage", "default_subdomain": "home"},
            {"id": "openclaw", "default_subdomain": "claw", "homepage": {"name": "OpenClaw"}},
        ]
    }
    state = State(
        {
            "domain": "example.com",
            "foundation_services": ["homepage"],
            "selected_services": ["openclaw"],
            "deployed": {"special_urls": {"openclaw": "https://claw.example.com/?token=abc"}},
        }
    )

    rows = deployed_service_urls(state, registry)

    assert rows == [
        {"service": "homepage", "label": "homepage", "url": "https://home.example.com/"},
        {"service": "openclaw", "label": "OpenClaw", "url": "https://claw.example.com/?token=abc"},
    ]


def test_deployed_service_urls_omit_openclaw_without_special_url():
    registry = {"services": [{"id": "openclaw", "default_subdomain": "claw"}]}
    state = State({"domain": "example.com", "selected_services": ["openclaw"]})

    assert deployed_service_urls(state, registry) == []


def test_registry_internal_access_rejects_duplicate_ports():
    registry = {
        "services": [
            {"id": "one", "internal_access": {"enabled": True, "host_port": 13000, "container_port": 80}},
            {"id": "two", "internal_access": {"enabled": True, "host_port": 13000, "container_port": 80}},
        ]
    }

    try:
        validate_registry_internal_access(registry)
    except ValueError as exc:
        assert "Duplicate internal_access.host_port 13000" in str(exc)
    else:
        raise AssertionError("duplicate internal port was accepted")
