"""Tests for browser-triggered setup runner behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from rakkib.docker import DockerError
from rakkib.web.host_auth import check_host_auth_readiness
import rakkib.web.run as web_run


def test_setup_child_env_normalizes_non_root_home(monkeypatch):
    monkeypatch.setenv("HOME", "/root")
    monkeypatch.setattr(web_run.os, "getuid", lambda: 1000)
    monkeypatch.setattr(web_run.pwd, "getpwuid", lambda uid: SimpleNamespace(pw_dir="/home/fayaa"))

    env = web_run._setup_child_env()

    assert env["HOME"] == "/home/fayaa"
    assert env["PYTHONUNBUFFERED"] == "1"


def test_setup_child_env_keeps_root_home_for_root(monkeypatch):
    monkeypatch.setenv("HOME", "/root")
    monkeypatch.setattr(web_run.os, "getuid", lambda: 0)

    env = web_run._setup_child_env()

    assert env["HOME"] == "/root"


def test_web_run_manager_builds_service_sync_command(tmp_path):
    manager = web_run.WebRunManager(tmp_path)

    command = manager._command_for_operation(web_run.SERVICE_SYNC_OPERATION)

    assert command[-1] == "sync-services"


def test_web_run_manager_uses_checkout_root_for_state_and_cwd(tmp_path):
    checkout = tmp_path / "Rakkib"
    package_dir = checkout / "src" / "rakkib"
    package_dir.mkdir(parents=True)
    (checkout / ".git").mkdir()

    manager = web_run.WebRunManager(package_dir)

    assert manager._repo_dir == checkout
    assert manager._state_path == checkout / ".fss-state.yaml"


def test_web_run_manager_cancel_terminates_child_and_persists_status(tmp_path):
    class FakeProcess:
        pid = 12345

        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return -15

    process = FakeProcess()
    manager = web_run.WebRunManager(tmp_path)
    manager._process = process
    manager._record = web_run.RunRecord(
        status="running",
        message="Setup run is in progress.",
        started_at="2026-05-09T00:00:00Z",
        command=["rakkib", "pull"],
        log_path=str(tmp_path / ".rakkib-web-run.log"),
        pid=process.pid,
    )

    snapshot = manager.cancel()

    assert process.terminated is True
    assert snapshot["status"] == "canceled"
    assert snapshot["pid"] is None
    assert snapshot["can_start"] is True


def test_host_auth_readiness_requires_sudo_when_not_cached(monkeypatch):
    monkeypatch.setattr("rakkib.web.host_auth.os.geteuid", lambda: 1000)
    monkeypatch.setattr("rakkib.web.host_auth.shutil.which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.setattr(
        "rakkib.web.host_auth.subprocess.run",
        lambda *args, **kwargs: MagicMock(returncode=1, stdout="", stderr="sudo required"),
    )

    status = check_host_auth_readiness()

    assert status.ok is False
    assert status.code == "sudo_required"
    assert status.command == "rakkib auth"


def test_host_auth_readiness_flags_docker_group_repair(monkeypatch):
    def fake_docker_run(args, **kwargs):
        raise DockerError(
            "permission denied",
            ["docker", *args],
            1,
            stderr="permission denied while trying to connect to /var/run/docker.sock",
        )

    monkeypatch.setattr("rakkib.web.host_auth.os.geteuid", lambda: 1000)
    monkeypatch.setattr("rakkib.web.host_auth.shutil.which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.setattr(
        "rakkib.web.host_auth.subprocess.run",
        lambda *args, **kwargs: MagicMock(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr("rakkib.web.host_auth.docker_run", fake_docker_run)

    status = check_host_auth_readiness()

    assert status.ok is False
    assert status.code == "docker_permission"
    assert status.requires_restart is True


def test_host_auth_readiness_on_mac_requires_docker_desktop(monkeypatch):
    monkeypatch.setattr("rakkib.web.host_auth.os.geteuid", lambda: 1000)
    monkeypatch.setattr("rakkib.web.host_auth.platform.system", lambda: "Darwin")
    monkeypatch.setattr("rakkib.web.host_auth.shutil.which", lambda _cmd: None)

    status = check_host_auth_readiness()

    assert status.ok is False
    assert status.code == "docker_desktop_missing"
    assert status.command is None
    assert "Docker Desktop" in status.message


def test_host_auth_readiness_on_mac_skips_sudo_when_docker_ready(monkeypatch):
    def fake_docker_run(args, **kwargs):
        if args == ["compose", "version"]:
            return MagicMock(returncode=0, stdout="Docker Compose version v2.24", stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("rakkib.web.host_auth.os.geteuid", lambda: 1000)
    monkeypatch.setattr("rakkib.web.host_auth.platform.system", lambda: "Darwin")
    monkeypatch.setattr("rakkib.web.host_auth.shutil.which", lambda cmd: f"/usr/local/bin/{cmd}" if cmd == "docker" else None)
    monkeypatch.setattr("rakkib.web.host_auth.docker_run", fake_docker_run)

    status = check_host_auth_readiness()

    assert status.ok is True
    assert status.code == "ready"
    assert "Docker Desktop" in status.message


def test_host_auth_readiness_allows_root(monkeypatch):
    monkeypatch.setattr("rakkib.web.host_auth.os.geteuid", lambda: 0)

    status = check_host_auth_readiness()

    assert status.ok is True
    assert status.command is None
