# Rakkib Simplification Plan

## Context

Rakkib's stated mission is small: an agent reads question files, fills `.fss-state.yaml`, renders `{{PLACEHOLDER}}` templates, and runs step files in numeric order with `## Verify` gates. The implementation has grown to ~6,400 LOC of markdown/shell/templates (excluding `web/`) and three of its four protocol docs now drift apart on the same five facts. Three audits found:

- **~60% of the bootstrapper shell is deletable** (1,937 → ~780 lines essential). Substantial dead code in `install.sh` and ~600 lines duplicated across `install.sh` / `bin/rakkib` / `scripts/rakkib-doctor`.
- **Four protocol docs restate the same content** and the canonical agent prompt now exists verbatim in 5 places, already drifting.
- **Templates have a 11-file Caddy fan-out and a 5-file Compose fan-out** that could collapse to one parametric template + a registry table.
- **`VErgo/` and `templates/vergo/` are an accidental fork** — `VErgo/templates/zshrc.mac.zsh` has an `agent-browser` block missing from the rendered `templates/vergo/zshrc.mac.zsh.tmpl`.

The goal is to shrink the surface area an operator (or agent) must hold to run Rakkib without changing its behavior or shipping less. Recommend a phased cleanup, riskiest changes last.

## Implementation Status

- Branch work is on local branch `Simplify`; installer defaults now point at branch `Simplify`.
- Phase 1 is complete: root docs now point to `AGENT_PROTOCOL.md`, `README.md` is under 80 lines, and the beads workflow moved to `docs/beads.md`.
- Phase 2 is complete with one correction: the repo now has 10 numbered step files, not 8, because `steps/70-host-agents.md` and `steps/72-host-customization.md` remain active first-class steps. The removed/folded files are `05-preflight`, `20-network`, `80-backups`, `82-restore-test`, `85-health-crons`, and `lib/validation.md`.
- Phase 4 is complete with one pragmatic deviation: shared helpers moved to `lib/common.sh`, dead bootstrapper/CLI paths were removed, and `bash -n` passes, but the shell total is 1,145 lines rather than the original sub-900 target because the active doctor checks, privileged helper, uninstall command, and safe bootstrap flow were preserved.
- Phases 3 and 5 remain pending.

---

## Phase 1 — Documentation collapse (completed)

**Problem:** `README.md` (228), `AGENT_PROTOCOL.md` (247), `AGENTS.md` (339), `CLAUDE.md` (111) overlap on the bootstrap path, agent prompt, state schema, service list, and privilege rules. The canonical agent prompt appears in `README.md:147-156`, `CLAUDE.md:11-19`, `AGENTS.md:57-67`, `install.sh:179-189`, `bin/rakkib:178-189` and is already drifting (e.g. `AGENTS.md` omits the "skip restore-test" clause). `AGENTS.md:229-339` is a 110-line beads-tracker block unrelated to the installer mission.

**Action:**
1. Make `AGENT_PROTOCOL.md` the **single normative spec**. Everything else links into it.
2. Shrink `README.md` to: tagline, 5-line quickstart (`curl ... | bash`), pointer to `AGENT_PROTOCOL.md`, license. Target ~60 lines.
3. Replace `CLAUDE.md` and `AGENTS.md` with one-line pointers (or delete and let the agent read `AGENT_PROTOCOL.md` directly — it's already the source they're paraphrasing).
4. Move the beads-tracker workflow out of `AGENTS.md` into `docs/beads.md` (or delete if not in active use).
5. Make `bin/rakkib`'s `agent_prompt()` the **single source of the prompt string**. `install.sh` and the docs reference it instead of duplicating the text.
6. Service lists: keep `registry.yaml` canonical. Delete service-table prose from `README.md:25-42`, `AGENTS.md:80-118`, `CLAUDE.md:50-55`. Where prose is needed, generate from the registry.

**Files touched:** `README.md`, `AGENT_PROTOCOL.md`, `AGENTS.md`, `CLAUDE.md`, `docs/beads.md`, `bin/rakkib`, `install.sh`. Net: root prose removed, drift reduced, and `bin/rakkib:agent_prompt()` is the prompt source.

---

## Phase 2 — Steps and lib trim (completed)

**Problem:** Three step files don't earn their keep, and `lib/validation.md` is a third copy of every step's `## Verify` block that has already drifted (it still says `id -u eq 0` for Step 00 while the step now says `-ne 0`).

**Action:**
1. Fold `steps/05-preflight.md` (23 lines, "run rakkib-doctor and stop on fail") into `steps/00-prereqs.md` as a final action.
2. Fold `steps/20-network.md` (13 lines, one `docker network create`) into `steps/30-caddy.md` action 0.
3. Move `steps/82-restore-test.md` to `docs/runbooks/restore-test.md` — `AGENT_PROTOCOL.md:184` already says it's skipped on first install; it's a runbook, not a step.
4. Merge `steps/80-backups.md` and `steps/85-health-crons.md` into a single `steps/80-cron-jobs.md` (both install cron entries with the same `# RAKKIB:` marker pattern).
5. Delete `lib/validation.md`. Step files are canonical for `## Verify` blocks.

