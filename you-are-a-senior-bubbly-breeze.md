# Rakkib — Production-Hardening Plan

## Context

Rakkib is a bare-metal home-server installer driven by `curl … | bash`. Code is ~8,700 LOC of
Python plus a 333-line `install.sh`. The user (solo senior eng) asked for a comprehensive
audit of redundancy, weak spots, and simplification opportunities, and a plan for an
"air-tight, production-ready" product. Three Explore agents mapped the codebase; one Plan
agent stress-tested sequencing. This document is the consolidated, sequenced execution plan.

The codebase is already structurally sound: registry-driven services, no `if svc_id == …`
branches in step code, clean `run/verify` step contract, `install.sh` robust on bare metal.
The work below is **hardening + decomposition**, not a rewrite.

Hot files by size:
`cli.py` 1473, `steps/cloudflare.py` 905, `hooks/services.py` 884, `steps/services.py` 723,
`doctor.py` 713, `interview.py` 637, `web/api.py` 480, `web/answers.py` 437.

---

## Findings (severity-graded; reordered after sequencing critique)

### CRITICAL — security / data-loss

- **C1. Auth bypass via query-string token.** `web/app.py:42-48` + `web/auth.py:43-47` accept
  `?token=ABC` for `/setup/*`. URL ends up in browser history, server logs, `Referer`.
  → Drop `request.query_params.get("token")` in `allow_setup_route`. SPA must POST the
  token to `/api/session/bootstrap` only.
- **C2. CSRF on state-mutating endpoints.** `web/auth.py:75` is `samesite="lax"`; nothing in
  `web/api.py` (`PATCH /api/state`, `POST /api/questions/phases/{n}/answers`,
  `POST /api/run/start`) checks a CSRF token.
  → `samesite="strict"`; issue a per-session CSRF token at bootstrap, require
  `X-CSRF-Token` header on every POST/PATCH/DELETE.
- **C3. State file written world-readable + non-atomic.** `state.py:50`
  `save_path.write_text(yaml.safe_dump(...))` has no `chmod` and no atomic rename; the
  state contains `secrets.values.POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY`, Cloudflare
  tunnel data. A power-cut mid-write produces an unparseable YAML.
  → Write to `<path>.tmp`, `chmod(0o600)`, `os.replace()`. Add a `verify` check that
  refuses a state file with mode broader than `0o600`.
- **C4. Cloudflare DNS records orphaned on service removal.** `steps/cloudflare.py` (905
  LOC) has no DNS-delete path; `hooks/services.py:880` `REMOVE_HOOKS` only covers
  openclaw/claude/codex teardown. Deselecting `vaultwarden` leaves
  `vault.example.com` resolving to the tunnel — subdomain hijacking / routing ambiguity
  vector when a different service later reuses the subdomain.
  → Add `cloudflare.delete_dns_route(state, subdomain)` (calls `cloudflared tunnel route
  dns delete`; tolerates "not found" as success). Wire as `hooks.remove:
  [cloudflare_dns_delete]` in `registry.yaml` for every service with a `default_subdomain`.
  This stays registry-driven — no per-service `if` branches.
- **C5. Postgres role/password embedded in SQL via f-string.** `steps/postgres.py:84-91`
  and `steps/services.py:347-350` interpolate `role`, `password`, `db_name` directly. Today
  mitigated only because `secrets.generate_password()` is alphanumeric; the `role`/`db`
  identifier path is unchecked — a registry author could write `role: "x; --"` legally.
  → Dollar-quote passwords (`PASSWORD $${pw}$$`); regex-validate identifiers
  (`^[a-z][a-z0-9_]{0,62}$`) at registry-load time and at SQL-emit time.
- **C6. `shell=True` on schema-loaded strings.** Five sites total — wider than the audit
  initially noted: `interview.py:287-289` (detect), `interview.py:559, 568, 576`
  (host_default), `web/answers.py:357-376`. Today the schema is in-repo (trusted) but the
  pattern is a footgun.
  → `shlex.split()` + `shell=False` everywhere. Reject any token with `;|&$\`(){}<>`
  on parse to keep the contract tight.
