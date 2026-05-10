# Service Addition Rules (Rakkib)

This is the checklist for adding any new service to Rakkib.

## Non-Negotiables

1. Use the `rakkib-add-service` skill

Follow the workflow in `.opencode/skills/rakkib-add-service/SKILL.md`.

2. Test on the test server (service-targeted bare-metal path)

All newly added services MUST be deployed and verified here:

`sshpass -p 'ub' ssh -o StrictHostKeyChecking=accept-new root@174.138.183.153`

Minimum validation steps:
1. `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash`
2. `rakkib add <service> --yes` or `rakkib add --service <service> --yes`
3. Continue with the service-specific verification steps below

Do not run `rakkib init` or full `rakkib pull` for normal new-service validation. Test one service at a time:
1. `rakkib add <service> --yes` or `rakkib add --service <service> --yes`
2. Check the service container/host process and logs
3. `rakkib smoke <service>` for browser-facing services
4. `rakkib remove <service> --yes` and confirm cleanup removes rendered artifacts, declared data, and service Postgres resources when declared
5. Re-add with `rakkib add <service> --yes` to prove removal did not leave stale state
6. Move to the next service only after the public or internal HTML smoke check passes

Do not treat local runs as proof.

## Required Implementation Shape

- Add a service entry to `src/rakkib/data/registry.yaml`.
- Add the service to `src/rakkib/data/questions/03-services.md` so the interview catalog, numeric aliases, subdomain examples, and placeholder mapping stay aligned.
- Add templates under `src/rakkib/data/templates/` (as needed):
  - `docker/<service>/.env.example`
  - `docker/<service>/docker-compose.yml.tmpl`
  - `caddy/routes/<service>.caddy.tmpl`
- Add hooks only when required (use `src/rakkib/hooks/services.py`).
- Prefer declarative registry fields and existing shared hooks. Do not add service-specific Python branches unless the behavior cannot be expressed through registry/templates/hooks.
- Keep registry `env_keys`, generated secrets, compose `${VAR}` references, and `.env.example` files consistent.
- Browser-facing Docker services should declare `internal_access` for internal exposure mode unless they are explicitly Cloudflare-only or unsupported in internal mode.
- Services that mount `/var/run/docker.sock` or otherwise control the host must call that risk out in registry `notes` and user-facing descriptions.
- Keep `rakkib add` behavior correct:
  - selectable in the UI
  - deploys cleanly
  - deselection fully purges service resources

## Current Lifecycle Commands

- `rakkib pull --service <service>` validates the targeted pull path without running the full services pass.
- `rakkib add <service> --yes` and `rakkib add --service <service> --yes` add one service non-interactively.
- Checkbox `rakkib add` is authoritative sync: unchecked services are removed, not merely ignored.
- `rakkib sync-services` applies the saved service selection without a full pull; the browser setup flow uses it after service selection changes.
- `rakkib remove <service> --yes` is the non-interactive removal path and must update state so later pulls do not re-add the service.
- `rakkib restart <service>` must work when a service declares restart hooks or render-sensitive artifacts.
- `rakkib web --lan` exposes the setup UI on the LAN with a tokenized URL; do not assume web setup means public Cloudflare exposure.
- `rakkib auth` is the current sudo/Docker access validation command. Do not document a sudo subcommand unless it exists.

## Exposure Modes

- `exposure_mode: internal` is the default private/LAN mode. Caddy routes, Cloudflare tunnel setup, and DNS publishing are skipped.
- Internal browser-facing services need `internal_access.enabled: true`, a unique `host_port`, a correct `container_port`, and optional `scheme`, `path`, or `compose_service` when needed.
- In internal mode, Rakkib injects the direct LAN port into compose only for services with `internal_access`; avoid hardcoded `ports:` for browser-facing Docker services unless there is a concrete reason.
- `exposure_mode: cloudflare` publishes explicit service hostnames through Caddy and Cloudflare.
- Smoke checks must use the correct URL for the active mode: LAN URL for internal mode, public HTTPS URL for Cloudflare mode.

## Acceptance Checks (Required)

- Service appears in `rakkib add` selection and can be selected.
- Installer-first validation followed by `rakkib add <service> --yes` or `rakkib add --service <service> --yes` deploys the service cleanly.
- `rakkib pull --service <service>` works when validating the targeted pull path.
- Cloudflare mode renders and validates the Caddy route when the service is browser-facing and public.
- Internal mode skips Caddy/Cloudflare and publishes the registry-declared direct LAN port when the service supports internal access.
- Browser-facing services declare registry `smoke.path` and `smoke.expected_text`, and `rakkib smoke <service>` passes with GET.
- Deselect/remove path works through checkbox `rakkib add` and/or `rakkib remove <service> --yes` (containers down, artifacts removed, Postgres resources dropped if declared).
- `rakkib sync-services` applies saved selection changes without a full pull.
- `rakkib restart <service>` works when restart hooks or render-drift behavior apply.
