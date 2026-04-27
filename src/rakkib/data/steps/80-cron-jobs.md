# Step 80 — Cron Jobs

Install local backup scripts, backup scheduling, and lightweight health monitoring jobs.

## Actions

1. Render `templates/backups/backup-local.sh.tmpl` into `{{BACKUP_DIR}}/backup-local.sh`.
2. Render `templates/backups/restore-local.sh.tmpl` into `{{BACKUP_DIR}}/restore-local.sh`.
3. Make both backup scripts executable.
4. Choose a backup schedule with the user if none was provided. Default: daily at 02:30.
5. Install or replace the backup cron entry using the marker `# RAKKIB: backup-local`.
6. Always install the cloudflared health check script into a user-owned directory such as `~/.local/bin` and make it executable.
7. Add cron entries with conservative cadence using marker replacement. Remove existing lines with the matching marker before adding the current line.
9. Retain local archives in daily, weekly, and monthly buckets. Do not configure cloud upload in v1.

## Default Cadence

- backup-local: daily at 02:30 unless the user chose another schedule
- cloudflared health check: every 5 minutes

## Cron Markers

- `# RAKKIB: backup-local`
- `# RAKKIB: cloudflared-healthcheck`
- `# RAKKIB: claw-healthcheck`
- `# RAKKIB: claw-memory-alert`

## Verify

- `test -x {{BACKUP_DIR}}/backup-local.sh`
- `test -x {{BACKUP_DIR}}/restore-local.sh`
- `{{BACKUP_DIR}}/backup-local.sh`
- `ls -1 {{BACKUP_DIR}} | grep rakkib`
- `test -f $(ls -dt {{BACKUP_DIR}}/rakkib_* | head -n 1)/manifest.json`
- `crontab -l`
- `bash ~/.local/bin/cloudflared-healthcheck.sh`
- if selected on Linux: `bash ~/.local/bin/claw-healthcheck.sh`
