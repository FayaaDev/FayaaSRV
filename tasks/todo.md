# Cloudflare Flow Improvement Plan

## Goal

Reduce user drop-off in the Cloudflare portion of the Rakkib install flow by making the browser-login handoff explicit, verifiable, and recoverable.

## Plan

- [x] Audit the live Cloudflare flow implementation against the normative docs to confirm where Step 40 blocks and what currently surfaces to the user.
- [x] Update `questions/04-cloudflare.md` to set expectations earlier that the install will pause later for Cloudflare approval and may require a second device.
- [x] Update `questions/06-confirm.md` so the final summary warns about the Step 40 Cloudflare interruption and the exact user action required for headless hosts.
- [x] Rewrite `steps/40-cloudflare.md` so browser-login authentication happens before tunnel discovery for new tunnels.
- [x] Add explicit Step 40 verification checkpoints for successful login, correct zone/account access, tunnel reuse-or-create, credentials placement, and DNS route creation.
- [x] Add a documented retry and recovery path for expired login links, wrong-account approvals, missing local credentials, and tunnel name collisions.
- [x] Decide how to model the Cloudflare browser-login auth artifact (`cert.pem`) and update docs so its role is consistent with backup and restore expectations.
- [x] Add a lightweight diagnostic or verification helper for Cloudflare auth readiness in `rakkib doctor` or as a clearly defined Step 40 command sequence.
- [x] Re-review all touched docs for consistency with `AGENT_PROTOCOL.md`, especially around `browser_login`, `api_token`, existing tunnels, and no-token-default behavior.

## Verification

- The Phase 4 question flow clearly tells the user that Cloudflare approval is a later blocking step.
- The Phase 6 confirmation summary clearly describes the Step 40 interruption for both local-browser and headless flows.
- The Step 40 sequence no longer attempts tunnel discovery before authentication when `cloudflare.auth_method: browser_login` and `tunnel_strategy: new`.
- Step 40 includes a clear success/failure decision point after `cloudflared tunnel login`.
- Step 40 includes at least one concrete recovery path for each common failure mode: expired link, wrong account, missing credentials, existing tunnel conflict.
- Documentation consistently explains whether `cert.pem` is required, where it lives, and how it relates to backups.

## Review

- Updated the Phase 4 and Phase 6 docs so users are warned in advance that Step 40 will pause for Cloudflare approval.
- Rewrote Step 40 so browser login happens before tunnel discovery for new tunnels and added concrete recovery branches.
- Standardized `{{DATA_ROOT}}/data/cloudflared/cert.pem` as the documented browser-login auth artifact without persisting it in `.fss-state.yaml`.
- Added non-destructive Cloudflare readiness checks to `rakkib doctor`.
- Verified `rakkib doctor` via pytest.

## AgentSchema Key Alignment

- [x] Identify remaining shortened `subdomains.*` contract keys after the parallel AgentSchema pass.
- [x] Normalize the protocol, registry, and placeholder reference to service-slug-only subdomain keys.
- [x] Remove shortened-key guidance from question-schema docs.
- [ ] Re-run repo-wide verification for legacy shortened `subdomains.*` references and close the loop on any remaining drift.

## AgentSchema Execution And Render Audit

- [x] Read the installer protocol, registry, placeholder reference, targeted steps, and any relevant templates for beads `Rakkib-juj.6` and `Rakkib-juj.7`.
- [x] Identify drift in placeholder names, subdomain keys, service slugs, secret keys, and execution-facing instructions.
- [x] Apply any minimal doc/template fixes that are safely within this lane.
- [x] Run targeted verification searches and lightweight checks.
- [x] Record readiness assessment for remaining `Rakkib-juj.6` and `Rakkib-juj.7` gaps.

## Review

- Fixed protocol drift where the authoritative Phase 3 subdomain contract and state example still used shortened keys instead of service-slug keys.
- Fixed step-order drift so Step 30 now only establishes the base Caddy config and Steps 60/70 own service-specific routes.
- Fixed Postgres/service step drift so Authentik DB prep is documented in Step 50 and Step 60 now consumes the prepared roles instead of recreating them.
- Fixed Linux-only verify commands that were still documented in shared or Mac paths for host-agent checks.
- Remaining question-file/schema-lane follow-up is intentionally untouched per task constraints.
