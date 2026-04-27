# Idempotency Contract

Running the installer again against the same machine must be safe. A re-apply may update rendered configuration and restart managed services, but it must not duplicate resources, overwrite secrets, or leave a half-applied state.

## Resource Rules

| Resource | Rule |
|---|---|
| `.env` files | If the file exists, never overwrite it. Read existing values and fill missing keys only. |
| `docker-compose.yml` | Re-render fully. `docker compose up -d` is the only container apply mechanism. |
| Caddyfile | Render to a candidate file, validate it, then replace the active file. If validation fails, keep or restore the previous file and stop. |
| Containers | Use `docker compose up -d`. Never use `docker run` for managed long-running services. |
| Networks | Create only after `docker network inspect` confirms the network is absent. |
| PostgreSQL roles and databases | Use existence checks before creating roles/databases. Do not rely on one-time init scripts for re-apply changes. |
| Cloudflare tunnel | Detect an existing tunnel by name before creating a new one. Reuse the existing UUID and credentials path when present. |
| Cron entries | Use marker comments such as `# RAKKIB: backup-local` and replace by marker. Never append duplicate lines. |
| systemd/launchd units | Re-render the unit/plist, reload the manager, then restart or bootstrap the service. |
| User dotfiles | Compare candidate content first. If replacement is needed, back up the existing file to `~/.backup-vergo/<timestamp>/`, then replace. Do not create duplicate backups when content is unchanged. |
| Linux root context | Verify `id -u` is `0` before root-required work; stop instead of attempting privilege escalation inside the agent. |

## Required Re-Apply Checks

Before changing target-machine state on a re-run:

- inventory existing managed containers with `docker ps --format '{{.Names}}'`
- record hashes for existing managed `.env` files before merge
- record the existing Caddyfile hash before replacement
- detect the Cloudflare tunnel by recorded UUID or tunnel name before creating anything
- list current Rakkib cron markers before installing schedules
- if `vergo_terminal` is selected, hash existing managed dotfiles before replacement

After re-apply:

- managed `.env` hashes must be unchanged unless a previously missing key was added
- the Caddyfile must either validate and apply or be restored to the previous version
- cron marker count must stay one per managed job
- `docker compose ps` must show the same managed services without duplicate containers
- selected VErgo Terminal dotfiles must exist and unchanged files must not produce duplicate backups
