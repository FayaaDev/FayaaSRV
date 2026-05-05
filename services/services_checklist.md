# Rakkib Service Implementation Checklist

Legend:
- `[x]` Implemented in Rakkib (present in `src/rakkib/data/registry.yaml` / service menu)
- `[ ]` Not implemented yet

Difficulty order (easiest to hardest):
- `A` static/simple web
- `B` app + volume
- `C` app + shared Postgres
- `E` admin/host-aware (docker socket, host mounts/metrics)
- `D` media/data heavy


## Batch 1 (20 services)

All Batch 1 services are implemented.

### File Sync And Sharing
- [x] File Browser (B)

### Developer Tools
- [x] IT-Tools (A)
- [x] CyberChef (A)

### Diagram And Design
- [x] Draw.io (A)
- [x] Excalidraw (A)

### Dashboards
- [x] Homer (A)
- [x] Glance (B)
- [x] Dashy (B)

### Finance
- [x] Actual Budget (B)

### Secrets And Auth
- [x] Vaultwarden (B)
- [ ] Adguard 

### Search And RSS
- [x] RSSHub (A)
- [x] FreshRSS (B)
- [x] Whoogle Search (B)

### Personal And Lifestyle
- [x] PrivateBin (B)
- [x] Stirling-PDF (B)
- [x] Mealie (C)

### Git And DevOps
- [x] Gitea (C)
- [x] Forgejo (C)

### Monitoring
- [x] Dozzle (E)
- [x] Beszel (E)

## BatchX (Low-Friction Candidates)

This list preserves `batchx.md` categorization and marks what is already implemented.
Duplicates already listed in **Batch 1** are removed here.

### Dashboards
- [ ] Homarr (B)

### Developer Tools
- [x] Planning Poker (A)
- [x] Hermes Agent (E)

### Books And Reading
- [ ] openbooks (B)

### Monitoring
- [ ] Grafana (B)
- [ ] Glances (E)
- [x] Watchtower (E)
- [x] Autoheal (E)

### Personal And Lifestyle
- [x] Moodist (A)
- [ ] DailyTxT (B)

### File Sync And Sharing
- [x] PairDrop (A)
- [ ] Pingvin Share (B)
- [ ] WebDAV (B)


### Document And Knowledge
- [ ] Memos (B)
- [ ] Notemark (B)


### Finance
- [ ] Wallos (B)

### AI
- [ ] Claude (A)
- [x] Codex (A)
- [x] Anse (B)
- [ ] Chatpad AI (B)
- [ ] Cheshire Cat AI (B)
- [ ] Flowise AI (B)
- [ ] Lobe Chat (B)
- [ ] Ollama - AMD (E)
- [ ] Ollama - CPU (E)
- [ ] Ollama - Nvidia (E)
- [ ] Open WebUI (B)
- [x] OpenClaw (B)
- [ ] Serge (B)

### Home Automation
- [ ] ESP Home (B)
- [ ] Gladys Assistant (B)
- [ ] Matter Server (B)

### Media
- [ ] Plex (D)

### Networking
- [ ] Gluten VPN (E)
