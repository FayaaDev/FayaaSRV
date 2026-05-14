# Rakkib Web UI Plan

## Goal

Add a browser-based setup and management UI without changing Rakkib's core contract: a fresh Ubuntu server remains installable through the one-line `install.sh` flow, and the target machine must not need Node.js, npm, pnpm, or a separate JavaScript server.

Primary flow:

```bash
curl -fsSL https://install.rakkib.app | bash
rakkib web --lan
```

`rakkib web` prints local and LAN URLs with a setup token so another device can continue setup in a browser.

## Core Decisions

- Frontend: React + Vite single-page app, built ahead of time.
- Backend: small Python ASGI app, preferably FastAPI + Uvicorn.
- Runtime packaging: ship built static assets inside the Python package under `src/rakkib/data/web/`.
- State source of truth: `.fss-state.yaml`, accessed through existing `rakkib.state.State` helpers.
- Streaming: Server-Sent Events for setup/log progress; WebSockets are unnecessary for v1.
- Security: bind to `127.0.0.1` by default, require a high-entropy token by default, expose LAN only through `--lan`.

## Architecture

```text
Browser
  -> rakkib web process
      -> serves built React SPA
      -> exposes JSON API and SSE events
      -> calls existing Rakkib Python modules
          - state
          - question/schema engine
          - registry.yaml
          - doctor checks
          - setup steps
          - service add/remove/restart
```

The web UI must be a thin adapter over existing Rakkib behavior. Do not duplicate installer, setup, state, service-selection, or doctor logic.

## Repository Layout

```text
web/
  package.json
  vite.config.ts
  src/
  dist/

src/rakkib/web/
  __init__.py
  app.py
  auth.py
  api.py
  events.py
  models.py
  runner.py
  static.py

src/rakkib/data/web/
  index.html
  assets/
```

Build `web/dist/` on a developer or CI machine, then copy it into `src/rakkib/data/web/` before packaging. The release package includes built assets only, never `node_modules`.

## CLI Command

Add:

```bash
rakkib web
rakkib web --lan
rakkib web --host 127.0.0.1 --port 8080
rakkib web --host 0.0.0.0 --port 8080
rakkib web --token <token>
rakkib web --no-token
rakkib web --no-open
```

Default behavior:

- Bind to `127.0.0.1`.
- Require token auth.
- Print a local URL.
- Do not auto-open a browser on headless Linux.
- Do not expose on LAN unless `--lan` or `--host 0.0.0.0` is explicit.

`--lan` binds to `0.0.0.0`, detects the primary LAN IP, prints a warning, and prints a tokenized LAN URL.

## API Surface

Initial endpoints:

```text
GET  /api/health
GET  /api/session
GET  /api/state
PATCH /api/state
GET  /api/state/resume
GET  /api/questions
GET  /api/questions/phases
GET  /api/questions/phases/{phase}
POST /api/questions/phases/{phase}/answers
GET  /api/registry
GET  /api/services
POST /api/services/selection/preview
POST /api/services/selection/apply
GET  /api/doctor
POST /api/doctor/fix/{check}
POST /api/pull/start
POST /api/pull/cancel
GET  /api/pull/status
GET  /api/pull/events
POST /api/services/{service_id}/restart
POST /api/services/restart-all
GET  /api/logs
GET  /api/logs/{name}
GET  /api/logs/events
```

Use a process-level lock for v1 so only one mutating job runs at a time: pull, service add/remove, restart all, or doctor auto-fix.

## Setup Flow

The UI maps to the existing six phases:

```text
1. Platform
2. Identity
3. Services
4. Cloudflare
5. Secrets
6. Confirm
```

Flow:

```text
Load state
Compute resume_phase()
Open first incomplete phase
Save each phase after valid answers
Mark confirmed only after final confirmation
Run pull only when confirmed
```

Expose schemas generated from `src/rakkib/data/questions/*.md`. The frontend renders field types from schema and must not hardcode forms or run host-detection commands. Derived values are resolved by the backend.

Supported field types:

```text
text
confirm
single_select
multi_select
secret_group
summary
derived
```

## Service Selection

Service management is registry-driven through `src/rakkib/data/registry.yaml` and must match `rakkib add` semantics.

UI requirements:

- Group services by registry category.
- Show always-installed services as locked.
- Preselect foundation services.
- Allow optional service selection.
- Preview additions, removals, dependencies, and destructive actions.
- Require explicit confirmation before removing installed services.

Unchecked installed services are fully removed, including containers, rendered config, service data directories, generated artifacts, and declared Postgres databases/roles.

## Pull Runner

`rakkib pull` is long-running and may need privileged operations, so it must not run inside a request handler.

Use a background runner:

```text
POST /api/pull/start
  - validates confirmed state
  - starts one setup job if none is running
  - returns job id

GET /api/pull/status
  - returns idle/running/succeeded/failed/cancelled
  - returns current step and last error

GET /api/pull/events
  - streams step output and status changes
```

## Privileges

Keep the current Rakkib model: run as the installed user and use sudo only when needed.

Rules:

- Do not run `rakkib web` as root by default.
- Do not store sudo passwords.
- Prefer existing non-interactive sudo checks.
- If sudo is required but unavailable, show the exact terminal command to run, such as `rakkib auth sudo`.
- Keep sudo password entry terminal-only for v1.

## Authentication And Privacy

Security rules:

- Generate a token at process start unless provided.
- Store the token only in process memory for v1.
- Accept token through query string once, then store it in an HTTP-only cookie.
- Require session cookie or bearer token for API requests.
- Set cache-control headers to avoid sensitive state caching.
- `--no-token` must be explicit.

API responses must redact secrets, passwords, tokens, Cloudflare tunnel tokens, database passwords, and service secret keys. Secret fields are write-only: empty means keep existing value, a new value replaces it, and reads return `configured: true` instead of plaintext.

