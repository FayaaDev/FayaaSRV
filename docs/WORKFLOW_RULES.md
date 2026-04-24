## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimat Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## DBHub Resolution Rules

### Default Rule
- When using DBHub, do not assume app config points directly to a physical SQL table.
- If the app references an ID, alias, base, model, workflow, or API abstraction, resolve that metadata first before querying data tables.
- Do not assume the table is in `public`; check metadata tables or `information_schema` when the app uses an abstraction layer.
- Once a mapping is proven stable, record it under `Known Mappings` so future queries can skip discovery.

### Resolution Order For Any App
1. Read the app config or env file first.
2. Identify the data source type: native Postgres, NocoDB, n8n, Supabase/PostgREST, or another abstraction.
3. If native Postgres, query the physical schema/table directly.
4. If abstracted, resolve the abstraction metadata to the physical schema/table first.
5. If the expected table is not in `public`, inspect `information_schema.tables` before guessing.
6. After resolving the physical target, query only the minimum columns needed.

### Native Postgres
- Query DBHub against the correct database first.
- Use `information_schema.tables` and `information_schema.columns` when table names or schemas are unclear.
- Prefer direct physical tables over application-layer assumptions.

### NocoDB
- When an app uses NocoDB env vars like `NEXT_PUBLIC_NOCODB_TABLE_ID`, do not assume the physical table is in `public`.
- Resolve the model in `nocodb.public.nc_models_v2` using the table ID.
- Resolve the source in `nocodb.public.nc_sources_v2` and read its `config.schema`.
- Query the physical table using `"<schema>"."<table_name>"`.
- If needed, verify with `information_schema.tables` and `information_schema.columns`.

### n8n
- If the app is asking about workflows, credentials, or executions, query the `n8n` database metadata tables first.
- Common tables include `public.workflow_entity`, `public.execution_entity`, and related sharing or history tables.
- n8n often uses quoted camelCase columns, so use quoted identifiers when querying fields like `"createdAt"` and `"updatedAt"`.
- If a workflow or execution references another resource indirectly, inspect the related metadata tables before assuming names.

### Supabase Or PostgREST-Style Apps
- Treat these as Postgres unless the app is clearly using a view, RPC, or storage abstraction.
- If the app references RPC names, views, or generated API names, resolve them through schema inspection before querying data.

### Other Abstractions
- If the app talks to an external API instead of a database, do not force DBHub use.
- If the app uses an ORM or service layer, read the app code to identify the real database objects before querying.

### Known Mappings
- `malaria-tracker`
- App config: `NEXT_PUBLIC_NOCODB_TABLE_ID=mswvdl0pvm4s6fd`
- NocoDB model: `MalariaTracker`
- Physical table: `"pr0oyxhwfn9aapx"."MalariaTracker"`
- Query via DBHub against the `nocodb` database.
