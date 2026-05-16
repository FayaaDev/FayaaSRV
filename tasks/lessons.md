# Lessons

- Do not close beads based only on static validation when the bead requires bare-metal/runtime verification; leave them open and report the validation as partial progress.
- Never hardcode workstation-specific temp paths into scripts or CI automation; use `TMPDIR`, `/tmp`, or another runtime-discovered temp directory so the workflow stays portable.
- Treat CI runtime deprecation warnings as real maintenance work; update pinned GitHub Actions promptly instead of leaving workflows on deprecated Node runtimes.
- When a workflow contract changes, update every agent-facing instruction file that repeats that contract (`AGENTS.md`, `CLAUDE.md`, and service-specific variants), not just the first matching doc.
- When a user specifies selection UX, match the requested default checked state exactly; do not assume pre-checked boxes are more convenient.
- When asked to validate pending services, continue through the full fix, commit, push, runtime-sync, and bare-metal validation loop unless the user explicitly asks for discovery only.
- MacSupport validation target: `ssh itest@192.168.0.100` (MacBook-Air, macOS 14.8.7, x86_64). Use this real Mac after each macOS installer fix before reporting the Mac experience as working; do not store the password in tracked files.
- For MacSupport sudo validation over SSH, allocate a TTY and feed the sudo prompt through that TTY; priming sudo with `sudo -S` before a curl-piped installer can cache credentials for the wrong context.
