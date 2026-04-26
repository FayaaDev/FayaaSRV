# Installer Question Schema

Rakkib keeps the human-readable installer phases in `questions/01-platform.md` through `questions/06-confirm.md`, and each phase also carries a small machine-readable `## AgentSchema` YAML block.

`AGENT_PROTOCOL.md` remains the normative installer spec. The schema exists to make question rendering, validation, defaults, and state writes explicit enough that agents do not have to infer them from prose.

## Authoring Rules

1. Preserve the markdown guidance. The schema complements the prose; it does not replace it.
2. Keep the schema small. Prefer plain YAML with `reads_state`, `writes_state`, `fields`, and a few phase-specific sections such as `service_catalog`.
3. Record canonical values in metadata, then mention convenience aliases separately.
4. Use installer state keys exactly as they should appear in `.fss-state.yaml`.
5. Use canonical service slugs from `registry.yaml` for all service identifiers.
6. Use service-slug keys for `subdomains`, even when the default hostname differs from the slug.
7. If a value is intentionally generated later instead of asked during the interview, document that explicitly.
8. When prose and schema disagree, fix both in the same change.

## Minimal Shape

```yaml
schema_version: 1
phase: 3
reads_state:
  - domain
writes_state:
  - foundation_services
  - selected_services
  - subdomains
fields:
  - id: optional_services
    type: multi_select
    prompt: Optional Services: type service slugs to add...
    canonical_values: [n8n, immich]
    numeric_aliases:
      "6": n8n
      "8": immich
    records:
      - selected_services
```

## Field Types

- `text`: free-form input with validation such as `pattern` or `non_empty`.
- `confirm`: yes/no input mapped to booleans or small canonical values.
- `single_select`: one choice from `canonical_values`.
- `multi_select`: multiple canonical slugs, usually with optional aliases.
- `derived`: host-detected or state-derived values that are recorded without asking the user.
- `summary`: a read-only presentation step before final confirmation.
- `secret_group`: a grouped set of secret prompts recorded under `secrets.values`.

## Canonical Inputs

Canonical answer formats should be stable, descriptive values rather than presentation-specific shortcuts.

- Use `linux`, not `1`.
- Use `openclaw`, not `10`.
- Use `vergo_terminal`, not `12`.

Numeric checklist entries may still appear in prose for usability, but they must be documented as aliases in schema metadata and normalized before writing state.

## Service And Subdomain Rules

Use `registry.yaml` service IDs as the source of truth for service slugs.

Examples:

- `foundation_services: [authentik, homepage]`
- `selected_services: [openclaw, hermes]`
- `subdomains.authentik: auth`
- `subdomains.homepage: home`
- `subdomains.uptime-kuma: status`
- `subdomains.openclaw: claw`

Do not record alias subdomain keys in new state files. Use the service slug as the only `subdomains.*` key.

## Secrets Coverage

When editing `questions/05-secrets.md`, reconcile against both `registry.yaml` and `steps/60-services.md`.

Current interview-time secret coverage:

- Always: `POSTGRES_PASSWORD`
- `nocodb`: `NOCODB_DB_PASS`, `NOCODB_ADMIN_PASS`
- `authentik`: `AUTHENTIK_SECRET_KEY`, `AUTHENTIK_DB_PASS`, `AUTHENTIK_ADMIN_PASS`
- `n8n`: `N8N_DB_PASS`, `N8N_ENCRYPTION_KEY`
- `immich`: `IMMICH_DB_PASSWORD`

Current execution-time generated-only values:

- `NOCODB_OIDC_CLIENT_ID`
- `NOCODB_OIDC_CLIENT_SECRET`
- `IMMICH_VERSION` defaults to `release` unless the repo is intentionally changed to pin another tag

If step or registry requirements change, update the question schema and prose in the same patch.

## Migration Checklist

When changing a question phase:

1. Update the `## AgentSchema` block.
2. Update the human-readable instructions in the same file.
3. Check `AGENT_PROTOCOL.md` for contract drift.
4. Check `registry.yaml` for canonical service IDs, defaults, and secret keys.
5. Check `lib/placeholders.md` and relevant `steps/*.md` for the state keys and placeholder names the phase feeds.
6. If a mismatch cannot be fixed in your lane, document it explicitly in your handoff instead of encoding another alias into state.

## Drift Prevention

Prefer one canonical recorded key with documented aliases at input time over writing multiple equivalent keys into `.fss-state.yaml`.

Good:

```yaml
selected_services:
  - openclaw
subdomains:
  openclaw: claw
```

Avoid:

```yaml
selected_services:
  - openclaw
subdomains:
  openclaw: claw
  claw: claw
```

The second form hides contract drift instead of fixing it.
