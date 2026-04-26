# Beads Workflow

This repository uses `bd` for issue tracking. Do not add parallel markdown task lists for project work.

## Start Work

```bash
bd ready --json
bd show <id> --json
bd update <id> --status in_progress --json
```

If no suitable issue exists, create one before changing code:

```bash
bd create "Issue title" --description "Why this issue exists and what needs to be done" -t task -p 2 --json
```

## Finish Work

```bash
bd close <id> --reason "Completed" --json
bd dolt pull
git status --short
git add <files>
git commit -m "message"
```

If the Dolt remote is not configured, record that in the handoff instead of blocking code verification.
