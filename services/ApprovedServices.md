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
| OpenBooks | `openbooks` |

Validation notes:
- OpenBooks: `rakkib add openbooks --yes`, `rakkib smoke openbooks`, `rakkib remove openbooks --yes`, and re-add passed on the test server using `https://openbooks.vazhs.com/`.

## Implemented, Pending Testing

| Service | Registry ID | Bucket |
| --- | --- | --- |
| Caddy | `caddy` | always |
| Cloudflared | `cloudflared` | always |
| PostgreSQL | `postgres` | always |
| n8n | `n8n` | selected_services |
| Immich | `immich` | selected_services |
| Jellyfin | `jellyfin` | selected_services |
| Hermes Agent | `hermes-agent` | selected_services |
| Chatpad AI | `chatpad` | selected_services |
| Lobe Chat | `lobe-chat` | selected_services |
| Open WebUI | `open-webui` | selected_services |
| Forgejo | `forgejo` | selected_services |
| OpenClaw | `openclaw` | selected_services |
| Claude | `claude` | selected_services |
| Codex | `codex` | selected_services |
| Cheshire Cat AI | `cheshire-cat-ai` | selected_services |
| Flowise | `flowise` | selected_services |
| Serge | `serge` | selected_services |
| Anse | `anse` | selected_services |
| Beszel | `beszel` | selected_services |
| Autoheal | `autoheal` | selected_services |
| Watchtower | `watchtower` | selected_services |
| FreshRSS | `freshrss` | selected_services |
| Actual Budget | `actual-budget` | selected_services |
| RSSHub | `rsshub` | selected_services |
| Vaultwarden | `vaultwarden` | selected_services |
| AdGuard Home | `adguard` | selected_services |
| Stirling-PDF | `stirling-pdf` | selected_services |
| Mealie | `mealie` | selected_services |
| Gitea | `gitea` | selected_services |
| Ollama (CPU) | `ollama-cpu` | selected_services |
| Ollama (AMD) | `ollama-amd` | selected_services |
| Ollama (NVIDIA) | `ollama-nvidia` | selected_services |
