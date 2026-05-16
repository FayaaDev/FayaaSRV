---
name: rakkib-add-service
description: Add a new service to Rakkib using the registry-driven workflow, including registry entry, templates, hooks, and verification updates.
metadata:
  project: Rakkib
  scope: project-local
---

# Rakkib Add Service

## Goal

Service is complete only when it works cleanly with `rakkib init`, `rakkib pull`, `rakkib pull --service <id>`, `rakkib add <id> --yes`, checkbox `rakkib add`, `rakkib sync-services`, `rakkib remove <id> --yes`, `rakkib smoke <id>`, and the Phase 3 interview catalog (`src/rakkib/data/questions/03-services.md`). If the service declares restart hooks or render drift matters, it must also work with `rakkib restart <id>`. Do not add hardcoded `if svc_id == ...` branches unless behavior cannot be expressed declaratively.

## Read First

- `src/rakkib/data/registry.yaml`
- `src/rakkib/data/questions/03-services.md`
- `src/rakkib/steps/services.py` & `steps/postgres.py`
- `src/rakkib/hooks/services.py`
- `src/rakkib/render.py` & `cli.py`
- `tests/test_registry_consistency.py` & `test_phase3b_output_snapshot.py`
- `tests/fixtures/sample_state.yaml`
- `AGENTS.md`

## Gather From User

- service id, display label, category (foundation / optional)
- docker image/tag policy, default port, `host_service`, `host_port`, default subdomain
- internal exposure support: direct LAN `internal_access.host_port`, `container_port`, optional `scheme`, `path`, and `compose_service`
- dependencies, env keys, generated secrets
- shared Postgres? monitoring? Homepage metadata?
- persistent `data_dirs` + chown? extra templates? custom hooks?
- public or auth-switchable Caddy route?
- does any hook run host package-manager commands (`apt`, `curl | bash`, etc.)?
- does the service mount `/var/run/docker.sock` or otherwise control the host?
- is this GA-supported, beta/unstable, or intentionally best-effort?

## Implementation Order

1. Registry fields in `src/rakkib/data/registry.yaml`
2. Templates under `src/rakkib/data/templates/`
3. Existing shared hooks in `src/rakkib/hooks/services.py`
4. New hook functions only when behavior is truly service-specific

Target is bare metal — avoid host tooling assumptions; do not test on the current machine.

## Current Service Lifecycle

- `rakkib pull --service <id>` validates selection, saves state, runs pre-service global steps, deploys one service, reloads Caddy, syncs shared artifacts, then persists `deployed.exists`, `deployed.foundation_services`, and `deployed.selected_services`.
- `rakkib add <id> --yes` adds one service to the saved selection, generates missing secrets, runs Postgres setup, deploys only that service, reloads Caddy, syncs shared artifacts, then persists deployed snapshots. It does not run every global pull step.
- Checkbox `rakkib add` is a registry-driven sync, not an append-only add flow. It pre-checks installed services, disables `always` services, and makes the final checkbox state authoritative.
- Unchecked services in checkbox `rakkib add` are fully purged before the new selection is applied: compose down with volumes, rendered service directory, declared `data_dirs`, `data/<id>`, Caddy route, `extra_templates`, and service-specific Postgres database/role.
- `rakkib remove <id> --yes` is the non-interactive removal path. It runs the same cleanup, updates `foundation_services` or `selected_services`, persists deployed snapshots, reloads Caddy, and syncs shared artifacts so a later `rakkib pull` will not re-add the service.
- `rakkib sync-services` applies the currently saved selection without a full pull. The web deployment flow uses this command for service selection changes.
- Full `rakkib pull` is whole-server validation. It skips selected services already installed and running, but still runs global setup and can expose unrelated state on a reused test server.
- Restart uses the deployed snapshots, not just the current selected state. Keep deployed state accurate after pull/add/remove flows.

### Host Installer Safety

Prefer Docker-only services. When a host installer is unavoidable:
- Route through shared hook runner (`_run_as_user` / `_run_as_service_user`), not bare `subprocess.run`
- Always wait for apt/dpkg locks
- Required noninteractive env: `DEBIAN_FRONTEND=noninteractive`, `APT_LISTCHANGES_FRONTEND=none`, `NEEDRESTART_MODE=a`, `NEEDRESTART_SUSPEND=1`, `UCF_FORCE_CONFFOLD=1`

## Typical Files

Always needed:
- `src/rakkib/data/registry.yaml`
- `src/rakkib/data/questions/03-services.md`

