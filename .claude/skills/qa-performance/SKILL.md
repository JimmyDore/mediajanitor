---
name: qa-performance
description: Performance-focused QA review for queries, bundle size, and caching. Adds findings to SUGGESTIONS.md.
---

# Performance QA Skill

Review the codebase for performance issues and add findings to SUGGESTIONS.md.

## Scope

This skill focuses on **performance concerns only**:
- Database queries (N+1, missing indexes)
- Frontend bundle size
- Caching strategies
- Unnecessary re-renders
- API response times

## Workflow

### Step 1: Database Query Analysis

Check for N+1 query patterns:

```python
# BAD - N+1 pattern
users = await db.execute(select(User))
for user in users:
    settings = await db.execute(select(UserSettings).where(...))  # N queries!

# GOOD - Eager loading
users = await db.execute(
    select(User).options(selectinload(User.settings))
)
```

Files to review:
- `backend/app/services/*.py` - All service functions
- `backend/app/routers/*.py` - Endpoint handlers

### Step 2: Check Database Indexes

Review queries and ensure indexes exist:

```python
# If you query by these columns frequently, they need indexes
select(CachedMediaItem).where(
    CachedMediaItem.user_id == user_id,
    CachedMediaItem.media_type == "movie",
    CachedMediaItem.played == False
)
```

Check `backend/app/database.py` for index definitions:
```python
__table_args__ = (
    Index('ix_cached_media_user_type', 'user_id', 'media_type'),
)
```

### Step 3: Frontend Bundle Analysis

Check for large dependencies:

```bash
cd frontend && npm run build
```

Look for:
- Large libraries that could be lazy-loaded
- Duplicate dependencies
- Unused imports

Common culprits:
- Chart libraries (lazy-load)
- Date libraries (use native or lightweight)
- Icon libraries (tree-shake or use SVG)

### Step 4: Check for Unnecessary Re-renders

In Svelte, look for:
- Reactive statements that run too often
- Large arrays/objects in `$state()` that change frequently
- Missing `{#key}` blocks for list updates

```svelte
<!-- BAD - entire list re-renders on any change -->
{#each items as item}
  <Item {item} />
{/each}

<!-- BETTER - keyed for efficient updates -->
{#each items as item (item.id)}
  <Item {item} />
{/each}
```

### Step 5: API Response Time Check

Look for slow endpoints:
- Endpoints that make multiple external API calls
- Endpoints without pagination
- Endpoints that return too much data

```python
# BAD - returns everything
@router.get("/items")
async def get_items():
    return await db.execute(select(Item))  # Could be 10,000 rows!

# GOOD - paginated
@router.get("/items")
async def get_items(skip: int = 0, limit: int = 100):
    return await db.execute(select(Item).offset(skip).limit(limit))
```

### Step 6: Caching Review

Check if expensive operations are cached:
- External API calls (Jellyfin, Jellyseerr)
- Computed aggregations
- Static configuration

```python
# Should cache external API responses
async def get_jellyfin_data():
    # Is this cached in DB or memory?
    # Or does it hit Jellyfin API every time?
```

### Step 7: Update SUGGESTIONS.md

Add findings to the **Performance** section:

```markdown
## Performance

- [P2] N+1 query in get_old_content() - loads whitelist per item
- [P2] Missing index on CachedMediaItem(user_id, media_type)
- [P3] Chart.js could be lazy-loaded - adds 200KB to bundle
```

Priority guide:
- **[P1]** - Causes timeouts or crashes
- **[P2]** - Noticeable slowness
- **[P3]** - Optimization opportunity

## What NOT to Do

- Do NOT implement fixes (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md (check both active AND struck-through `~~items~~`)
- Do NOT check non-performance concerns
- Do NOT modify any code
- Do NOT add positive observations (e.g., "good implementation", "works correctly", "no issues found") - SUGGESTIONS.md tracks only items that need improvement

## Example Findings

```markdown
## Performance

### Database
- [P2] `get_content_issues()` makes separate query for each whitelist type - combine into single query
- [P3] Add composite index on `CachedMediaItem(user_id, media_type, played)`

### Frontend
- [P3] Consider lazy-loading the charts library on dashboard
- [P3] Icon library imports entire set - switch to individual SVG imports

### API
- [P2] `/api/sync` endpoint has no timeout - external API delays cause worker exhaustion
- [P3] `/api/content/issues` returns full raw_data JSON - only return needed fields

### Caching
- [P2] Jellyseerr requests fetched on every page load - should use cached data
```
