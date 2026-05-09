"""Shared service-catalog state side effects for CLI and web setup."""

from __future__ import annotations

import re
from typing import Any

from rakkib.state import State, subdomain_placeholder_key

_SUBDOMAIN_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def cloudflare_enabled(state: State) -> bool:
    """Return true when this state should publish through Cloudflare.

    Existing installs predate ``exposure_mode`` but have persisted Cloudflare
    state, so treat them as Cloudflare-enabled unless they explicitly choose
    internal mode.
    """
    mode = state.get("exposure_mode")
    if mode is not None:
        return str(mode).strip().lower() == "cloudflare"
    return bool(state.get("cloudflare.auth_method") or state.get("cloudflare.tunnel_uuid"))


def selected_service_ids(state: State) -> set[str]:
    """Return currently selected foundation and optional service ids."""
    ids = set(state.get("foundation_services", []) or [])
    ids.update(state.get("selected_services", []) or [])
    return ids


def validate_service_dependencies(selected_ids: set[str], registry: dict[str, Any]) -> list[str]:
    """Return human-readable dependency errors for a selected service set."""
    by_id = {svc["id"]: svc for svc in registry["services"]}
    errors: list[str] = []

    for svc_id in sorted(selected_ids):
        svc = by_id[svc_id]
        missing = []
        for dep in svc.get("depends_on", []):
            dep_svc = by_id.get(dep, {})
            if dep_svc.get("state_bucket") == "always":
                continue
            if dep not in selected_ids:
                missing.append(dep)
        if missing:
            errors.append(f"{svc_id} requires {', '.join(missing)}")

    return errors


def apply_service_catalog_selection(state: State, registry: dict[str, Any], selected_ids: set[str]) -> None:
    """Apply service selection side effects to the shared setup state."""
    active_ids = set(selected_ids)
    active_ids.update(svc["id"] for svc in registry["services"] if svc.get("state_bucket") == "always")

    foundation_ids = [
        svc["id"]
        for svc in registry["services"]
        if svc.get("state_bucket") == "foundation_services" and svc["id"] in active_ids
    ]
    optional_ids = [
        svc["id"]
        for svc in registry["services"]
        if svc.get("state_bucket") == "selected_services" and svc["id"] in active_ids
    ]

    state.set("foundation_services", foundation_ids)
    state.set("selected_services", optional_ids)
    if "nocodb" in foundation_ids:
        state.set("admin_email", "admin@nocodb.com")

    subdomains: dict[str, str] = {}
    current_subdomains = state.get("subdomains", {}) or {}
    secrets_values = dict(state.get("secrets.values", {}) or {})

    for svc in registry["services"]:
        svc_id = svc["id"]
        placeholder = svc.get("subdomain_placeholder") or subdomain_placeholder_key(svc_id)
        if svc_id not in active_ids:
            state.delete(placeholder)
            for key in (svc.get("secrets") or {}).keys():
                state.delete(key)
                secrets_values.pop(key, None)
            for condition in svc.get("conditional_secrets", []):
                for key in (condition.get("keys") or {}).keys():
                    state.delete(key)
                    secrets_values.pop(key, None)
            continue

        default_subdomain = svc.get("default_subdomain")
        if not default_subdomain:
            continue

        subdomain = current_subdomains.get(svc_id) or default_subdomain
        subdomains[svc_id] = subdomain
        state.set(placeholder, subdomain)

        if svc.get("host_service") and not state.get("host_gateway"):
            state.set("host_gateway", default_host_gateway(state))

    state.set("subdomains", subdomains)
    state.set("secrets.values", secrets_values)


def normalize_subdomain(value: str) -> str:
    """Normalize a service subdomain label from prompt or web input."""
    return str(value or "").strip().strip(".").lower()


def validate_subdomain_label(value: str) -> str | None:
    """Return an error message for an invalid single DNS label."""
    label = normalize_subdomain(value)
    if not label:
        return "Subdomain cannot be empty."
    if "." in label:
        return "Use only the subdomain label, not the full domain."
    if not _SUBDOMAIN_LABEL_RE.match(label):
        return "Use lowercase letters, numbers, and hyphens; do not start or end with a hyphen."
    return None


def validate_subdomain_map(subdomains: dict[str, str]) -> list[str]:
    """Validate all selected service subdomains and reject duplicates."""
    errors: list[str] = []
    seen: dict[str, str] = {}
    for svc_id, value in subdomains.items():
        label = normalize_subdomain(value)
        message = validate_subdomain_label(label)
        if message:
            errors.append(f"{svc_id}: {message}")
            continue
        if label in seen:
            errors.append(f"{svc_id}: duplicates subdomain used by {seen[label]}")
            continue
        seen[label] = svc_id
    return errors


def service_fqdn(state: State, svc: dict[str, Any]) -> str | None:
    """Return the configured public FQDN for a registry service."""
    domain = str(state.get("domain") or "").strip().strip(".")
    if not domain:
        return None

    svc_id = svc["id"]
    subdomains = state.get("subdomains", {}) or {}
    subdomain = normalize_subdomain(subdomains.get(svc_id) or svc.get("default_subdomain") or "")
    if not subdomain:
        return None
    if subdomain == domain or subdomain.endswith(f".{domain}"):
        return subdomain
    return f"{subdomain}.{domain}"


def mark_deployment_stale(state: State) -> None:
    """Mark prior confirmation/deployment as stale after setup answers change."""
    state.set("confirmed", False)
    state.set("web_deployment.status", "stale")


def default_host_gateway(state: State) -> str:
    """Return the platform-specific host gateway default."""
    platform = str(state.get("platform", "linux")).lower()
    if platform == "mac":
        return "host.docker.internal"
    return "172.18.0.1"
