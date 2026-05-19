# Rakkib Production-Readiness Audit

## Context

Rakkib is the `curl … | bash`-installed CLI that bootstraps fresh Ubuntu servers (entry: `install.sh` → `src/rakkib/`). It claims 2.0.0a and is meant to be exposed to outside operators. The audit below catalogs the gaps that would bite a real production user: a non-atomic core flow, unpinned container images, no PR-time CI, no schema-versioned state, and no end-to-end test of the install→pull→add→remove contract. The plan below fixes those in six small, reversible commits with tests, then ships a tightened checklist.

Project constraints honored throughout: service validation runs only on `174.138.183.153`; this dev box never executes service tests; the public runtime repo allowlists `install.sh`, `pyproject.toml`, `LICENSE`, `README.md`, `src/rakkib/**` only — anything under `tests/`, `scripts/`, `tools/`, `.github/` lives in the private dev repo only and that is fine.

---

## 1. Top risks (cited, ranked by robustness gain)

### P0 — production blockers

1. **No PR-time CI.** `.github/workflows/` contains only `publish-runtime.yml` and it is `workflow_dispatch` (manual). Zero lint, type, test, or install-script smoke runs before merge. Anything can land broken.
2. **`rakkib pull` / `rakkib add` are non-atomic** — `cli.py:299-320` saves state at line 305 *before* `run_single_service` runs, then returns False on exception (line 312-314) without rollback. `cli.py:323-372` (`_sync_services_to_state_selection`) wraps remove → apply → postgres → add with **no try/except**: a failure mid-add leaves containers and data dirs on disk while `deployed.*` state is never updated. Next run drifts.
3. **43 of 63 compose templates pin `:latest`** (`src/rakkib/data/templates/docker/*/docker-compose.yml.tmpl`). `docker compose pull` silently swaps images. Reproducibility is gone; healthy installs degrade over time without a code change.
4. **State has no schema version and no `fsync`** — `state.py:71-91` does atomic-rename but never `fsync(fd)` or `fsync(dir_fd)` before `os.replace`; YAML is loaded as a raw dict (line 68) with no `version` field, so once the schema changes there is no migration hook and old state will silently mis-parse. One-way trap.
5. **No end-to-end test of the install → pull → add → remove contract.** 28 test files exist (`tests/`) but all mock subprocess and never run `install.sh` in a clean Ubuntu image or exercise a real registry deploy + teardown.

### P1 — should-fix before outside users

6. **`RAKKIB_UPDATE_MODE` default is `reset`** (install.sh:11) — re-running `curl | bash` over an existing checkout silently `git reset --hard` + `git clean -fd` (lines 394-397, 451-454). User edits or in-progress state are destroyed without confirmation.
7. **`RAKKIB_REPO` / `RAKKIB_BRANCH` env vars are unvalidated** (install.sh:7-8). Anyone running `RAKKIB_REPO=… curl … | bash` installs from an arbitrary URL. No allowlist regex, no fingerprint.
8. **Service-specific branches in shared code violate the project's own rule** ("Do not add new hardcoded `if svc_id == …` branches"): nocodb default in `service_catalog.py:80-81`, openclaw user/bin resolution in `hooks/services.py:228-343`, caddy/cloudflare skip logic in `cli.py:248-249`. Each new service multiplies the surface.
9. **0/63 services have resource limits, 3/63 have healthchecks** in `src/rakkib/data/templates/docker/`. A runaway container starves the host; `depends_on` cannot wait for readiness.
10. **Public-runtime sync is manual** (`.github/workflows/publish-runtime.yml` workflow_dispatch + `scripts/publish-runtime-repo.sh`). `install.rakkib.app | bash` can install code days behind dev.

---

## 2. Simplify or remove

