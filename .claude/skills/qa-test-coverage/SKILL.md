---
name: qa-test-coverage
description: Test coverage review for missing tests and edge cases. Adds findings to SUGGESTIONS.md.
---

# Test Coverage QA Skill

Review test coverage and identify missing tests. Add findings to SUGGESTIONS.md.

## Scope

This skill focuses on **test coverage concerns only**:
- Missing unit tests
- Missing integration tests
- Untested edge cases
- Flaky tests
- Test organization

## Workflow

### Step 0: Review Existing Findings

**Before starting any review, read `SUGGESTIONS.md`** to understand what has already been discovered:

```bash
# Read the Test Coverage section of SUGGESTIONS.md
```

Focus on:
- **Active items** - Don't duplicate these
- **Struck-through items (`~~item~~`)** - Already fixed, don't re-report
- **Gaps** - What test coverage concerns HAVEN'T been checked yet?

This prevents wasting time re-discovering known issues and helps you focus on finding NEW problems.

### Step 1: Run Test Coverage Report

```bash
cd backend && uv run pytest --cov=app --cov-report=term-missing
cd frontend && npm run test -- --coverage
```

Note files with low coverage (<80%).

### Step 2: Review Backend Test Coverage

For each service/router, check:

| Module | Tests Should Cover |
|--------|-------------------|
| **Routers** | Happy path, validation errors, auth errors, edge cases |
| **Services** | Business logic, error handling, edge cases |
| **Database** | Model constraints, relationships |

Files to check:
- `backend/tests/test_*.py`
- Compare against `backend/app/routers/` and `backend/app/services/`

### Step 3: Identify Missing Backend Tests

Look for:
- Endpoints without test files
- Service functions not tested
- Error paths not covered
- Edge cases:
  - Empty inputs
  - Large inputs
  - Null/None values
  - Concurrent access
  - Invalid foreign keys

### Step 4: Review Frontend Test Coverage

For each route/component, check:

| Module | Tests Should Cover |
|--------|-------------------|
| **Routes** | Rendering, API calls, user interactions |
| **Components** | Props, events, slots |
| **Stores** | State mutations, async actions |
| **API** | Request format, response handling, errors |

Files to check:
- `frontend/tests/*.test.ts`
- Compare against `frontend/src/routes/` and `frontend/src/lib/`

### Step 5: Identify Missing Frontend Tests

Look for:
- Pages without test files
- Components without tests
- Stores without tests
- Missing test cases:
  - Loading states
  - Error states
  - Empty states
  - Form validation
  - User interactions

### Step 6: Check Edge Case Coverage

Common untested scenarios:

**Backend:**
- User with no settings configured
- Empty database tables
- Invalid/expired JWT tokens
- External API timeouts
- Database connection failures

**Frontend:**
- Slow network responses
- API returns unexpected shape
- User spam-clicks button
- Browser back/forward navigation
- Page refresh during operation

### Step 7: Review Test Quality

Look for:
- Tests that don't assert anything meaningful
- Tests that test implementation, not behavior
- Flaky tests (timing-dependent)
- Tests with hardcoded dates that will break
- Missing cleanup/teardown

### Step 8: Update SUGGESTIONS.md

Add findings to a **Test Coverage** section:

```markdown
## Test Coverage

- [P2] No tests for DELETE /api/content/movie/{tmdb_id} endpoint
- [P2] Settings page missing unit tests for form validation
- [P3] Add edge case test for sync when Jellyfin API is down
```

Priority guide:
- **[P1]** - Critical path untested
- **[P2]** - Important feature untested
- **[P3]** - Edge case or polish

## What NOT to Do

- Do NOT write tests (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md (check both active AND struck-through `~~items~~`)
- Do NOT check non-testing concerns
- Do NOT modify any code
- Do NOT add positive observations (e.g., "good implementation", "works correctly", "no issues found") - SUGGESTIONS.md tracks only items that need improvement

## Example Findings

```markdown
## Test Coverage

### Backend
- [P2] `services/content.py::delete_movie()` has no tests - critical deletion logic
- [P2] No test for expired JWT token handling in auth middleware
- [P3] Add test for sync behavior when CachedMediaItem already exists

### Frontend
- [P2] `/settings` page has no unit tests - form validation untested
- [P2] WhitelistModal component not tested for keyboard interactions
- [P3] Add test for dashboard when all issue counts are zero

### Edge Cases
- [P2] No test for what happens when user deletes their only whitelist item
- [P3] Test sync behavior when Jellyfin returns 500 error

### Test Quality
- [P3] `test_auth.py::test_login` uses hardcoded "2024" - will break next year
- [P3] Flaky: `test_sync.py::test_concurrent_sync` fails intermittently
```
