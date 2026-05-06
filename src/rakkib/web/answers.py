"""Non-interactive phase answer processing for the browser UI."""

from __future__ import annotations

import subprocess
from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from rakkib.normalize import apply_normalize, eval_when
from rakkib.schema import FieldDef, QuestionSchema
from rakkib.state import State, subdomain_placeholder_key
from rakkib.steps import load_service_registry

_TEMPLATE_KEY_RE = re.compile(r"\{\{([^{}]+)\}\}")


@dataclass
class PhaseValidationError(Exception):
    """Structured validation failures for web phase submissions."""

    message: str
    field_errors: dict[str, str]


def apply_phase_answers(
    state: State,
    schema: QuestionSchema,
    answers: dict[str, Any],
    *,
    confirmations: dict[str, bool] | None = None,
) -> State:
    """Apply a browser phase submission to a cloned state object."""
    working = State(deepcopy(state.to_dict()))
    confirmations = confirmations or {}

    if schema.service_catalog and state.get("web_deployment.status") == "succeeded":
        if not state.get("deployed.exists"):
            working.set("deployed.exists", True)
            working.set("deployed.foundation_services", state.get("foundation_services", []) or [])
            working.set("deployed.selected_services", state.get("selected_services", []) or [])

    for _ in range(max(1, len(schema.fields) + 1)):
        before = deepcopy(working.to_dict())
        _apply_fields(working, schema, answers)
        if working.to_dict() == before:
            break

    if schema.service_catalog:
        _apply_service_catalog_side_effects(working, confirmations)

    if schema.phase < 6:
        working.set("confirmed", False)
        working.set("web_deployment.status", "stale")

    return working


def _apply_fields(state: State, schema: QuestionSchema, answers: dict[str, Any]) -> None:
    """Apply all active fields in order against the working state."""
    for field in schema.fields:
        if field.when and not eval_when(field.when, state):
            continue

        if field.type == "derived":
            _handle_derived(field, state)
            continue

        if field.type == "summary":
            continue

        if field.repeat_for:
            _handle_repeat(field, state, schema)
            continue

        if field.type == "secret_group":
            _apply_secret_group(field, state, answers.get(field.id))
            continue

        submitted = answers.get(field.id, _MISSING)
        if submitted is _MISSING:
            continue

        normalized = _normalize_submitted_value(field, submitted)
        _record_field_value(field, normalized, state)


def _apply_secret_group(field: FieldDef, state: State, submitted: Any) -> None:
    """Apply secret-group values while preserving already-saved secrets."""
    submitted_map = submitted if isinstance(submitted, dict) else {}

    for entry in field.entries:
        key = str(entry.get("key", "")).strip()
        when = str(entry.get("when", "always")).strip()

        if not key:
            continue
        if when != "always" and not eval_when(when, state):
            continue

        incoming = submitted_map.get(key, _MISSING)
        if incoming is _MISSING:
            continue

        value = str(incoming).strip()
        if not value or value == "[redacted]":
            continue

        state.set(f"secrets.values.{key}", value)


def _normalize_submitted_value(field: FieldDef, submitted: Any) -> Any:
    """Normalize and validate a submitted field value."""
    if field.type == "text":
        return _normalize_text(field, submitted)
    if field.type == "confirm":
        return _normalize_confirm(field, submitted)
    if field.type == "single_select":
        return _normalize_single_select(field, submitted)
    if field.type == "multi_select":
        return _normalize_multi_select(field, submitted)

    raise PhaseValidationError("Unsupported field type in phase submission.", {field.id: field.type})


def _normalize_text(field: FieldDef, submitted: Any) -> str:
    value = str(submitted).strip()
    message = _validate_text_value(field, value)
    if message:
        raise PhaseValidationError("Invalid text field value.", {field.id: message})
    return apply_normalize(value, field.normalize)


