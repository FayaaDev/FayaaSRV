# Codex Production Readiness Review

Date: 2026-05-06

Scope: Ubuntu 24.04 Production GA readiness. macOS is treated as development-only unless the support matrix is intentionally expanded.

## Verdict

Rakkib is **not approved for Production GA** yet.

Current state is appropriate for continued private beta with hands-on support, but GA is blocked by release-path hygiene, security, registry consistency, reproducibility, smoke coverage, and broader bare-metal validation evidence gaps.

## Resolved Findings

### Fixed P0: Cloudflare State Can Persist To The Wrong File

CLI commands load state from the installed package directory, but the Cloudflare step calls `state.save()` without an explicit path. That writes `.fss-state.yaml` to the process current working directory, not necessarily the package state path used by later `rakkib pull` runs.

Impact: tunnel UUIDs, credential paths, and Cloudflare recovery data can be lost between reruns after the most failure-prone setup step.

Evidence:
- `src/rakkib/cli.py`: default `repo_dir` is `Path(__file__).resolve().parent`.
- `src/rakkib/cli.py`: `pull` loads `repo_dir / ".fss-state.yaml"`.
- `src/rakkib/steps/cloudflare.py`: calls `state.save()` without a path.
- `src/rakkib/state.py`: default save path is relative `.fss-state.yaml`.

Fix shipped:
- `main` commit `670f34d` (`Prevent state saves from drifting into cwd`) makes `State.load(path)` bind the state object to its source path, makes explicit `save(path)` update that binding, and makes unbound bare `save()` fail loudly instead of writing to cwd.
- `runtime` commit `d0e12ad` (`Keep runtime state saves bound to install path`) mirrors the runtime source changes used by the public installer.
- `src/rakkib/interview.py` preserves the bound path across reset and only auto-persists interview progress when a state path exists.

Validation performed:
- Ran the public installer on `root@174.138.183.153`: `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash`.
- Confirmed `/opt/rakkib` fast-forwarded to `origin/runtime` commit `d0e12ad`.
- Ran a server-side venv regression that loaded state from a package-path temp file, executed `cloudflare.run(state)` with external Cloudflare/Docker calls mocked, and verified Cloudflare fields persisted to the loaded path while caller cwd had no `.fss-state.yaml`.
- Verified unbound `State({"x": 1}).save()` raises instead of creating a cwd state file.

Remaining risk: the validation exercised the state-persistence path with mocked external commands. It did not create or mutate a real Cloudflare tunnel.

## Blocking Findings

### P0: Runtime Branch Violates The Release Contract

The installer defaults to `RAKKIB_BRANCH=runtime`, but `origin/runtime` contains files outside the documented slim runtime set.

Unexpected files found:
- `.claude/worktrees/agent-a902829421f8ebba5`
- `services/services_checklist.md`

Impact: customer installs may receive development artifacts. This also weakens confidence that runtime is being produced by a controlled release process.

Required fix: rebuild/sync `runtime` from an allowlist containing only `.gitignore`, `README.md`, `install.sh`, `pyproject.toml`, and `src/rakkib/**`, then push it.

### P1: Sudo Recovery Command Is Wrong

The README and layout failure message tell users to run `rakkib auth sudo`, but the CLI defines `rakkib auth` as a command with no subcommand.

Impact: a fresh Ubuntu user blocked on directory creation may be given a command that fails.

Evidence:
- README command list documents `rakkib auth sudo`.
- `src/rakkib/steps/layout.py` tells users to run `rakkib auth sudo`.
- `src/rakkib/cli.py` defines `@cli.command() def auth(...)`.

Required fix: either implement `rakkib auth sudo` as an alias/subcommand or update all docs/messages to `rakkib auth`.

### P1: Docker Socket Services Need A Security Gate

Several services mount `/var/run/docker.sock`; Dockge has full socket access and others have either full or read-only socket mounts.

Affected templates:
- `src/rakkib/data/templates/docker/dockge/docker-compose.yml.tmpl`
- `src/rakkib/data/templates/docker/dozzle/docker-compose.yml.tmpl`
- `src/rakkib/data/templates/docker/watchtower/docker-compose.yml.tmpl`
- `src/rakkib/data/templates/docker/autoheal/docker-compose.yml.tmpl`

Impact: these services can expose host-level control or sensitive container metadata. Public routes make this especially risky.

Required fix: add explicit risk acknowledgement for Docker-socket services, document exposure clearly in the service picker, and require an access-control/default-private story before GA.

