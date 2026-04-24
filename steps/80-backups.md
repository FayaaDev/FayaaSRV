# Step 80 — Backups

Install the local-only backup script and backup schedule.

## Actions

1. Render `templates/backups/backup-local.sh.tmpl` into `{{BACKUP_DIR}}/backup-local.sh`.
2. Render `templates/backups/restore-local.sh.tmpl` into `{{BACKUP_DIR}}/restore-local.sh`.
3. Make both scripts executable.
4. Choose a schedule with the user if none was provided. Default: daily at 02:30.
5. Install a cron entry or platform-equivalent job to run it using marker replacement. The cron line must include `# FAYAASRV: backup-local`; remove any existing line with that marker before adding the new one.
6. Retain local archives in daily, weekly, and monthly buckets. Do not configure cloud upload in v1.

## Verify

- `test -x {{BACKUP_DIR}}/backup-local.sh`
- `test -x {{BACKUP_DIR}}/restore-local.sh`
- `{{BACKUP_DIR}}/backup-local.sh`
- `ls -1 {{BACKUP_DIR}} | grep fayaasrv`
- `test -f $(ls -dt {{BACKUP_DIR}}/fayaasrv_* | head -n 1)/manifest.json`
