# Lessons

- Do not close beads based only on static validation when the bead requires bare-metal/runtime verification; leave them open and report the validation as partial progress.
- Never hardcode workstation-specific temp paths into scripts or CI automation; use `TMPDIR`, `/tmp`, or another runtime-discovered temp directory so the workflow stays portable.
- Treat CI runtime deprecation warnings as real maintenance work; update pinned GitHub Actions promptly instead of leaving workflows on deprecated Node runtimes.
- When a workflow contract changes, update every agent-facing instruction file that repeats that contract (`AGENTS.md`, `CLAUDE.md`, and service-specific variants), not just the first matching doc.
- When a user specifies selection UX, match the requested default checked state exactly; do not assume pre-checked boxes are more convenient.
- When asked to validate pending services, continue through the full fix, commit, push, runtime-sync, and bare-metal validation loop unless the user explicitly asks for discovery only.
- For Questionary disabled choices, put the status in `Choice.disabled` only; do not duplicate it in `Choice.title` because the UI appends the disabled reason.
