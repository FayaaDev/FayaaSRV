# Step Reordering Plan

**Date:** 2026-04-27
**Change:** Rebase step numbers from `10,30,40,50,60,80,90` to `1,2,3,4,5,6,7`

## Mapping Table

| Module     | Old | New |
|------------|-----|-----|
| layout     | 10  | 1   |
| caddy      | 30  | 2   |
| cloudflare | 40  | 3   |
| postgres   | 50  | 4   |
| services   | 60  | 5   |
| cron       | 80  | 6   |
| verify     | 90  | 7   |

Note: `00-prereqs.md` is markdown-only (no Python module); it is not renumbered.

## Decisions

- `30-caddy.md` line 23 referenced "Step 70 for host services" which was never implemented. Cron (new Step 6) handles host services — that note is updated to reference Step 6.
- `step60-{svc_id}.log` log filenames are updated to `step5-{svc_id}.log`.

---

## Files to Update

### A. Python Source (9 files)

| File | Lines | Change |
|------|-------|--------|
| `src/rakkib/cli.py` | 128-136 | step labels `10,30,40,50,60,80,90` → `1,2,3,4,5,6,7` |
| `src/rakkib/cli.py` | 456 | `Step 60` → `Step 5` |
| `src/rakkib/steps/layout.py` | 1 | docstring `Step 10` → `Step 1` |
| `src/rakkib/steps/caddy.py` | 1 | docstring `Step 30` → `Step 2` |
| `src/rakkib/steps/cloudflare.py` | 1, 138, 145, 215 | `Step 40` → `Step 3` |
| `src/rakkib/steps/postgres.py` | 1, 62 | `Step 50` → `Step 4` |
| `src/rakkib/steps/services.py` | 1, 288 | `Step 60` → `Step 5` + log filename `step60-` → `step5-` |
| `src/rakkib/steps/cron.py` | 1 | docstring `Step 80` → `Step 6` |
| `src/rakkib/steps/verify.py` | 1 | docstring `Step 90` → `Step 7` |

### B. doctor.py (5 references)

| Line | Change |
|------|--------|
| 256 | `Step 00` stays (prereqs), `Step 40` → `Step 3` |
| 341 | `Step 40` → `Step 3` |
| 372 | `Step 40` → `Step 3` |
| 381 | `Step 40` → `Step 3` |
| 432 | `Step 40` → `Step 3` |

### C. Markdown Step Files — rename + update title + cross-refs

| Old Name | New Name | Changes |
|----------|----------|---------|
| `10-layout.md` | `1-layout.md` | title `Step 10` → `Step 1` |
| `30-caddy.md` | `2-caddy.md` | title `Step 30` → `Step 2`; line 23: `Step 60`→`Step 5`, `Step 70`→`Step 6` |
| `40-cloudflare.md` | `3-cloudflare.md` | title `Step 40` → `Step 3`; line 12: `Step 40` → `Step 3` |
| `50-postgres.md` | `4-postgres.md` | title `Step 50` → `Step 4` |
| `60-services.md` | `5-services.md` | title `Step 60` → `Step 5`; lines 30,40,110: `Step 50`→`Step 4`, `Step 60`→`Step 5` |
| `80-cron-jobs.md` | `6-cron-jobs.md` | title `Step 80` → `Step 6` |
| `90-verify.md` | `7-verify.md` | title `Step 90` → `Step 7` |
| `00-prereqs.md` | *(no rename)* | lines 23,33,39: `Step 40` → `Step 3` |

### D. Question Files (2 files)

| File | Lines | Change |
|------|-------|--------|
| `data/questions/04-cloudflare.md` | 55, 66, 67 | `Step 40` → `Step 3` |
| `data/questions/06-confirm.md` | 102-105 | `Step 40` → `Step 3` |

### E. Registry (1 file)

| File | Line | Change |
|------|------|--------|
| `data/registry.yaml` | 26 | `Step 40` → `Step 3` |

### F. Task List (1 file)

| File | Change |
|------|--------|
| `data/tasks/todo.md` | 12 step refs: `Step 30`→`2`, `Step 40`→`3`, `Step 50`→`4`, `Step 60`→`5` |

### G. Docs (6 files)

| File | Change |
|------|--------|
| `pyplan.md` | 13 refs: lines 25,29,63-69,91,95,134,135 |
| `pygaps.md` | 2 refs: `Step 40`→`3`, `Step 90`→`7` |
| `pyqr.md` | 2 refs: `Step 40`→`3` |
| `docs/3bugfixes.md` | 4 refs: `Step 60`→`5` |
| `docs/vergo-history/@` | 1 ref: `Step 90`→`7` |
| `docs/runbooks/restore-test.md` | 1 ref: `Step 90`→`7` |

### H. Tests (5 files)

| File | Change |
|------|--------|
| `tests/test_steps_layout.py` | docstring `Step 10` → `Step 1` |
| `tests/test_steps_caddy.py` | docstring `Step 30` → `Step 2` |
| `tests/test_steps_cloudflare.py` | docstring `Step 40` → `Step 3` |
| `tests/test_steps_postgres.py` | docstring `Step 50` → `Step 4` |
| `tests/test_e2e_verification.py` | 4 refs: `Step 60` → `Step 5` |

---

## Execution Order

1. Python step modules + `cli.py` + `doctor.py`
2. Test files
3. Question files + registry.yaml + todo.md
4. Markdown step files (rename + update)
5. Doc files
