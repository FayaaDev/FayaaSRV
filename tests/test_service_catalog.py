"""Tests for shared service-catalog side effects."""

from __future__ import annotations

from rakkib.service_catalog import (
    apply_service_catalog_selection,
    cloudflare_enabled,
    service_fqdn,
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
    assert cloudflare_enabled(State({"exposure_mode": "internal", "cloudflare": {"auth_method": "browser_login"}})) is False


def test_service_fqdn_uses_custom_or_default_subdomain():
    state = State({"domain": "example.com", "subdomains": {"webdav": "dav"}})

    assert service_fqdn(state, {"id": "webdav", "default_subdomain": "webdav"}) == "dav.example.com"
    assert service_fqdn(state, {"id": "vaultwarden", "default_subdomain": "vault"}) == "vault.example.com"
