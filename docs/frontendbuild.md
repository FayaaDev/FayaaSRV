# Frontend Build Plan

## Goal

Build a browser-based Rakkib setup and management UI without changing the core contract:

- `install.sh` remains the only install entrypoint on a fresh Ubuntu host
- the target host must not require Node.js, npm, pnpm, or a separate JS server at runtime
- the browser UI must be a thin layer over existing Rakkib Python logic
- the existing dark marketing page remains available at `/`
- setup users with a valid token should land in the installer flow automatically

Primary target flow:

```bash
curl -fsSL https://install.rakkib.app | bash
rakkib web --lan
```

Printed URL behavior:

- normal visitor opens `/` and sees the marketing page
- setup visitor opens a tokenized URL
- frontend shows a short bridge screen
- backend validates token and establishes a session cookie
- frontend redirects to `/setup`

## Product Scope

### Keep

- current dark marketing page theme
- landing page at `/`
- existing i18n support in `web/src/i18n/`
- existing backend state, interview, service, doctor, and pull logic as the source of truth

### Build

- Python web backend under `src/rakkib/web/`
- `rakkib web` CLI command
- packaged static serving for the built SPA
- token and session auth
- `/setup` installer UI
- schema-driven phase rendering
- state save/resume flow
- setup runner and SSE progress stream
- later service management and doctor screens

### Do Not Build

- a separate Node.js runtime on target machines
- frontend-owned setup logic
- duplicated service dependency logic in React
- duplicated `when` / derived-value evaluation in JavaScript

## Existing Source Of Truth

The web UI should wrap these modules instead of reimplementing them:

- `src/rakkib/state.py`
  - state load/save
  - `resume_phase()`
  - `is_phase_complete()`
- `src/rakkib/schema.py`
  - question schema loading
- `src/rakkib/interview.py`
  - field processing
  - validation
  - derived values
  - phase rules
  - service catalog behavior
- `src/rakkib/cli.py`
  - service selection apply/validate
  - pull orchestration helpers
- `src/rakkib/steps/services.py`
  - service deploy/remove/restart/smoke behavior
- `src/rakkib/doctor.py`
  - doctor checks and guided fixes
- `src/rakkib/data/questions/*.md`
  - phase schemas
- `src/rakkib/data/registry.yaml`
  - service metadata and dependencies

## User Experience Plan

### Route Map

- `/`
  - current landing page
  - if no token/session, remain on landing page
  - if token present, render bridge screen and continue into setup
- `/setup`
  - installer shell
  - loads session and resume phase
- `/setup/phase/:phase`
  - phase form UI
- `/setup/confirm`
  - review and final confirmation
- `/setup/run`
  - live setup execution screen
- future:
  - `/setup/services`
  - `/setup/doctor`
  - `/setup/logs`

### Token Bootstrap Flow

1. User opens a printed URL from `rakkib web`.
2. URL contains a token, likely `/?token=...` or `/setup?token=...`.
3. Frontend shows a short `Connecting to setup...` bridge screen.
4. Backend validates the token.
5. Backend stores an HTTP-only session cookie.
6. Frontend strips the token from the visible URL.
7. Frontend redirects to `/setup`.
8. Frontend requests session state and resume phase.

Failure states:

- invalid token
- stale token from an old `rakkib web` process
- expired or missing session when navigating directly to `/setup`

Error UX should always include the recovery command:

```bash
rakkib web --lan
```

### Setup Screens

Initial screens:

- Start / Resume
- Platform
- Identity
- Services
- Cloudflare
- Secrets
- Confirm
- Run Setup

Later screens:

- Deployment Summary
- Manage Services
- Doctor
- Logs

### Theme Direction

Preserve the current dark theme as the baseline:

- dark shell background
- dark surfaces and bordered cards
- light foreground text with muted secondary copy
- compact, technical type stack
- mobile-friendly single-column collapse

Use this theme for the installer flow instead of replacing it with a new design system during the first implementation.

## Architecture Plan

### Frontend

Framework:

- React
- Vite
- TypeScript
- React Router
- TanStack Query

Recommended file structure:

```text
web/src/
  main.tsx
  app/
    App.tsx
    router.tsx
  api/
    client.ts
    types.ts
  routes/
    Landing.tsx
    SetupBridge.tsx
    SetupStart.tsx
    SetupPhase.tsx
    SetupConfirm.tsx
    SetupRun.tsx
  components/
    SetupShell.tsx
    StepTimeline.tsx
    FieldEditor.tsx
    FieldRenderer.tsx
    EventLog.tsx
  styles/
    tokens.css
```

State model:

- TanStack Query for server state
- local component state for unsaved inputs
- no frontend source of truth for setup logic

### Backend

Add:

