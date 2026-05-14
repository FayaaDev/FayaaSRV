# Services Workspace — Agent Rules (Rakkib)

This folder is where service names/lists get turned into real, deployable Rakkib services.
Use `bd` for task tracking.

## bd Task Tracking (Brief)

- Use `bd` for ALL task/issue tracking. Do not keep markdown TODO lists.
- Start work by checking what is unblocked: `bd ready --json`
- Create work items as needed:
  - `bd create "Title" --description "Context" -t task|bug|feature -p 0-4 --json`
  - Use stdin for descriptions with tricky quoting: `printf '%s' '...' | bd create "Title" --description=- --json`
- Claim/update non-interactively (do NOT use `bd edit`):
  - `bd update <id> --claim --json`
  - `bd update <id> --notes "..." --acceptance "..." --priority 1 --json`
- Close when done: `bd close <id> --reason "Done" --json`

## Mission

When OpenCode is launched inside `Rakkib/services`, the user can:
- mention a service name (example: "Vaultwarden", "File Browser"), or
- reference a list file here (examples: `PendingServices.md`, `MoreServices/*.md`),
and the agent implements the service in the Rakkib app (registry + templates + hooks + verification updates).

## Branch Rules

- **All commits go to `main`.** Never commit service work directly to `runtime`.
- For every service implementation or service-definition change, commit the completed work to `main`, push `main`, then regenerate `runtime` with `scripts/runtime-branch.sh sync --push` before test-server validation. The test server installs from `runtime` by default.
- Do not hand-edit `runtime` and do not copy files outside the runtime allowlist.

## Hard Requirements

1. Mandatory test-server validation for EVERY new service

Service work is not complete until the implementation has been committed, pushed to `main`, synced to `runtime`, and validated on the test server.

Use the dedicated project subagents for test-server validation:
- `RakkibTester1`, `RakkibTester2`, and `RakkibTester3` are the only agents that should run the test-server validation workflow.
- Assign exactly one service/bead to one tester agent at a time; do not run multiple validations concurrently on the resource-limited test server.
- Tester agents validate only. They must not edit source files, update approval docs, close beads, commit, or push. The primary agent reviews their evidence, then performs any required repository updates and bead closure.
- If a tester reports high load, memory pressure, swap exhaustion, another active validation, or a failing command, stop and document the blocker instead of marking the service complete.
- After a service passes validation, remove it immediately from the test server with `rakkib remove <service> --yes`. Do not leave successfully tested services running unless the user explicitly asks.

Before implementing a service, check `PendingServices.md` and `ApprovedServices.md`:
- if the service is in `PendingServices.md`, implement and test it, then remove it from `PendingServices.md` after successful validation
- if the service is already in `ApprovedServices.md` as `Implemented and tested`, do not reimplement it unless the user asks for a change
- if the service is in `ApprovedServices.md` as `Implemented, pending testing`, validate it before changing its status

Run deployments on the test server (not this machine):

sshpass -p 'z45rdKUe' ssh -o StrictHostKeyChecking=accept-new root@174.138.183.153 'set -euo pipefail; /root/.local/bin/rakkib --help | sed -n "1,220p"'

- The Fayaalink host at `192.168.0.235` is never a validation target. Do not test, deploy, or run service-validation workflows on `192.168.0.235`.

When delegating validation, feed the selected `RakkibTester` subagent the target bead/service, the command above, and the validation checklist below. Do not ask a beads-task-agent to run service validation.

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
- after successful validation and evidence capture, run `rakkib remove <service> --yes` again so the service does not remain on the test server
- after successful validation, mark the service in `ApprovedServices.md` as `Implemented and tested` with concise validation notes
- if validation succeeds, close the related `bd` issue and report exactly that the service is implemented successfully and tested
- if validation fails, leave the related `bd` issue open, document the issue and failing command/output, and report the blocking issue instead of claiming success

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
