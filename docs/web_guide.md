# Rakkib Web Guide

## Start

From the repo root:

```bash
PYTHONPATH=src python3 -m rakkib web --lan --no-open
```

What it does:

- starts the Python web server
- prints a local URL
- prints a LAN URL when available
- requires a token by default

## Open The UI

- Open the base URL to see the landing page at `/`
- Open the full printed token URL to enter setup

Expected token flow:

1. open printed `?token=...` URL
2. bridge screen appears
3. backend validates token
4. session cookie is set
5. browser redirects to `/setup`
6. setup resumes at the current phase

## Implemented Now

- landing page at `/`
- token bootstrap flow
- session-protected `/setup`
- setup shell and phase timeline
- backend-driven phase rendering
- phase save and resume
- secret redaction in API responses

## Not Implemented Yet

- final confirm screen behavior
- browser-triggered setup run
- SSE live run output
- service management UI
- doctor UI

## Useful Checks

Build frontend:

```bash
cd web
npm run build
```

Compile Python web modules:

```bash
python3 -m compileall src/rakkib/web
```

Verify app import:

```bash
PYTHONPATH=src python3 -c "from rakkib.web import WebRuntimeConfig, create_app; create_app(WebRuntimeConfig(host='127.0.0.1', port=8080, token_auth_enabled=True, startup_token='test')); print('ok')"
```

## Common Recovery

If the token is stale or the session is missing, start a fresh web session:

```bash
rakkib web --lan
```