```text
src/rakkib/web/
  __init__.py
  app.py
  answers.py
  auth.py
  api.py
  events.py
  models.py
  runner.py
  static.py
```

Recommended stack:

- FastAPI
- Uvicorn
- standard streaming responses for SSE, unless a very small helper package is needed

### Runtime Packaging

Build frontend assets on a development or CI machine only.

Packaged layout:

```text
src/rakkib/data/web/
  index.html
  assets/
```

The target server receives only:

- Python package
- built static files

The target server must not need:

- `node`
- `npm`
- `pnpm`
- `wrangler`

## Backend Implementation Plan

### Phase 1: Web Skeleton (Completed)

Status: implemented in `pyproject.toml`, `src/rakkib/web/`, `src/rakkib/data/web/`, and the `rakkib web` CLI command.

Add web runtime dependencies to `pyproject.toml`.

Add a new CLI command to `src/rakkib/cli.py`:

```text
rakkib web
rakkib web --lan
rakkib web --host 127.0.0.1 --port 8080
rakkib web --host 0.0.0.0 --port 8080
rakkib web --token <token>
rakkib web --no-token
rakkib web --no-open
```

Default behavior:

- bind to `127.0.0.1`
- require token auth by default
- print local URL
- only expose LAN with `--lan` or explicit host

Responsibilities in this phase:

- create app factory
- serve built static assets
- support SPA fallback for `/`, `/setup`, and nested setup routes
- print tokenized URLs

Acceptance:

- `rakkib web` starts locally
- static frontend is served by Python
- tokenized URLs are printed

### Phase 2: Session And Auth (Completed)

Status: implemented with token bootstrap, HTTP-only session cookies, protected `/setup` routing, and authenticated API access.

Implement token validation and cookie-backed session handling.

Rules:

- generate token at process start unless provided
- store token only in process memory for v1
- accept token from query string once
- issue HTTP-only cookie after validation
- require cookie or bearer token for API access
- set cache-control headers on sensitive routes
- `--no-token` must be explicit

Acceptance:

- valid token establishes session
- invalid token fails cleanly
- token does not need to remain in URL after bootstrap
- `/setup` rejects missing session

### Phase 3: Read-Only API Slice (Completed)

Status: implemented in `src/rakkib/web/api.py` with real state/schema loading, backend-filtered active fields, and secret redaction.

Implement:

- `GET /api/health`
- `GET /api/session`
- `GET /api/state`
- `GET /api/state/resume`
- `GET /api/questions/phases`
- `GET /api/questions/phases/{phase}`

Backend wrappers should use:

- `State.load()`
- `State.resume_phase()`
- `load_all_schemas()`

Important constraints:

- redact secrets
- do not return plaintext secret values
- do not let frontend compute resume logic itself

Acceptance:

- frontend can discover current session and resume phase
- frontend can load phase schemas from real backend data

### Phase 4: State Write APIs (Completed)

Status: implemented in `src/rakkib/web/api.py` and `src/rakkib/web/answers.py` with non-interactive phase answer processing and `.fss-state.yaml` persistence.

Implement:

- `PATCH /api/state`
- `POST /api/questions/phases/{phase}/answers`

These APIs must be backed by extracted or shared logic from the current interview flow.

Required backend-owned behavior:

- validation
- derived value handling
- `when` handling
- record keys
- phase rules
- secret write semantics

Important warning:

- phase 3 services are not a generic field-only phase
- service selection must stay aligned with existing CLI and registry behavior

Acceptance:

- answers persist to `.fss-state.yaml`
- browser refresh resumes correctly
- no frontend duplication of interview semantics

### Phase 5: Setup Runner

Implement background setup execution.

Endpoints:

- `POST /api/pull/start`
- `POST /api/pull/cancel`
- `GET /api/pull/status`
- `GET /api/pull/events`

Rules:

- no mutating job inside a request handler
- only one mutating job at a time
- unconfirmed state must be rejected
- reuse existing pull orchestration logic

Acceptance:

- confirmed setup can be started from the browser
- progress is streamed live
- failures surface actionable recovery guidance

### Phase 6: Services And Doctor

Implement later, after installer flow is stable.

Services endpoints:

- `GET /api/registry`
- `GET /api/services`
- `POST /api/services/selection/preview`
- `POST /api/services/selection/apply`
- `POST /api/services/{service_id}/restart`
- `POST /api/services/restart-all`

Doctor endpoints:

- `GET /api/doctor`
- `POST /api/doctor/fix/{check}`

Rules:

- backend must own dependency validation
- backend must own destructive removal preview
- backend must own restart order
- backend must own doctor fix semantics

## Frontend Implementation Plan

### Phase 1: Routing Refactor (Completed)

Status: implemented with routed landing and setup placeholder routes in `web/src/app/router.tsx` and `web/src/routes/`.

