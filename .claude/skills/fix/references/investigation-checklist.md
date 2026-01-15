# Bug Investigation Checklist

Quick reference for systematic bug fixing.

## Pre-Investigation

- [ ] Read and understand the bug report/error
- [ ] Identify: error type, location hints, reproduction steps
- [ ] Ask clarifying questions if needed

## Investigation Steps

### 1. Reproduce
- [ ] Run the failing test or trigger the bug manually
- [ ] Confirm you can see the same error
- [ ] Note exact steps to reproduce

### 2. Search Codebase
- [ ] Grep for error message text
- [ ] Find the function/endpoint mentioned in stacktrace
- [ ] Check `git log` for recent changes to related files
- [ ] Look for similar patterns elsewhere

### 3. Check Logs
- [ ] Docker logs: `docker-compose logs <service> --tail 100`
- [ ] Test output: `uv run pytest -v --tb=long`
- [ ] Frontend checks: `npm run check`

### 4. Identify Root Cause
- [ ] What is the bug? (behavior)
- [ ] Why does it happen? (cause)
- [ ] Where is the fix needed? (file:line)

## Fix Process

### 5. Determine Mode
- [ ] prd.json bug → Auto-fix
- [ ] User-reported → Explain + suggest
- [ ] Critical/obvious → Auto-fix
- [ ] Uncertain → Suggest with caveats

### 6. Implement Fix
- [ ] Write failing test first (if possible)
- [ ] Apply minimal fix
- [ ] Verify test passes

### 7. Verify
- [ ] `uv run pytest` passes
- [ ] `npm run test` passes
- [ ] Type checks pass (`mypy`, `npm run check`)
- [ ] Docker works (if backend changed)

### 8. Regression Test
- [ ] Test exists for this bug scenario
- [ ] Test name is descriptive
- [ ] Test would catch regression

## Common Bug Patterns

| Symptom | Likely Cause | Fix Location |
|---------|--------------|--------------|
| 500 error | Unhandled None/null | Service layer |
| TypeError in Python | Missing null check | Service or model |
| 401 Unauthorized | Token expired or missing | Auth middleware |
| CORS error | Missing headers | CORS config |
| "no such column" | Missing migration | Alembic migration |
| Test passes, Docker fails | Sync/async mismatch | Session setup |
