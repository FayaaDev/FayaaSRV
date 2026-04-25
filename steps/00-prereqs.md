# Step 00 — Prerequisites

Install or verify the base tools needed for the rest of the deployment.

## Inputs

- `platform`
- `privilege_mode`
- `privilege_strategy`
- `docker_installed`

## Actions

1. Verify `curl` is available.
2. On Linux, verify `id -u` is `0` and `privilege_mode: root` is recorded. If not, stop and tell the user to re-run `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | sudo -E bash`.
3. Verify `docker` and `docker compose` are available.
4. If Docker is not installed, install Docker by platform:
   - Mac: use the normal Docker Desktop install flow.
   - Linux: on Ubuntu, install Docker Engine directly as root using Docker's official apt repository instructions. Install `ca-certificates`, `curl`, and `gnupg`; add Docker's GPG key under `/etc/apt/keyrings`; write `/etc/apt/sources.list.d/docker.list`; then install `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, and `docker-compose-plugin`.
   - If Linux is not Ubuntu, stop and ask the user before continuing because this repo's documented Linux install path is the official Ubuntu Docker Engine method.
5. On Linux, enable and start Docker, add `{{ADMIN_USER}}` to the `docker` group if that user exists, and continue using root for this install session.
6. Verify the Docker daemon is running.
7. Verify a local host `cloudflared` binary is available. Step 40 uses the host CLI for tunnel login, creation, and DNS routing, so the Docker image alone is not sufficient.
8. If `cloudflared` is missing, install it into the admin user's `~/.local/bin/cloudflared` without requiring a system package, then ensure later steps can invoke it either through `PATH` or by absolute path.

## Platform Notes

Linux:
- Prefer Docker Engine on headless Ubuntu hosts using Docker's official docs: `https://docs.docker.com/engine/install/ubuntu/`
- This documented path assumes Ubuntu and a root installer process.
- Do not continue on Linux unless the current process is root.
- Install the host `cloudflared` CLI into the admin user's `~/.local/bin/cloudflared` if it is missing before continuing to Step 40.
- A portable install path is acceptable. For example, download the matching release archive for `linux-$ARCH`, extract `cloudflared`, place it at `~/.local/bin/cloudflared`, and `chmod 755` it.

Mac:
- Prefer Docker Desktop.
- Ensure file sharing allows `{{DATA_ROOT}}`.
- Install the host `cloudflared` CLI into `~/.local/bin/cloudflared` if it is missing before continuing to Step 40.
- A portable install path is acceptable. For example, download the matching Darwin release for the recorded architecture, place it at `~/.local/bin/cloudflared`, and `chmod 755` it.

## Verify

- Linux: `test "$(id -u)" -eq 0`
- `docker --version`
- `docker compose version`
- `docker info`
- `curl --version`
- `cloudflared --version` or `~/.local/bin/cloudflared --version`
