# Step 30 — Caddy

Render and deploy the base Caddy reverse proxy.

## Actions

1. Render `templates/caddy/Caddyfile.header.tmpl`.
2. Render `templates/caddy/routes/root.caddy.tmpl`.
3. Always render `templates/caddy/routes/nocodb.caddy.tmpl`.
4. Render `templates/caddy/routes/n8n.caddy.tmpl` only if `n8n` is selected.
5. Render `templates/caddy/routes/dbhub.caddy.tmpl` only if `dbhub` is selected.
6. Render `templates/caddy/routes/immich.caddy.tmpl` only if `immich` is selected.
7. Render `templates/caddy/routes/transfer.caddy.tmpl` only if `transfer` is selected.
8. Render `templates/caddy/routes/claw.caddy.tmpl` only if `openclaw` is selected.
9. Render `templates/caddy/routes/hermes.caddy.tmpl` only if `hermes` is selected.
10. Render `templates/caddy/Caddyfile.footer.tmpl`.
11. Concatenate the pieces into `{{DATA_ROOT}}/docker/caddy/Caddyfile.next`.
12. Validate the candidate before replacing the active file. Use the Caddy image if the container is not running yet, for example: `docker run --rm -v {{DATA_ROOT}}/docker/caddy/Caddyfile.next:/etc/caddy/Caddyfile:ro caddy:2 caddy validate --config /etc/caddy/Caddyfile`.
13. If `{{DATA_ROOT}}/docker/caddy/Caddyfile` already exists, copy it to `{{DATA_ROOT}}/docker/caddy/Caddyfile.bak` before replacement.
14. Move the validated candidate into `{{DATA_ROOT}}/docker/caddy/Caddyfile`.
15. Render `templates/docker/caddy/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/caddy/docker-compose.yml`.
16. Start or update the container with `docker compose up -d` from `{{DATA_ROOT}}/docker/caddy`.
17. If Caddy is already running, reload it with `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`. If reload fails, restore `Caddyfile.bak`, rerun `docker compose up -d`, and stop for diagnosis.

## Notes

- The root route is intentionally generic for v1. It confirms the server is up even if the user has no landing page yet.
- Host services such as OpenClaw and Hermes must reverse proxy to `{{HOST_GATEWAY}}`, not the public domain.
- Never replace the active Caddyfile with an unvalidated candidate.

## Verify

- `docker ps | grep caddy`
- `curl -s http://localhost/health`
- `docker logs --tail 50 caddy`
