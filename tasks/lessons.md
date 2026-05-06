# Lessons

- Do not close beads based only on static validation when the bead requires bare-metal/runtime verification; leave them open and report the validation as partial progress.
- Never hardcode workstation-specific temp paths into scripts or CI automation; use `TMPDIR`, `/tmp`, or another runtime-discovered temp directory so the workflow stays portable.
- Treat CI runtime deprecation warnings as real maintenance work; update pinned GitHub Actions promptly instead of leaving workflows on deprecated Node runtimes.
