# Question File 03 — Services

**Phase 3 of 6. No writes outside the repo occur during this phase.**

## AgentSchema

```yaml
schema_version: 1
phase: 3
reads_state:
  - domain
writes_state:
  - foundation_services
  - selected_services
  - host_addons
  - subdomains
service_catalog:
  foundation_bundle:
    - slug: nocodb
      label: NocoDB
      numeric_alias: 1
      subdomain_key: nocodb
      default_subdomain: nocodb
    - slug: homepage
      label: Homepage
      numeric_alias: 2
      subdomain_key: homepage
      default_subdomain: home
    - slug: uptime-kuma
      label: Uptime Kuma
      numeric_alias: 3
      subdomain_key: uptime-kuma
      default_subdomain: status
    - slug: dockge
      label: Dockge
      numeric_alias: 4
      subdomain_key: dockge
      default_subdomain: dockge
  optional_services:
    - slug: n8n
      label: n8n
      numeric_alias: 6
      subdomain_key: n8n
      default_subdomain: n8n
    - slug: immich
      label: Immich
      numeric_alias: 7
      subdomain_key: immich
      default_subdomain: immich
    - slug: transfer
      label: transfer.sh
      numeric_alias: 8
      subdomain_key: transfer
      default_subdomain: transfer
    - slug: jellyfin
      label: Jellyfin
      numeric_alias: 9
      subdomain_key: jellyfin
      default_subdomain: jellyfin
    - slug: openclaw
      label: OpenClaw
      numeric_alias: 10
      subdomain_key: openclaw
      default_subdomain: claw
    - slug: claude
      label: Claude
      numeric_alias: 47
      subdomain_key: null
      default_subdomain: null
    - slug: codex
      label: Codex
      numeric_alias: 48
      subdomain_key: null
      default_subdomain: null
    - slug: anse
      label: Anse
      numeric_alias: 37
      subdomain_key: anse
      default_subdomain: anse
    - slug: filebrowser
      label: File Browser
      numeric_alias: 12
      subdomain_key: filebrowser
      default_subdomain: files
    - slug: webdav
      label: WebDAV
      numeric_alias: 50
      subdomain_key: webdav
      default_subdomain: webdav
    - slug: it-tools
      label: IT-Tools
      numeric_alias: 13
      subdomain_key: it-tools
      default_subdomain: tools
    - slug: cyberchef
      label: CyberChef
      numeric_alias: 14
      subdomain_key: cyberchef
      default_subdomain: cyberchef
    - slug: drawio
      label: Draw.io
      numeric_alias: 15
      subdomain_key: drawio
      default_subdomain: drawio
    - slug: excalidraw
      label: Excalidraw
      numeric_alias: 16
      subdomain_key: excalidraw
      default_subdomain: excalidraw
    - slug: homer
      label: Homer
      numeric_alias: 17
      subdomain_key: homer
      default_subdomain: homer
    - slug: dozzle
      label: Dozzle
      numeric_alias: 18
      subdomain_key: dozzle
      default_subdomain: dozzle
    - slug: homarr
      label: Homarr
      numeric_alias: 53
      subdomain_key: homarr
      default_subdomain: homarr
    - slug: glance
      label: Glance
      numeric_alias: 19
      subdomain_key: glance
      default_subdomain: glance
    - slug: dashy
      label: Dashy
      numeric_alias: 20
      subdomain_key: dashy
      default_subdomain: dashy
    - slug: beszel
      label: Beszel
      numeric_alias: 21
      subdomain_key: beszel
      default_subdomain: beszel
    - slug: freshrss
      label: FreshRSS
      numeric_alias: 22
      subdomain_key: freshrss
      default_subdomain: freshrss
    - slug: actual-budget
      label: Actual Budget
      numeric_alias: 23
      subdomain_key: actual-budget
      default_subdomain: actual
    - slug: rsshub
      label: RSSHub
      numeric_alias: 24
      subdomain_key: rsshub
      default_subdomain: rsshub
    - slug: vaultwarden
      label: Vaultwarden
      numeric_alias: 25
      subdomain_key: vaultwarden
      default_subdomain: vault
    - slug: adguard
      label: AdGuard Home
      numeric_alias: 49
      subdomain_key: adguard
      default_subdomain: adguard
    - slug: whoogle
      label: Whoogle
      numeric_alias: 26
      subdomain_key: whoogle
      default_subdomain: whoogle
    - slug: forgejo
      label: Forgejo
      numeric_alias: 27
      subdomain_key: forgejo
      default_subdomain: forgejo
    - slug: privatebin
      label: PrivateBin
      numeric_alias: 28
      subdomain_key: privatebin
      default_subdomain: privatebin
    - slug: stirling-pdf
      label: Stirling-PDF
      numeric_alias: 29
      subdomain_key: stirling-pdf
      default_subdomain: pdf
    - slug: mealie
      label: Mealie
      numeric_alias: 30
      subdomain_key: mealie
      default_subdomain: mealie
    - slug: gitea
      label: Gitea
      numeric_alias: 31
      subdomain_key: gitea
      default_subdomain: gitea
    - slug: whoami
      label: Whoami
      numeric_alias: 32
      subdomain_key: whoami
      default_subdomain: whoami
    - slug: pairdrop
      label: PairDrop
      numeric_alias: 33
      subdomain_key: pairdrop
      default_subdomain: pairdrop
    - slug: moodist
      label: Moodist
      numeric_alias: 34
      subdomain_key: moodist
      default_subdomain: moodist
    - slug: hermes-agent
      label: Hermes Agent
      numeric_alias: 36
      subdomain_key: hermes-agent
      default_subdomain: hermes
    - slug: cheshire-cat-ai
      label: Cheshire Cat AI
      numeric_alias: 38
      subdomain_key: cheshire-cat-ai
      default_subdomain: cat
    - slug: flowise
      label: Flowise
      numeric_alias: 39
      subdomain_key: flowise
      default_subdomain: flowise
    - slug: serge
      label: Serge
      numeric_alias: 40
      subdomain_key: serge
      default_subdomain: serge
    - slug: chatpad
      label: Chatpad AI
      numeric_alias: 44
      subdomain_key: chatpad
      default_subdomain: chatpad
    - slug: lobe-chat
      label: Lobe Chat
      numeric_alias: 45
      subdomain_key: lobe-chat
      default_subdomain: lobe
    - slug: open-webui
      label: Open WebUI
      numeric_alias: 46
      subdomain_key: open-webui
      default_subdomain: webui
    - slug: ollama-cpu
      label: Ollama (CPU)
      numeric_alias: 41
      subdomain_key: ollama-cpu
      default_subdomain: ollama-cpu
    - slug: ollama-amd
      label: Ollama (AMD)
      numeric_alias: 42
      subdomain_key: ollama-amd
      default_subdomain: ollama-amd
    - slug: ollama-nvidia
      label: Ollama (NVIDIA)
      numeric_alias: 43
      subdomain_key: ollama-nvidia
      default_subdomain: ollama-nvidia
    - slug: autoheal
      label: Autoheal
      numeric_alias: 51
      subdomain_key: null
      default_subdomain: null
    - slug: watchtower
      label: Watchtower
      numeric_alias: 52
      subdomain_key: null
      default_subdomain: null
  host_addons:
    - slug: vergo_terminal
      label: VErgo Terminal
      numeric_alias: 11
fields:
  - id: foundation_services
    type: multi_select
    selection_mode: deselect_from_default
    prompt: "Foundation Bundle: type service slugs to deselect (e.g. `homepage dockge`); numeric aliases like `2 4` are also accepted, or press Enter to accept all:"
    canonical_values: [nocodb, homepage, uptime-kuma, dockge]
    numeric_aliases:
      "1": nocodb
      "2": homepage
      "3": uptime-kuma
      "4": dockge
    records:
      - foundation_services
  - id: optional_services
    type: multi_select
    selection_mode: add_to_empty
    prompt: "Service categories: type service slugs to add (e.g. `n8n immich filebrowser`); numeric aliases like `6 8 12` are also accepted, or press Enter to skip all:"
    canonical_values: [n8n, immich, transfer, jellyfin, openclaw, claude, codex, anse, filebrowser, webdav, it-tools, cyberchef, drawio, excalidraw, homer, dozzle, homarr, glance, dashy, beszel, freshrss, actual-budget, rsshub, vaultwarden, adguard, whoogle, forgejo, privatebin, stirling-pdf, mealie, gitea, whoami, pairdrop, moodist, hermes-agent, cheshire-cat-ai, flowise, serge, chatpad, lobe-chat, open-webui, ollama-cpu, ollama-amd, ollama-nvidia, autoheal, watchtower]
    numeric_aliases:
      "6": n8n
      "7": immich
      "8": transfer
      "9": jellyfin
      "10": openclaw
      "47": claude
      "48": codex
      "37": anse
      "12": filebrowser
      "50": webdav
      "13": it-tools
      "14": cyberchef
      "15": drawio
      "16": excalidraw
      "17": homer
      "18": dozzle
      "53": homarr
      "19": glance
      "20": dashy
      "21": beszel
      "22": freshrss
      "23": actual-budget
      "24": rsshub
      "25": vaultwarden
      "49": adguard
      "26": whoogle
      "27": forgejo
      "28": privatebin
      "29": stirling-pdf
      "30": mealie
      "31": gitea
      "32": whoami
      "33": pairdrop
      "34": moodist
      "36": hermes-agent
      "38": cheshire-cat-ai
      "39": flowise
      "40": serge
      "41": ollama-cpu
      "42": ollama-amd
      "43": ollama-nvidia
      "44": chatpad
      "45": lobe-chat
      "46": open-webui
      "51": autoheal
      "52": watchtower
    records:
      - selected_services
  - id: host_addons
    type: multi_select
    selection_mode: add_to_empty
    prompt: "Host Addons: type addon slugs to add (e.g. `vergo_terminal`); numeric aliases like `11` are also accepted, or press Enter to skip all:"
    canonical_values: [vergo_terminal]
    numeric_aliases:
      "11": vergo_terminal
    records:
      - host_addons
  - id: service_subdomain
    type: text
    repeat_for: selected_service_slugs
    prompt_template: "Subdomain for <service>? [default: <default>]"
    records:
      - subdomains
```