- **C7. Unchecked sudo chown.** `steps/services.py:274-285` ignores `returncode` on
  `sudo -n chown -R …`. Without passwordless sudo, chown silently fails and downstream
  ops mount with the wrong owner.
  → Check returncode; raise `RuntimeError(stderr.strip())`.

### HIGH — correctness

- **H1. `remove` not idempotent.** `steps/services.py:384` `route_path.unlink()` raises on
  second run. → `unlink(missing_ok=True)`.
- **H2. Postgres init SQL file written without chmod.** `steps/postgres.py:180` writes a
  plaintext-password file with default umask. → `chmod(0o600)` after write.
- **H3. No session revocation.** `web/auth.py` has no logout. → `POST /api/session/logout`
  removes the id from `_sessions` and clears the cookie.
- **H4. Service-catalog side-effects diverge between web and CLI.** `web/answers.py:53-55,
  220-308` sets `confirmed=False` and `web_deployment.status="stale"`; the CLI
  (`interview.py:127-204`) does not. Same data, two code paths.
  → Extract `service_catalog.ServiceCatalogHandler` consumed by both **after** M5
  validators land (so the handler reuses one validator, not two).
- **H5. Web API has zero tests.** `web/api.py` (480 LOC) and `web/auth.py` are
  untested — C1 and C2 would have been caught.
  → New `tests/test_web_api.py` with `fastapi.testclient.TestClient`. **Land first**, with
  failing regression tests for C1 + C2; the C1/C2 PRs flip them green.
- **H6. Doctor `--fix` pipes scripts from the internet without checksums.**
  `doctor.py:607-673` runs `curl … | sh` for cloudflared and the Compose plugin.
  → Pin SHA256 for cloudflared release + Compose plugin URL. For `get.docker.com` keep
  but document the trust boundary.
- **H7. Render leaves `{{ KEY }}` literals on missing variables.** `render.py:21` uses
  `DebugUndefined`; a missing `N8N_ENCRYPTION_KEY` ships as the literal `{{ N8N_ENCRYPTION_KEY }}`
  into `.env`. → In `steps/verify.py`, refuse rendered `.env`/`Caddyfile`/compose files
  containing the substring `{{ ` and emit a clear error with the offending key.
- **H8. `runtime-branch.sh` push without `--force-with-lease`.** Two engineers running
  `sync --push` simultaneously can lose commits. → Use `git push --force-with-lease` at
  `scripts/runtime-branch.sh:255`.
- **H9. `web/run.py` orphans subprocesses.** `WebRunManager` has no kill path — if
  `rakkib pull` hangs (cloudflared login waiting forever), the user's only recovery is
  restarting `rakkib web`, leaving an orphan child. → `POST /api/run/cancel` →
  `process.terminate()`; track child PID in state for visibility.

### MEDIUM — maintainability (no behavior change)

- **M1. Decompose `cli.py` (1473 → ~600 LOC).** 27 helpers live above the `@cli.group`
  decorator. Move:
  - service-selection helpers (lines ~120–264, 301–354, 644–691) → `steps/services.py`
    (or a new `services_cli.py`)
  - docker-prereq logic (lines 365–501) → `doctor.py`
  - state helpers (93–117) → methods on `State`
  - small utilities (`_web_url`, `_checkout_dir`, `_default_host_gateway`,
    `_detect_lan_ip`) → new `util.py`
  **Do this before M2/M3/M4** — they all touch `cli.py`.
- **M2. Consolidate `_resolve_admin_user` (cli.py:68-78) + `_docker_access_user`
  (cli.py:365-373).** Single `resolve_user(state, *, explicit=None, require=False)`.
- **M3. Consolidate `_build_add_choices` (cli.py:120-174) + `_build_restart_choices`
  (cli.py:177-238).** ~90% identical; parameterize with a `PickerOptions` dataclass.
- **M4. Stop reaching for `data_root` and `repo_dir` everywhere.** 7+ inlined
  `Path(state.get("data_root", "/srv"))`, 6+ inlined `Path(__file__).resolve().parent.parent / "data"`.
  Add `state.data_root` property and a module-level `RAKKIB_DATA_DIR` constant; sweep
  `steps/*.py` and `cli.py`.
