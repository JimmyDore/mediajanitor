---
name: fix
description: Investigate and fix bugs from error messages, test failures, or bug descriptions. Use this skill when users report bugs, paste errors, describe unexpected behavior, or notice data discrepancies between the UI and external systems (Jellyseerr, Jellyfin, Radarr). Includes production database investigation via SSH and live API verification. Use whenever something "looks wrong" in the app, even without a stacktrace.
---

# Fix

## Overview

Systematically investigate and fix bugs in the codebase. Handles error messages, test failures, and bug descriptions. Automatically determines whether to fix directly or suggest based on context.

## Definition of Done

**A fix is NOT complete until ALL of these are true:**

1. Root cause identified and explained to user
2. Code change implemented
3. Existing tests pass
4. **Regression test added** (prevents bug from returning)
5. Fix verified (curl/browser/Docker as appropriate)

**The regression test is MANDATORY, not optional.** Without it, the same bug can reappear later.

## When to Use

Invoke with `/fix <description>` when:
- User pastes an error message or stacktrace
- User describes unexpected behavior
- A test is failing
- A bug is logged in prd.json
- User says something "looks wrong" in the UI (data mismatch, wrong status, etc.)
- User shares screenshots showing discrepancies between MediaJanitor and Jellyseerr/Jellyfin/Radarr

## Workflow

### Step 1: Understand the Bug

**Parse the input to extract:**
- Error type (TypeError, 500 error, assertion failure, etc.)
- Location hints (file names, line numbers, function names)
- Reproduction steps if provided

**If input is vague**, ask clarifying questions:
- What was the expected behavior?
- What actually happened?
- Can you provide steps to reproduce?

### Step 2: Reproduce

**Try to trigger the bug** before fixing. This confirms understanding and validates the fix later.

**For backend bugs:**
```bash
# Run specific test
cd backend && uv run pytest tests/test_<module>.py -v -k "<test_name>"

# Or curl the endpoint
curl -X POST http://localhost:8080/api/<endpoint> -H "Content-Type: application/json" -d '{...}'
```

**For frontend bugs:**
```bash
# Run specific test
cd frontend && npm run test -- --grep "<test_name>"

# Or check in browser
npm run dev  # Then manually test
```

**For Docker issues:**
```bash
docker-compose up --build -d
docker-compose logs backend --tail 50
docker-compose logs frontend --tail 50
```

### Step 3: Search Codebase

**Find related code:**
- Grep for error messages, function names, variable names
- Check recent commits that touched related files
- Look for similar patterns elsewhere in codebase

```bash
# Search for error message
rg "error message text" --type py

# Check recent changes to a file
git log -5 --oneline -- path/to/file.py
git diff HEAD~5 -- path/to/file.py
```

### Step 4: Check Logs

**Examine available logs:**

```bash
# Docker logs
docker-compose logs backend --tail 100 2>&1 | grep -i error

# Test output (re-run with verbose)
cd backend && uv run pytest tests/ -v --tb=long

# Frontend build errors
cd frontend && npm run check
```

### Step 4.5: Investigate Production Data (when bug is a data discrepancy)

When the bug is "X looks wrong in the UI" rather than a crash, the root cause is often a gap between what external APIs report and what our cached DB stores. Before hypothesizing, gather evidence from all layers.

See `references/prod-investigation.md` for the full cookbook of queries and patterns.

**The investigation flow:**

1. **Query the cached DB** — check what our app stored for the item in question
2. **Call the live external API** — compare what Jellyseerr/Jellyfin actually says right now
3. **Cross-reference** — spot the divergence between stored vs live data
4. **Trace the sync code** — find where in `sync.py` the transformation happens
5. **Trace the analysis code** — find where in `content_analysis.py` / `content_queries.py` the decision is made

