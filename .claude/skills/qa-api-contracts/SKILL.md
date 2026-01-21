---
name: qa-api-contracts
description: API contract review for frontend/backend alignment and type consistency. Adds findings to SUGGESTIONS.md.
---

# API Contracts QA Skill

Review API contracts between frontend and backend for consistency. Add findings to SUGGESTIONS.md.

## Scope

This skill focuses on **API contract concerns only**:
- Request/response type alignment
- Missing error handling
- Inconsistent naming
- Undocumented endpoints
- Breaking changes

## Workflow

### Step 1: Inventory API Endpoints

List all backend endpoints:

```bash
grep -r "@router\." backend/app/routers/ | grep -E "(get|post|put|patch|delete)"
```

For each endpoint, note:
- HTTP method and path
- Request body schema (Pydantic model)
- Response schema
- Auth requirement

### Step 2: Inventory Frontend API Calls

Search for fetch calls:

```bash
grep -r "fetch(" frontend/src/ --include="*.svelte" --include="*.ts"
```

For each call, note:
- URL and method
- Request body structure
- Expected response handling

### Step 3: Compare Contracts

For each endpoint, verify:

| Check | Backend | Frontend |
|-------|---------|----------|
| **URL** | `/api/content/issues` | Same path? |
| **Method** | `GET` | Same method? |
| **Request body** | `{type: str, limit: int}` | Same fields? |
| **Response** | `{items: [...], total: int}` | Handles all fields? |
| **Errors** | `400, 401, 404, 500` | Handles all codes? |

### Step 4: Check Type Definitions

Compare Pydantic models to TypeScript interfaces:

**Backend (`backend/app/models/`):**
```python
class ContentIssueItem(BaseModel):
    jellyfin_id: str
    name: str
    media_type: str  # "movie" | "series"
    size_bytes: int | None
```

**Frontend (should have matching type):**
```typescript
interface ContentIssueItem {
    jellyfin_id: string;
    name: string;
    media_type: "movie" | "series";
    size_bytes: number | null;
}
```

Look for:
- Missing fields in frontend types
- Different field names (snake_case vs camelCase)
- Different nullability
- Missing union type options

### Step 5: Check Error Handling

For each API call in frontend:

```typescript
// Does it handle all error cases?
const response = await fetch('/api/...');
if (!response.ok) {
    // Does it check specific status codes?
    // Does it parse error body?
    // Does it show user-friendly message?
}
```

Common gaps:
- Only handles 200, ignores 201/204
- Doesn't parse error message from body
- Generic "Something went wrong" for all errors
- No handling for network failures

### Step 6: Check for Undocumented Behavior

Look for:
- Query parameters not in Pydantic model
- Response fields not in schema
- Side effects not documented
- Rate limits not communicated

### Step 7: Update SUGGESTIONS.md

Add findings to an **API Contracts** section:

```markdown
## API Contracts

- [P2] Frontend expects `size_bytes` but backend returns `size` for whitelist items
- [P2] DELETE /api/whitelist/{id} returns 204 but frontend expects JSON body
- [P3] Add TypeScript interfaces matching Pydantic models
```

Priority guide:
- **[P1]** - Causes runtime errors
- **[P2]** - Inconsistency that may cause bugs
- **[P3]** - Documentation/typing improvement

## What NOT to Do

- Do NOT implement fixes (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md
- Do NOT check non-contract concerns
- Do NOT modify any code

## Example Findings

```markdown
## API Contracts

### Type Mismatches
- [P2] `RecentlyAvailableItem.availability_date` is `str` in Python but frontend parses as `Date` - should be ISO format
- [P2] Frontend `ContentIssueItem` missing `raw_data` field that backend returns

### Error Handling
- [P2] `/api/sync` can return 409 (already syncing) but frontend doesn't handle it
- [P3] API errors should return consistent `{detail: string}` format

### Naming Inconsistency
- [P3] Backend uses `jellyfin_id`, some frontend code uses `jellyfinId` - standardize
- [P3] `media_type` values: backend allows any string, frontend assumes "movie" | "series"

### Missing Documentation
- [P3] `/api/content/issues` accepts undocumented `?type=` query parameter
- [P3] Add OpenAPI schema generation for frontend type generation
```
