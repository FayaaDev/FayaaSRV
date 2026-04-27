# Step 30 — Caddy

Render and deploy the base Caddy reverse proxy.

## Actions

1. Create the external bridge network `{{DOCKER_NET}}` if it does not already exist.
2. Do not use per-stack auto-generated networks for the main service-to-proxy path.
3. Render `templates/caddy/Caddyfile.header.tmpl`.
4. Render `templates/caddy/routes/root.caddy.tmpl`.
5. Render `templates/caddy/Caddyfile.footer.tmpl`.
6. Concatenate the pieces into `{{DATA_ROOT}}/docker/caddy/Caddyfile.next`.
7. Validate the candidate before replacing the active file. Use the Caddy image if the container is not running yet, for example: `docker run --rm -v {{DATA_ROOT}}/docker/caddy/Caddyfile.next:/etc/caddy/Caddyfile:ro caddy:2 caddy validate --config /etc/caddy/Caddyfile`.
8. If `{{DATA_ROOT}}/docker/caddy/Caddyfile` already exists, copy it to `{{DATA_ROOT}}/docker/caddy/Caddyfile.bak` before replacement.
9. Move the validated candidate into `{{DATA_ROOT}}/docker/caddy/Caddyfile`.
10. Render `templates/docker/caddy/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/caddy/docker-compose.yml`.
11. Start or update the container with `docker compose up -d` from `{{DATA_ROOT}}/docker/caddy`.
12. If Caddy is already running, reload it with `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`. If reload fails, restore `Caddyfile.bak`, rerun `docker compose up -d`, and stop for diagnosis.

## Notes

- The root route is intentionally generic for v1. It confirms the server is up even if the user has no landing page yet.
- Service-specific routes are added later by Step 60 for Docker services and Step 70 for host services, after each selected service is actually available.
- Host services such as OpenClaw and Hermes must reverse proxy to `{{HOST_GATEWAY}}`, not the public domain.
- Never replace the active Caddyfile with an unvalidated candidate.

## Verify

- `docker ps | grep caddy`
- `docker network inspect {{DOCKER_NET}}`
- `curl -s http://localhost/health`
- `docker logs --tail 50 caddy`
