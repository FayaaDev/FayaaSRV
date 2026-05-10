"""Host authorization readiness checks for browser-triggered setup runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import shutil
import subprocess

from rakkib.docker import DockerError, docker_run, is_docker_permission_error


AUTH_COMMAND = "rakkib auth"


@dataclass(frozen=True)
class HostAuthStatus:
    ok: bool
    code: str
    message: str
    command: str | None = AUTH_COMMAND
    requires_restart: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sudo_noninteractive_ok() -> bool:
    if os.geteuid() == 0:
        return True
    if shutil.which("sudo") is None:
        return False
    result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True)
    return result.returncode == 0


def check_host_auth_readiness() -> HostAuthStatus:
    """Return whether a web-triggered setup run can use host privileges safely."""
    if os.geteuid() == 0:
        return HostAuthStatus(True, "root", "Rakkib is running as root.", command=None)

    if shutil.which("sudo") is None:
        return HostAuthStatus(
            False,
            "sudo_missing",
            "sudo is required for browser deployment. Install sudo or run Rakkib from a root shell.",
            command=None,
        )

    sudo_ready = _sudo_noninteractive_ok()
    if not sudo_ready:
        return HostAuthStatus(
            False,
            "sudo_required",
            "Host authorization is required before browser deployment can run privileged setup steps. Run `rakkib auth` in the terminal that started this web session, then recheck.",
        )

    if shutil.which("docker") is None:
        return HostAuthStatus(
            True,
            "sudo_ready_docker_missing",
            "Host authorization is ready; setup can install Docker if needed.",
            command=None,
        )

    try:
        docker_run(["info"])
    except DockerError as exc:
        detail = exc.stderr or str(exc)
        if is_docker_permission_error(detail):
            return HostAuthStatus(
                False,
                "docker_permission",
                "Docker is installed, but this user cannot access /var/run/docker.sock. Run `rakkib auth`, then open a new shell or run `newgrp docker` and restart `rakkib web`.",
                requires_restart=True,
            )
        return HostAuthStatus(
            False,
            "docker_unavailable",
            f"Docker is installed but not usable by this session: {exc}",
            command=None,
        )

    compose = docker_run(["compose", "version"], check=False)
    compose_output = f"{compose.stdout or ''}\n{compose.stderr or ''}"
    if compose.returncode != 0 and is_docker_permission_error(compose_output):
        return HostAuthStatus(
            False,
            "docker_permission",
            "Docker Compose cannot access /var/run/docker.sock. Run `rakkib auth`, then open a new shell or run `newgrp docker` and restart `rakkib web`.",
            requires_restart=True,
        )

    return HostAuthStatus(True, "ready", "Host authorization is ready.", command=None)