### P1: Registry And Env Templates Are Inconsistent

Some services declare required env keys that are not rendered into their `.env.example` files.

Observed inconsistencies:
- `pairdrop` declares `ADMIN_UID`, `ADMIN_GID`, and `TZ`; compose uses `${ADMIN_UID}`, `${ADMIN_GID}`, and `${TZ}`, but `.env.example` only contains `PAIRDROP_IMAGE`.
- `hermes-agent` declares `ADMIN_UID` and `ADMIN_GID`; compose uses those variables, but `.env.example` does not define them.
- `uptime-kuma` declares admin env keys, but `.env.example` says it has no required env vars. This may be intentional if hooks manage setup, but the registry contract is unclear.

Impact: Docker Compose may receive blank substitutions or service setup may depend on undeclared side effects.

Required fix: enforce registry/env/template consistency in tests and either render all declared env keys or remove registry declarations that are not actually template inputs.

### P1: Release Reproducibility Is Weak

41 of 53 services use floating image tags such as `latest` or `main`.

Impact: a customer install can change behavior without a Rakkib release. This makes GA support, debugging, and rollback difficult.

Required fix: pin images for GA-supported services to version tags or digests. Keep `latest` only behind an explicitly documented beta/unstable service tier.

## Additional Risks

### Smoke Coverage Is Incomplete

34 of 53 services declare smoke checks. Important services without registry smoke checks include NocoDB, Homepage, Uptime Kuma, Dockge, n8n, Immich, transfer.sh, Jellyfin, and OpenClaw.

Required fix: add smoke checks for all GA-supported browser-facing services, and mark services without smoke checks as beta or unsupported.

### Tests Appear Stale

`tests/test_cli.py` still references CLI options and symbols that do not exist in the current CLI shape, including `init --agent`, `--no-agent`, `--print-prompt`, `--resume`, and `rakkib.cli.handoff`.

Impact: the test suite may not be a reliable release gate until stale expectations are removed or the CLI compatibility layer is restored.

Required fix: align CLI tests with the current command surface and add regression tests for the blockers above.

### Web State Patch Is Too Broad

The authenticated web API exposes a generic `/state` patch endpoint that merges arbitrary state without schema validation.

Impact: token auth reduces exposure, but LAN setup mode still makes this a broad mutation surface for a home-server installer.

Required fix: restrict patchable fields or validate patches against the phase schemas.

### Mac Support Messaging Needs To Stay Narrow

The repo has macOS-friendly paths, but the actual production deployment path is Ubuntu-focused. The README currently says Ubuntu is the tested deployment target and macOS is supported for development, which is the right GA boundary.

Required fix: keep macOS out of the production support matrix unless a separate Mac deployment test matrix is added.

## Required GA Gate

Before Production GA approval:

1. Fix remaining P0 and P1 findings.
2. Rebuild and push a clean `runtime` branch from an allowlist.
3. Pin GA service images or define a beta tier for unpinned services.
4. Add smoke checks for all GA-supported browser-facing services.
5. Update stale tests and add regression coverage for auth command messaging, registry/env consistency, and runtime branch allowlist.
6. Run clean Ubuntu 24.04 bare-metal validation using the public curl-pipe entrypoint.
7. Validate idempotent rerun, service removal, restart-all, doctor JSON, backup/restore dry run, and at least one service from each risk category.

## Verification Performed

This review was static-only. Local app tests were not run because project guidance says the app should be tested on bare-metal target machines, not the current machine.

Commands and inspection included:
- `bd ready --json`
- `git status --short --branch`
- Runtime branch file listing with `git ls-tree`
- Source inspection across installer, CLI, steps, web API, registry, templates, and tests
- Registry metrics for service count, floating image tags, smoke coverage, Docker socket mounts, host services, and env/template inconsistencies

Follow-up validation after state fix:
- `git diff --check`
- AST parse for edited Python files
- Public installer rerun on `root@174.138.183.153`
- Server-side state-path regression in `/opt/rakkib/.venv`

## Files Changed By This Review

- `CodexReview.md`
- `.beads/issues.jsonl` was updated by `bd` task tracking for audit task `Rakkib-y4f`.
- State persistence fix changed `src/rakkib/state.py`, `src/rakkib/interview.py`, `tests/test_state.py`, and `tests/test_steps_cloudflare.py` on `main`; runtime mirror changed `src/rakkib/state.py` and `src/rakkib/interview.py`.