The key tables to check:
- `cached_jellyseerr_requests` — synced from Jellyseerr, has `status` and `raw_data` (full API response)
- `cached_media_items` — synced from Jellyfin, has streams/sizes/dates
- `user_settings` — API keys (encrypted), server URLs
- `whitelists` — user whitelists that exclude items from issues

**Principle: always validate hypotheses against prod data before writing a fix.** Code-reading alone can mislead — a plausible-looking bug may not match real data patterns (e.g., "this affects all rows" vs "this only affects 4 of 568 rows").

### Step 5: Identify Root Cause

**Before fixing, articulate:**
1. What is the bug? (specific behavior)
2. Why does it happen? (root cause)
3. Where is the fix needed? (file:line)

**Write a brief summary** for the user explaining the root cause.

### Step 6: Fix

**Determine fix mode based on context:**

| Context | Mode | Action |
|---------|------|--------|
| Bug from prd.json | Auto-fix | Implement fix directly, update prd.json |
| User-reported bug | Suggest | Explain fix, ask for approval before applying |
| Critical/obvious bug | Auto-fix | Fix directly if clearly correct |
| Uncertain root cause | Suggest | Propose fix, explain uncertainty |

**Apply TDD when possible:**
1. Write a failing test that reproduces the bug
2. Implement the fix
3. Verify the test passes

### Step 7: Verify

**Confirm the fix works:**

```bash
# Run tests
cd backend && uv run pytest
cd frontend && npm run test

# Type checking
cd backend && uv run mypy app/
cd frontend && npm run check

# Docker verification (if backend changed)
docker-compose up --build -d
# Test the fixed endpoint
```

### Step 8: Add Regression Test

**If no test exists for this bug**, add one:
- Place in appropriate test file
- Name descriptively: `test_<function>_<bug_scenario>`
- Include comment referencing the bug if from an issue

## Example Session

**User:** `/fix the sync status endpoint returns 500 when no sync has ever run`

**Claude's process:**

1. **Understand**: 500 error on `/api/sync/status` when no prior sync exists
2. **Reproduce**: `curl http://localhost:8080/api/sync/status` → confirms 500
3. **Search**: Find sync status endpoint in `app/routers/sync.py`
4. **Check logs**: `docker-compose logs backend` shows `NoneType has no attribute 'last_sync'`
5. **Identify**: Root cause is accessing `.last_sync` on None when no SyncStatus record exists
6. **Fix**: Add null check, return default status when no record exists
7. **Verify**: Curl returns 200 with default values
8. **Test**: Add `test_sync_status_when_no_sync_exists` to tests

## Example Session (Data Discrepancy)

**User:** `/fix Mission Impossible shows as Unavailable but it's available everywhere (Jellyseerr, Jellyfin, Radarr)`

**Claude's process:**

1. **Understand**: Data discrepancy, not a crash. Item shows in wrong tab.
2. **Search**: Trace the data flow: `sync.py` caches requests → `content_analysis.py::is_unavailable_request()` decides availability → `content_queries.py` returns to frontend
3. **Investigate prod data**: SSH into VPS, query `cached_jellyseerr_requests` for the movie. Find `status=2` stored. Compare with `raw_data.media.status=5` (available).
4. **Call live API**: Hit Jellyseerr `/api/v1/request/314` from inside the container. Confirms `request.status=2, media.status=5` — Jellyseerr itself has this discrepancy.
5. **Distribution analysis**: Count how many rows have this pattern. Find 4/568 rows stuck — rare edge case, not systemic.
6. **Root cause**: Jellyseerr left `request.status` at APPROVED(2) because media was added outside Radarr. `media.status=5` is the source of truth (Jellyseerr's own UI uses it for the "Disponible" badge).
7. **Fix**: Add `media.status == 5` check in `is_unavailable_request()`, TDD-style.
8. **Test**: Regression test with the exact prod data shape.

## Resources

### references/

- `investigation-checklist.md` — printable checklist version of the investigation workflow
- `prod-investigation.md` — reusable patterns for querying prod DB and calling live APIs via SSH