- **M5. Web/TUI validation duplication.** Text validator (`web/answers.py:199-217` vs
  `interview.py:585-613`), confirm (`135-162` vs `350-379`), secret group (`89-111` vs
  `448-463`), single-/multi-select. Extract `src/rakkib/validators.py` with pure functions;
  consume from both call sites. **Do this before H4.**
- **M6. Decompose `steps/cloudflare.py` (905 LOC).** Split into:
  - `cloudflare/client.py` — typed `cloudflared` wrapper (list/create/get tunnel,
    add/delete DNS route)
  - `cloudflare/auth.py` — three auth methods
  - `cloudflare/credentials.py` — discovery, ownership/perm repair
  - `cloudflare/verify.py` — metrics + edge-health (absorbs `doctor.py:412-536`
    `check_cloudflare_readiness`)
  - `steps/cloudflare.py` — orchestration + state mutation only
  Each ≤ 250 LOC. C4's DNS-delete function lives in `cloudflare/client.py`.
- **M7. `HookContext` for hooks.** All hooks in `hooks/services.py` take 6 args; most use
  one. Replace with `@dataclass class HookContext` (state, svc, repo, data_root, log_path,
  registry). Sweep all hook signatures.
- **M8. Per-fragment Caddy validation.** `steps/caddy.py:69` only validates the assembled
  Caddyfile — error messages don't identify the broken service. After rendering each
  fragment, validate against a synthetic Caddyfile containing just that fragment; report
  service id on failure. Bundle with H7.
- **M9. Cycle detection in service-dependency topo-sort.** `steps/__init__.py:97-98`
  silently appends remaining nodes. → Detect remaining-after-Kahn = cycle; raise
  `RegistryError("dependency cycle: …")`.
- **M10. install.sh signal handling.** Ctrl-C mid-`pip install` leaves a half-installed
  venv at `${INSTALL_DIR}/.venv`. Add `trap` for INT/TERM/ERR that warns the user the
  venv is incomplete and points at the recovery command (`rm -rf ${INSTALL_DIR}/.venv &&
  rerun`). (Promoted from LOW.)
- **M11. Subprocess error messages truncate stderr.** `docker.py:_error_message`
  (around lines 257–261) — when a service fails to start during a fresh-server install,
  truncated `stderr` is what gates 80% of user support cost. Include up to 2 KB of
  `stderr.strip()`. (Promoted from LOW.)

### LOW — polish (bundle as one PR)

- **L1.** Drop `main()` wrapper in `cli.py`; point `pyproject.toml` `[project.scripts]
  rakkib = "rakkib.cli:cli"` directly.
- **L2.** Promote `"always"`/`"foundation_services"`/`"selected_services"` to a `StateBucket`
  `StrEnum` in `state.py`.
- **L3.** `extra_templates` missing-file check in `steps/services.py:288-293` — raise
  with the registry-author–facing message (which `svc_id`, which path).
- **L4.** Path-traversal defense for `caddy.template`: reject names containing `/` or `..`
  in `steps/services.py:245-259`. (Defense-in-depth; registry is in-repo.)
- **L5.** Ollama variants (`registry.yaml:1715-1764`) — three near-identical entries differ
  only in `image`. Optional `gpu_variant` field with an `image_variants` map.
- **L6.** Test fixture consolidation into `tests/conftest.py`. (Lands as part of PR-01.)

### Dropped from earlier draft

- **`_run_steps` per-step rollback** (originally M13) — already documented intent of the
  `run/verify` contract; one-paragraph addition to CLAUDE.md is enough.
- **`cli.py:544-547` verify-break** — flagged in critique but the early-break already has
  a comment (`already ran _collect_verifications`); not a bug.
- **OpenClaw timeouts to registry** (M8 in earlier draft) — three constants in one hook;
  cost of registry schema extension > readability win until other host services
  accumulate similar magic numbers.
- **Snapshot-test brittleness** — keep until a flake instance materializes.

---

## Sequenced PR plan (each <60 min review)

The order matters because some refactors enable others. **PR-01 first** so C1/C2 land
under regression coverage.

1. **PR-01 — Web API test scaffold (H5 + L6).** `tests/conftest.py` shared fixtures;
   `tests/test_web_api.py` covers health, bootstrap, state GET/PATCH, phases GET/POST,
   run start. Includes failing regressions for C1 and C2. Pure-test PR, no source edits.