def _normalize_confirm(field: FieldDef, submitted: Any) -> Any:
    accepted = field.accepted_inputs or {}
    if not accepted:
        if isinstance(submitted, bool):
            return submitted
        lowered = str(submitted).strip().lower()
        if lowered in {"true", "yes", "y", "1"}:
            return True
        if lowered in {"false", "no", "n", "0"}:
            return False
        raise PhaseValidationError("Invalid confirm field value.", {field.id: "Choose yes or no."})

    values = set(accepted.values())
    if submitted in values:
        return submitted

    lowered = str(submitted).strip().lower()
    for key, value in accepted.items():
        if lowered == str(key).strip().lower():
            return value

    if values <= {True, False}:
        if lowered in {"true", "yes", "y", "1"}:
            return True
        if lowered in {"false", "no", "n", "0"}:
            return False

    raise PhaseValidationError("Invalid confirm field value.", {field.id: "Choose one of the allowed values."})


def _normalize_single_select(field: FieldDef, submitted: Any) -> str:
    lowered = str(submitted).strip().lower()
    for canonical in field.canonical_values:
        if lowered == canonical.lower():
            return canonical
        aliases = field.aliases.get(canonical, [])
        if lowered in {alias.lower() for alias in aliases}:
            return canonical

    raise PhaseValidationError("Invalid single-select value.", {field.id: "Choose one of the listed options."})


def _normalize_multi_select(field: FieldDef, submitted: Any) -> list[str]:
    if submitted is None:
        selected: list[str] = []
    elif isinstance(submitted, list):
        selected = [str(item).strip() for item in submitted if str(item).strip()]
    else:
        raise PhaseValidationError("Invalid multi-select value.", {field.id: "Submit an array of selected values."})

    allowed = set(field.canonical_values)
    numeric_aliases = field.numeric_aliases or {}
    normalized: list[str] = []

    for item in selected:
        value = numeric_aliases.get(item, item)
        if value not in allowed:
            raise PhaseValidationError("Invalid multi-select value.", {field.id: f"`{item}` is not an allowed option."})
        if value not in normalized:
            normalized.append(value)

    return normalized


def _validate_text_value(field: FieldDef, value: str) -> str | None:
    validate_spec = field.validate
    if not validate_spec:
        return None

    if isinstance(validate_spec, dict):
        if validate_spec.get("non_empty") and not value.strip():
            return str(validate_spec.get("message") or "Value cannot be empty.")

        pattern = validate_spec.get("pattern")
        if pattern:
            import re

            if not re.match(str(pattern), value):
                return str(validate_spec.get("message") or "Invalid format.")

        return None

    return None if value.strip() else "Value cannot be empty."


def _apply_service_catalog_side_effects(state: State, confirmations: dict[str, bool]) -> None:
    """Apply phase-3 side effects using the same state shape as the CLI."""
    registry = load_service_registry()
    selected_ids = set(state.get("foundation_services", []) or [])
    selected_ids.update(state.get("selected_services", []) or [])

    dependency_errors = _validate_service_dependencies(selected_ids, registry)
    if dependency_errors:
        raise PhaseValidationError(
            "Selected services have missing dependencies.",
            {"optional_services": "; ".join(dependency_errors)},
        )

    _apply_service_selection(state, registry, selected_ids)


def _validate_service_dependencies(selected_ids: set[str], registry: dict[str, Any]) -> list[str]:
    """Validate registry dependencies for the selected service set."""
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


def _apply_service_selection(state: State, registry: dict[str, Any], selected_ids: set[str]) -> None:
    """Apply service selection side effects to state."""
    active_ids = set(selected_ids)
    active_ids.update(
        svc["id"]
        for svc in registry["services"]
        if svc.get("state_bucket") == "always"
    )

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

    subdomains: dict[str, str] = {}
    current_subdomains = state.get("subdomains", {}) or {}
    secrets_values = dict(state.get("secrets.values", {}) or {})
    for svc in registry["services"]:
        svc_id = svc["id"]
        if svc_id not in active_ids:
            state.delete(subdomain_placeholder_key(svc_id))
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
        state.set(subdomain_placeholder_key(svc_id), subdomain)

        if svc.get("host_service") and not state.get("host_gateway"):
            state.set("host_gateway", _default_host_gateway(state))

    state.set("subdomains", subdomains)
    state.set("secrets.values", secrets_values)