**Result:** 14 steps → 10. One fewer duplicate validation file to keep in sync.

**Files touched:** `steps/*`, `docs/runbooks/restore-test.md`, `lib/validation.md`, plus references in `AGENT_PROTOCOL.md`.

---

## Phase 3 — Template parametrization

**Problem:** Heavy fan-out where one parametric template + a registry table would do.

**Action:**
1. **Caddy routes:** replace 11 of 12 templates in `templates/caddy/routes/` with one `route.caddy.tmpl` driven by per-service entries in `registry.yaml`:
   ```yaml
   caddy:
     subdomain_key: SUBDOMAIN_NOCODB
     upstream: nocodb:8080
     auth: false
   ```
   Keep `root.caddy.tmpl` bespoke. The byte-identical `header_up X-Forwarded-*` block (8 files) and the byte-identical `forward_auth authentik-server:9000 { ... }` block (4 files) collapse into the parametric template.
2. **Docker compose simple services:** replace `uptime-kuma`, `dockge`, `homepage`, `nocodb`, `n8n` compose templates with one `simple-service.yml.tmpl` driven by registry fields (`image`, `volumes[]`, `healthcheck`, `needs_docker_sock`, `needs_env_file`). Keep `authentik`, `immich`, `dbhub`, `postgres`, `caddy`, `cloudflared`, `transfer` bespoke (genuine multi-container or special).
3. **Resolve VErgo fork:** pick `VErgo/templates/` (it has the `agent-browser` block) as the source, regenerate `templates/vergo/*.tmpl` from it, and either delete the unused dev artifacts in `VErgo/` (`Plan1.md`, `Plan2.md`, `aerospace.sh`, `terminal.sh`, `files/.p10k.zsh`, `files/.wezterm.lua`, `opencode/command/power10k.md`, the empty `@/` dir) or move them into `docs/`.
4. Drop unused `{{TUNNEL_CREDS_HOST_PATH}}` from `lib/placeholders.md` (grep returns zero hits in any template) — or wire it in.
5. Audit and remove the cargo-culted `Environment="OPENCLAW_WINDOWS_TASK_NAME=…"` line in `templates/systemd/claw-gateway.service.tmpl`.

**Result:** ~15 fewer template files, ~250 fewer lines, no behavior loss.

**Files touched:** `templates/caddy/routes/*`, `templates/docker/{uptime-kuma,dockge,homepage,nocodb,n8n}/*`, `templates/vergo/*` and `VErgo/*`, `templates/systemd/claw-gateway.service.tmpl`, `registry.yaml`, `lib/placeholders.md`, `steps/30-caddy.md` (rendering loop), `steps/60-services.md` (rendering loop).

---

## Phase 4 — Shell consolidation (completed)

**Problem:** `install.sh` (553), `bin/rakkib` (927), `scripts/rakkib-doctor` (457) = 1,937 lines with ~220 dead in `install.sh` alone and ~600 duplicated across the three.

**Action:**
1. **Delete dead code in `install.sh`** (these never run from `main`):
   - `ensure_linux_root` (lines 144-160) — defined, never called.
   - `run_doctor` + `RUN_DOCTOR`/`DOCTOR_ONLY` flags + parsing for `--skip-doctor`/`--doctor-only` (8-9, 107-114, 162-176).
   - The entire agent-launch stack: `agent_prompt`, `print_agent_prompt`, `agent_label`, `select_agent`, `offer_install_opencode`, `ensure_opencode_on_path`, `launch_agent`, `PRINT_PROMPT_ONLY`, `AGENT_MODE` (10-11, 178-397).
   - `--sudo-preauth` flag parsed and discarded (129-132).
   - The "root with `SUDO_USER`" bootstrap-user path (`BOOTSTRAP_USER`, `BOOTSTRAP_USER_HOME`, `run_as_bootstrap_user` and all callers, 13-24, 65-71). README already discourages this invocation.
2. **Extract a shared helper** `lib/common.sh` (sourced by all three scripts) covering: `command_exists`, `log/warn/die`, `detect_platform`, `state_value` (the awk YAML reader), `shell_quote`, `rerun_command`, `parse_args`. ~150-200 lines, replaces ~600 lines of duplication.
3. **Drop `bin/rakkib` subcommands the agent already covers:**
   - `cmd_install` (829-848) — confirmed-gate logic the agent enforces by reading state.
   - `auth cloudflare` (669-688), `auth agent` (655-666) — duplicates `rakkib-doctor` checks and `select_agent`.
   - `start_sudo_keepalive` + `maybe_authorize_sudo_for_agent` (369-441, ~80 lines) — protocol can simply require `sudo -v` once before launch; the agent's per-action `sudo -n` should fail loud, not be papered over by a background keepalive.
