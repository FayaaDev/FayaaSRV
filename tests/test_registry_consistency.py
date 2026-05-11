"""Consistency checks for registry-declared templates and hooks."""

from __future__ import annotations

import re

import pytest

from rakkib.hooks.services import POST_RENDER_HOOKS, POST_START_HOOKS, PRE_START_HOOKS, REMOVE_HOOKS, RESTART_HOOKS
from rakkib.postgres_sql import validate_registry_postgres_identifiers
from rakkib.steps import data_dir, load_service_registry


ENV_ASSIGNMENT_RE = re.compile(r"^\s*#?\s*([A-Z_][A-Z0-9_]*)\s*=", re.MULTILINE)
COMPOSE_ENV_REF_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::-[^}]*)?\}")
TEMPLATE_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Z_][A-Z0-9_]*)\s*(?:\|[^}]*)?\}\}")


def test_registry_templates_and_hooks_resolve():
    registry = load_service_registry()
    repo = data_dir()

    for svc in registry["services"]:
        caddy = svc.get("caddy") or {}
        for template_name in (caddy.get("template"), caddy.get("public_template")):
            if template_name:
                assert (repo / "templates" / "caddy" / "routes" / template_name).exists()

        for extra in svc.get("extra_templates", []):
            assert (repo / extra["src"]).exists()

        hooks = svc.get("hooks") or {}
        for hook_name in hooks.get("post_render", []):
            assert hook_name in POST_RENDER_HOOKS
        for hook_name in hooks.get("pre_start", []):
            assert hook_name in PRE_START_HOOKS
        for hook_name in hooks.get("post_start", []):
            assert hook_name in POST_START_HOOKS
        for hook_name in hooks.get("restart", []):
            assert hook_name in RESTART_HOOKS
        for hook_name in hooks.get("remove", []):
            assert hook_name in REMOVE_HOOKS


def test_registry_postgres_contracts_are_complete():
    registry = load_service_registry()

    for svc in registry["services"]:
        postgres = svc.get("postgres") or {}
        if not postgres:
            continue

        password_key = postgres.get("password_key")
        assert password_key, f"{svc['id']} postgres config must declare password_key"

        declared_secret_keys = set(svc.get("env_keys", []) or [])
        declared_secret_keys.update((svc.get("secrets") or {}).keys())
        for condition in svc.get("conditional_secrets", []):
            declared_secret_keys.update((condition.get("keys") or {}).keys())

        assert password_key in declared_secret_keys, (
            f"{svc['id']} postgres password_key '{password_key}' must be declared in env_keys, "
            "secrets, or conditional_secrets"
        )

        pre_start_hooks = (svc.get("hooks") or {}).get("pre_start", [])
        assert "service_postgres_login_preflight" in pre_start_hooks, (
            f"{svc['id']} declares postgres and must use service_postgres_login_preflight"
        )


def test_registry_postgres_identifiers_are_valid():
    registry = load_service_registry()

    validate_registry_postgres_identifiers(registry)


def test_registry_postgres_identifier_validation_rejects_invalid_values():
    registry = {
        "services": [
            {
                "id": "bad",
                "postgres": {"role": "bad;drop", "password_key": "BAD_DB_PASS"},
            }
        ]
    }

    with pytest.raises(ValueError, match="Invalid postgres role"):
        validate_registry_postgres_identifiers(registry)


def test_registry_env_keys_match_service_templates():
    registry = load_service_registry()
    repo = data_dir()
    failures: dict[str, dict[str, list[str]]] = {}

    for svc in registry["services"]:
        svc_id = svc["id"]
        docker_dir = repo / "templates" / "docker" / svc_id
        if not docker_dir.exists():
            continue

        env_text = (docker_dir / ".env.example").read_text() if (docker_dir / ".env.example").exists() else ""
        compose_text = (
            (docker_dir / "docker-compose.yml.tmpl").read_text()
            if (docker_dir / "docker-compose.yml.tmpl").exists()
            else ""
        )

        env_assignments = set(ENV_ASSIGNMENT_RE.findall(env_text))
        compose_refs = set(COMPOSE_ENV_REF_RE.findall(compose_text))
        template_inputs = env_assignments | compose_refs | set(TEMPLATE_PLACEHOLDER_RE.findall(env_text))

        missing_env_examples = sorted(compose_refs - env_assignments)
        unused_registry_keys = sorted(set(svc.get("env_keys") or []) - template_inputs)

        if missing_env_examples or unused_registry_keys:
            failures[svc_id] = {}
            if missing_env_examples:
                failures[svc_id]["compose_refs_missing_from_env_example"] = missing_env_examples
            if unused_registry_keys:
                failures[svc_id]["registry_env_keys_missing_from_templates"] = unused_registry_keys

    assert failures == {}
