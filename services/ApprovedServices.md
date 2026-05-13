# Approved Services

This file tracks services that exist in `src/rakkib/data/registry.yaml` and their validation status.

Status meanings:
- `Implemented and tested`: committed, pushed, synced to `runtime`, and validated on the test server.
- `Implemented, pending testing`: registry/templates/hooks exist, but the service has not yet completed the current test-server validation flow.

## Implemented And Tested

| Service | Registry ID |
| --- | --- |
| Homarr | `homarr` |
| NocoDB | `nocodb` |
| Homepage | `homepage` |
| Uptime Kuma | `uptime-kuma` |
| Dockge | `dockge` |
| transfer.sh | `transfer` |
| File Browser | `filebrowser` |
| WebDAV | `webdav` |
| IT-Tools | `it-tools` |
| CyberChef | `cyberchef` |
| Whoami | `whoami` |
| Moodist | `moodist` |
| PairDrop | `pairdrop` |
| Draw.io | `drawio` |
| Excalidraw | `excalidraw` |
| Whoogle | `whoogle` |
| PrivateBin | `privatebin` |
| Homer | `homer` |
| Glance | `glance` |
| Dashy | `dashy` |
| Dozzle | `dozzle` |
| Glances | `glances` |
| Grafana | `grafana` |
| OpenBooks | `openbooks` |
| DailyTxT | `dailytxt` |
| Wallos | `wallos` |
| n8n | `n8n` |
| FreshRSS | `freshrss` |
| Vaultwarden | `vaultwarden` |
| Immich | `immich` |
| Jellyfin | `jellyfin` |
| Chatpad AI | `chatpad` |
| Hermes Agent | `hermes-agent` |
| Lobe Chat | `lobe-chat` |
| Beszel | `beszel` |
| Watchtower | `watchtower` |
| Actual Budget | `actual-budget` |
| PostgreSQL | `postgres` |
| Open WebUI | `open-webui` |
| Forgejo | `forgejo` |
| OpenClaw | `openclaw` |
| Claude | `claude` |
| Codex | `codex` |
| Cheshire Cat AI | `cheshire-cat-ai` |
| Flowise | `flowise` |
| Serge | `serge` |
| Anse | `anse` |
| Autoheal | `autoheal` |
| RSSHub | `rsshub` |
| AdGuard Home | `adguard` |
| Stirling-PDF | `stirling-pdf` |
| Mealie | `mealie` |
| Gitea | `gitea` |
| Caddy | `caddy` |
| Cloudflared | `cloudflared` |
Validation notes:
- OpenBooks: `rakkib add openbooks --yes`, `rakkib smoke openbooks`, `rakkib remove openbooks --yes`, and re-add passed on the test server using `https://openbooks.vazhs.com/`.
- DailyTxT: `rakkib add dailytxt --yes`, `rakkib smoke dailytxt`, `rakkib remove dailytxt --yes`, and re-add passed on the test server using `https://dailytxt.vazhs.com/`.
- n8n: installer-first `rakkib add n8n --yes`, internal LAN smoke, `rakkib remove n8n --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13004/`.
- FreshRSS: installer-first `rakkib add freshrss --yes`, internal LAN smoke, `rakkib remove freshrss --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13032/`.
- Vaultwarden: installer-first `rakkib add vaultwarden --yes`, internal LAN smoke, `rakkib remove vaultwarden --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13035/`.
- Immich: installer-first `rakkib add immich --yes`, internal LAN smoke, `rakkib remove immich --yes` cleanup, re-add, and final smoke passed on the rebuilt test server using `http://174.138.183.153:13005/`; service leaves the small test server under heavy memory/swap pressure.
- Jellyfin: after removing the approved Immich test deployment to free resources, installer-first `rakkib add jellyfin --yes`, internal LAN smoke, `rakkib remove jellyfin --yes` cleanup, re-add, and final smoke passed on the rebuilt test server using `http://174.138.183.153:13007/`.
- Chatpad AI: installer-first `rakkib add chatpad --yes`, internal LAN smoke, `rakkib remove chatpad --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13017/`.
- Hermes Agent: installer-first `rakkib add hermes-agent --yes`, internal LAN smoke, `rakkib remove hermes-agent --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13016/` after fixing root UID handling and internal dashboard port mapping.
- Lobe Chat: installer-first `rakkib add lobe-chat --yes`, internal LAN smoke, `rakkib remove lobe-chat --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13018/`.
- Beszel: installer-first `rakkib add beszel --yes`, internal LAN smoke, `rakkib remove beszel --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13031/` after fixing internal `APP_URL` rendering.
- Watchtower: installer-first `rakkib add watchtower --yes`, healthy container/log checks, `rakkib remove watchtower --yes` cleanup, and re-add passed on the test server; logs confirmed label-scoped operation without touching unrelated containers.
- Actual Budget: installer-first `rakkib add actual-budget --yes`, internal LAN smoke, `rakkib remove actual-budget --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13033/`.
- PostgreSQL: installer-first `rakkib add postgres --yes` refresh, `pg_isready`, `select 1`, and a second idempotent `rakkib add postgres --yes` all passed on the test server; `postgres` stayed healthy on `127.0.0.1:5432`.
- Open WebUI: installer-first `rakkib add open-webui --yes`, internal LAN smoke, `rakkib remove open-webui --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13019/` after extending startup tolerance for transient unhealthy states.
- Forgejo: installer-first `rakkib add forgejo --yes`, internal LAN smoke, `rakkib remove forgejo --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13020/` after fixing internal server URL rendering.
- OpenClaw: installer-first `rakkib add openclaw --yes`, host gateway health checks, internal LAN smoke on `http://174.138.183.153:18789/healthz`, `rakkib remove openclaw --yes` cleanup, re-add, and final smoke passed after adding internal access metadata.
- Claude: installer-first `rakkib add claude --yes`, CLI reachability via `/root/.local/bin/claude --version`, `rakkib remove claude --yes` cleanup, re-add, and final cleanup passed after fixing uninstall artifact removal.
- Codex: installer-first `rakkib add codex --yes`, CLI reachability via `bash -lc 'command -v codex && codex --version'`, `rakkib remove codex --yes` cleanup, re-add, and final cleanup passed after fixing uninstall artifact removal.
- Cheshire Cat AI: installer-first `rakkib add cheshire-cat-ai --yes`, internal LAN smoke on `/admin`, `rakkib remove cheshire-cat-ai --yes` cleanup, re-add, and final smoke passed after fixing internal host/origin config and smoke expectation.
- Flowise: installer-first `rakkib add flowise --yes`, internal LAN smoke, `rakkib remove flowise --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13024/`; immediate smoke needed a short retry while the service finished startup.
- Serge: installer-first `rakkib add serge --yes`, internal LAN smoke, `rakkib remove serge --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13025/`.
- Anse: installer-first `rakkib add anse --yes`, internal LAN smoke, `rakkib remove anse --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13026/`.
- Autoheal: installer-first `rakkib add autoheal --yes`, healthy container/log checks, disposable unhealthy-container restart verification, `rakkib remove autoheal --yes` cleanup, re-add, and final cleanup passed; autoheal only restarted the labeled probe container.
- RSSHub: installer-first `rakkib add rsshub --yes`, healthz smoke, `rakkib remove rsshub --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13034/healthz` with `rsshub`, `rsshub-redis`, and `rsshub-browserless` all healthy.
- AdGuard Home: installer-first `rakkib add adguard --yes`, internal LAN smoke, `rakkib remove adguard --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13036/`.
- Stirling-PDF: installer-first `rakkib add stirling-pdf --yes`, internal LAN smoke, `rakkib remove stirling-pdf --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13038/`.
- Mealie: installer-first `rakkib add mealie --yes`, internal LAN smoke, `rakkib remove mealie --yes` cleanup, re-add, and final smoke passed on the test server using `http://174.138.183.153:13039/`.
- Gitea: installer-first `rakkib add gitea --yes`, internal LAN smoke, `rakkib remove gitea --yes` cleanup including Postgres DB/role removal, re-add, and final smoke passed on the test server using `http://174.138.183.153:13040/` after fixing internal server URL rendering.
- Caddy: manually verified by the user as working well on the test server after the remaining service batch validation.
- Cloudflared: manually verified by the user as working well on the test server after the remaining service batch validation.

## Implemented, Pending Testing

No services currently pending testing.
