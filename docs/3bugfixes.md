# Rakkib UX fixes from dry-run feedback

> **v2 Migration Note.** The issues below were identified during v1 (bash-driven) dry-run
> feedback. They are resolved structurally by the v2 Python rewrite (`pyplan.md`). The
> `bin/rakkib` bash script, `lib/common.sh`, and `scripts/rakkib-doctor` have been removed;
> their logic was absorbed into the Python CLI (`src/rakkib/`). Where this doc references
> those old files, the fixes were reimplemented in Python rather than patched in bash.

## Context

User dry-tested Rakkib v1 (bash implementation) on a fresh Linux box and hit three rough edges:
1. After `install.sh`, both `rakkib` and a freshly installed `opencode` need a manual `source ~/.bashrc` before they resolve on PATH.
2. Docker image pulls during Step 5 stream layer-by-layer progress through the agent, burning tokens and feeling slow because the agent has to "watch" each pull complete.
3. Re-opening the AI session after completing onboarding (questions phases 1–6) restarts the interview from question 1 instead of resuming from the recorded `.fss-state.yaml`.

These are fixed in the v2 Python CLI.

Goal: make first-run frictionless, decouple heavy Docker work from the agent's token stream, and make onboarding resumable.

---

## Issue 1 — Auto-applied PATH so nothing has to be sourced

**Root cause.** `install.sh` writes a PATH block to `~/.bashrc` (line 154–174 in `install.sh`) but never applies it to the *current* shell, and never touches `~/.zshrc` / `~/.profile`. When the user closes the bootstrap and reopens a terminal whose login shell is `zsh` (Ubuntu 24.04 desktop default for new users in some images, and the default on macOS), the PATH change never takes effect. Same situation hits the OpenCode installer that `offer_install_opencode()` invoked (`bin/rakkib:201` in v1) — it wrote its own bashrc block but the running rakkib process and any new terminal needed a re-source.

**Fix — multi-shell PATH only, no auto-launch.**
1. In `install.sh::ensure_bash_path` (rename to `ensure_shell_path`), write the same PATH block to `~/.bashrc`, `~/.zshrc`, and `~/.profile` whenever those files exist, plus always to the rc file matching `$SHELL`. Keep the same `# Added by Rakkib:` marker so it stays idempotent and `rakkib uninstall` can clean all three.
2. In the v1 bash entrypoint, after a successful OpenCode `curl | bash` install, mirror the same logic for `~/.opencode/bin` across bashrc/zshrc/profile, and `hash -r`. The in-process `export PATH=` already happens — that part is fine.
3. Update the `print_next_steps` message in `install.sh` to make clear that opening a new terminal is enough — no `source ~/.bashrc` needed — and to show the absolute-path command (`~/.local/bin/rakkib init`) as a fallback for the *current* shell.

**Files to modify.**
- `install.sh` — extend the PATH-writing helper to cover zsh and profile; tweak `print_next_steps` wording.
- `bin/rakkib` — extend `ensure_opencode_on_path` and `cmd_uninstall` to handle the additional rc files. *(Superseded by v2: `bin/rakkib` was removed; PATH and uninstall logic live in the Python CLI.)*

---

## Issue 2 — Decouple Docker pulls from the agent

**Root cause.** Step 5 (`steps/5-services.md`) drives `docker compose up -d` per service while the agent watches stdout/stderr. Compose dumps per-layer progress for every image (Authentik ≈600 MB across multiple containers, Immich ≈3 GB with the custom Postgres image), so the agent's context window is flooded with pull noise it doesn't act on.

**Recommended approach: split image acquisition from service start.**

1. **New `rakkib pull` command.** Reads `.fss-state.yaml`, computes the set of images needed for `foundation_services + selected_services`, and runs `docker pull` for each in a single shell, redirecting all per-layer output to `${DATA_ROOT}/logs/rakkib-pull.log`. Prints only one summary line per image (`pulled <image>` / `failed <image>`). Safe to run any time after Phase 3 because it doesn't write or start anything — pulls are pure caching.
2. **Add an "Image Manifest" block to `registry.yaml`** so `rakkib pull` and Step 5 share the same source of truth (image name + tag per service, including the Immich-bundled images).
3. **Update `steps/00-prereqs.md`** to instruct the agent: after Docker is verified and the user has confirmed selections, *"run `rakkib pull` in a separate terminal and proceed with onboarding while it runs."* The agent can then move on with question phases 4–6 in parallel with the download.
4. **Update `steps/60-services.md`** so per-service `docker compose up -d` calls run with `--quiet-pull` and stdout/stderr redirected to a per-service log file (`${DATA_ROOT}/logs/<svc>-up.log`); the agent only reads the exit code and the existing `## Verify` curl checks. If `rakkib pull` was already run, this becomes a near-instant no-op because images are local.
5. **No background/auto-trigger mode.** Even a polled background job costs tokens (every status check is a tool result). Keep `rakkib pull` strictly user-run in a separate terminal — the agent only references it as an instruction.

