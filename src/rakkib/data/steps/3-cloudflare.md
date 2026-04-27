# Step 3 — Cloudflare

Render and deploy the Cloudflare tunnel after the user confirms the setup.

## Actions

0. If `cloudflare.zone_in_cloudflare` is `false`, stop before any tunnel login or DNS routing work. Help the user finish Cloudflare zone setup first using Cloudflare's docs, then resume this step once the zone is active in the intended account.
1. Confirm the host `cloudflared` CLI is installed and runnable with `cloudflared --version` before doing any tunnel work. If it was installed into `~/.local/bin`, invoke that path directly when the shell `PATH` has not been refreshed yet.
2. Create `{{DATA_ROOT}}/data/cloudflared` if needed before any login or credential normalization work.
3. Treat `{{DATA_ROOT}}/data/cloudflared/cert.pem` as the standardized browser-login auth artifact path. Do not store that path or the cert contents in `.fss-state.yaml`, but do preserve the file on re-runs and include it in backups.
4. Use the recorded Cloudflare connection method:
   - `browser_login`: authenticate before any tunnel discovery for new tunnels. Run `cloudflared tunnel login` first. Tell the user clearly that Step 3 is paused until Cloudflare approval finishes.
   - `api_token`: ask for a temporary Cloudflare API token only now, export it only for the commands that require it, verify it with Cloudflare's token verification endpoint before tunnel or DNS changes, and unset it after Cloudflare work is complete. Do not write the token into `.fss-state.yaml` or rendered files.
   - `existing_tunnel`: prefer the existing credentials JSON and recorded UUID. Use browser login only if tunnel discovery, credentials repair, or DNS route repair requires it.
5. For `browser_login`, verify the login handoff before continuing:
   - If `cloudflare.headless` is `true`, tell the user to open the printed Cloudflare URL on another device, sign in to the same account that owns `{{DOMAIN}}`, approve the domain, then return to the terminal.
   - If `cloudflare.headless` is `false`, tell the user to complete the approval in the local browser window.
   - Confirm `{{DATA_ROOT}}/data/cloudflared/cert.pem` exists, or if `cloudflared` only wrote the cert to its default user location, copy it into the standardized path before continuing.
   - Confirm `cloudflared tunnel list` succeeds after approval. If it fails, stop and resolve auth before any create or DNS work.
6. Recovery rules for the login handoff:
   - If the printed login URL expires or the user closes it, rerun `cloudflared tunnel login` and retry the approval.
   - If the user approved the wrong Cloudflare account, rerun `cloudflared tunnel login` and complete approval in the account that owns `{{DOMAIN}}`.
   - If `{{DOMAIN}}` is in Cloudflare but not in the approved account, stop. Do not continue until the correct account owns the zone for this install.
   - If browser login succeeded previously but `cert.pem` is missing locally, restore it from backup or rerun `cloudflared tunnel login` before any tunnel management commands.
7. For `cloudflare.tunnel_strategy: new`, authenticate first when needed, then run `cloudflared tunnel list` and look for the recorded `<tunnel_name>`. If it already exists, record its UUID and reuse it instead of creating another tunnel.
8. If no tunnel with that name exists, run `cloudflared tunnel create <tunnel_name>`.
9. For `cloudflare.tunnel_strategy: existing`, confirm the tunnel exists and gather its UUID if not already recorded. If the tunnel exists but the local credentials JSON is missing, repair the login state first and re-copy the credentials JSON into the standardized location before rendering.
10. If a tunnel name collision exists but it belongs to the intended account and environment, reuse it. If the name collision belongs to a different environment, stop and ask the user to choose a different tunnel name rather than overwriting or replacing the existing tunnel.
11. Ensure the credentials JSON ends up at the standardized host path `{{TUNNEL_CREDS_HOST_PATH}}`. If the file currently lives elsewhere, copy or move it into place before rendering.
12. Ensure the credentials JSON is readable only by the admin user.
13. Update `.fss-state.yaml` with the final `tunnel_uuid`, `tunnel_creds_host_path`, and `tunnel_creds_container_path`.
14. Render `templates/cloudflared/config.yml.tmpl` into `{{DATA_ROOT}}/data/cloudflared/config.yml`.
15. Render `templates/docker/cloudflared/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/cloudflared/docker-compose.yml`.
16. Verify the tunnel can be inspected with `cloudflared tunnel info <tunnel_uuid or tunnel_name>` before DNS changes.
17. Create or update DNS routes in Cloudflare for `{{DOMAIN}}`, `*.{{DOMAIN}}`, and `{{SSH_SUBDOMAIN}}.{{DOMAIN}}`.
18. If DNS route creation fails because of missing zone access, wrong account, or expired auth, stop and recover the auth state first instead of continuing with stale or partial routing.
19. If a temporary API token was used, unset it before continuing.
20. Start the container with `docker compose up -d` from `{{DATA_ROOT}}/docker/cloudflared`.

## Manual Command Pattern

If the zone is not yet in Cloudflare, first help the user complete one of these:

- primary setup (full): `https://developers.cloudflare.com/dns/zone-setups/full-setup/`
- CNAME setup (partial): `https://developers.cloudflare.com/dns/zone-setups/partial-setup/`

Do not run the tunnel DNS route commands until the zone is active in the Cloudflare account that owns the tunnel.

Normal browser-login pattern for a new or reused tunnel, using the actual tunnel name from state:

```bash
mkdir -p "{{DATA_ROOT}}/data/cloudflared"
cloudflared tunnel login
test -f "{{DATA_ROOT}}/data/cloudflared/cert.pem" || test -f "$HOME/.cloudflared/cert.pem"
cloudflared tunnel list
cloudflared tunnel create <tunnel_name>
cloudflared tunnel info <tunnel_name>
cloudflared tunnel route dns <tunnel_name> {{DOMAIN}}
cloudflared tunnel route dns <tunnel_name> '*.{{DOMAIN}}'
cloudflared tunnel route dns <tunnel_name> {{SSH_SUBDOMAIN}}.{{DOMAIN}}
```

On a headless server, `cloudflared tunnel login` prints a Cloudflare URL instead of opening a browser. Tell the user to open that URL on a laptop or phone, sign in to Cloudflare, approve the domain in the correct account, then return to the terminal.

Only use the advanced API token method if `cloudflare.auth_method` is `api_token`:

```bash
read -r -s -p "Cloudflare API token: " CLOUDFLARE_API_TOKEN
export CLOUDFLARE_API_TOKEN
curl -fsS --max-time 10 -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" https://api.cloudflare.com/client/v4/user/tokens/verify
# Run only the Cloudflare commands that require the token.
unset CLOUDFLARE_API_TOKEN
```

Do not store the raw API token in `.fss-state.yaml`, `.env`, rendered compose files, shell history, or documentation outputs.

## Verify

- `cloudflared --version`
- `test -d {{DATA_ROOT}}/data/cloudflared`
- If `cloudflare.auth_method` is `browser_login`: `test -f {{DATA_ROOT}}/data/cloudflared/cert.pem`
- `cloudflared tunnel list`
- `cloudflared tunnel info {{TUNNEL_UUID}}` or `cloudflared tunnel info <tunnel_name>`
- `test -f {{DATA_ROOT}}/data/cloudflared/config.yml`
- `test -f {{TUNNEL_CREDS_HOST_PATH}}`
- `docker ps | grep cloudflared`
- `curl -fsS http://127.0.0.1:{{CLOUDFLARED_METRICS_PORT}}/metrics`
