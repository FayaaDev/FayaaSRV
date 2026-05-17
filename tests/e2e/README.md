# Rakkib Manual E2E Contract

These checks validate the real install -> init -> add -> pull -> remove contract on the test server.

Run them only on `174.138.183.153`. Never run service deployment validation on the dev workstation at `192.168.0.235`.

## Preconditions

- Publish runtime changes first when `install.sh`, `pyproject.toml`, `LICENSE`, `docs/public/README.md`, or `src/rakkib/**` changed: `scripts/publish-runtime-repo.sh sync --push`.
- Start from a disposable test-server state, or confirm any existing services are intentionally present.
- Capture command output as validation evidence.

## Roundtrip

```bash
curl -fsSL https://install.rakkib.app | bash
~/.local/bin/rakkib --version
~/.local/bin/rakkib init

# Select two lightweight browser-facing services in the TUI, such as whoami and it-tools.
~/.local/bin/rakkib add

~/.local/bin/rakkib pull --service whoami
~/.local/bin/rakkib pull --service it-tools
~/.local/bin/rakkib smoke whoami
~/.local/bin/rakkib smoke it-tools

# Deselect the same two services in the TUI and confirm removal.
~/.local/bin/rakkib add

docker ps --format '{{.Names}}' | grep -E 'whoami|it-tools' && exit 1 || true
test ! -d /srv/docker/whoami
test ! -d /srv/docker/it-tools
test ! -d /srv/data/whoami
test ! -d /srv/data/it-tools

~/.local/bin/rakkib uninstall --yes
```

After any successful service validation, remove the validated services immediately unless the operator explicitly asks to keep them running.
