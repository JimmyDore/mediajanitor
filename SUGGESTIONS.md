# Suggestions & Observations

Items spotted during development. Mark with: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

---

## Security

- ~~[P2] Default SECRET_KEY in config.py is insecure - should validate/warn if using default in production~~
- ~~[P2] User registration (`/api/auth/register`) lacks password strength validation - only checks min_length=8, but `UserCreate` should use the same `validate_password_strength` validator as password reset/change (requires uppercase, lowercase, digit)~~
- [P2] Encryption key derivation in `services/encryption.py:17` is weak - uses simple padding `(key_bytes * 2)[:32]` rather than a proper KDF like PBKDF2 or scrypt. Short secret keys produce predictable Fernet keys.
- [P2] Password reset token lookup in `routers/auth.py:514-530` iterates all unexpired tokens doing bcrypt comparisons - potential timing attack vector and performance issue with many users. Consider indexing by user_id first or using a different lookup strategy.
- [P3] Add CSRF protection for state-changing operations
- [P3] Consider adding Content-Security-Policy headers to mitigate XSS
- [P3] SSRF mitigation: Server-side requests to user-provided URLs (Jellyfin/Jellyseerr/Radarr/Sonarr/Ultra) have HttpUrl validation but no blocklist for private IP ranges (127.0.0.1, 192.168.x.x, 10.x.x.x, etc.) - could probe internal network
- [P3] Rate limiter uses in-memory storage - bypassed when backend restarts and doesn't work across multiple backend instances (would need Redis-backed rate limiting for production scaling)
- [P3] Missing security headers - no X-Content-Type-Options, X-Frame-Options, or Strict-Transport-Security headers configured in FastAPI middleware
- [P3] `datetime.utcnow()` used in password reset code (`routers/auth.py:468,517`) is deprecated in Python 3.12+ - should use `datetime.now(UTC)` for consistency

## UI/UX

### Navigation & Routing

- ~~[P2] Mobile hamburger menu doesn't appear to toggle sidebar open on click - navigation broken on mobile.~~

### Mobile Responsiveness

- ~~[P2] Issues page "Unavailable" tab truncated to "Unavail" on mobile - tabs should abbreviate better or wrap.~~

### Form Validation

- [P2] Login form shows no validation errors when submitted empty or with invalid email - form just clears silently.
- [P2] Login form with invalid credentials gives no user feedback - no error toast or inline error message visible.

### Settings Page

- ~~[P2] Connection inline editing is jarring - form expands and pushes content down. Consider modal/drawer or animated expand.~~
- ~~[P2] "Thresholds" help text ("Used by: Old tab") assumes users know app structure. Use more descriptive text like "Used to identify content for deletion".~~
- [P3] Nickname table arrow column is decorative clutter - remove it, use visual proximity.
- [P3] Connection status dots (8px green) are too subtle - add "Connected" text label or badge.
- [P3] Theme selector has icons + text making it wide/busy - use icons-only with tooltips or text-only.
- [P3] Dark mode contrast issues: Edit buttons and input borders blend in slightly.
- [P3] Nickname action icons (edit/delete) have small touch targets - increase to 32px.

### Toast Notifications

- [P2] Inconsistent toast implementations: some pages use local `toast` state, others use global `toasts` store. Standardize on global store for consistency.

## Accessibility

### Focus Management

- [P1] User dropdown in Header.svelte (line 75) and Sidebar.svelte (line 161) doesn't trap focus - Tab escapes to background. The `svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions` comments indicate known issues being ignored.
- [P2] Global focus styles missing - app.css has no `:focus` or `:focus-visible` styles defined. Input fields only change `border-color` on focus without visible outline. Links and buttons have no visible focus indicator.
- [P2] Mobile backdrop overlay in Sidebar.svelte (line 52) doesn't trap keyboard focus - user can Tab to elements behind the overlay.

### Keyboard Navigation

- ~~[P2] User dropdown menus (Header.svelte:73-89, Sidebar.svelte:159-171) not keyboard accessible - can't navigate with arrow keys, no roving tabindex, no Escape key handler to close.~~
- [P2] Whitelist page tab buttons (whitelist/+page.svelte:237-247) are `<button>` elements which is correct, but missing `role="tablist"` on container and `role="tab"` on buttons.
- [P3] Landing page feature cards are not keyboard focusable - they animate on hover but provide no keyboard interaction alternative.

