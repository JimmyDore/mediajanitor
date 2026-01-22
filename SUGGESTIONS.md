# Suggestions & Observations

Items spotted during development. Mark with: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

---

## Security

- [P2] Authenticated users can access /login and /register pages - should redirect to dashboard
- [P2] Default SECRET_KEY in config.py is insecure - should validate/warn if using default in production
- [P2] User registration (`/api/auth/register`) lacks password strength validation - only checks min_length=8, but `UserCreate` should use the same `validate_password_strength` validator as password reset/change (requires uppercase, lowercase, digit)
- [P3] Add CSRF protection for state-changing operations
- [P3] Consider adding Content-Security-Policy headers to mitigate XSS
- [P3] SSRF mitigation: Server-side requests to user-provided URLs (Jellyfin/Jellyseerr/Radarr/Sonarr/Ultra) have HttpUrl validation but no blocklist for private IP ranges (127.0.0.1, 192.168.x.x, 10.x.x.x, etc.) - could probe internal network
- [P3] Rate limiter uses in-memory storage - bypassed when backend restarts and doesn't work across multiple backend instances (would need Redis-backed rate limiting for production scaling)

## UI/UX

### Settings Page

- [P2] Inconsistent save patterns: Connections need explicit Save, Theme auto-saves on click, Recent Days auto-saves on blur, Toggle auto-saves. Users can't predict behavior. Standardize to auto-save with toast feedback everywhere.
- [P2] Connection inline editing is jarring - form expands and pushes content down. Consider modal/drawer or animated expand.
- [P2] "Thresholds" help text ("Used by: Old tab") assumes users know app structure. Use more descriptive text like "Used to identify content for deletion".
- [P3] Nickname table arrow column is decorative clutter - remove it, use visual proximity.
- [P3] Connection status dots (8px green) are too subtle - add "Connected" text label or badge.
- [P3] Theme selector has icons + text making it wide/busy - use icons-only with tooltips or text-only.
- [P3] Dark mode contrast issues: Edit buttons and input borders blend in slightly.
- [P3] Nickname action icons (edit/delete) have small touch targets - increase to 32px.

### Toast Notifications

- [P2] Inconsistent toast implementations: some pages use local `toast` state, others use global `toasts` store. Standardize on global store for consistency.

## Accessibility

(No current items)

## Architecture

- [P3] Consider extracting sync status display into reusable component for dashboard

## Database

- [P3] Add database indexes on CachedMediaItem for common queries (media_type, played, size_bytes)

## API Contracts

### Type Definitions & Frontend/Backend Alignment

- [P2] `frontend/src/lib/types.ts` contains stale interfaces (`OldUnwatchedResponse`, `ContentItem`, `LargeMoviesResponse`, etc.) that don't match current backend Pydantic models. Frontend pages define their own inline TypeScript interfaces instead (e.g., `issues/+page.svelte:10-50`). Should consolidate to shared type definitions or generate from OpenAPI schema.

- [P3] Inconsistent `media_type` values across APIs: Jellyfin uses "Movie"/"Series" (PascalCase), Jellyseerr uses "movie"/"tv" (lowercase). Frontend handles both (`isMovieItem()` in issues page), but type definitions should use union types like `"movie" | "Movie" | "tv" | "Series"` for clarity.

- [P3] `SyncResponse` backend model at `sync.py:22` has fields `media_items_synced` and `requests_synced`, but frontend `SyncResponse` interface at `+page.svelte:28-34` marks these as optional. When `status: "sync_started"`, backend returns `media_items_synced=0, requests_synced=0`, not omitting them - types are aligned but could be clearer.

### Error Handling Patterns

- [P2] Error response format inconsistent: Some endpoints return `{"detail": "error message"}` (FastAPI HTTPException), others return model-specific errors. Frontend handles both patterns but should standardize on `{"detail": string}` everywhere.

- [P3] Frontend doesn't always parse error body: In several places (e.g., `settings/connections/+page.svelte:191-193`), errors are caught via `throw new Error(data.detail || 'Failed to save settings')` which is good, but other places just show generic messages like `'Sync failed'` without extracting detail from response.

- [P3] `/api/sync` can return 409 status code if sync is already in progress but frontend only checks for 429 (rate limit). The `is_syncing` check in `sync_status` handles this at polling level, but direct 409 handling is missing.

### Missing Type Exports

- [P3] Backend Pydantic models at `backend/app/models/content.py` and `backend/app/models/settings.py` could be used to generate TypeScript types via OpenAPI/swagger export, eliminating manual interface duplication in frontend.

### Undocumented Query Parameters

- [P3] `/api/library` endpoint accepts undocumented query params: `type`, `search`, `watched`, `min_year`, `max_year`, `min_size_gb`, `max_size_gb`, `sort`, `order`. These work correctly but aren't documented in Pydantic Query descriptions.

### Naming Consistency

- [P3] Backend uses `snake_case` for all field names (e.g., `jellyfin_id`, `media_type`). Frontend correctly maintains this in API responses. Good consistency - no issues found.

## Test Coverage

Overall backend coverage: **69%** (962 statements missed out of 3120)

### Backend - Low Coverage Files

- [P2] `app/routers/content.py`: 26% coverage - `/api/content/issues` endpoint (lines 102-161) and delete endpoints (lines 196-535) lack unit tests for:
  - Filter parameter handling (`filter=old|large|language|requests`)
  - Sonarr slug map building for TV show requests
  - Delete endpoint helper functions (`_get_user_settings`, `_lookup_jellyseerr_media_by_tmdb`, `_delete_cached_media_by_tmdb_id`)

- [P2] `app/services/jellyfin.py`: 42% coverage - Missing tests for:
  - `validate_jellyfin_connection()` success/failure paths
  - `save_jellyfin_settings()` create/update logic
  - `get_decrypted_jellyfin_api_key()` null handling

- [P2] `app/services/nicknames.py`: 36% coverage - Missing tests for:
  - `create_nickname()` duplicate detection
  - `get_nicknames()` ordering
  - `update_nickname()` and `delete_nickname()` not found cases

- [P2] `app/services/sonarr.py`: 43% coverage - Missing tests for:
  - `validate_sonarr_connection()` timeout handling
  - `save_sonarr_settings()` create vs update paths
  - `get_sonarr_series_by_tmdb_id()` API error handling
  - `get_sonarr_tmdb_to_slug_map()` empty response handling

- [P2] `app/services/radarr.py`: 54% coverage - Missing tests for:
  - `validate_radarr_connection()` network errors
  - `save_radarr_settings()` update existing settings

- [P3] `app/routers/whitelist.py`: 58% coverage - Whitelist POST/DELETE endpoints (lines 68-74, 97-103, etc.) have missing coverage for error paths (409 conflict, 404 not found)

- [P3] `app/services/content.py`: 53% coverage - Large file with complex business logic; many edge cases untested in functions like `get_content_issues()`, `get_unavailable_requests()`

### Backend - Test Quality Issues

- [P2] `datetime.utcnow()` deprecation warnings in `test_password_reset.py` (lines 594, 735, 782) - should use `datetime.now(UTC)` for Python 3.12+ compatibility

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

## Features (Future Scope)

- [P3] Google Sign Up - OAuth 2.0 flow with "Continue with Google" button