## Frontend UX

The UI should feel like a guided installer, not a generic admin dashboard.

Core screens:

```text
Start / Resume
Host Check
Platform
Identity
Services
Cloudflare
Secrets
Confirm
Run Setup
Deployment Summary
Manage Services
Doctor
Logs
```

UX requirements:

- Show current phase and completion state.
- Save progress after each phase.
- Survive browser refresh.
- Separate detection results from user answers.
- Warn before destructive service removal.
- Stream setup output live.
- Surface exact recovery commands when blocked.
- Provide copyable URLs after deployment.
- Work well from phone/tablet on LAN.

## Frontend Technical Plan

Recommended stack:

```text
React
Vite
TypeScript
React Router
TanStack Query
CSS Modules or Tailwind CSS
```

Keep state simple: TanStack Query for server state, local component state for unsaved form values. Keep forms schema-driven so question changes do not require frontend rewrites.

Suggested files:

```text
web/src/main.tsx
web/src/app/App.tsx
web/src/app/router.tsx
web/src/api/client.ts
web/src/api/types.ts
web/src/routes/*.tsx
web/src/components/FieldRenderer.tsx
web/src/components/ServiceCard.tsx
web/src/components/StepTimeline.tsx
web/src/components/EventLog.tsx
web/src/styles/tokens.css
```

## Backend Technical Plan

Suggested modules:

```text
src/rakkib/web/app.py      create_app(), static serving, route registration
src/rakkib/web/auth.py     token generation and session validation
src/rakkib/web/api.py      REST routes
src/rakkib/web/events.py   SSE helpers
src/rakkib/web/runner.py   background jobs and lock
src/rakkib/web/models.py   API response models
src/rakkib/web/static.py   package-data static lookup
```

Extract shared functions from CLI code only when needed. Likely candidates: repo/state path resolution, registry loading, dependency validation, service selection application, setup step execution, deployed URL summaries, and doctor checks/fixes.

## Development And Release

Local frontend:

```bash
cd web
npm install
npm run dev
```

Backend:

```bash
rakkib web --host 127.0.0.1 --port 8080
```

Production build:

```bash
cd web
npm ci
npm run build
rm -rf ../src/rakkib/data/web
mkdir -p ../src/rakkib/data/web
cp -R dist/* ../src/rakkib/data/web/
```

During development, Vite can proxy `/api` to the Python backend.

## Testing Strategy

Do not use the current development machine as proof of bare-metal behavior. Final install behavior must be validated on fresh Ubuntu 24.04.

Test layers:

```text
Frontend:
  npm run build
  field rendering tests
  API client tests with mocked responses

Backend:
  token auth
  state redaction
  schema-to-API serialization
  service selection preview

Integration:
  rakkib web starts and serves static UI
  token required
  existing .fss-state.yaml resumes
  /api/pull/start refuses unconfirmed state
  destructive service removal is previewed

Bare-metal acceptance:
  fresh Ubuntu 24.04
  install.sh succeeds
  rakkib web --lan starts
  browser on another LAN device can complete setup
  refresh resumes from saved state
```

## Milestones

### 1. Backend Skeleton

- Add web dependencies.
- Add `src/rakkib/web/`.
- Add `rakkib web`.
- Serve placeholder static page.
- Implement token guard and URL printing.

Acceptance: localhost starts, `--lan` prints LAN URL, unauthenticated API requests fail.

### 2. State And Schema API

- Expose redacted state.
- Expose phase schemas.
- Save answers through API.
- Compute resume phase.

Acceptance: browser can complete phases 1-6 using `.fss-state.yaml`, refresh resumes, secrets are not returned.

### 3. React Installer UI

- Replace placeholder with Vite React SPA.
- Build guided phase screens.
- Implement schema-driven field renderer.
- Implement confirmation screen.

Acceptance: browser can complete the `rakkib init` equivalent and CLI `rakkib pull` can use the resulting state.

### 4. Setup Runner

- Add background job runner.
- Start setup from web UI.
- Stream setup events via SSE.
- Show success/failure state.

Acceptance: confirmed setup runs from the browser, progress streams live, failures show actionable errors and log paths.

### 5. Service Management

- Add registry-driven service management UI.
- Preview add/remove changes.
- Require destructive confirmation.
- Add restart actions.

Acceptance: web service management matches `rakkib add`, including destructive removal warnings and CLI-aligned restarts.

### 6. Doctor And Polish

- Add Doctor screen.
- Add safe guided fixes.
- Add deployment summary with service URLs.
- Polish mobile and accessibility.

Acceptance: phone/tablet LAN use works, common blockers show exact fix commands, summary matches CLI status output.

## Risks And Open Decisions

Open decisions:

- Install web dependencies by default or behind an extra such as `rakkib[web]`.
- Include `rakkib web` in default `install.sh` immediately or gate behind beta.
- Keep sudo authentication terminal-only in v1.
- Add file-based locking if multiple `rakkib web` processes become a real issue.

Primary risks:

- Accidentally requiring Node.js on the target server.
- Duplicating CLI logic instead of sharing it.
- Exposing a privileged LAN server without strong token auth.
- Returning secrets through APIs.
- Allowing multiple mutating jobs concurrently.

## Definition Of Done

The web UI is complete when:

- `rakkib web --lan` starts after a fresh install.
- Another device on the LAN can open the printed URL.
- The browser can complete the Rakkib interview and start setup after confirmation.
- Setup progress streams live and remains understandable.
- Browser refresh resumes from server-side state.
- Secrets are redacted in all API responses.
- Service selection and removal behavior matches `rakkib add`.
- The CLI remains fully usable without the web UI.
- No Node.js runtime is required on the target server.