Refactor the current single-page app into a routed app without changing landing page behavior.

Tasks:

- move current landing page UI into `routes/Landing.tsx`
- add router setup in `app/router.tsx`
- keep current dark styling and i18n intact
- add empty route placeholders for setup flow

Acceptance:

- `/` renders the same landing page as before
- frontend uses client-side routing

### Phase 2: Bridge Screen (Completed)

Status: implemented in `web/src/routes/SetupBridge.tsx` with token detection, bootstrap call, URL cleanup, redirect, and recovery UX.

Add `SetupBridge.tsx`.

Responsibilities:

- detect token in URL
- display loading state
- call session bootstrap endpoint
- handle invalid token state
- redirect to `/setup` on success
- remove token from visible URL

Acceptance:

- tokenized entry flows cleanly into setup
- invalid token state is understandable

### Phase 3: Setup Shell

Status: implemented in `web/src/components/SetupShell.tsx`, `web/src/components/StepTimeline.tsx`, and installer route styling in `web/src/App.css`.

Add `SetupShell.tsx` as the common frame for installer routes.

Responsibilities:

- phase navigation / timeline
- page title and action region
- session-aware gating
- layout that preserves the current dark visual language

Acceptance:

- installer pages feel cohesive with landing page theme
- shell works on mobile and tablet

### Phase 4: Read-Only Setup Flow (Completed)

Status: implemented in `web/src/routes/SetupStart.tsx`, `web/src/routes/SetupPhase.tsx`, `web/src/components/FieldRenderer.tsx`, and the setup API client/types.

Build:

- `SetupStart.tsx`
- `SetupPhase.tsx`

Responsibilities:

- load current session and resume phase
- fetch schema for a phase
- render fields via `FieldRenderer`
- show phase completion state

Acceptance:

- browser can navigate setup phases using backend data
- no answers are saved yet in this slice

### Phase 5: Field Rendering (Completed)

Status: implemented with backend-driven field payloads, read-only summary/derived rendering, editable field inputs, and service catalog display.

Support these field types:

- `text`
- `confirm`
- `single_select`
- `multi_select`
- `secret_group`
- `summary`
- `derived`

Rules:

- frontend renders backend schema
- frontend does not evaluate schema conditions locally
- frontend does not invent derived values

Acceptance:

- phase forms render from real schema payloads

### Phase 6: Save And Resume (Completed)

Status: implemented with per-phase submission, backend validation errors, partial saves for newly activated fields, and resume-aware navigation.

Wire form submission to backend write APIs.

Responsibilities:

- submit answers per phase
- handle validation errors
- persist answers
- reload resume phase
- support refresh and resume

Acceptance:

- form answers persist correctly
- refresh returns the user to the right point in setup

### Phase 7: Confirm And Run

Build:

- `SetupConfirm.tsx`
- `SetupRun.tsx`
- `EventLog.tsx`

Responsibilities:

- display summary
- final confirmation
- start setup job
- stream live output
- show success/failure states

Acceptance:

- browser can trigger the setup run
- job progress is live and understandable

### Phase 8: Service Management And Doctor

Later build:

- service management UI aligned to `rakkib add`
- doctor UI aligned to `rakkib doctor`

## API Contract Plan

### Initial Endpoints

```text
GET  /api/health
GET  /api/session
GET  /api/state
PATCH /api/state
GET  /api/state/resume
GET  /api/questions/phases
GET  /api/questions/phases/{phase}
POST /api/questions/phases/{phase}/answers
POST /api/pull/start
POST /api/pull/cancel
GET  /api/pull/status
GET  /api/pull/events
```

### Later Endpoints

```text
GET  /api/registry
GET  /api/services
POST /api/services/selection/preview
POST /api/services/selection/apply
GET  /api/doctor
POST /api/doctor/fix/{check}
POST /api/services/{service_id}/restart
POST /api/services/restart-all
GET  /api/logs
GET  /api/logs/{name}
GET  /api/logs/events
```

## Data And Logic Ownership Rules

### Backend Owns

- token validation
- session validity
- state persistence
- resume phase
- field defaults and derived values
- `when` evaluation
- secret redaction
- service dependency validation
- service selection preview/apply logic
- destructive removal semantics
- doctor checks and fixes
- setup job execution

### Frontend Owns

- routing
- interaction flow
- local unsaved form state
- presentation and loading/error states
- live log rendering

### Frontend Must Not Own

- schema semantics
- resume logic
- service dependency rules
- secret generation or storage rules
- pull orchestration

## Required Refactors

### Backend Refactors

Likely extraction targets from CLI/interview code:

- reusable non-interactive phase answer processing
- reusable summary generation
- reusable service-catalog payload generation
- reusable service-selection preview/apply API helpers
- reusable pull runner wrapper

