# Homeage And Kuma Fix Plan

## Goals

- Find why Homepage continues listing removed services after `rakkib add` deselects them.
- Implement registry-driven auto-monitor provisioning for Uptime Kuma so it does not deploy empty.
- Keep both behaviors deterministic and derived from the same selected-service state.

## Part 1: Investigate Homepage Stale Entries

### Expected Behavior

- `rakkib add` updates `.fss-state.yaml` to remove deselected services.
- Homepage `services.yaml` is regenerated from `selected_service_defs(state, registry)`.
- Homepage reads only the regenerated file and stops showing removed services.

### Known Code Paths

- Homepage config generation happens in `src/rakkib/hooks/services.py::homepage_services_yaml()`.
- That hook writes `data/homepage/config/services.yaml` from the current selected services.
- The hook only runs when the Homepage service post-render hook executes.
- `rakkib add` currently removes services, rewrites state, then runs `postgres_step.run(state)` and `services_step.run(state)`.

### Investigation Checklist

1. Reproduce the issue on the target bare-metal test machine.
2. Capture the pre-change state:
   - `.fss-state.yaml`
   - `DATA_ROOT/data/homepage/config/services.yaml`
   - Homepage UI screenshot or visible stale entries
3. Deselect one known service via `rakkib add`.
4. Immediately compare post-change artifacts:
   - confirm the service is removed from `foundation_services` or `selected_services`
   - confirm its `subdomains.<service>` key is removed
   - confirm it is absent from generated `services.yaml`
5. If `services.yaml` is correct but UI is stale:
   - verify Homepage mounts `DATA_ROOT/data/homepage/config`
   - verify the container restarts or reloads config after regeneration
   - check whether Homepage caches config or requires an explicit restart
6. If `services.yaml` is stale:
   - verify Homepage remains selected after the sync
   - verify `homepage_services_yaml()` actually runs during `rakkib add`
   - inspect whether hook execution depends on Homepage being redeployed in a way that skips regeneration
7. If state is stale:
   - inspect `_apply_service_selection()` and removal ordering
   - verify removed services are pruned before Homepage regeneration begins

### Likely Root Causes To Validate

- Homepage hook is not re-run when unrelated services are removed.
- Homepage config file is regenerated in one path but container reads another.
- Homepage container does not reload changed config without restart.
- A stale generated file survives because a later render step overwrites with old state.

### Fix Strategy Options

#### Option A: Keep current model, guarantee regeneration

- Ensure Homepage config regeneration runs whenever service selection changes, even if Homepage itself was not added or removed.
- Treat Homepage generated config as a global artifact of the selected service set, not only of Homepage deployment.

#### Option B: Add explicit global post-sync hooks

- Introduce a post-sync phase in `rakkib add` for shared derived artifacts:
  - Homepage `services.yaml`
  - Authentik downstream blueprints
  - future Uptime Kuma monitor config
- This is likely cleaner than tying global generated files to one service's own render lifecycle.

### Recommended Direction

- Prefer Option B.
- Homepage app listing is not really service-local state; it is a projection of the whole selected deployment.
- Shared projections should be regenerated after the final service set is known.

### Verification For Homepage Fix

1. Select Homepage plus two optional apps.
2. Confirm both apps appear in Homepage.
3. Deselect one app with `rakkib add`.
4. Confirm the removed app disappears from:
   - `.fss-state.yaml`
   - generated `services.yaml`
   - Homepage UI
5. Repeat for a foundation service and an optional service.

## Part 2: Implement Uptime Kuma Auto-Monitoring

### Objective

- When `uptime-kuma` is selected, automatically provision monitors for selected services instead of leaving Kuma empty.

### Design Principle

- Do not derive monitor definitions from `homepage:` metadata.
- Add a dedicated registry section for monitoring because monitor needs differ from dashboard-card needs.

### Proposed Registry Schema

Add a `monitoring:` block to services that should appear in Kuma.

Example:

```yaml
monitoring:
  enabled: true
  type: http
  target: public_url
  path: /
  interval: 60
  timeout: 10
  retries: 3
```

Possible fields:

- `enabled`: include in Kuma generation
- `type`: `http`, `https`, `tcp`, `ping`
- `target`: `public_url`, `container`, `host_port`, `custom`
- `path`: HTTP path when relevant
- `port`: explicit port when not implied
- `interval`: polling frequency
- `timeout`: monitor timeout
- `retries`: retry count
- `name`: optional override for monitor display name
- `custom_url`: explicit URL when `target: custom`

### URL Resolution Rules

- `public_url`: `https://<subdomain>.<domain><path>`
- `container`: internal Docker target if Kuma and service share a network and stable container name exists
- `host_port`: `http://127.0.0.1:<port><path>` or another declared local target
- `custom`: exact value from registry

### Implementation Approach

1. Extend `src/rakkib/data/registry.yaml` with `monitoring:` blocks for monitorable services.
2. Add a new shared hook or helper in `src/rakkib/hooks/services.py` to generate Kuma monitor definitions from selected services.
3. Decide on the provisioning mechanism:
   - preferred: generate config via Kuma-supported import/API workflow
   - fallback: seed a JSON payload or bootstrap script consumed after container start
4. Run this generation only when `uptime-kuma` is selected.
5. Re-run monitor generation after any `rakkib add` sync so Kuma stays aligned with selected services.

### Open Technical Decision

- Need to confirm the most reliable non-interactive provisioning method for Uptime Kuma in this repo context:
  - API bootstrap after container becomes healthy
  - database seed file
  - supported import/export format

This should be researched before implementation so we do not build against an unstable internal DB format.

### Recommended Kuma Architecture

- Add a global derived-artifact step after service sync.
- That step should:
  - regenerate Homepage `services.yaml`
  - regenerate Authentik downstream artifacts
  - regenerate Kuma monitor definitions
- This creates one consistent post-selection projection layer.

### Verification For Kuma

1. Select `uptime-kuma` and several services with `monitoring.enabled: true`.
2. Run deployment on the bare-metal test machine.
3. Confirm Kuma contains monitors for all selected monitored services.
4. Deselect one monitored service.
5. Confirm its Kuma monitor is removed or disabled according to chosen sync semantics.
6. Add a new monitored service later with `rakkib add`.
7. Confirm Kuma gains the new monitor automatically.

## Suggested Task Breakdown

1. Reproduce and isolate Homepage stale-entry bug.
2. Decide whether shared generated artifacts move to a dedicated post-sync phase.
3. Implement Homepage regeneration fix.
4. Research Kuma non-interactive provisioning method.
5. Add `monitoring:` registry schema.
6. Implement Kuma monitor generation.
7. Add tests for generated Homepage and Kuma artifacts where practical.
8. Validate end-to-end on the target bare-metal machine.

## Success Criteria

- Removed services no longer remain visible in Homepage.
- Homepage app list always matches the currently selected services.
- Uptime Kuma deploys with monitors for selected monitorable services.
- `rakkib add` remains the single sync point for both adding and removing service-derived dashboard/monitor artifacts.