---

## Instructions for the Agent

Present the full service menu below as a TUI-style checklist. Collect selections in three rounds:
1. **Foundation Bundle** — all pre-selected; user types service slugs to deselect.
2. **Service categories** — none pre-selected; user types service slugs to select.
3. **Host Addons** — none pre-selected; user types addon slugs to select.

Numeric checklist positions may still be accepted as convenience aliases, but canonical recorded inputs are always slugs.

When rendering the checklist, the selectable label must always be the service or addon name shown below (`NocoDB`, `Homepage`, `VErgo Terminal`, etc.). Use `[✓]` and `[ ]` only as visual state markers. Do not render `selected`, `unselected`, `true`, or `false` as an option label.

Subdomains are automatically set to the defaults from the service catalog for Cloudflare routing. In internal exposure mode, do not prompt for subdomains because Caddy routes are not created. Record all results into `.fss-state.yaml`. Do not advance to `questions/04-cloudflare.md` until recording is complete.

---

## Present This Menu

Display the following to the user (substituting the actual `domain` value from `.fss-state.yaml`):

```
=== Service Selection ===

Always installed — no choice needed:
  [✓] Caddy          — reverse proxy; only when Cloudflare exposure mode is selected
  [✓] Cloudflared    — only when Cloudflare exposure mode is selected
  [✓] PostgreSQL     — shared database backend

Foundation Bundle (recommended):
  [✓] 1  NocoDB        — no-code database UI    →  nocodb.<domain>
  [✓] 2  Homepage      — service dashboard      →  home.<domain>
  [✓] 3  Uptime Kuma   — uptime monitoring      →  status.<domain>
  [✓] 4  Dockge        — Compose manager        →  dockge.<domain>

Automation:
  [ ] 6  n8n           — workflow automation    →  n8n.<domain>

Media:
  [ ] 7  Immich        — photo library          →  immich.<domain>
  [ ] 9  Jellyfin      — media server           →  jellyfin.<domain>

File Sharing:
  [ ] 8  transfer.sh   — public file sharing    →  transfer.<domain>
  [ ] 12 File Browser  — browser file manager   →  files.<domain>

AI:
  [ ] 10 OpenClaw      — AI assistant gateway   →  claw.<domain>
  [ ] 47 Claude        — Claude Code (CLI)
  [ ] 48 Codex         — OpenAI Codex (CLI)
  [ ] 37 Anse          — AI chat UI             →  anse.<domain>
  [ ] 38 Cheshire Cat  — agent microservice     →  cat.<domain>
  [ ] 39 Flowise       — visual agent builder   →  flowise.<domain>
  [ ] 40 Serge         — local LLM chat UI      →  serge.<domain>
  [ ] 41 Ollama (CPU)   — local LLM API (11434)
  [ ] 42 Ollama (AMD)   — local LLM API (11434)
  [ ] 43 Ollama (NVIDIA) — local LLM API (11434)
  [ ] 44 Chatpad AI     — ChatGPT UI             →  chatpad.<domain>
  [ ] 45 Lobe Chat      — LLM chat UI            →  lobe.<domain>
  [ ] 46 Open WebUI     — Ollama / OpenAI UI     →  webui.<domain>

Developer Tools:
  [ ] 13 IT-Tools      — browser utilities      →  tools.<domain>
  [ ] 14 CyberChef     — data transformation    →  cyberchef.<domain>
  [ ] 27 Forgejo       — self-hosted git forge  →  forgejo.<domain>
  [ ] 24 RSSHub        — RSS generator          →  rsshub.<domain>

Diagram And Design:
  [ ] 15 Draw.io       — diagramming app        →  drawio.<domain>
  [ ] 16 Excalidraw    — sketch whiteboard      →  excalidraw.<domain>

Dashboards:
  [ ] 17 Homer         — static server homepage →  homer.<domain>
  [ ] 53 Homarr        — modern server dashboard →  homarr.<domain>
  [ ] 19 Glance        — glanceable dashboard    →  glance.<domain>
  [ ] 20 Dashy         — customisable dashboard  →  dashy.<domain>

Monitoring:
  [ ] 18 Dozzle        — container log viewer   →  dozzle.<domain>
  [ ] 21 Beszel        — server monitoring hub  →  beszel.<domain>

News:
  [ ] 22 FreshRSS      — RSS feed reader        →  freshrss.<domain>

Finance:
  [ ] 23 Actual Budget — personal finance       →  actual.<domain>

Security:
  [ ] 25 Vaultwarden   — password manager       →  vault.<domain>
  [ ] 49 AdGuard Home   — network ad blocking    →  adguard.<domain>

Search:
  [ ] 26 Whoogle       — privacy search         →  whoogle.<domain>

Lifestyle:
  [ ] 30 Mealie        — recipe manager         →  mealie.<domain>

Host Addons:
  [ ] 11 VErgo Terminal — zsh, prompt, completions, CLI UX
```