- `state.py:200-241` `_eval_when` — hand-rolled string-split expression parser. Replace with a tiny safe evaluator over flattened state (or reuse Jinja's already-loaded environment in `render.py`).
- `web/run.py:84-155` `WebRunManager` — daemon thread + lock + snapshot machine for "is the subprocess running." Collapse to a `poll()`-based property; no thread needed.
- `hooks/services.py` `HookContext` plus the `_coerce_hook_context` shim (lines 34-41). Pick one signature; delete the bridge.
- `render.py:34-38` and `render.py:71-78` — two render entry points that each re-flatten state. Single function; caller passes a context dict.
- Duplicate `_sudo_run()` in `hooks/services.py:283-286` and `steps/services.py:498-500` — extract to `src/rakkib/proc.py` along with a single subprocess helper that always sets `timeout=`, `check=`, and summarizes stderr.

---

## 3. Refactor order (six small, reversible commits)

Each commit is independently mergeable, lands behind passing CI, and is reversible by `git revert`. Files cited are exact targets.

**Commit 1 — CI baseline.** Add `.github/workflows/ci.yml` running `pytest -q`, `ruff check`, `ruff format --check`, `python -m compileall src/rakkib`. Add `[tool.ruff]` and `[tool.pytest.ini_options]` blocks to `pyproject.toml`. Enable branch protection on `main` requiring this workflow. No application change.

**Commit 2 — Pin docker images + enforce.** For each of the 43 templates returned by `grep -rlE 'image:.*:latest' src/rakkib/data/templates/docker/`, replace `:latest` with a current upstream tag (one-time `docker manifest inspect` lookup). Add a CI step that fails on any new `:latest` (`! grep -rE 'image:.*:latest' src/rakkib/data/templates/docker/`). Single bulk diff but trivial review.

**Commit 3 — install.sh hardening.** In `install.sh`:
- Add `validate_repo_url()` against allowlist regex `^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)FayaaDev/(rakkib|rakkib-dev)(\.git)?$` after `parse_args` (rejects via `die`).
- Add `validate_branch()` against `^[A-Za-z0-9][A-Za-z0-9._/-]{0,200}$`.
- Change `UPDATE_MODE` default from `reset` to `skip` (line 11); update the usage block; document the security tradeoff in the help text.
- Existing tests in `tests/test_install_sh.py` source the script with `RAKKIB_INSTALL_TEST_MODE=1`; extend them to cover the new validators.

**Commit 4 — State versioning + crash safety + single-source version.** In `state.py:71-91`:
- Add `version: 1` field on save; on load, dispatch through `_MIGRATIONS = {0: _upgrade_0_to_1}`.
- `os.fsync(fd)` before closing; `os.fsync(dir_fd)` on the parent directory before `os.replace`.
- Replace the `2.0.0a1` literal in `src/rakkib/__init__.py:3` with `importlib.metadata.version("rakkib")` (fixes the `pyproject.toml`-vs-`__init__.py` drift).
- New test `tests/test_state_migration.py` round-trips a v0 fixture and asserts v1 output.

**Commit 5 — Atomic `pull` / `add` / `sync`.** In `cli.py`:
- Wrap `_run_service_pull` (299-320) so the `state.save` at line 305 is replaced by an in-memory snapshot; only save *after* the deploy succeeds. On exception, restore the snapshot and re-save.
- Wrap `_sync_services_to_state_selection` (323-372) in a try/except that, on failure, calls `services_step.remove_single_service` for the IDs added during this run and restores the pre-call snapshot.
- New test `tests/test_add_atomic.py` patches `services_step.run_single_service` to raise on the third of five service IDs and asserts: (a) state file unchanged from pre-call baseline, (b) `remove_single_service` was called for the two that did succeed.

**Commit 6 — Install-script smoke + e2e contract test.** Add `.github/workflows/install-test.yml` that runs `install.sh` in a fresh `ubuntu:24.04` container and asserts `rakkib --version` works. Add `tests/e2e/README.md` documenting the manual roundtrip script that runs only on `174.138.183.153` (per project CLAUDE.md and stored memory): install → `rakkib init` → `rakkib add` (select two services) → assert containers up → `rakkib add` (deselect both) → assert containers, dirs, postgres roles gone → `rakkib uninstall --yes`. Then `rakkib remove <svc> --yes` cleanup is implicit since both were already deselected.

Two cleanup commits (P1) can land after the six above: (7) unify logging via stdlib `logging` + `RAKKIB_LOG_LEVEL` + `--verbose`; replace `print()` outside `cli.py` UI helpers; (8) move nocodb/openclaw/caddy hardcoded branches into registry fields per project rule.

---

## 4. Test plan

All service-touching validation runs on `174.138.183.153` only (project CLAUDE.md + stored memory). After each remote validation, `rakkib remove <svc> --yes` immediately.

**Golden path (remote, manual + CI-smoked).**
- Fresh `ubuntu:24.04` container: `curl -fsSL https://install.rakkib.app | bash` succeeds; `rakkib --version` prints the `pyproject.toml` version.
- `rakkib init` → `rakkib add` selects N≥3 services → `rakkib pull` → every selected container reaches `healthy` (post Commit 9 healthchecks) or `running` baseline.

**Failure modes (each must produce actionable error + leave system in a known state).**
- *Docker daemon down mid-pull*: stop docker after first service is up; rerun should resume idempotently, not double-create containers, and not corrupt state. Covered by Commit 5 atomic test plus a remote spot-check.
- *Hook raises on service N of M*: covered by `tests/test_add_atomic.py` (Commit 5). Asserts state + disk match pre-call baseline.
- *Kill rakkib mid-`state.save`* (SIGKILL during write): state file is either old or new, never partial. Covered by a Commit 4 test that hardlinks the tmp path and asserts atomicity.
- *Stale state schema*: v0 fixture → new rakkib reads → migration runs, no field loss. Covered by `tests/test_state_migration.py`.
- *Hostile env var*: `RAKKIB_REPO=https://example.com/evil curl … | bash` is rejected with a clear `die` message. Covered by Commit 3 test.

**Coverage target.** `pytest --cov=rakkib --cov-fail-under=70` in CI after Commit 1 lands the `pytest-cov` dependency.

---

## 5. Production checklist

Tick when the cited file or workflow proves it.

**Security**
- [ ] `RAKKIB_REPO`/`RAKKIB_BRANCH` validated against allowlist (`install.sh`)
- [ ] `RAKKIB_UPDATE_MODE` default = `skip` (`install.sh:11`)
- [ ] Service IDs validated `^[a-z0-9-]+$` before fs/docker use (`src/rakkib/steps/services.py`)
- [ ] `.env` files chmod 600 verified by test
- [ ] `yaml.safe_load` only (already true at `state.py:68`); add `bandit`/`ruff S506` rule in CI
- [ ] No `shell=True`; enforce via `ruff S602` in CI

**Config**
- [ ] `state.py` writes a `version:` field; migration table tested
- [ ] No `:latest` in `src/rakkib/data/templates/docker/**` (CI-enforced)
- [ ] CI runs `docker compose config` against rendered fixtures
- [ ] `pyproject.toml` version is the single source; `__init__.py` reads via `importlib.metadata`

**Logging**
- [ ] stdlib `logging` with `RAKKIB_LOG_LEVEL`; `--verbose` → DEBUG
- [ ] No raw `print()` outside `cli.py` UI helpers (grep-enforced in CI)
- [ ] `die()` messages include the next command to run

**CI/CD**
- [ ] PR pipeline: `ruff check`, `ruff format --check`, `pytest -q`, `install.sh` smoke in `ubuntu:24.04`
- [ ] Branch protection on `main` requiring those checks + 1 review
- [ ] `publish-runtime.yml` triggers on tag push, not manual dispatch
- [ ] Public-runtime sync verified by `scripts/publish-runtime-repo.sh verify` in CI before push

**Docker**
- [ ] No `:latest` (43 → 0)
- [ ] `healthcheck:` on every long-running service (3 → 60+)
- [ ] `mem_limit` and `cpus` on every service (1 → 60+)
- [ ] `depends_on.condition: service_healthy` where applicable

**Rollback**
- [ ] `_run_service_pull` atomic (Commit 5 test)
- [ ] `_sync_services_to_state_selection` atomic (Commit 5 test)
- [ ] State migrations covered both directions
- [ ] `rakkib remove` snapshots `/srv/data/<svc>` to `/srv/backups/` before deletion

---

## Verification

- **Local** (this dev box): `pytest -q` + `ruff check` + `ruff format --check` finish in <30s. Never run service validation here.
- **CI**: PR pipeline above must be green before merge; install-script smoke must pass in `ubuntu:24.04` container.
- **Remote** (`174.138.183.153` only): run the golden-path roundtrip after each commit that touches `install.sh`, `pyproject.toml`, `LICENSE`, `docs/public/README.md`, or `src/rakkib/**`. Publish runtime via `scripts/publish-runtime-repo.sh sync --push` first, since `install.rakkib.app` pulls from `FayaaDev/rakkib`. After each validation, `rakkib remove <svc> --yes` per stored memory.

## Critical files referenced

- `install.sh:7-11, 240, 394-397, 451-454, 477, 497` — installer entrypoint
- `src/rakkib/__init__.py:3` — version literal to remove
- `src/rakkib/cli.py:248-249, 299-320, 323-372` — non-atomic flows + hardcoded skips
- `src/rakkib/state.py:68-91, 200-241` — load/save/fsync + eval_when
- `src/rakkib/service_catalog.py:80-81` — nocodb hardcode
- `src/rakkib/hooks/services.py:34-41, 228-343, 283-286` — coerce shim, openclaw branches, dup sudo
- `src/rakkib/steps/services.py:268-280, 498-500, 764-770` — fragile df parse, dup sudo, silent rmtree
- `src/rakkib/render.py:34-38, 71-78` — two render entry points
- `src/rakkib/web/run.py:84-155, 152-154` — overengineered runner, silent daemon thread
- `src/rakkib/data/templates/docker/*/docker-compose.yml.tmpl` — 43 unpinned, 60+ missing health/limits
- `.github/workflows/publish-runtime.yml` — only workflow; manual; needs PR-time sibling
- `scripts/publish-runtime-repo.sh` — public-runtime sync; manual today
- `pyproject.toml` — single-source version; missing `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.coverage]`