### Screen Reader Support

- ~~[P2] SVG icons throughout the app lack accessibility attributes - icons in Sidebar.svelte nav items (lines 72-139) have no `aria-hidden="true"` and adjacent text creates duplicate announcements.~~
- ~~[P2] Logo SVG icon in login/register pages (login/+page.svelte:67-71, register/+page.svelte:122-126) lacks `aria-hidden="true"` - screen readers announce raw path data.~~
- ~~[P2] Status dots in connections page (settings/connections/+page.svelte:416-418, 492-494) only have `title` attribute for sighted users - add `aria-label` or visually-hidden text for screen readers.~~
- ~~[P2] Loading spinners in multiple components (whitelist/+page.svelte:253, dashboard +page.svelte:491, settings/connections/+page.svelte:407) have `aria-hidden="true"` on the visual element but parent containers don't always have `role="status"` or `aria-live` for announcement.~~

### Color Contrast

- ~~[P2] `--text-muted` (gray-500: #64748b) in dark mode on gray-900 (#0f172a) background has approximately 4.1:1 contrast - borderline failing WCAG AA.~~

### Semantic HTML

- ~~[P2] Dashboard stats in +page.svelte (lines 660-685) are interactive `<button>` elements styled as cards - correct for interactivity, but missing `aria-describedby` linking to the meta info below.~~
- ~~[P2] Whitelist page tabs (whitelist/+page.svelte:234-248) should use `<nav role="tablist">` and `role="tab"` on buttons for proper tab pattern semantics.~~

## Architecture

### God Objects / Large Files



- [P3] `services/sync.py` is 1697 lines - handles Jellyfin media fetch, Jellyseerr requests fetch, user aggregation, language checking, season size calculation, caching, and status updates. Could extract:
  - `services/jellyfin_sync.py` - Jellyfin-specific fetch and aggregation logic
  - `services/jellyseerr_sync.py` - Jellyseerr request fetching and title enrichment
  - `services/sync_language.py` - Language checking for movies and series episodes

### Code Duplication



- [P3] Database models for whitelists (ContentWhitelist, FrenchOnlyWhitelist, LanguageExemptWhitelist, LargeContentWhitelist) at `database.py:165-227` are identical except table name. Could use SQLAlchemy mixins or table inheritance to reduce duplication

- [P3] Toast notification handling duplicated across pages - `issues/+page.svelte`, `whitelist/+page.svelte`, and settings pages each implement local `showToast()`, `closeToast()`, `toast` state. Should use global `toasts` store from `lib/stores/index.ts`

### Layer Separation


- [P3] `routers/whitelist.py:361-392` contains TMDB fallback title lookup logic for requests whitelist - this should be in the content service, not the router

### Missing Abstractions

- [P3] No API client abstraction in frontend - each page directly calls `authenticatedFetch()` with inline URL construction. Consider `lib/api/` folder with typed functions like `api.content.getIssues(filter)`, `api.whitelist.add(type, item)`

- [P3] External API clients (Jellyfin, Jellyseerr, Radarr, Sonarr) don't share common patterns. Consider extracting `BaseApiClient` class with:
  - Connection validation with retry
  - Common header handling
  - Error response normalization

### Technical Debt

- [P3] Consider extracting sync status display into reusable component for dashboard

## Performance

### Database Queries




- [P3] `_delete_cached_media_by_tmdb_id()` in `routers/content.py:200-236` fetches ALL user media items then filters in Python to match TMDB ID. SQLite JSON queries are limited, but could use JSON_EXTRACT for this specific lookup: `WHERE JSON_EXTRACT(raw_data, '$.ProviderIds.Tmdb') = ?`

### Sync Performance


- [P3] `fetch_jellyseerr_requests()` in `services/sync.py:654-783` makes individual API calls for each unique media item (English title + French title). Could batch these or use concurrent requests with `asyncio.gather()` with rate limiting.

### Missing Indexes

- [P3] Add composite index on `CachedMediaItem(user_id, media_type)` - queries in `get_content_issues()` and `get_library()` filter by both columns
- [P3] Add composite index on `CachedMediaItem(user_id, played)` - frequently filtered together in old/unwatched queries
- [P3] Add index on `CachedJellyseerrRequest(user_id, status)` - filtered together in unavailable requests queries

### Frontend

- [P3] Library page (`library/+page.svelte`) fetches full library on each filter change via `fetchLibrary()`. Consider client-side filtering for already-loaded data, or implement server-side pagination with smaller page sizes.


### Caching Opportunities

- [P3] `get_sonarr_tmdb_to_slug_map()` is called separately from `get_content_issues()` and `get_library()` endpoints. The Sonarr series list rarely changes - could cache for 5-10 minutes in memory or database.

- [P3] `get_user_thresholds()` queries `UserSettings` on every content analysis call. Settings rarely change - could cache per-request or use a short TTL.

## Database

- [P3] Add database indexes on CachedMediaItem for common queries (media_type, played, size_bytes)

## API Contracts

### Type Definitions & Frontend/Backend Alignment

- [P2] `frontend/src/lib/types.ts` contains stale interfaces (`OldUnwatchedResponse`, `ContentItem`, `LargeMoviesResponse`, etc.) that don't match current backend Pydantic models. Frontend pages define their own inline TypeScript interfaces instead (e.g., `issues/+page.svelte:10-50`). Should consolidate to shared type definitions or generate from OpenAPI schema.

- [P3] Inconsistent `media_type` values across APIs: Jellyfin uses "Movie"/"Series" (PascalCase), Jellyseerr uses "movie"/"tv" (lowercase). Frontend handles both (`isMovieItem()` in issues page), but type definitions should use union types like `"movie" | "Movie" | "tv" | "Series"` for clarity.

- [P3] `frontend/src/lib/types.ts:60-68` `ProblematicEpisode` interface has extra fields (`availableLanguages`, `hasFrenchSubs`) that don't exist in backend `ProblematicEpisode` model at `backend/app/models/content.py:132-139`. These fields are unused - the inline interface at `issues/+page.svelte:10-16` is the correct version matching the backend.

- [P3] `SyncResponse` backend model at `sync.py:22` has fields `media_items_synced` and `requests_synced`, but frontend `SyncResponse` interface at `+page.svelte:28-34` marks these as optional. When `status: "sync_started"`, backend returns `media_items_synced=0, requests_synced=0`, not omitting them - types are aligned but could be clearer.

### Error Handling Patterns

- [P2] Error response format inconsistent: Some endpoints return `{"detail": "error message"}` (FastAPI HTTPException), others return model-specific errors. Frontend handles both patterns but should standardize on `{"detail": string}` everywhere.

- [P3] Frontend doesn't always parse error body: In several places (e.g., `settings/connections/+page.svelte:191-193`), errors are caught via `throw new Error(data.detail || 'Failed to save settings')` which is good, but other places just show generic messages like `'Sync failed'` without extracting detail from response.

- [P3] `/api/sync` can return 409 status code if sync is already in progress but frontend only checks for 429 (rate limit). The `is_syncing` check in `sync_status` handles this at polling level, but direct 409 handling is missing.

### Missing Type Exports

- [P3] Backend Pydantic models at `backend/app/models/content.py` and `backend/app/models/settings.py` could be used to generate TypeScript types via OpenAPI/swagger export, eliminating manual interface duplication in frontend.

### Undocumented Query Parameters

- [P3] `/api/library` endpoint accepts undocumented query params: `type`, `search`, `watched`, `min_year`, `max_year`, `min_size_gb`, `max_size_gb`, `sort`, `order`. These work correctly but aren't documented in Pydantic Query descriptions.


## Test Coverage

Overall backend coverage: **71%** (1018 statements missed out of 3454)

### Backend - Low Coverage Files








- [P3] `app/routers/whitelist.py`: 58% coverage - Whitelist POST/DELETE endpoints (lines 68-74, 97-103, etc.) have missing coverage for error paths (409 conflict, 404 not found)

- [P3] `app/services/content.py`: 56% coverage - Large file with complex business logic; many edge cases untested in functions like `get_content_issues()`, `get_unavailable_requests()`

### Backend - Test Quality Issues

- [P2] `datetime.utcnow()` deprecation warnings in `test_password_reset.py` (15+ locations) and `app/routers/auth.py` (lines 468, 517) - should use `datetime.now(UTC)` for Python 3.12+ compatibility

- [P3] Flaky test: `test_integration.py::TestIntegrationDisplaySettings::test_save_recently_available_days` fails intermittently (failed in last run)

### Frontend - Test Coverage Gaps

All major pages have test files, but some component-level tests may be missing:

- [P3] `/info/recent` page - has `info.test.ts` but verify recently-available content filtering is tested
- [P3] Whitelist page - verify keyboard navigation in whitelist modals is tested (similar to issues modal tests)

### Edge Cases Not Tested

**Backend:**
- [P2] External API timeout scenarios (Jellyfin/Jellyseerr/Radarr/Sonarr) - httpx timeouts are caught but not explicitly tested
- [P2] Database connection failures during sync operations
- [P3] User with no settings configured attempting sync
- [P3] Empty cache tables when fetching content issues
- [P3] Concurrent whitelist modifications (race conditions)

**Frontend:**
- [P3] API returning unexpected data shapes (missing fields)
- [P3] Page refresh during delete operations
- [P3] Browser back/forward during multi-step workflows

## Documentation

### CLAUDE.md

- [P2] "Current Status" section is stale - says "Phase: Epic 7" and "Next US: US-7.1.5" but prd.json shows US-48 through US-52 stories are now passing. Current phase appears to be Epic 52+.
- [P3] `.env.example` documented in CLAUDE.md doesn't match actual file - docs say `REDIS_URL` is commented/unused but docker-compose.yml actively uses `REDIS_URL=redis://redis:6379/0` for Celery.
- [P3] "Completed: US-0.1 through US-2.3, US-7.1 (11 stories)" is outdated - many more stories have been completed.

### README.md

- [P3] README doesn't mention Celery/Redis as part of the stack, but docker-compose.yml includes `redis`, `celery-worker`, and `celery-beat` services. Users may be surprised by these background services.
- [P3] Configuration table lists only 2 env vars (`SECRET_KEY`, `DATABASE_URL`) but actual production setup uses many more (see `.env.example` comments: `SMTP2GO_API_KEY`, `SLACK_WEBHOOK_*`, `DISABLE_SIGNUPS`, etc.)

### Docstrings

- [P3] `services/sync.py` functions are mostly documented but some helper functions like `_fetch()` closures and `_get_` prefixed functions lack docstrings.

## Infrastructure

### Database Backups

- [P2] No documented restore procedure - if database corruption occurs, there's no documented recovery process.

### Docker Compose Configuration

- [P3] Frontend container has no health check - could silently fail without orchestration detection.

### Deployment Pipeline

- [P3] Docker prune runs on every deploy (`docker system prune -f --volumes`) - could accidentally delete named volumes if not careful. The `redis_data` volume is safe (named), but documentation should clarify this.

### Health Endpoints & Monitoring

- [P2] No `/ready` endpoint - Docker health check tests liveness, but Kubernetes/orchestrators need a separate readiness endpoint that checks DB + Redis are connected.
- [P2] No external uptime monitoring mentioned - no UptimeRobot, Pingdom, or similar service to alert on downtime.
- [P3] No error tracking service (Sentry, etc.) configured - application errors are only visible in Docker logs.
- [P3] Slack webhooks for sync failures exist but no general error alerting.

### Environment Variable Management

- [P3] `.env.example` missing `REDIS_URL` documentation - docker-compose.yml uses `REDIS_URL=redis://redis:6379/0` but it's not in `.env.example`. Developers may miss this when setting up locally.

### SSL/TLS

- [P3] No visible SSL configuration in repo - likely handled by nginx/certbot on VPS, but no documentation. Consider documenting certificate renewal process.

## Features (Future Scope)

- [P3] Google Sign Up - OAuth 2.0 flow with "Continue with Google" button
