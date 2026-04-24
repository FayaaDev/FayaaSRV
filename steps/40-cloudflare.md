# Step 40 — Cloudflare

Render and deploy the Cloudflare tunnel after the user confirms the setup.

## Actions

0. If `cloudflare.zone_in_cloudflare` is `false`, stop before any tunnel login or DNS routing work. Help the user finish Cloudflare zone setup first using Cloudflare's docs, then resume this step once the zone is active in the intended account.
1. Confirm the host `cloudflared` CLI is installed and runnable with `cloudflared --version` before doing any tunnel work. If it was installed into `~/.local/bin`, invoke that path directly when the shell `PATH` has not been refreshed yet.
2. If `cloudflare.tunnel_strategy` is `new`, first run `cloudflared tunnel list` and look for the recorded `<tunnel_name>`. If it already exists, record its UUID and reuse it instead of creating another tunnel.
3. If no tunnel with that name exists, guide the user through:
   `cloudflared tunnel login` and `cloudflared tunnel create <tunnel_name>`.
4. If `cloudflare.tunnel_strategy` is `existing`, confirm the tunnel exists and gather its UUID if not already recorded.
5. Create `{{DATA_ROOT}}/data/cloudflared` if needed.
6. Ensure the credentials JSON ends up at the standardized host path `{{TUNNEL_CREDS_HOST_PATH}}`. If the file currently lives elsewhere, copy or move it into place before rendering.
7. Ensure the credentials JSON is readable only by the admin user.
8. Update `.fss-state.yaml` with the final `tunnel_uuid`, `tunnel_creds_host_path`, and `tunnel_creds_container_path`.
9. Render `templates/cloudflared/config.yml.tmpl` into `{{DATA_ROOT}}/data/cloudflared/config.yml`.
10. Render `templates/docker/cloudflared/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/cloudflared/docker-compose.yml`.
11. Create or update DNS routes in Cloudflare for `{{DOMAIN}}`, `*.{{DOMAIN}}`, and `{{SSH_SUBDOMAIN}}.{{DOMAIN}}`.
12. Start the container with `docker compose up -d` from `{{DATA_ROOT}}/docker/cloudflared`.

## Manual Command Pattern

If the zone is not yet in Cloudflare, first help the user complete one of these:

- primary setup (full): `https://developers.cloudflare.com/dns/zone-setups/full-setup/`
- CNAME setup (partial): `https://developers.cloudflare.com/dns/zone-setups/partial-setup/`

Do not run the tunnel DNS route commands until the zone is active in the Cloudflare account that owns the tunnel.

Use the actual tunnel name from state:

```bash
cloudflared tunnel login
cloudflared tunnel create <tunnel_name>
cloudflared tunnel route dns <tunnel_name> {{DOMAIN}}
cloudflared tunnel route dns <tunnel_name> '*.{{DOMAIN}}'
cloudflared tunnel route dns <tunnel_name> {{SSH_SUBDOMAIN}}.{{DOMAIN}}
```

## Verify

- `cloudflared --version`
- `test -f {{DATA_ROOT}}/data/cloudflared/config.yml`
- `test -f {{TUNNEL_CREDS_HOST_PATH}}`
- `docker ps | grep cloudflared`
- `curl -fsS http://127.0.0.1:{{CLOUDFLARED_METRICS_PORT}}/metrics`
