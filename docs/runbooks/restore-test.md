# Restore Test Runbook

Optional restore verification. Skip this runbook on first install unless the user explicitly asks for a restore dry run or a real restore round-trip test.

## Actions

1. Confirm that `{{BACKUP_DIR}}/backup-local.sh` and `{{BACKUP_DIR}}/restore-local.sh` exist and are executable.
2. Run `{{BACKUP_DIR}}/backup-local.sh --dry-run` to verify the backup plan without writing archives.
3. Run `{{BACKUP_DIR}}/restore-local.sh --latest --dry-run --yes` to verify that the latest backup can be selected and planned.
4. If the user requests a real restore test, create an explicit marker row or marker file in a selected service first.
5. Run `{{BACKUP_DIR}}/backup-local.sh`.
6. Remove only the marker created for this test.
7. Run `{{BACKUP_DIR}}/restore-local.sh --latest --yes`.
8. Verify the marker was restored and all Step 90 smoke checks still pass.

## Safety Notes

- Do not run a real restore test on production data unless the user explicitly accepts the overwrite risk.
- Do not pass `--restore-secrets` unless the test requires restoring `.env` files or `{{DATA_ROOT}}/secrets`.
- A dry run is enough for first-install validation.

## Verify

- `{{BACKUP_DIR}}/backup-local.sh --dry-run`
- `{{BACKUP_DIR}}/restore-local.sh --latest --dry-run --yes`
- if real test requested: marker data exists after restore
