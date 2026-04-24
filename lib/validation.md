# Post-Step Validation Checklist

Use these checks after each deployment step. Do not continue if a required check fails.

## Step 00

- Linux helper path: `/usr/local/libexec/rakkib-root-helper probe` as root or `sudo -n /usr/local/libexec/rakkib-root-helper probe` from a helper-enabled user
- `docker --version`
- `docker compose version`
- `docker info`
- `curl --version`
- `cloudflared --version` or `~/.local/bin/cloudflared --version`

## Step 05

- `./scripts/rakkib-doctor`
- `./scripts/rakkib-doctor --json`
- no `"status":"fail"` checks in the JSON report before continuing

## Step 10

- `ls -ld {{DATA_ROOT}}/docker {{DATA_ROOT}}/data {{DATA_ROOT}}/backups {{DATA_ROOT}}/MDs`
- `test -w {{DATA_ROOT}}/docker`

## Step 20

- `docker network inspect {{DOCKER_NET}}`

## Step 30

- candidate Caddyfile validates before replacement
- `docker ps | grep caddy`
- `curl -s http://localhost/health`

## Step 40

- `cloudflared --version` or `~/.local/bin/cloudflared --version`
- `test -f {{DATA_ROOT}}/data/cloudflared/config.yml`
- `test -f {{TUNNEL_CREDS_HOST_PATH}}`
- `docker ps | grep cloudflared`
- `curl -fsS http://127.0.0.1:{{CLOUDFLARED_METRICS_PORT}}/metrics`

## Step 50

- `docker ps | grep postgres`
- `docker exec postgres pg_isready -U postgres`
- `docker exec postgres psql -U postgres -c '\l'`
- confirm `nocodb_db` exists
- if selected, confirm `n8n_db` exists

## Step 60

- `docker ps | grep nocodb`
- if selected: `docker ps | grep n8n`
- if selected: `docker ps | grep dbhub`
- local proxy check through Caddy for each selected route

## Step 70

- `node --version`
- `npm --version`
- `test -x "$HOME/.local/bin/openclaw"`
- `"$HOME/.local/bin/openclaw" --version`
- Linux: `systemctl --user status openclaw-gateway.service --no-pager`
- Mac: `launchctl print gui/$(id -u)/openclaw-gateway`
- `curl -I http://localhost:{{CLAW_GATEWAY_PORT}}/`

## Step 80

- `test -x {{BACKUP_DIR}}/backup-local.sh`
- `test -x {{BACKUP_DIR}}/restore-local.sh`
- run the script once and confirm a new backup directory exists
- latest backup directory contains `manifest.json`

## Step 82

- `{{BACKUP_DIR}}/backup-local.sh --dry-run`
- `{{BACKUP_DIR}}/restore-local.sh --latest --dry-run --yes`
- if running a real restore test, confirm the selected marker row or file exists after restore

## Step 85

- `crontab -l`
- run the installed health check scripts manually once

## Step 90

- `docker ps`
- `docker exec postgres pg_isready -U postgres`
- `curl -s http://localhost/health`
- `./scripts/rakkib-doctor`
- `curl -I https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{N8N_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{DBHUB_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{OPENCLAW_SUBDOMAIN}}.{{DOMAIN}}/`
- `test -f {{DATA_ROOT}}/README.md`
- `test -f ~/.claude/CLAUDE.md`

## Second-Run Check

After a successful install, run a re-apply from `steps/05-preflight.md` through `steps/90-verify.md` on the same machine.

- record `sha256sum` for managed `.env` files before and after; values must stay unchanged unless a missing key was filled
- record `sha256sum {{DATA_ROOT}}/docker/caddy/Caddyfile` before and after; content should stay stable for the same state
- confirm `crontab -l` contains one line per `# RAKKIB:` marker
- confirm `docker compose ps` does not show duplicate managed containers