2. **PR-02 — C1 (auth bypass).** `web/app.py:42-48` + `web/auth.py:43-47`. C1 tests pass.
3. **PR-03 — C2 (CSRF + samesite=strict).** `web/auth.py:69-78` cookie flags;
   `csrf_token` issued at bootstrap; `X-CSRF-Token` enforced in `web/api.py` POSTs/PATCHes.
4. **PR-04 — C3 (state file).** `state.py:37-50`: tmp + chmod + `os.replace`. New
   `tests/test_state.py::test_save_creates_0o600`. Add a `verify` check.
5. **PR-05 — C5 (postgres SQL).** Add `_postgres_quote.py` with identifier validator and
   dollar-quoter; rewrite `steps/postgres.py:84-91` and `steps/services.py:347-350`.
6. **PR-06 — C6 (shell=True sweep).** All five sites in `interview.py` and `web/answers.py`.
   Switch to `shlex.split` + `shell=False`; assert with each detect string in
   `data/questions/*.md`.
7. **PR-07 — C4 + C7 + H1 + H2 (service-removal correctness).** Coherent
   "teardown/hygiene" theme: DNS cleanup hook, sudo-chown returncode, `unlink(missing_ok=True)`,
   `init.sql` chmod.
8. **PR-08 — H3 + H6 + H7 + H9 (web + render hardening).** Logout endpoint,
   pinned-checksum doctor fixes, refuse `{{ ` literals in rendered output, run-cancel
   endpoint.
9. **PR-09 — H8 + M10 + M11 (install / subprocess polish).** `--force-with-lease`,
   install.sh trap, `_error_message` keeps 2 KB of stderr.
10. **PR-10 — M5 (validators extraction).** Pure refactor, broad reach but no behavior
    change. Strong tests already exist in `test_interview.py`/`test_web_answers.py`; mirror
    them in a new `tests/test_validators.py`.
11. **PR-11 — H4 (ServiceCatalogHandler).** Now consumes M5 validators. Land the
    behavior unification (CLI gains `confirmed=False`/`web_deployment.status="stale"`
    semantics under explicit flag).
12. **PR-12 — M1 (cli.py decomposition).** ~600 LOC moved across new homes; commands
    stay in `cli.py`.
13. **PR-13 — M2 + M3 + M4 (dedupe inside the new structure).** Cheap once M1 is in.
14. **PR-14 — M6 (Cloudflare split).** Absorbs `check_cloudflare_readiness` from
    `doctor.py`. C4's DNS-delete moves into `cloudflare/client.py` cleanly.
15. **PR-15 — M7 (HookContext).** Touches every hook — sweep is mechanical.
16. **PR-16 — M8 + M9 (Caddy per-fragment validate + cycle detection).**
17. **PR-17 — LOW polish bundle (L1–L5).**

---

## Critical files to modify (top of each PR's diff)

- `src/rakkib/web/auth.py`, `src/rakkib/web/api.py`, `src/rakkib/web/app.py`,
  `src/rakkib/web/answers.py`, `src/rakkib/web/run.py`
- `src/rakkib/state.py`
- `src/rakkib/steps/postgres.py`, `src/rakkib/steps/services.py`,
  `src/rakkib/steps/cloudflare.py`, `src/rakkib/steps/caddy.py`, `src/rakkib/steps/verify.py`,
  `src/rakkib/steps/__init__.py`
- `src/rakkib/hooks/services.py`
- `src/rakkib/data/registry.yaml` (new `hooks.remove: [cloudflare_dns_delete]` entries
  for services with `default_subdomain`)
- `src/rakkib/render.py`, `src/rakkib/interview.py`, `src/rakkib/cli.py`,
  `src/rakkib/docker.py`, `src/rakkib/doctor.py`
- `install.sh`, `scripts/runtime-branch.sh`, `pyproject.toml`
- `tests/test_web_api.py` (new), `tests/test_validators.py` (new),
  `tests/test_service_catalog.py` (new), `tests/conftest.py` (consolidate)

## Reuse — don't reinvent

- `rakkib.normalize.eval_when` already evaluates conditional expressions for both web and
  CLI paths; the `ServiceCatalogHandler` (H4) must consume it, not reimplement.