---

## Round 1 — Foundation Bundle

Ask:

> "Foundation Bundle: type service slugs to deselect (e.g. `homepage dockge`); numeric aliases like `2 4` are also accepted, or press Enter to accept all:"

- Parse the response as a space-separated list of canonical service slugs.
- Accept the numeric aliases shown in the checklist as a convenience input and normalize them to the same canonical service slugs before recording state.
- Remove the corresponding services from the selected foundation set.
- If the user presses Enter with no input, keep all four selected.
- Re-render the updated checklist showing `[✓]` / `[ ]` states and ask the user to confirm.

---

## Round 2 — Service Categories

Ask:

> "Service categories: type service slugs to add (e.g. `n8n immich filebrowser`); numeric aliases like `6 8 12` are also accepted, or press Enter to skip all:"

- Parse the response as a space-separated list of canonical service slugs.
- Accept the numeric aliases shown in the checklist as a convenience input and normalize them to the same canonical service slugs before recording state.
- Add the corresponding services to the selection.
- If the user presses Enter with no input, none are selected.
---

## Round 3 — Host Addons

Ask:

> "Host Addons: type addon slugs to add (e.g. `vergo_terminal`); numeric aliases like `11` are also accepted, or press Enter to skip all:"

- Parse the response as a space-separated list of canonical addon slugs.
- Accept the numeric aliases shown in the checklist as a convenience input and normalize them to the same canonical addon slugs before recording state.
- `11` selects `vergo_terminal`.
- If the user presses Enter with no input, no host addons are selected.
- Warn before recording `vergo_terminal`: "VErgo Terminal modifies the admin user's shell dotfiles (`~/.zshrc`, `~/.zshenv`, `~/.p10k.zsh`, and on Mac `~/.wezterm.lua`). Existing files are backed up before replacement."

