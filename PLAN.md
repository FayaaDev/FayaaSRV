# Plan: `FayaaSRV` — Agent-Installable Server Kit

## Context
FayaaLink is a dense, opinionated mini-PC server (Caddy + Cloudflare Tunnel + Postgres + ~15 Dockerized apps + host-level OpenCode/OpenClaw + cron health checks + rclone→GDrive backups). The setup is encoded across `/srv/docker/*`, `/srv/apps/static/*`, `/srv/MDs/*`, `/srv/backups/*`, systemd units, and a crontab — it works but is bespoke to `fayaalink` / `fayaa92.sa` / `192.168.0.235`.

The goal is a **GitHub repo a user's coding agent (Claude Code, Copilot CLI, Codex, etc.) can clone to reproduce the same stack on their own Mac or Linux machine**. The repo is not a shell installer — the agent is the installer. The repo's job is to (a) interview the user, (b) hand the agent structured templates + step files to render and deploy, and (c) leave behind a `CLAUDE.md`/`AGENTS.md` that keeps the machine operable the same way FayaaLink is.

## Repo
**`FayaaSRV`** — already exists at https://github.com/FayaaDev/FayaaSRV, current working directory `/srv/FayaaSRV/`. **Private** while iterating; flip public after a dry-run on a clean VM.

## v1 scope (locked)
- **Always install**: Caddy, Cloudflared, Postgres, NocoDB.
- **Prompt (y/n) per service**: n8n, OpenClaw, DBHub.
- **Backup**: local-only timestamped tarballs (no rclone/GDrive/S3 in v1). Cloud targets deferred to v2.
- Out of scope for v1: ChangeDetection, SehaRadar, LightRAG, Superset, Excalidraw, example apps (malaria-tracker, pha, vazhs, fayafolio), gdrive, OpenCode host service.

## Top-level shape

```
FayaaSRV/
├── README.md                     # Agent entry point + user-facing intro
├── AGENTS.md                     # Copy of README.md (multi-agent support)
├── AGENT_PROTOCOL.md             # How the agent walks the repo (state machine)
├── registry.yaml                 # Service catalog — deps, ports, subdomains
├── docs/
│   ├── REFERENCE_SERVER.md       # (renamed from README.md — original FayaaLink doc)
│   └── WORKFLOW_RULES.md         # (renamed from README2.md)
├── questions/
│   ├── 01-platform.md            # Mac vs Linux; Docker Desktop vs native; arch
│   ├── 02-identity.md            # server name, domain, admin user, LAN IP, TZ, email
│   ├── 03-services.md            # y/n for n8n, OpenClaw, DBHub
│   ├── 04-cloudflare.md          # CF account, tunnel creation walkthrough, DNS
│   ├── 05-secrets.md             # collect/generate per-service secrets
│   └── 06-confirm.md             # dry-run summary before any writes
├── steps/
│   ├── 00-prereqs.md             # Docker, rsync, curl, cloudflared
│   ├── 10-layout.md              # create {DATA_ROOT}/{docker,apps/static,data,backups,MDs}
│   ├── 20-network.md             # caddy_net bridge, firewall notes
│   ├── 30-caddy.md               # deploy Caddy + render Caddyfile from selection
│   ├── 40-cloudflare.md          # cloudflared tunnel create + ingress config
│   ├── 50-postgres.md            # pgvector/pg16 + per-service DB+user bootstrap
│   ├── 60-services.md            # loop selected services, render, docker compose up
│   ├── 70-host-agents.md         # OpenClaw systemd (Linux) / launchd (Mac) — only if selected
│   ├── 80-backups.md             # local tarball backup script + cron
│   ├── 85-health-crons.md        # health-check cron jobs (parameterized)
│   └── 90-verify.md              # smoke tests: curl each subdomain, docker ps, pg_isready
├── templates/
│   ├── docker/<svc>/             # docker-compose.yml.tmpl, .env.example, README.md
│   ├── caddy/
│   │   ├── Caddyfile.header.tmpl
│   │   └── routes/<svc>.caddy.tmpl
│   ├── cloudflared/config.yml.tmpl
│   ├── systemd/claw-gateway.service.tmpl
│   ├── launchd/                  # Mac equivalents
│   ├── backups/
│   │   ├── backup-local.sh.tmpl
│   │   └── healthchecks/*.sh.tmpl
│   └── agent-memory/
│       ├── CLAUDE.md.tmpl        # global — points at generated server README
│       └── SERVER_README.md.tmpl # lives at {DATA_ROOT}/README.md on target box
└── lib/
    ├── placeholders.md           # canonical placeholder list
    └── validation.md             # post-step checks the agent must run
```

## Interaction model

`README.md` opens with an explicit agent prompt block: *"If you are an AI coding agent, read `AGENT_PROTOCOL.md` and follow it. Do not execute anything until Phase 6 (confirm)."*

`AGENT_PROTOCOL.md` defines six phases mirroring the `questions/` files, with one rule per phase: **ask → record answer into an in-repo scratch file `.fss-state.yaml` (gitignored) → proceed**. No writes outside the repo until Phase 6. Every `steps/*.md` file ends with a `## Verify` block the agent must pass before advancing.

Cloudflare step is **guided manual**: the agent pastes exact `cloudflared tunnel login`, `tunnel create <name>`, DNS route commands and waits for the user to paste back the tunnel UUID and credentials path before rendering `config.yml`.

## Templating

