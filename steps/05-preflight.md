# Step 05 — Preflight Doctor

Run the standalone host health check after prerequisites are available and before creating or changing the managed layout.

## Inputs

- `.fss-state.yaml`
- `domain`
- `data_root`
- optional `CF_API_TOKEN` or `CLOUDFLARE_API_TOKEN` in the shell environment

## Actions

1. Run `./scripts/rakkib-doctor --json` from the repo root.
2. Read the JSON report and stop on any check with `"status":"fail"`.
3. Treat blocking failures as install gates that must be fixed before continuing. Blocking checks include OS support, Docker daemon access, Docker Compose v2, and ports 80/443 being free or owned by Rakkib Caddy.
4. Treat warnings as advisory. Explain them to the user and continue only when they do not invalidate the selected install path.
5. Use the same command as a standalone diagnostic any time the user asks whether the host is healthy enough for Rakkib.

## Verify

- `./scripts/rakkib-doctor`
- `./scripts/rakkib-doctor --json`