---

## Record in .fss-state.yaml

```yaml
foundation_services:
  - nocodb
  - homepage
  - uptime-kuma
  - dockge
selected_services:
  - n8n
host_addons:
  - vergo_terminal
subdomains:
  nocodb: nocodb
  homepage: home
  uptime-kuma: status
  dockge: dockge
  n8n: n8n
  immich: immich
  transfer: transfer
  jellyfin: jellyfin
  openclaw: claw
  anse: anse
  cheshire-cat-ai: cat
  flowise: flowise
  serge: serge
  ollama-cpu: ollama-cpu
  ollama-amd: ollama-amd
  ollama-nvidia: ollama-nvidia
  chatpad: chatpad
  lobe-chat: lobe
  open-webui: webui
  filebrowser: files
  it-tools: tools
  cyberchef: cyberchef
  forgejo: forgejo
  drawio: drawio
  excalidraw: excalidraw
  homer: homer
  homarr: homarr
  dozzle: dozzle
  glance: glance
  dashy: dashy
  beszel: beszel
  freshrss: freshrss
  actual-budget: actual
  rsshub: rsshub
  vaultwarden: vault
  adguard: adguard
  whoogle: whoogle
  mealie: mealie
```

Record only subdomains for services that are actually selected (foundation or optional).
Do not introduce alias subdomain keys in new state files. Use the service slug as the only `subdomains.*` key.