### Frontend Refactors

- move current landing page out of `App.tsx`
- add router
- add API client layer
- add installer-specific components

### Tooling Cleanup

Current frontend still includes Cloudflare-oriented tooling in `vite.config.ts` and `package.json`.

Target direction:

- keep plain Vite build
- remove runtime assumptions unrelated to Python static serving

This cleanup should happen once Python static serving is active, so it does not introduce unnecessary unrelated changes too early.

## Build And Packaging Plan

Frontend build flow:

```bash
cd web
npm ci
npm run build
rm -rf ../src/rakkib/data/web
mkdir -p ../src/rakkib/data/web
cp -R dist/* ../src/rakkib/data/web/
```

Rules:

- build on development or CI machines only
- ship built assets only
- do not ship `node_modules`
- keep target runtime Python-only

## Verification Plan

### Local Verification

Must verify:

- frontend builds successfully
- `rakkib web` starts
- `/` renders the marketing page
- tokenized entry shows bridge screen
- valid token redirects to `/setup`
- invalid token shows clear recovery guidance
- `/setup` enforces session presence
- read-only APIs return real backend state and schema data
- answers persist to `.fss-state.yaml`
- refresh resumes correctly
- secrets are redacted from API responses
- `/api/pull/start` rejects unconfirmed state
- live setup output streams on run screen

Current completed local verification:

- `python3 -m compileall src/rakkib/web`
- `PYTHONPATH=src python3 -c "from rakkib.web import WebRuntimeConfig, create_app; create_app(WebRuntimeConfig(host='127.0.0.1', port=8080, token_auth_enabled=True, startup_token='test')); print('ok')"`
- `cd web && npm run build`

### Bare-Metal Verification

Do not treat the current development machine as proof of install behavior.

Final acceptance must be checked on fresh Ubuntu 24.04:

- `install.sh` succeeds
- `rakkib web --lan` starts
- another device can open the printed URL
- token flow reaches `/setup`
- browser refresh resumes state
- runtime does not require Node.js on the target host

## Milestones

### Milestone 1: Backend Skeleton (Completed)

Status: implemented with the Python web package, placeholder static frontend, `rakkib web`, and tokenized URL printing.

- add dependencies
- add `src/rakkib/web/`
- add `rakkib web`
- serve placeholder static frontend
- print tokenized URLs

Acceptance:

- localhost starts
- tokenized URL is printed
- unauthenticated API access fails

### Milestone 2: Session And Read-Only APIs (Completed)

Status: implemented with auth/session handling, read-only state/schema APIs, and token bootstrap flow.

- implement auth/session handling
- add read-only state and schema endpoints
- add token bootstrap flow

Acceptance:

- tokenized browser entry reaches authenticated setup shell

### Milestone 3: Routed Frontend And `/setup` (Completed)

Status: implemented with preserved landing page behavior, bridge flow, installer shell, and backend-driven phase rendering.

- preserve `/`
- add bridge screen
- add `/setup` shell and phase navigation
- render backend-provided phase data

Acceptance:

- landing page still works
- `/setup` loads real backend data

### Milestone 4: Save And Resume (Completed)

Status: implemented with backend write APIs, editable phase forms, state persistence, and resume after refresh/navigation.

- submit answers
- persist state
- resume after refresh

Acceptance:

- browser can complete phases 1-6 against `.fss-state.yaml`

### Milestone 5: Run Setup

- add background runner
- add SSE progress stream
- add confirm and run screens

Acceptance:

- confirmed setup can be run from the browser

### Milestone 6: Services And Doctor

- add service management UI
- add doctor UI
- align behavior with CLI

Acceptance:

- service and doctor flows match CLI semantics

## Risks

Primary risks:

- duplicating CLI/interview logic in React
- returning secrets in API payloads
- treating phase 3 as a generic schema phase
- allowing multiple mutating jobs concurrently
- breaking `install.sh` or runtime packaging assumptions
- leaving Cloudflare frontend tooling coupled to the wrong runtime model

## Decisions Already Made

- keep the current dark marketing page at `/`
- add installer flow under `/setup`
- use a bridge screen for tokenized entry
- preserve Python as the runtime host for the web UI
- preserve backend ownership of all setup logic

## Definition Of Done

The web frontend is complete when:

- `rakkib web --lan` starts after a fresh install
- another device can open the printed URL
- tokenized entry reaches `/setup`
- the browser can complete the setup interview
- refresh resumes from saved state
- secrets are redacted in all API responses
- the browser can start and observe setup execution
- service selection behavior matches `rakkib add`
- doctor behavior matches `rakkib doctor`
- the CLI remains fully usable without the web UI
- the target host runtime does not require Node.js
