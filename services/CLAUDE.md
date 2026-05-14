# Services Workspace — Agent Rules (Rakkib)

This folder is where service names/lists get turned into real, deployable Rakkib services.

## Mission

When OpenCode is launched inside `Rakkib/services`, the user can:
- mention a service name (example: "Vaultwarden", "File Browser"), or
- reference a list file here (examples: `PendingServices.md`, `batch1.md`, `batchx.md`, `MoreServices/*.md`),
and the agent implements the service in the Rakkib app (registry + templates + hooks + verification updates).

## Branch Rules

- **All commits go to `main`.** Never commit service work directly to `runtime`.
- After pushing to `main`, regenerate `runtime` with `scripts/runtime-branch.sh sync --push`. The test server installs from `runtime` by default.
- Do not hand-edit `runtime` and do not copy files outside the runtime allowlist.

## Hard Requirements

1. Mandatory test-server validation for EVERY new service

Run deployments on the test server (not this machine):

`sshpass -p 'ub' ssh -o StrictHostKeyChecking=accept-new root@174.138.183.153`

Validation must follow the service-targeted bare-metal flow:
- `curl -fsSL https://install.rakkib.app | bash`
- deploy only the target service with `rakkib add <service> --yes` or `rakkib add --service <service> --yes`
- continue with the service-specific verification steps below

Do not run `rakkib init` or full `rakkib pull` for normal new-service validation. Avoid redeploying unrelated selected services:
- deploy the target with `rakkib add <service> --yes` or `rakkib add --service <service> --yes`
- verify it with `rakkib smoke <service>`
- confirm container/host status and logs before moving to the next service
- reserve full `rakkib pull` only for explicit whole-server validation; it skips already-running selected services but still runs global setup
- validate `rakkib remove <service> --yes` cleanup and re-add the service after removal when adding or changing service definitions
- for services that support `exposure_mode: internal`, confirm Caddy/Cloudflare are skipped, the direct LAN port is published, and smoke uses the LAN URL

2. Mandatory skill usage

You MUST use the project skill `rakkib-add-service` for all service additions:
- Skill path: `.opencode/skills/rakkib-add-service/SKILL.md`

Do not hand-roll the workflow; the skill is the contract for registry fields, templates, hooks, and verification alignment.

## Implementation Rules

- Service additions are registry-driven:
  - `src/rakkib/data/registry.yaml`
  - `src/rakkib/data/questions/03-services.md`
  - templates under `src/rakkib/data/templates/`
  - hooks only when necessary in `src/rakkib/hooks/services.py`
- Avoid hardcoded per-service branches in Python unless the behavior cannot be expressed via registry/templates/hooks.
- Browser-facing Docker services should declare `internal_access` for internal exposure mode unless they are explicitly Cloudflare-only or unsupported in internal mode.
- `internal_access.host_port` values must be unique and `internal_access.container_port` must match the real application listener.
- Services that mount `/var/run/docker.sock` or expose host control must call that risk out in registry `notes` and user-facing descriptions.
- Keep registry `env_keys`, generated secrets, compose `${VAR}` references, and `.env.example` files consistent.
- A service is only "done" if it works with:
  - `rakkib pull --service <service>` when validating a targeted pull path
  - installer-first validation followed by `rakkib add <service> --yes` or `rakkib add --service <service> --yes`
  - checkbox `rakkib add` deselect/removal behavior
  - `rakkib sync-services` for applying the saved selection without a full pull
  - `rakkib remove <service> --yes` as the non-interactive removal path
  - `rakkib smoke <service>` when it is browser-facing
  - `rakkib restart <service>` when restart hooks or render-drift behavior apply
  - destructive removal on deselect (containers, rendered config, data dirs, generated artifacts, Postgres db/role when declared)

## Current Rakkib Features To Respect

- `exposure_mode: internal` is the default private/LAN mode. It does not deploy Caddy routes or Cloudflare DNS/tunnel resources.
- `exposure_mode: cloudflare` publishes explicit service hostnames through Caddy and Cloudflare.
- `rakkib web` runs the browser setup UI locally; `rakkib web --lan` binds to `0.0.0.0`, prints a tokenized LAN URL, and can drive deployment changes through `rakkib sync-services`.
- `rakkib auth` validates sudo/Docker access for the current terminal. Do not document a sudo subcommand unless the CLI actually adds one.
- `rakkib uninstall` is aggressive and removes Rakkib-managed containers, state, Cloudflare artifacts, checkout, and configured data-root artifacts.

## How To Handle User Requests

- If the user gives a service name: locate it in `PendingServices.md`, `ApprovedServices.md`, `batch1.md`, `batchx.md`, or `MoreServices/*.md`; if it is not there, add it to the most appropriate list.
- If the name is missing/ambiguous: ask for the upstream repo URL and whether it needs Postgres.