This gives the user a visible, terminal-native progress experience for the heavy download (in their own shell, with full Docker progress), while the agent stays out of it.

**Files to modify.**
- `bin/rakkib` — add `cmd_pull`. *(Superseded by v2: `bin/rakkib` was removed; pull logic lives in the Python CLI.)*
- `registry.yaml` — add `image:` per service entry.
- `steps/00-prereqs.md` — recommend running `rakkib pull` in parallel.
- `steps/60-services.md` — switch to `--quiet-pull` + log redirection.

---

## Issue 3 — Resume an interrupted session from `.fss-state.yaml`

**Root cause.** The v1 agent prompt in `bin/rakkib::agent_prompt` (now superseded by the Python CLI) told the agent *"ask me the question files in order, record answers in .fss-state.yaml"* but never said *"if a state file already exists, read it and skip past phases whose required keys are populated."* `AGENT_PROTOCOL.md` calls `.fss-state.yaml` "the single source of truth" but had no Resume section. Result: a new chat session started at question 1 every time.

**Fix.**
1. **Add a "Resume Rules" section to `AGENT_PROTOCOL.md`.** Define an explicit resume algorithm:
   - On startup, read `.fss-state.yaml` if it exists.
   - For each phase in order, check `writes_state` keys (already declared in each `questions/*.md` AgentSchema) — if every required key for that phase is non-null, mark the phase complete and skip it.
   - **Mid-onboarding (some phase incomplete):** silently continue from the first incomplete phase. Do not re-ask earlier phases. Do not prompt — just pick up where the user left off.
   - **Onboarding complete (`confirmed: true`):** ask the user once: *"Onboarding is already complete. Start over? This will overwrite `.fss-state.yaml`. (y/N)"* — default N proceeds to step execution; y truncates the state file and restarts at Phase 1.
   - Idempotency rules in `lib/idempotency.md` already cover re-applying steps safely on the post-confirmation path.
2. **Update `agent_prompt()` in `bin/rakkib`** to embed the resume directive so all supported agents (opencode, claude, codex) get it without depending on `AGENT_PROTOCOL.md` recall on a cold session. *(Superseded by v2: `bin/rakkib` was removed; resume is native in the Python CLI.)*
3. **Optional:** add a `rakkib status` command that prints the resume snapshot (which phase will be next, which keys are populated) so the user can sanity-check before relaunching.

**Files to modify.**
- `AGENT_PROTOCOL.md` — new "Resume Rules" section, near the existing "Phase Order" section.
- `bin/rakkib` — extend `agent_prompt()` and optionally add `cmd_status`. *(Superseded by v2: `bin/rakkib` was removed; resume and `rakkib status` are native in the Python CLI.)*

---

## Verification

1. **Issue 1.** On a fresh Ubuntu VM with `zsh` as login shell: `curl … install.sh | bash` → answer "Y" to auto-launch → land directly in agent session. Open a new terminal → `rakkib --version` resolves without sourcing anything.
2. **Issue 2.** With selections including Immich and Authentik: run `rakkib pull` in terminal A, run `rakkib init` in terminal B. Terminal A shows full docker progress; terminal B's agent context shows no per-layer noise. After `rakkib pull` finishes and the agent reaches Step 5, services come up in seconds because images are cached.
3. **Issue 3.** Complete onboarding through Phase 6 confirmation, exit the agent, relaunch `rakkib init`. Agent reports "resuming — all questions answered, jumping to Step execution" instead of re-asking question 1.

---

## Out of scope

- The v1.1 service expansion in `expansions.md` (separate plan).
- Actual idempotency fixes for already-deployed services (handled by `lib/idempotency.md`).
- Replacing the AGENT_PROTOCOL.md prompt with a structured tool — keep the markdown-driven approach.