4. **Doctor cleanup:**
   - Move `check_cloudflare_token` (368-386) into `steps/40-cloudflare.md` where Cloudflare lives.
   - Drop `check_firewall` (417-427) — emits no actionable threshold, decorative.
5. **`install.sh` final shape:** clone repo, install shim, edit `.bashrc` for PATH, print "now run `rakkib init`". Target was ~80 lines; actual is 204 lines to preserve local/remote bootstrap safety checks and help text.

**Result:** 1,937 → 1,145 lines across `install.sh`, `bin/rakkib`, `scripts/rakkib-doctor`, and `lib/common.sh`. `bin/rakkib` keeps `init`, `doctor`, `auth sudo`, `prompt`, `privileged`, `uninstall`, and `version`.

**Files touched:** `install.sh`, `bin/rakkib`, `scripts/rakkib-doctor`, new `lib/common.sh`, `steps/40-cloudflare.md`, `AGENT_PROTOCOL.md` (drop sudo-keepalive section).

---

## Phase 5 — State file cleanup

**Problem:** Constants and never-varying combinations live in `.fss-state.yaml`.

**Action:**
1. Move `claw_gateway_port: 18789`, `hermes_dashboard_port: 9119`, `cloudflared_metrics_port: 20241` from state into `registry.yaml` defaults. They are constants, not user choices.
2. Collapse `privilege_mode` + `privilege_strategy` into one field — only two combinations are ever recorded.
3. Update `lib/placeholders.md`, `CLAUDE.md` (state schema section), and any step files that read these values.

**Files touched:** `lib/placeholders.md`, `registry.yaml`, `CLAUDE.md` (state schema), `questions/01-platform.md`, step files that reference these placeholders.

---

## Critical Files To Read Before Executing

- `AGENT_PROTOCOL.md` — the spec the agent obeys. Phase 1 makes this canonical.
- `bin/rakkib:178-189` (`agent_prompt`) — will be the single source of the prompt string after Phase 1.
- `registry.yaml` — gains a `caddy:` block per service in Phase 3 and the constant ports in Phase 5.
- `lib/placeholders.md` — shrinks in Phase 3 (drop unused) and Phase 5 (drop constants).
- `steps/30-caddy.md`, `steps/60-services.md` — their template-rendering loops change in Phase 3.
- `install.sh:178-397` — large dead-code deletion in Phase 4.

## Reuse Already Available

- `registry.yaml` is already the canonical service catalog — Phases 1 and 3 lean on it instead of inventing a new index.
- `bin/rakkib:agent_prompt()` already exists; Phase 1 promotes it to the single source rather than writing a new mechanism.
- Step files' existing `## Verify` blocks are already the canonical verifier — Phase 2 deletes `lib/validation.md` rather than writing a new validator.

---

## Verification

Each phase is independently verifiable; do not advance past a failing check.

**Phase 1:** `grep -n "Read README.md and AGENT_PROTOCOL.md first" -r .` returns no active root-doc or CLI hits. `wc -l README.md` < 80. Beads workflow lives in `docs/beads.md`; root docs only point to it.

**Phase 2:** `ls steps/` shows 10 numbered files. `lib/validation.md` is gone. Run a clean install end-to-end against a test VM; every `## Verify` block passes.

**Phase 3:** `ls templates/caddy/routes/ | wc -l` = 2 (root + parametric). `ls templates/docker/` no longer contains `uptime-kuma/docker-compose.yml.tmpl` etc. Render a state file with all foundation services and diff the output against the pre-refactor render — expect identical bytes.

**Phase 4:** `wc -l install.sh bin/rakkib scripts/rakkib-doctor lib/common.sh` currently totals 1,145. `bash -n` passes on each. Re-run `curl ... | bash` against a fresh VM; bootstrap completes; `rakkib init` launches the agent; `rakkib doctor` runs cleanly.

**Phase 5:** `grep -E "claw_gateway_port|hermes_dashboard_port|cloudflared_metrics_port" .fss-state.yaml.example` returns nothing. Render templates with a fresh state file — placeholders still resolve via registry defaults.

**Final smoke:** end-to-end install against a fresh Linux VM and a fresh Mac, foundation + one optional service each. Every step's `## Verify` block passes. `rakkib doctor` clean. Public hostnames serve over HTTPS.

---

## Out of Scope

- v2 CLI architecture in `v1.1-tool-expansion.md` and `v2.md` — separate effort.
- The `web/` Vite app — not part of the installer's complexity.
- Adding new services or features — this plan only removes/consolidates.
- Beads issue tracker integration — orthogonal; either keep as-is or remove independently.
