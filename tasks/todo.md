# Rakkib-tl3 Draw.io Verification

- [x] Inspect Draw.io registry, templates, and catalog entries.
- [x] Validate Draw.io on the bare-metal test server with installer-first `rakkib add drawio --yes`.
- [x] Check Draw.io container status/logs, rendered host routing, public URL, and `rakkib smoke drawio`.
- [x] Fix any Draw.io-specific contract gaps found during validation with minimal repo changes.
- [x] Verify removal/deselect cleanup behavior via the same removal functions used by `rakkib add` deselection, then re-add and smoke again.
- [x] Record final verification results and bead close eligibility.

## Review

- Registry/catalog inspection found Draw.io declared correctly with `jgraph/drawio:latest`, port `8080`, default subdomain `drawio`, Caddy route, and `draw.io` smoke marker.
- Installer-first validation ran on the test server with `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash`, then `/root/.local/bin/rakkib add drawio --yes` because the non-interactive SSH shell did not load `~/.local/bin` into `PATH`.
- Initial add deployed Draw.io and passed container, route, upstream, public URL, and `rakkib smoke drawio` checks.
- Cleanup was verified through `rakkib.steps.services.remove_single_service`, the same removal function used by `rakkib add` deselection; the Draw.io container, compose file, and Caddy route were removed.
- Re-add exposed a Draw.io readiness gap: `rakkib add drawio --yes` returned while Tomcat was still starting, and an immediate `rakkib smoke drawio` saw a public `502`.
- Fixed the gap by adding a Draw.io container healthcheck and making Docker service deployment wait for `health_check` before reporting success.
- Patched runtime files were copied to `/opt/rakkib` on the test server and validation was repeated.
- Final cleanup, re-add, container health, public URL, and `rakkib smoke drawio` all passed; Draw.io is eligible for bead closure.

# Rakkib Wave 2-3 Services

- [ ] Implement Beszel service (registry, templates, catalog, tests)
- [ ] Implement FreshRSS service (registry, templates, catalog, tests)
- [ ] Implement Actual Budget service (registry, templates, catalog, tests)
- [ ] Implement RSSHub service (registry, templates, catalog, tests)
- [ ] Implement Vaultwarden service (registry, templates, catalog, tests)
- [ ] Implement Whoogle service (registry, templates, catalog, tests)
- [ ] Validate each service on bare-metal test server with installer-first flow and `rakkib add <id> --yes`, then `rakkib smoke <id>`
- [ ] Mirror `install.sh`, `pyproject.toml`, and `src/rakkib/**` to `runtime` branch after all merges

## Review

- Pending.

# Rakkib AI Services (Chatpad AI, Lobe Chat, Open WebUI)

- [x] Add registry entries for `chatpad`, `lobe-chat`, `open-webui` with caddy routes + smoke checks
- [x] Add docker templates (+ .env.example) for each service
- [x] Update Phase 3 interview catalog: `src/rakkib/data/questions/03-services.md`
- [x] Update any registry/template consistency fixtures or tests if required
- [x] Sanity check registry references resolve locally (no deploy)

## Review

- Pending.