- `rakkib.docker.docker_run` is the right wrapper for any new subprocess call (handles
  log redirection, permission-error detection); use it for the new
  `cloudflared … route dns delete`.
- `rakkib.secrets.ensure_secrets` already handles conditional secrets and propagation —
  M7's `HookContext` should expose its results, not regenerate.
- `rakkib.render.flatten_state` + `render_file` are the rendering surface; H7's strict
  check belongs at the `render_file` boundary so all callers benefit.
- The orphan-worktree pattern in `scripts/runtime-branch.sh` (lines 209–235) is the
  reference for any future "promote to runtime" tooling — do not invent a parallel path.

## Acceptance criteria for the four ship-blockers

**C1 (auth bypass):**
- `GET /` and `GET /setup/...` with `?token=$VALID` → 401 unless also presenting a session
  cookie or `Authorization: Bearer`.
- `auth.allow_setup_route` no longer reads `request.query_params`.
- New tests: `?token=` → 401; `Authorization: Bearer $T` → 200; bootstrap+cookie → 200.

**C2 (CSRF):**
- `samesite="strict"` on session cookie.
- `csrf_token` issued at bootstrap, stored server-side keyed by session id.
- All POST/PATCH/DELETE endpoints in `web/api.py` require `X-CSRF-Token`.
- Test: valid session cookie + missing/wrong `X-CSRF-Token` → 403 on `PATCH /api/state`,
  `POST /api/questions/phases/{n}/answers`, `POST /api/run/start`.

**C3 (state file):**
- Save uses `tmp = path.with_suffix(path.suffix + ".tmp")`; `os.chmod(tmp, 0o600)` before
  `os.replace(tmp, path)`.
- Test: after `State.save()`, `(stat.st_mode & 0o777) == 0o600`.
- `verify` step fails if existing `.fss-state.yaml` has wider mode.

**C4 (DNS cleanup):**
- `cloudflare.delete_dns_route(state, fqdn)` calls
  `cloudflared tunnel route dns delete <tunnel> <fqdn>`; "not found" maps to success.
- `registry.yaml` adds `hooks.remove: [cloudflare_dns_delete]` for every service with a
  `default_subdomain` (filebrowser, vaultwarden, forgejo, mealie, cheshire-cat-ai, etc.).
- Test: with a fixture state holding `vault.example.com`, calling
  `services.remove_single_service(state, "vaultwarden")` invokes the hook with
  `subdomain=vault, domain=example.com` (assert exact `cloudflared` argv via subprocess
  mock).
- Manual smoke (bare-metal box): deploy with vaultwarden, run `dig vault.example.com`
  (resolves), `rakkib remove vaultwarden`, `dig vault.example.com` (no longer resolves
  via the tunnel).

---

## Verification (end-to-end)

Per CLAUDE.md, **do not run install.sh / `rakkib pull` / docker / cloudflared on this dev
machine**. The full functional bar is exercised on a fresh Ubuntu 24.04 bare-metal target;
this dev box runs only static checks and pytest.

On this dev machine, after each PR:

```
# install dev deps once
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'

# unit + web TestClient suite
.venv/bin/pytest -q

# install.sh shellcheck
shellcheck install.sh scripts/runtime-branch.sh

# registry consistency (already a test; ensures no broken depends_on, hook names, templates)
.venv/bin/pytest -q tests/test_registry_consistency.py
```

On the bare-metal target after the security PRs (PR-02 through PR-08) ship to `runtime`:

```
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
rakkib init && rakkib pull
rakkib add        # deselect a service that has a Cloudflare subdomain
dig <removed>.<domain>   # must NOT resolve via the tunnel
stat -c '%a' ~/Rakkib/.fss-state.yaml   # must be 600
curl -i 'http://<server>/setup/?token=$BOOTSTRAP'   # must be 401 without bootstrap POST
```

After M-series refactors land, rerun the same bare-metal smoke to prove behavior parity.

After every PR that touches `install.sh`, `pyproject.toml`, or `src/rakkib/**`, regenerate
the runtime branch:

```
scripts/runtime-branch.sh sync --push
```

(Never hand-edit `runtime`; only `main` is the development branch.)
