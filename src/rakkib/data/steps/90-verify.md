# Step 90 — Verify

Run the final smoke tests for the deployed server.

## Actions

1. Confirm all expected containers are running.
2. Confirm PostgreSQL is accepting connections.
3. Confirm Caddy is serving locally.
4. Confirm the Cloudflare tunnel metrics endpoint is healthy.
5. Run `rakkib doctor` again and resolve any remaining failures.
6. Confirm each selected service responds on its public HTTPS hostname. If `cloudflare.zone_in_cloudflare` is `false`, treat these checks as blocked until the domain is active in the intended Cloudflare account and do not mark the deployment fully complete.
7. On Linux, ensure the repo directory and any files created during the install are owned by `{{ADMIN_USER}}`. Use `sudo -n rakkib privileged fix-repo-owner --state .fss-state.yaml --repo-dir <repo_root>` when needed, plus targeted ownership fixes for user-writable files under `{{DATA_ROOT}}`, so later maintenance can run from the normal account.

## Verify

```bash
# Core
docker ps
docker exec postgres pg_isready -U postgres
curl -s http://localhost/health
rakkib doctor
```

```bash
# Foundation Bundle — run each only if the service is in foundation_services
curl -I https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{AUTHENTIK_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{HOMEPAGE_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{UPTIME_KUMA_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{DOCKGE_SUBDOMAIN}}.{{DOMAIN}}/
```

```bash
# Optional Services — run each only if the service is in selected_services
curl -I https://{{N8N_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{DBHUB_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{IMMICH_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{TRANSFER_SUBDOMAIN}}.{{DOMAIN}}/
```

```bash
# Host addons — run only if vergo_terminal is in host_addons
command -v zsh
command -v eza
command -v zoxide
command -v fzf
test -d ~/.zi/bin
test -f ~/.zshrc
test -f ~/.zshenv
test -f ~/.p10k.zsh
zsh -i -c exit
```

```bash
# VErgo Terminal fonts — run platform-specific check only if vergo_terminal is in host_addons
test -f "$HOME/.local/share/fonts/MesloLGS NF Regular.ttf"      # Linux
test -f "$HOME/Library/Fonts/MesloLGS NF Regular.ttf"           # Mac
test -f ~/.wezterm.lua                                           # Mac
```

```bash
# Authentik-specific (only if authentik is in foundation_services)
docker exec authentik-server ak healthcheck
# Confirm Authentik admin UI is reachable
curl -sf https://{{AUTHENTIK_SUBDOMAIN}}.{{DOMAIN}}/-/health/ready/
# Confirm blueprints were applied — check worker logs for blueprint apply messages
docker logs authentik-worker 2>&1 | grep -i blueprint
```
