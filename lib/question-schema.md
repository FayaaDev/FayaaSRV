# Question Schema Reference

Rakkib question files may embed a machine-readable schema as a single fenced `yaml` block under a `## AgentSchema` heading.

Minimal shape:

```yaml
schema_version: 1
phase: 3
reads_state: [domain]
writes_state: [selected_services]
fields:
  - id: optional_services
    type: multi_select
    prompt: Optional Services: type service slugs to add (e.g. `n8n immich hermes`); numeric aliases like `6 8 11` are also accepted, or press Enter to skip all:
    canonical_values: [n8n, dbhub, immich, transfer, openclaw, hermes]
    numeric_aliases:
      "6": n8n
      "8": immich
      "11": hermes
    records:
      - selected_services
```

Allowed top-level fields:

- `schema_version`
- `phase`
- `reads_state`
- `writes_state`
- `fields`
- `service_catalog`
- `rules`
- `execution_generated_only`

Common field properties:

- `id`
- `type`
- `prompt`
- `prompt_template`
- `when`
- `default`
- `default_from_state`
- `default_from_host`
- `canonical_values`
- `numeric_aliases`
- `aliases`
- `accepted_inputs`
- `validate`
- `detect`
- `normalize`
- `derive_from`
- `value`
- `derived_value`
- `value_if_true`
- `records`
- `repeat_for`
- `summary_fields`
- `entries`

Rules:

- Keep the schema declarative. Do not add a custom DSL beyond the fields above.
- Record canonical state keys and canonical enum values only.
- Keep prose instructions aligned with the schema until all question files rely on the embedded block.
- `AGENT_PROTOCOL.md` remains the authoritative contract for defaults, normalization, derived values, and cross-phase dependencies.
