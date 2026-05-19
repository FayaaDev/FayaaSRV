from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import pytest

from rakkib.interview import _handle_service_catalog
from rakkib.services_cli import build_add_choices
from rakkib.state import State
from rakkib.steps import services as services_step


def test_build_add_choices_include_description_and_resource_suffixes():
    state = State({"foundation_services": [], "selected_services": []})
    registry = {
        "services": [
            {
                "id": "hermes-agent",
                "state_bucket": "selected_services",
                "homepage": {"category": "AI"},
                "notes": "Self-improving AI agent.",
                "resource_requirements": {
                    "recommended_ram_mb": 8192,
                    "recommended_disk_gb": 25,
                },
            }
        ]
    }

    choices = build_add_choices(state, registry)
    titles = [choice.title for choice in choices]

    assert any(
        "hermes-agent [Self-improving AI agent] [heavy: 8 GB RAM, 25 GB disk recommended]" in title for title in titles
    )


def test_interview_service_catalog_includes_description_and_resource_suffixes():
    schema = SimpleNamespace(
        service_catalog={
            "foundation_bundle": [],
            "optional_services": [{"slug": "hermes-agent", "label": "Hermes Agent"}],
            "host_addons": [],
        }
    )
    state = State({"exposure_mode": "internal"})
    registry = {
        "services": [
            {
                "id": "hermes-agent",
                "homepage": {"category": "AI", "description": "Self-improving AI agent"},
                "resource_requirements": {
                    "recommended_ram_mb": 8192,
                    "recommended_disk_gb": 25,
                },
            }
        ]
    }

    with (
        patch("rakkib.interview.load_service_registry", return_value=registry),
        patch("rakkib.interview.prompt_checkbox", return_value=[]) as mock_checkbox,
    ):
        _handle_service_catalog(schema, state)

    titles = [choice.title for choice in mock_checkbox.call_args.kwargs["choices"]]
    assert any(
        "Hermes Agent [Self-improving AI agent] [heavy: 8 GB RAM, 25 GB disk recommended]" in title for title in titles
    )


def test_service_resource_preflight_fails_below_min_disk_with_clear_message(monkeypatch, tmp_path: Path):
    state = State({"data_root": str(tmp_path / "srv")})
    svc = {
        "id": "hermes-agent",
        "host_service": False,
        "resource_requirements": {
            "min_ram_mb": 4096,
            "recommended_ram_mb": 8192,
            "min_disk_gb": 12,
            "recommended_disk_gb": 25,
            "install_warning": "Pulls a very large upstream image.",
        },
    }

    monkeypatch.setattr(services_step, "_available_ram_mb", lambda: 8192)
    monkeypatch.setattr(services_step, "_resource_disk_probe_path", lambda _state, _svc: Path("/var/lib/containerd"))
    monkeypatch.setattr(services_step, "_disk_probe_status", lambda _probe: (7, "/"))

    with pytest.raises(RuntimeError) as exc:
        services_step._enforce_service_resource_requirements(state, svc)

    message = str(exc.value)
    assert "Service 'hermes-agent' cannot start installation" in message
    assert "at least 12 GB free" in message
    assert "filesystem backing /var/lib/containerd" in message
    assert "VM disk alone is not enough" in message


def test_service_resource_preflight_warns_below_recommended(monkeypatch, tmp_path: Path):
    state = State({"data_root": str(tmp_path / "srv")})
    svc = {
        "id": "hermes-agent",
        "host_service": False,
        "resource_requirements": {
            "min_ram_mb": 4096,
            "recommended_ram_mb": 8192,
            "min_disk_gb": 12,
            "recommended_disk_gb": 25,
            "install_warning": "Pulls a very large upstream image.",
        },
    }

    monkeypatch.setattr(services_step, "_available_ram_mb", lambda: 6144)
    monkeypatch.setattr(services_step, "_resource_disk_probe_path", lambda _state, _svc: Path("/var/lib/containerd"))
    monkeypatch.setattr(services_step, "_disk_probe_status", lambda _probe: (20, "/"))

    with patch.object(services_step.console, "print") as mock_print:
        services_step._enforce_service_resource_requirements(state, svc)

    rendered = " ".join(str(call.args[0]) for call in mock_print.call_args_list)
    assert "Service 'hermes-agent' is resource-heavy" in rendered
    assert "recommends 8 GB RAM" in rendered
    assert "recommends 25 GB free" in rendered