def _default_host_gateway(state: State) -> str:
    """Return the platform-specific host gateway default."""
    platform = str(state.get("platform", "linux")).lower()
    if platform == "mac":
        return "host.docker.internal"
    return "172.18.0.1"


def _handle_derived(field: FieldDef, state: State) -> None:
    """Apply derived-field behavior without the interactive CLI layer."""
    if field.detect:
        result = _run_detect(field, state)
        if isinstance(result, dict):
            for key, value in result.items():
                state.set(key, value)
        elif result is not None:
            _record_field_value(field, result, state)
        return

    if field.template:
        template = field.template
        derive_keys = field.derive_from
        if isinstance(derive_keys, str):
            derive_keys = [derive_keys]
        for key in derive_keys or []:
            template = template.replace(f"{{{{{key}}}}}", str(state.get(key, "")))
        _record_field_value(field, template, state)
        return

    if field.value is not None:
        value = field.value
        if isinstance(value, dict):
            if field.records and all(record in value for record in field.records):
                rendered = _render_template_dict(value, state)
                for key, rendered_value in rendered.items():
                    state.set(key, rendered_value)
                return

            platform = state.get("platform")
            if platform and platform in value:
                value = value[platform]
            elif "default" in value:
                value = value["default"]

        _record_field_value(field, value, state)


def _run_detect(field: FieldDef, state: State) -> Any:
    """Run detect commands for derived fields."""
    detect = field.detect
    command = None

    if isinstance(detect, dict):
        if "command" in detect:
            command = detect["command"]
        else:
            platform = state.get("platform")
            if platform == "linux" and "linux" in detect:
                command = detect["linux"]
            elif platform == "mac" and "mac" in detect:
                command = detect["mac"]

    if not command:
        return None

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        output = result.stdout.strip()
    except Exception:
        output = ""

    normalize = detect.get("normalize") if isinstance(detect, dict) else None
    if normalize and isinstance(normalize, dict):
        if output in normalize:
            return normalize[output]
        if "default" in normalize:
            return normalize["default"]

    if field.normalize:
        return apply_normalize(output, field.normalize)

    return output


def _render_template_dict(value: dict[str, Any], state: State) -> dict[str, Any]:
    """Render {{key}} placeholders in dict values."""
    rendered: dict[str, Any] = {}
    for key, entry in value.items():
        if isinstance(entry, str):
            for template_key in _TEMPLATE_KEY_RE.findall(entry):
                entry = entry.replace(f"{{{{{template_key}}}}}", str(state.get(template_key, "")))
        rendered[key] = entry
    return rendered


def _handle_repeat(field: FieldDef, state: State, schema: QuestionSchema | None) -> None:
    """Apply repeat-for subdomain defaults for selected services."""
    if field.repeat_for != "selected_service_slugs":
        return

    foundation = state.get("foundation_services", []) or []
    selected = state.get("selected_services", []) or []
    slugs = foundation + selected

    defaults: dict[str, str] = {}
    if schema and schema.service_catalog:
        for section in ("foundation_bundle", "optional_services"):
            for item in schema.service_catalog.get(section, []):
                slug = item.get("slug", "")
                defaults[slug] = item.get("default_subdomain", slug)

    for slug in slugs:
        default = defaults.get(slug, slug)
        state.set(f"subdomains.{slug}", default)
        state.set(subdomain_placeholder_key(slug), default)


def _record_field_value(field: FieldDef, value: Any, state: State) -> None:
    """Record a field value into each configured state key."""
    if field.records:
        for record_key in field.records:
            state.set(record_key, value)
        return

    state.set(field.id, value)


_MISSING = object()
