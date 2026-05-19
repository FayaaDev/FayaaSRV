"""Tests for Step 1 — Layout."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from rakkib.state import State
from rakkib.steps import layout


def test_layout_run_creates_directories(tmp_path):
    state = State(
        {
            "data_root": str(tmp_path),
            "platform": "mac",
            "foundation_services": [],
            "selected_services": [],
        }
    )
    layout.run(state)

    assert (tmp_path / "docker").is_dir()
    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "apps" / "static").is_dir()
    assert (tmp_path / "backups").is_dir()
    assert (tmp_path / "MDs").is_dir()
    assert (tmp_path / "logs").is_dir()


def test_layout_run_creates_service_directories(tmp_path):
    state = State(
        {
            "data_root": str(tmp_path),
            "platform": "mac",
            "exposure_mode": "cloudflare",
            "foundation_services": ["nocodb"],
            "selected_services": ["n8n"],
        }
    )
    layout.run(state)

    assert (tmp_path / "docker" / "caddy").is_dir()
    assert (tmp_path / "docker" / "cloudflared").is_dir()
    assert (tmp_path / "docker" / "postgres").is_dir()
    assert (tmp_path / "docker" / "nocodb").is_dir()
    assert (tmp_path / "docker" / "n8n").is_dir()


def test_layout_run_skips_caddy_and_cloudflared_for_internal_mode(tmp_path):
    state = State(
        {
            "data_root": str(tmp_path),
            "platform": "mac",
            "exposure_mode": "internal",
            "foundation_services": ["nocodb"],
            "selected_services": [],
        }
    )
    layout.run(state)

    assert not (tmp_path / "docker" / "caddy").exists()
    assert not (tmp_path / "docker" / "cloudflared").exists()
    assert not (tmp_path / "data" / "cloudflared").exists()
    assert (tmp_path / "docker" / "postgres").is_dir()
    assert (tmp_path / "docker" / "nocodb").is_dir()


def test_layout_run_sudo_on_linux(tmp_path):
    state = State(
        {
            "data_root": str(tmp_path),
            "platform": "linux",
            "admin_user": "ubuntu",
            "foundation_services": [],
            "selected_services": [],
        }
    )
    with patch("os.geteuid", return_value=1000):
        with patch("rakkib.steps.layout.subprocess.run") as mock_run:
            with patch("pathlib.Path.write_text"):
                mock_run.return_value.returncode = 0
                layout.run(state)

    # First call should be mkdir -p, subsequent calls chown.
    calls = mock_run.call_args_list
    assert calls[0][0][0][0:3] == ["sudo", "-n", "mkdir"]
    assert calls[1][0][0] == ["sudo", "-n", "chown", "ubuntu", str(tmp_path)]


def test_layout_run_recursively_repairs_admin_config_trees(tmp_path):
    state = State(
        {
            "data_root": str(tmp_path),
            "platform": "linux",
            "admin_user": "ubuntu",
            "foundation_services": [],
            "selected_services": [],
        }
    )
    with patch("os.geteuid", return_value=1000):
        with patch("rakkib.steps.layout.subprocess.run") as mock_run:
            with patch("pathlib.Path.write_text"):
                mock_run.return_value.returncode = 0
                layout.run(state)

    commands = [call[0][0] for call in mock_run.call_args_list]
    assert ["sudo", "-n", "chown", "-R", "ubuntu", str(tmp_path / "docker")] in commands
    assert ["sudo", "-n", "chown", "-R", "ubuntu", str(tmp_path / "logs")] in commands
    assert ["sudo", "-n", "chown", "ubuntu", str(tmp_path / "data")] in commands
    assert ["sudo", "-n", "chown", "-R", "ubuntu", str(tmp_path / "data")] not in commands


def test_layout_run_sudo_creates_logs_before_writing(tmp_path):
    state = State(
        {
            "data_root": str(tmp_path / "srv"),
            "platform": "linux",
            "admin_user": "ubuntu",
            "foundation_services": [],
            "selected_services": [],
        }
    )

    with patch("os.geteuid", return_value=1000):
        with patch("rakkib.steps.layout.subprocess.run") as mock_run:
            with patch("pathlib.Path.write_text"):
                mock_run.return_value.returncode = 0
                layout.run(state)

    mkdir_args = mock_run.call_args_list[0][0][0]
    assert mkdir_args[0:4] == ["sudo", "-n", "mkdir", "-p"]
    assert str(tmp_path / "srv" / "logs") in mkdir_args


def test_layout_run_sudo_failure_raises(tmp_path):
    state = State(
        {
            "data_root": str(tmp_path),
            "platform": "linux",
            "foundation_services": [],
            "selected_services": [],
        }
    )
    with patch("os.geteuid", return_value=1000):
        with patch("rakkib.steps.layout.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            with pytest.raises(RuntimeError, match="rakkib auth"):
                layout.run(state)


def test_layout_run_as_root_on_linux(tmp_path):
    state = State(
        {
            "data_root": str(tmp_path),
            "platform": "linux",
            "admin_user": "ubuntu",
            "foundation_services": [],
            "selected_services": [],
        }
    )
    with patch("os.geteuid", return_value=0):
        layout.run(state)

    assert (tmp_path / "docker").is_dir()
    assert (tmp_path / "data").is_dir()


def test_layout_verify_success(tmp_path):
    state = State({"data_root": str(tmp_path)})
    # Pre-create dirs.
    for d in ["docker", "data", "apps/static", "backups", "MDs", "logs"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    result = layout.verify(state)
    assert result.ok is True
    assert result.step == "layout"


def test_layout_verify_failure_missing_dir(tmp_path):
    state = State({"data_root": str(tmp_path)})
    result = layout.verify(state)
    assert result.ok is False
    assert "does not exist" in result.message


def test_layout_verify_failure_not_writable(tmp_path):
    state = State({"data_root": str(tmp_path)})
    for d in ["docker", "data", "apps/static", "backups", "MDs", "logs"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    # Remove write permission from one dir
    (tmp_path / "docker").chmod(0o555)
    result = layout.verify(state)
    (tmp_path / "docker").chmod(0o755)
    assert result.ok is False
    assert "not writable" in result.message