Flat placeholder set in `lib/placeholders.md`:
`{{SERVER_NAME}}`, `{{DOMAIN}}`, `{{ADMIN_USER}}`, `{{ADMIN_EMAIL}}`, `{{LAN_IP}}`, `{{TZ}}`, `{{DATA_ROOT}}` (default `/srv` on Linux, `$HOME/srv` on Mac), `{{DOCKER_NET}}`, `{{TUNNEL_UUID}}`, `{{TUNNEL_CREDS_PATH}}`, `{{BACKUP_DIR}}`, plus per-service `{{<SVC>_SUBDOMAIN}}`, `{{<SVC>_DB_PASS}}`.

Rendering is done by the agent (simple find/replace) — no build tool.

## Service registry (`registry.yaml`)

```yaml
# Required — always installed, no prompt
- id: caddy       { required: true }
- id: cloudflared { required: true }
- id: postgres    { required: true }
- id: nocodb      { required: true, depends_on: [postgres] }

# Optional — prompt y/n each
- id: n8n      { optional: true, depends_on: [postgres] }
- id: dbhub    { optional: true, depends_on: [postgres] }
- id: openclaw { optional: true, host_service: true }   # systemd user unit, not docker
```

Each entry carries: `image`, `default_port`, `default_subdomain`, `env_keys` (names only), `depends_on`, `required`/`optional`, `notes`. Step 60 iterates in dependency order.

## Files to mine from the live server

Copy (with secrets stripped) into `templates/`:

- `/srv/docker/{caddy,cloudflared,postgres,nocodb,n8n,dbhub}/docker-compose.yml` → `templates/docker/<svc>/docker-compose.yml.tmpl`
- Matching `.env` files → generate `.env.example` with keys only, no values
- `/srv/docker/caddy/Caddyfile` → split relevant per-host blocks into `templates/caddy/routes/<svc>.caddy.tmpl`
- `/srv/data/cloudflared/config.yml` → `templates/cloudflared/config.yml.tmpl`
- `~/.config/systemd/user/openclaw-gateway.service` → `templates/systemd/claw-gateway.service.tmpl`
- `/srv/backups/backup-to-gdrive.sh` → adapt into `templates/backups/backup-local.sh.tmpl` (strip rclone upload, keep tarball + retention logic)
- `/home/fayaalink/.local/bin/*healthcheck*.sh` → `templates/backups/healthchecks/*.sh.tmpl`
- `/srv/MDs/network_guide.md`, `cloudflareSETUP.md`, `SECRETS_MANAGEMENT.md` → rewritten into `steps/*.md` (not copied verbatim — domain-agnostic, imperative).

## Generated outputs on the target machine

1. **`{{DATA_ROOT}}/README.md`** — equivalent to current `/srv/FayaaSRV/README.md`: chosen services, ports, subdomains, paths.
2. **Global `~/.claude/CLAUDE.md`** (plus `~/.config/github-copilot/AGENTS.md`, `~/.codex/AGENTS.md` if those dirs exist) — short pointer: *"This machine follows FayaaSRV standards. Before any infra action, read @{{DATA_ROOT}}/README.md. Rules: backups first, one issue at a time, never serve from source dir, never rotate `N8N_ENCRYPTION_KEY`."*

If a `CLAUDE.md` already exists, append under a marked section rather than overwriting.

## Mac vs Linux differences

- **Paths**: `/srv/...` (Linux) vs `$HOME/srv/...` (Mac — `/srv` requires root and breaks Docker Desktop bind mounts).
- **Host agents**: systemd unit (Linux) vs `launchd` plist (Mac).
- **Docker host IP**: `172.18.0.1` (Linux bridge gateway) vs `host.docker.internal` (Mac).
- **Firewall**: `ufw` hints on Linux, none on Mac.
- **cloudflared**: Docker container on both; `tunnel login` requires a browser either way.

Step files branch on `{{PLATFORM}}` set in Phase 1.

## Verification

Shippable when:
- An agent given only the repo URL + a human to answer questions can bring up Caddy + Cloudflare Tunnel + Postgres + NocoDB on a fresh Ubuntu 24.04 box and reach `https://nocodb.<domain>` externally.
- The generated `CLAUDE.md` successfully steers a fresh agent session into reading the generated server README before acting.
- `steps/90-verify.md` passes all curl/docker/pg_isready checks.

Test loop: throwaway Multipass or Lima VM → clone repo → run Claude Code → answer questions → confirm all `Verify` blocks green.

## Critical files to read before first commit

- `/srv/docker/caddy/Caddyfile`
- `/srv/docker/{caddy,cloudflared,postgres,nocodb,n8n,dbhub}/docker-compose.yml`
- `/srv/data/cloudflared/config.yml`
- `/srv/backups/backup-to-gdrive.sh`
- `~/.config/systemd/user/openclaw-gateway.service`
- `/home/fayaalink/.local/bin/*.sh`
- `crontab -l`

## Decisions (locked with user)

- Repo: `FayaaSRV` (github.com/FayaaDev/FayaaSRV), private until v1 is dry-run-verified.
- Services v1: baseline Caddy/Cloudflared/Postgres/NocoDB + optional n8n/OpenClaw/DBHub.
- Backup v1: local-only tarballs; cloud targets deferred.
- Existing `README.md` and `README2.md` will be preserved as reference docs (renamed `docs/REFERENCE_SERVER.md` and `docs/WORKFLOW_RULES.md`) — the new `README.md` becomes the agent entry point.