Needed for Docker services:
- `src/rakkib/data/templates/docker/<id>/docker-compose.yml.tmpl`
- `src/rakkib/data/templates/docker/<id>/.env.example`

Needed for browser or host HTTP services in Cloudflare exposure mode:
- `src/rakkib/data/templates/caddy/routes/<id>.caddy.tmpl` or `<id>-public.caddy.tmpl`

Add only when required: `internal_access`, `extra_templates`, `hooks`, `postgres`, `homepage`, `data_dirs`, `chown`, `env_preserve_keys`, `conditional_secrets`, `installed_check`, `health_timeout`, `smoke`

## Template Safety

1. **Service name mismatches** — if Rakkib renames a dependency container, override the upstream env var in `.env.example`.
2. **Every `${VAR}` in compose** must exist in `.env.example`, come from Docker/shell runtime, or have a safe inline default like `${VAR:-value}`. Do not rely on undocumented hook side effects.
3. **Every required `.env.example` key** must be represented by registry `env_keys`, `secrets`, or `conditional_secrets`, unless it is intentionally derived from normal state such as `TZ`, `ADMIN_UID`, `ADMIN_GID`, `DOMAIN`, or subdomain placeholders.
4. **Dynamic values** (generated IDs, ports, UIDs, one-time tokens, migration keys) must be rendered into `docker/<id>/.env` and referenced via `${VAR}`.
5. **`env_preserve_keys`** — add any key written dynamically or unsafe to rotate that should survive re-renders, restarts, and later `pull` runs.
6. **Unresolved Jinja placeholders are dangerous** because `DebugUndefined` leaves missing `{{PLACEHOLDER}}` text in rendered files. Verify rendered output contains no `{{` or `}}`.
7. **Read upstream docs** (`docker-compose.yml`, `.env`, install guide) before finalizing templates; compensate for any divergence.
8. **Internal mode port publishing** — browser-facing Docker services should normally avoid hardcoded compose `ports:` and declare `internal_access` instead; Rakkib injects the direct LAN port only when `exposure_mode: internal`.
9. **Multi-service compose** — if Rakkib cannot infer the service that should receive the direct LAN port, set `internal_access.compose_service` to the compose service name.
10. **Verify rendered output**: all inter-container hostnames resolve, no missing vars, service survives `rakkib pull` re-render and `rakkib restart <id>` render drift checks.

## Registry Fields Checklist

`id` · `state_bucket` · `required`/`optional` · `foundation` (explicit bool for foundation services) · `image` · `container_name` · `default_port` · `host_service` · `host_port` · `installed_check` · `health_timeout` · `default_subdomain` · `subdomain_key` · `subdomain_placeholder` · `depends_on` · `internal_access` (`enabled`, `host_port`, `container_port`, optional `scheme`, `path`, `compose_service`) · `caddy` (`template`, `public_template`) · `env_keys` · `secrets` · `conditional_secrets` · `postgres` · `monitoring` (`enabled`, `type`, `target`, `path`, `port`, `interval`, `timeout`, `retries`, `hostname`, `custom_url`, `name`) · `homepage` · `data_dirs` · `chown` · `extra_templates` · `hooks` (`post_render`, `pre_start`, `post_start`, `restart`, `remove`) · `env_preserve_keys` · `smoke` (`path`, `expected_text`, optional `timeout`) · `notes`

### Registry Risk Rules

- Browser-facing services with a Caddy route must declare `smoke.path` and `smoke.expected_text`, or the registry notes must clearly mark why the service is beta/unsupported and not smoke-gated.
- Browser-facing Docker services should declare `internal_access.enabled: true` with a unique direct LAN `host_port`, unless the service is explicitly Cloudflare-only or unsupported in internal mode and that limitation is called out in `notes`.
- Internal direct LAN ports are bound on `0.0.0.0` in internal mode. Do not expose unsafe admin/control-plane services this way without explicit notes and a deliberate user-facing description.
- `internal_access.host_port` values must be unique across the registry; `validate_registry_internal_access()` rejects duplicates and missing `host_port`/`container_port` values.
- Services that mount `/var/run/docker.sock` must be explicitly called out in `notes` and user-facing service descriptions. Default exposure must be deliberate because Docker socket access is host control.
- GA-supported services should use pinned image tags or digests. Floating tags such as `latest`, `main`, or `release` are acceptable only when the service is explicitly treated as beta/unstable/best-effort in notes/docs.
- Host services with `host_port: false` need `installed_check` so Rakkib can decide whether they are already installed.
- Host HTTP services need monitoring/smoke paths that match the actual local listener path, not just `/` by habit.

