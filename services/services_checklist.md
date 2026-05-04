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
- [ ] Heimdall (B)
- [ ] Homarr (B)
- [ ] Dash. / Dashdot (E)

### Developer Tools
- [x] Planning Poker (A)
- [ ] Code Server (B)
- [ ] Atuin Server (C)

### Books And Reading
- [ ] openbooks (B)
- [ ] Booksonic (D)
- [ ] Calibre-Web (D)
- [ ] Kavita (D)
- [ ] Komga (D)
- [ ] PodFetch (D)
- [ ] Readarr (D)
- [ ] Suwayomi (D)

### Monitoring
- [ ] Grafana (B)
- [ ] Glances (E)
- [ ] Netdata (E)

### Personal And Lifestyle
- [x] Moodist (A)
- [ ] DailyTxT (B)
- [ ] Flightlog (B)
- [ ] Grocy (B)
- [ ] Hammond (B)
- [ ] HomeBox (B)
- [ ] Koillection (B)
- [ ] LinkStack (B)
- [ ] LubeLogger (B)
- [ ] Movary (B)

### File Sync And Sharing
- [x] PairDrop (A)
- [ ] Pingvin Share (B)
- [ ] Send (B)
- [ ] Syncthing (B)
- [ ] Zipline (B)

### Search And RSS
- [ ] RSS (A)
- [ ] SearXNG (B)

### Media Management
- [ ] Bazarr (D)
- [ ] Kapowarr (D)
- [ ] Lidarr (D)
- [ ] Maintainerr (D)
- [ ] Mylar3 (D)
- [ ] Radarr (D)
- [ ] Sonarr (D)
- [ ] Tautulli (D)
- [ ] Wizarr (D)

### Media Server
- [ ] Audiobookshelf (D)
- [ ] mStream Music (D)
- [ ] Navidrome (D)
- [ ] Owncast (D)

### Document And Knowledge
- [ ] ChangeDetection (B)
- [ ] DokuWiki (B)
- [ ] flatnotes (B)
- [ ] Memos (B)
- [ ] Notemark (B)
- [ ] Silverbullet (B)
- [ ] Trilium (B)
- [ ] Kiwix Server (D)

### Finance
- [ ] Wallos (B)

### Git And DevOps
- [ ] OneDev (B)

### Remote Access
- [ ] Hello World (A)
- [x] Whoami (A)
- [ ] Sshwifty (B)

### Secrets And Auth
- [ ] 2FAuth (B)

### Utility
- [ ] LibreTranslate (B)

### Calendar And Contacts
- [ ] Baikal (B)

### Diagram And Design
