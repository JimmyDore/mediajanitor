---
name: qa-architecture
description: Architecture review for code organization, patterns, and refactoring opportunities. Adds findings to SUGGESTIONS.md.
---

# Architecture QA Skill

Review the codebase architecture and add findings to SUGGESTIONS.md.

## Scope

This skill focuses on **architectural concerns only**:
- Code organization
- Design patterns
- Technical debt
- Refactoring opportunities
- Separation of concerns

## Workflow

### Step 0: Review Existing Findings

**Before starting any review, read `SUGGESTIONS.md`** to understand what has already been discovered:

```bash
# Read the Architecture section of SUGGESTIONS.md
```

Focus on:
- **Active items** - Don't duplicate these
- **Struck-through items (`~~item~~`)** - Already fixed, don't re-report
- **Gaps** - What architectural concerns HAVEN'T been checked yet?

This prevents wasting time re-discovering known issues and helps you focus on finding NEW problems.

### Step 1: Review Project Structure

Check if code is organized consistently:

```
backend/
├── app/
│   ├── routers/      # API endpoints (thin, delegate to services)
│   ├── services/     # Business logic
│   ├── models/       # Pydantic schemas
│   └── database.py   # SQLAlchemy models

frontend/
├── src/
│   ├── routes/       # Pages
│   ├── lib/
│   │   ├── components/  # Reusable UI components
│   │   ├── stores/      # Global state
│   │   └── api/         # API client functions
```

Look for:
- Business logic in routers (should be in services)
- Database queries in routers (should be in services)
- Duplicated code across files
- God files (too many responsibilities)

### Step 2: Check Layer Separation

**Backend layers:**

| Layer | Responsibility | Should NOT contain |
|-------|---------------|-------------------|
| Routers | HTTP handling, validation | Business logic, raw SQL |
| Services | Business logic | HTTP concerns, direct DB models |
| Models | Data schemas | Business logic |
| Database | ORM models | Business logic |

**Frontend layers:**

| Layer | Responsibility | Should NOT contain |
|-------|---------------|-------------------|
| Routes | Page composition | Complex logic, API calls |
| Components | Reusable UI | API calls, global state mutation |
| Stores | Global state | UI rendering logic |
| API | HTTP client | Business logic |

### Step 3: Identify Code Duplication

Search for patterns that appear multiple times:

```bash
# Look for similar function signatures
grep -r "async def get_" backend/app/services/
```

Common duplication:
- Similar CRUD operations across services
- Repeated error handling patterns
- Similar validation logic
- Copy-pasted API call patterns in frontend

### Step 4: Check for God Objects

Files that do too much:
- More than 500 lines
- Multiple unrelated responsibilities
- Used by every other module

Candidates:
- `backend/app/services/content.py` - Does it handle too many content types?
- `frontend/src/routes/issues/+page.svelte` - Should parts be extracted?

### Step 5: Review Design Patterns

Check for consistent patterns:

| Pattern | Usage |
|---------|-------|
| **Repository** | Database access abstracted? |
| **Service** | Business logic isolated? |
| **Factory** | Object creation centralized? |
| **Strategy** | Similar operations with variations? |

Look for opportunities:
- Repeated switch statements → Strategy pattern
- Complex object creation → Factory pattern
- Direct DB access in multiple places → Repository pattern

### Step 6: Technical Debt Assessment

Look for:
- TODO/FIXME/HACK comments
- Deprecated code still in use
- Unused imports/functions
- Inconsistent naming conventions
- Magic numbers/strings

```bash
grep -r "TODO\|FIXME\|HACK" backend/ frontend/src/
```

### Step 7: Dependency Analysis

Check for:
- Circular dependencies
- Tight coupling between modules
- Missing dependency injection

### Step 8: Update SUGGESTIONS.md

Add findings to the **Architecture** section:

```markdown
## Architecture

- [P2] content.py is 800+ lines - split into content_queries.py and content_service.py
- [P2] Whitelist logic duplicated across 5 services - extract base WhitelistService
- [P3] Consider repository pattern for database access
```

Priority guide:
- **[P1]** - Blocking future development
- **[P2]** - Growing technical debt
- **[P3]** - Improvement opportunity

## What NOT to Do

- Do NOT implement refactoring (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md (check both active AND struck-through `~~items~~`)
- Do NOT check non-architecture concerns
- Do NOT modify any code
- Do NOT add positive observations (e.g., "good implementation", "works correctly", "no issues found") - SUGGESTIONS.md tracks only items that need improvement

## Example Findings

```markdown
## Architecture

### Code Organization
- [P2] `issues/+page.svelte` is 2000+ lines - extract WhitelistModal, IssueFilters, IssueTable components
- [P3] API client functions scattered in routes - consolidate in `lib/api/`

### Layer Violations
- [P2] Router `content.py` contains business logic for calculating issue types - move to service
- [P3] Stores contain API call logic - extract to api layer

### Duplication
- [P2] Whitelist add/remove logic copied across 5 services - extract BaseWhitelistService
- [P3] Similar table components on Issues, Whitelist, Recently Available - extract DataTable component

### Technical Debt
- [P3] 12 TODO comments in codebase - review and create stories or remove
- [P3] `utils.py` has 3 unused functions - remove dead code

### Patterns
- [P3] Consider extracting JellyfinClient and JellyseerrClient classes for external API calls
```