### Bare-Metal Validation Flow

Validate one new service at a time. Use non-interactive commands whenever possible:

1. Install/update the test server from the public runtime repo. For development-tree validation, publish private `main` first with `scripts/publish-runtime-repo.sh sync --push`.
2. Run `rakkib init` when state is missing or intentionally reset.
3. Deploy only the target service with `rakkib pull --service <id>` or `rakkib add <id> --yes`.
4. Confirm the container/host service is running.
5. For `exposure_mode: internal`, confirm no Caddy route is rendered, the service compose publishes the registry-declared direct LAN port, and `rakkib smoke <id>` uses the LAN URL.
6. For `exposure_mode: cloudflare`, confirm the Caddy route is rendered, Cloudflare publishing runs when configured, and `rakkib smoke <id>` uses the public HTTPS URL.
7. Run `rakkib smoke <id>` and verify the target URL returns the expected app HTML.
8. Run `rakkib remove <id> --yes` and confirm cleanup updates state and removes rendered/data/Postgres artifacts declared for that service.
9. Re-add with `rakkib add <id> --yes` to confirm removal did not leave stale state that breaks redeploy.
10. If the service declares restart hooks or render-sensitive artifacts, run `rakkib restart <id>`.
11. Only then move to the next service.

Avoid full `rakkib pull` during service-by-service testing unless intentionally validating the whole selected server. Full pull skips already-running selected services, but it still runs global setup and can expose unrelated state on a reused test server.

## Interview Catalog (`03-services.md`)

- Add service to correct `service_catalog` section with unique numeric alias
- Update `fields.optional_services` or `fields.foundation_services`
- Update "Present This Menu" checklist text
- Update `subdomains:` example and placeholder mapping list
- Describe host-backed services accurately (not as containerized)

## Verification Checklist

1. All referenced template paths exist
2. All hook names resolve for `post_render`, `pre_start`, `post_start`, `restart`, and `remove`; update `tests/test_registry_consistency.py` if it does not cover a hook category you add
3. Service discoverable by id in `registry.yaml`
4. Service appears in `rakkib init` via `03-services.md`
5. `rakkib add <id>` and checkbox `rakkib add` have valid bucket, dependencies, final-selection sync behavior, and subdomain cleanup for deselected services
6. Browser-facing Docker services declare `internal_access` or clearly explain why internal mode is unsupported in `notes`
7. `internal_access.host_port` is unique, `container_port` matches the actual app listener, `scheme`/`path` match smoke behavior, and `compose_service` is set for multi-service compose files when inference is ambiguous
8. Internal-mode rendering skips Caddy routes and injects the direct port only into the intended compose service
9. All inter-container hostnames are valid after any Rakkib renaming
10. Every compose `${VAR}` is sourced from `.env.example`, shell runtime, or intentional inline default
11. Every required `.env.example` value is declared in registry `env_keys`, `secrets`, or `conditional_secrets`, or is intentionally derived from normal state
12. Dynamic setup values are persisted to `.env` when later re-renders depend on them
13. Rendered files contain no unresolved `{{...}}` placeholders
14. Host installer hooks use shared runner or explicitly preserve the noninteractive env
15. Update Phase 3 service catalog tests when services are added or reordered
16. Update CLI/web tests when add-sync, deployed snapshots, removal, `sync-services`, internal mode, or direct-port behavior changes
17. Update fixture/snapshot expectations if rendered outputs change materially
18. Declare `smoke.path` and `smoke.expected_text` for browser-facing services so `rakkib smoke <id>` can verify the target page with a GET request in both Cloudflare and internal mode when supported
19. For app+volume containers, inspect the image runtime user and add registry `chown` for writable persistent directories when needed
20. Use `rakkib add <id> --yes` for non-interactive add-path validation, then verify deselection/removal through checkbox `rakkib add` and/or `rakkib remove <id> --yes`
21. After successful pull/add/remove, confirm deployed snapshots match the actual deployed service set
22. If `install.sh`, `pyproject.toml`, `LICENSE`, `docs/public/README.md`, or `src/rakkib/**` changed, publish the public runtime repo only through `scripts/publish-runtime-repo.sh sync --push` after private `main` changes are ready; never hand-edit `FayaaDev/rakkib`

## Done When

The repo contains the full declarative definition and all referenced assets needed to deploy and cleanly remove the service through the existing pipeline — no ad hoc follow-up edits required.
