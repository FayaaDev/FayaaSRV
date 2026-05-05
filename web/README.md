# Rakkib Frontend Setup Guide

This directory contains the React + Vite frontend for Rakkib's browser-based setup and management UI.

The product direction lives in `web/WebUI.md`. The current visual baseline is the existing dark marketing page implemented in `src/App.tsx`, `src/App.css`, and `src/index.css`.

## Purpose

The frontend is a thin UI layer over existing Rakkib behavior.

- The target server must stay installable through `install.sh`
- The target server must not require Node.js at runtime
- The frontend ships as built static assets inside the Python package
- The Python backend remains the source of truth for state, questions, services, logs, and setup progress

Primary flow:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
rakkib web --lan
```

## Local Development

Frontend app:

```bash
cd web
npm install
npm run dev
```

Backend from the repo root:

```bash
rakkib web --host 127.0.0.1 --port 8080
```

Recommended workflow:

1. Start `rakkib web` in one terminal.
2. Start `npm run dev` in `web/`.
3. Point the Vite app at the Python backend for `/api` requests.
4. Build UI against real backend schemas and responses rather than duplicating business logic in React.

## Runtime Model

The frontend is built ahead of time and served by the Python app.

- React + Vite SPA in `web/`
- Python backend under `src/rakkib/web/`
- Built assets copied into `src/rakkib/data/web/`
- No `node_modules` or Node.js runtime on the target host

Repository layout:

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

## Frontend Rules

The React app must stay a thin adapter over existing Rakkib behavior.

- Do not duplicate installer, setup, state, service-selection, or doctor logic
- Do not hardcode interview forms
- Render question flows from backend schemas
- Treat secrets as write-only
- Use backend-derived values instead of recomputing them in the browser
- Assume only one mutating job can run at a time

Supported schema field types from `web/WebUI.md`:

```text
text
confirm
single_select
multi_select
secret_group
summary
derived
```

## Suggested Stack

Target stack from `web/WebUI.md`:

- React
- Vite
- TypeScript
- React Router
- TanStack Query
- CSS Modules or Tailwind CSS

Suggested file layout:

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

Use TanStack Query for server state and local component state for unsaved form values.

## Current Theme Baseline

Maintain the current dark marketing page theme unless a new Rakkib-specific design system replaces it.

Current characteristics from the checked-in frontend:

- dark shell background
- dark card surfaces
- light text with muted secondary copy
- compact mono-heavy type stack
- simple bordered cards and controls
- marketing-style landing page with install command and service grid

When extending the UI, preserve the established dark visual language in `src/index.css` and `src/App.css` instead of introducing a conflicting replacement system.

## Core Screens

The UI should feel like a guided installer, not a generic admin dashboard.

Core screens planned in `web/WebUI.md`:

- Start / Resume
- Host Check
- Platform
- Identity
- Services
- Cloudflare
- Secrets
- Confirm
- Run Setup
- Deployment Summary
- Manage Services
- Doctor
- Logs

UX requirements:

- show current phase and completion state
- save progress after each phase
- survive browser refresh
- separate detection results from user answers
- warn before destructive service removal
- stream setup output live
- surface exact recovery commands when blocked
- provide copyable URLs after deployment
- work well from phone and tablet on LAN

## Build And Packaging

Production build flow:

```bash
cd web
npm ci
npm run build
rm -rf ../src/rakkib/data/web
mkdir -p ../src/rakkib/data/web
cp -R dist/* ../src/rakkib/data/web/
```

Packaging rules:

- build on a development machine or CI machine
- copy only built assets into `src/rakkib/data/web/`
- never ship `node_modules`
- never require Node.js on the target server

## API Areas The Frontend Depends On

Important API groups from `web/WebUI.md`:

- session and auth
- state and resume phase
- question schemas and answer submission
- registry and service metadata
- service selection preview and apply
- doctor checks and guided fixes
- setup runner status and events
- logs and log events

## Verification

Frontend work is ready when:

- `npm run build` succeeds
- the built SPA can be served by `rakkib web`
- refresh resumes from saved backend state
- secrets stay redacted in API responses
- phase rendering is schema-driven
- destructive removals are previewed before apply
- setup progress streams live
- phone and tablet LAN use remains usable
- target-host runtime still does not require Node.js