During rendering, flatten these values into service placeholders:

- `subdomains.nocodb` -> `{{NOCODB_SUBDOMAIN}}`
- `subdomains.homepage` -> `{{HOMEPAGE_SUBDOMAIN}}`
- `subdomains.uptime-kuma` -> `{{UPTIME_KUMA_SUBDOMAIN}}`
- `subdomains.dockge` -> `{{DOCKGE_SUBDOMAIN}}`
- `subdomains.n8n` -> `{{N8N_SUBDOMAIN}}`
- `subdomains.immich` -> `{{IMMICH_SUBDOMAIN}}`
- `subdomains.transfer` -> `{{TRANSFER_SUBDOMAIN}}`
- `subdomains.jellyfin` -> `{{JELLYFIN_SUBDOMAIN}}`
- `subdomains.openclaw` -> `{{OPENCLAW_SUBDOMAIN}}`
- `subdomains.anse` -> `{{ANSE_SUBDOMAIN}}`
- `subdomains.cheshire-cat-ai` -> `{{CHESHIRE_CAT_AI_SUBDOMAIN}}`
- `subdomains.flowise` -> `{{FLOWISE_SUBDOMAIN}}`
- `subdomains.serge` -> `{{SERGE_SUBDOMAIN}}`
- `subdomains.ollama-cpu` -> `{{OLLAMA_CPU_SUBDOMAIN}}`
- `subdomains.ollama-amd` -> `{{OLLAMA_AMD_SUBDOMAIN}}`
- `subdomains.ollama-nvidia` -> `{{OLLAMA_NVIDIA_SUBDOMAIN}}`
- `subdomains.chatpad` -> `{{CHATPAD_SUBDOMAIN}}`
- `subdomains.lobe-chat` -> `{{LOBE_CHAT_SUBDOMAIN}}`
- `subdomains.open-webui` -> `{{OPEN_WEBUI_SUBDOMAIN}}`
- `subdomains.filebrowser` -> `{{FILEBROWSER_SUBDOMAIN}}`
- `subdomains.webdav` -> `{{WEBDAV_SUBDOMAIN}}`
- `subdomains.it-tools` -> `{{IT_TOOLS_SUBDOMAIN}}`
- `subdomains.cyberchef` -> `{{CYBERCHEF_SUBDOMAIN}}`
- `subdomains.forgejo` -> `{{FORGEJO_SUBDOMAIN}}`
- `subdomains.drawio` -> `{{DRAWIO_SUBDOMAIN}}`
- `subdomains.excalidraw` -> `{{EXCALIDRAW_SUBDOMAIN}}`
- `subdomains.homer` -> `{{HOMER_SUBDOMAIN}}`
- `subdomains.homarr` -> `{{HOMARR_SUBDOMAIN}}`
- `subdomains.dozzle` -> `{{DOZZLE_SUBDOMAIN}}`
- `subdomains.glance` -> `{{GLANCE_SUBDOMAIN}}`
- `subdomains.dashy` -> `{{DASHY_SUBDOMAIN}}`
- `subdomains.beszel` -> `{{BESZEL_SUBDOMAIN}}`
- `subdomains.freshrss` -> `{{FRESHRSS_SUBDOMAIN}}`
- `subdomains.actual-budget` -> `{{ACTUAL_BUDGET_SUBDOMAIN}}`
- `subdomains.rsshub` -> `{{RSSHUB_SUBDOMAIN}}`
- `subdomains.vaultwarden` -> `{{VAULTWARDEN_SUBDOMAIN}}`
- `subdomains.adguard` -> `{{ADGUARD_SUBDOMAIN}}`
- `subdomains.whoogle` -> `{{WHOOGLE_SUBDOMAIN}}`
- `subdomains.mealie` -> `{{MEALIE_SUBDOMAIN}}`
