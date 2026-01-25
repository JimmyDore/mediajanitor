# Media Janitor - Product Requirements Document

## Vision

A SaaS web application that helps media server owners manage their Plex/Jellyfin libraries. Users sign up, connect their Jellyfin/Jellyseerr instances, and get actionable insights about content to clean up, language issues, and pending requests.

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: SvelteKit + TypeScript
- **Database**: PostgreSQL (production) / SQLite (dev)
- **Background Tasks**: Celery or FastAPI BackgroundTasks
- **Deployment**: Docker + GitHub Actions + VPS
- **Auth**: JWT-based authentication

## Architecture Decisions

- **Background data fetching**: Jellyfin/Jellyseerr APIs are slow. Data is fetched daily via background tasks and cached in DB. Users can trigger manual refresh.
- **Multi-tenant SaaS**: Each user has their own API keys, whitelists, and data, completely isolated from others. **All database tables storing user data MUST have a `user_id` foreign key.** This includes:
  - Cached media items (movies, series)
  - Cached Jellyseerr requests
  - All whitelist tables
  - User settings and preferences
- **Full-stack user stories**: Each story delivers end-to-end value (API + UI).
- **Read-only v1**: Dashboard displays insights; users take actions in Jellyfin/Sonarr/Radarr directly.

### Dashboard & Issues Architecture

Instead of one tab per feature (Old Content, Large Movies, Language Issues, etc.), the app uses a **unified dashboard + issues system**:

```
┌─────────────────────────────────────────────────────────────────┐
│                         DASHBOARD                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Old Content  │ │ Large Movies │ │   Language   │   ISSUES    │
│  │    221       │ │      18      │ │     34       │   (click    │
│  │   741 GB     │ │   312 GB     │ │              │    card)    │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐                                               │
│  │ Unavailable  │                                               │
│  │  Requests    │                                               │
│  └──────────────┘                                               │
│  ───────────────────────────────────────────────────────────    │
│  ┌──────────────┐                                               │
│  │  Recently    │   INFO (not problems)                         │
│  │  Available   │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Click card → Unified Issues View
┌─────────────────────────────────────────────────────────────────┐
│  Filters: [All] [Old] [Large] [Language] [Requests]             │
│  │ Name              │ Type  │ Size   │ Issues           │ Act  │
│  │ Spider-Man        │ Movie │ 12.4GB │ 🕐 Old 📦 Large  │ ... │
│  │ LOTR: Two Towers  │ Movie │ 11.3GB │ 🕐 Old 📦 Large  │ ... │
└─────────────────────────────────────────────────────────────────┘
```

**Feature categorization:**
- **ISSUES** (problems to resolve): Old Content, Large Movies, Language Problems, Unavailable Requests
- **INFO** (informational): Recently Available

**Navigation:** `Dashboard | Issues | Whitelist | Settings`

Content items can have **multiple issues** (e.g., both Old AND Large), shown as badges in the unified view.

---

## Completed Stories

All user stories have been implemented and archived.

See [ARCHIVED_PRD.md](./ARCHIVED_PRD.md) for the complete list of **209 completed user stories** across **52 epics**.

---

## Pending Stories

### Epic 53: Route Fixes

#### US-53.1: Add /dashboard route alias
**As a** user sharing or bookmarking URLs
**I want** `/dashboard` to work as a route
**So that** shared links and bookmarks don't break

**Background:**
The sidebar links to `/` for the dashboard, but users may expect `/dashboard` to work. The landing page mockup shows `mediajanitor.com/dashboard` in the browser URL bar, setting this expectation.

**Acceptance Criteria:**
- [ ] Navigating to `/dashboard` shows the dashboard content (same as `/`)
- [ ] Can be implemented as a redirect or a route alias
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: `/dashboard` loads the dashboard

#### US-53.2: Redirect authenticated users from login/register pages
**As an** authenticated user
**I want** to be redirected to the dashboard if I visit `/login` or `/register`
**So that** I don't see confusing login forms when already logged in

**Background:**
Currently, authenticated users can access `/login` and `/register` pages - the sidebar is visible showing they're authenticated, but the login form is still displayed.

**Acceptance Criteria:**
- [ ] Visiting `/login` while authenticated redirects to `/` (dashboard)
- [ ] Visiting `/register` while authenticated redirects to `/` (dashboard)
- [ ] Unauthenticated users can still access these pages normally
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: log in, then manually navigate to `/login` - should redirect

### Epic 55: Settings UX Improvements

#### US-55.1: Standardize settings auto-save behavior
**As a** user changing settings
**I want** consistent save behavior across all settings
**So that** I know when my changes are saved

**Background:**
Currently inconsistent: Connections need explicit Save button, Theme auto-saves on click, Recent Days auto-saves on blur, Toggles auto-save. Users can't predict behavior.

**Acceptance Criteria:**
- [ ] All settings auto-save on change (no explicit Save button needed)
- [ ] Toast notification confirms each successful save
- [ ] Error toast if save fails
- [ ] Loading indicator while saving (if > 200ms)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: change settings, see confirmation toasts

### Epic 56: Accessibility Improvements

#### US-56.1: Improve placeholder text contrast
**As a** user with vision impairments
**I want** placeholder text to have sufficient contrast
**So that** I can read input placeholders

**Background:**
Placeholder text uses `--text-muted` (gray-400: #94a3b8 in light mode) on white background - contrast ratio is approximately 3.1:1, below WCAG AA 4.5:1 requirement for normal text.

**Acceptance Criteria:**
- [ ] Placeholder text meets WCAG AA contrast ratio (4.5:1)
- [ ] Update `--text-muted` or use a separate placeholder color variable
- [ ] Both light and dark mode meet contrast requirements
- [ ] Typecheck passes
- [ ] Unit tests pass

#### US-56.2: Use semantic HTML on landing page
**As a** screen reader user
**I want** the landing page to use semantic elements
**So that** I can navigate by landmarks

**Background:**
Landing page (Landing.svelte) uses generic `<div class="feature-card">` instead of semantic `<article>` elements - impacts screen reader navigation.

**Acceptance Criteria:**
- [ ] Feature cards use `<article>` elements
- [ ] Main sections use appropriate landmarks (`<main>`, `<section>`, `<nav>`)
- [ ] Headings follow proper hierarchy (h1 → h2 → h3)
- [ ] Typecheck passes
- [ ] Unit tests pass

### Epic 57: Backend Architecture Refactoring

#### US-57.1: Split content.py into focused modules
**As a** developer
**I want** smaller, focused service modules
**So that** the codebase is easier to maintain and test

**Background:**
`services/content.py` is 2474 lines containing 5+ whitelist types, content analysis, issue detection, and library queries. Split into focused modules.

**Acceptance Criteria:**
- [x] Create `services/whitelist.py` - All whitelist CRUD operations
- [x] Create `services/content_analysis.py` - is_old_or_unwatched, is_large_movie, has_language_issues
- [x] Create `services/content_queries.py` - get_content_summary, get_content_issues, get_library
- [x] `services/content.py` remains as thin facade with imports
- [x] All existing tests pass
- [x] No changes to API contracts
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Split into 3 focused modules: whitelist.py (558 lines), content_analysis.py (423 lines), content_queries.py (880 lines). content.py is now a thin facade (197 lines) re-exporting from these modules for backwards compatibility.

#### US-57.2: Extract generic whitelist service
**As a** developer
**I want** a reusable whitelist service pattern
**So that** whitelist CRUD isn't duplicated 5 times

**Background:**
5 nearly identical implementations for add/get/remove/get_ids across ContentWhitelist, FrenchOnlyWhitelist, LanguageExemptWhitelist, LargeContentWhitelist, JellyseerrRequestWhitelist.

**Acceptance Criteria:**
- [x] Create `BaseWhitelistService` generic class with whitelist model as type parameter
- [x] Refactor existing whitelist services to use base class
- [x] All existing tests pass
- [x] No changes to API contracts
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Created whitelist_base.py with two generic base classes: BaseJellyfinIdWhitelistService (for ContentWhitelist, FrenchOnly, LanguageExempt, Large) and BaseJellyseerrIdWhitelistService (for JellyseerrRequest). Refactored whitelist.py to use these classes. EpisodeLanguageExempt not refactored due to different field structure. All 657 tests pass, mypy clean.

#### US-57.3: Consolidate whitelist router endpoints
**As a** developer
**I want** DRY whitelist endpoints
**So that** adding new whitelist types is simple

**Background:**
`routers/whitelist.py` has identical GET/POST/DELETE patterns repeated for 6 whitelist types.

**Acceptance Criteria:**
- [x] Use endpoint factory pattern OR path parameter `/api/whitelist/{type}`
- [x] All 6 whitelist types work identically to before
- [x] All existing tests pass
- [x] OpenAPI schema documents all endpoints
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Used endpoint factory pattern (create_jellyfin_whitelist_routes) for 4 jellyfin-id-based whitelists. Requests and episode-exempt kept separate due to special logic. Reduced from 516 to 435 lines (~16% reduction). All 694 tests pass, mypy clean, all endpoints verified in Docker.

#### US-57.4: Move business logic from content router to services
**As a** developer
**I want** routers to only handle HTTP concerns
**So that** business logic is testable in isolation

**Background:**
`routers/content.py` contains `_delete_cached_media_by_tmdb_id()`, `_lookup_jellyseerr_media_by_tmdb()`, and service URL construction.

**Acceptance Criteria:**
- [x] Move `_delete_cached_media_by_tmdb_id()` to content service
- [x] Move `_lookup_jellyseerr_media_by_tmdb()` to content service
- [x] Move service URL construction to appropriate service
- [x] Router only contains HTTP handling code
- [x] All existing tests pass
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Created content_cache.py with 6 functions: get_user_settings, lookup_jellyseerr_media_by_tmdb, lookup_jellyseerr_media_by_request_id, delete_cached_media_by_tmdb_id, delete_cached_jellyseerr_request_by_tmdb_id, delete_cached_jellyseerr_request_by_id. Router reduced from 528 to 403 lines (~24% reduction). All 694 tests pass, mypy clean, integration tests pass.

### Epic 58: Frontend Architecture Refactoring

#### US-58.1: Extract Issues page components
**As a** developer
**I want** smaller, reusable components
**So that** the Issues page is maintainable

**Background:**
`issues/+page.svelte` is 2797 lines combining data fetching, filtering, sorting, search, 3 modals, row expansion, and whitelist actions.

**Acceptance Criteria:**
- [ ] Extract `DurationPickerModal.svelte` - reusable duration selection
- [ ] Extract `DeleteConfirmModal.svelte` - delete confirmation with checkboxes
- [ ] Extract `IssueRow.svelte` - single issue item with expand/collapse
- [ ] Extract `IssueFilters.svelte` - filter tabs, search, sub-filters
- [ ] Issues page uses extracted components
- [ ] All existing functionality preserved
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: all issue page features work

### Epic 59: Performance Optimizations

#### US-59.1: Parallelize content summary queries
**As a** user
**I want** the dashboard to load faster
**So that** I can quickly see my content summary

**Background:**
`get_content_summary()` makes 4 separate sequential whitelist queries. These are independent and can run in parallel.

**Acceptance Criteria:**
- [x] Use `asyncio.gather()` to parallelize whitelist queries
- [x] Dashboard summary loads faster (measure before/after)
- [x] All existing tests pass
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Parallelized 5 independent queries using asyncio.gather(): get_large_whitelist_ids, get_french_only_ids, get_language_exempt_ids, get_unavailable_requests_count, get_recently_available_count. All 696 tests pass, mypy clean, 37 integration tests pass.

#### US-59.2: Parallelize content issues queries
**As a** user
**I want** the Issues page to load faster
**So that** I can quickly see content issues

**Background:**
`get_content_issues()` makes 4 separate whitelist queries plus a Sonarr API call sequentially.

**Acceptance Criteria:**
- [x] Use `asyncio.gather()` to parallelize independent queries
- [x] Issues page loads faster (measure before/after)
- [x] All existing tests pass
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Parallelized 5 independent queries using asyncio.gather(): get_user_thresholds, _get_user_settings, get_french_only_ids, get_language_exempt_ids, get_large_whitelist_ids. Sonarr slug map fetch runs after (depends on user_settings). All 696 tests pass, mypy clean, 37 integration tests pass.

#### US-59.3: Add server-side pagination to library endpoint
**As a** user with large libraries
**I want** the Library page to load efficiently
**So that** it doesn't freeze with 1000+ items

**Background:**
`get_library()` fetches ALL items then filters in Python. Should push filtering to SQL and add pagination.

**Acceptance Criteria:**
- [ ] Library endpoint uses SQL WHERE clauses for filtering
- [ ] Add LIMIT/OFFSET pagination (default 50 items per page)
- [ ] Frontend handles pagination UI
- [ ] All existing tests pass
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: Library page loads efficiently with pagination

#### US-59.4: Optimize sync season size calculation
**As a** user running sync
**I want** faster sync times
**So that** I don't wait so long for data refresh

**Background:**
`calculate_season_sizes()` fetches episodes multiple times - once for size, then again per user for watch data. With 15 users and 100 series, this is ~8000 API calls.

**Acceptance Criteria:**
- [x] Fetch episode data once and reuse for size + watch calculations
- [x] Sync time reduced significantly (measure before/after)
- [x] All existing tests pass
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Optimized calculate_season_sizes() to: 1) Fetch seasons once (reused for size + language check), 2) Fetch episodes once per season (reused for size + language), 3) Batch user watch data fetches at series level (1 call per user per series instead of 1 call per user per season). Added fetch_series_episodes() for batched episode fetching and check_episodes_languages() for inline language checking. Reduces API calls from (2 + 2N + NU) to (1 + N + U) per series. All 697 tests pass, mypy clean, 37 integration tests pass.

### Epic 60: Test Coverage Improvements

#### US-60.1: Add content router tests
**As a** developer
**I want** comprehensive tests for content router
**So that** filter handling and delete operations are verified

**Background:**
`app/routers/content.py` has 26% coverage. Missing tests for filter parameter handling, Sonarr slug map building, delete helper functions.

**Acceptance Criteria:**
- [x] Tests for `/api/content/issues` with each filter type (old, large, language, requests)
- [x] Tests for Sonarr slug map building
- [x] Tests for `_delete_cached_media_by_tmdb_id()` helper
- [x] Tests for `_lookup_jellyseerr_media_by_tmdb()` helper
- [x] Coverage for content.py reaches 70%+
- [x] Typecheck passes
- [x] All tests pass

**Note:** Created tests/test_content_cache_service.py with 21 tests covering all content_cache.py functions: get_user_settings, lookup_jellyseerr_media_by_tmdb, lookup_jellyseerr_media_by_request_id, delete_cached_media_by_tmdb_id, delete_cached_jellyseerr_request_by_tmdb_id, delete_cached_jellyseerr_request_by_id. All 718 tests pass, mypy clean. content.py and content_cache.py have 100% coverage.

#### US-60.2: Add auth router tests
**As a** developer
**I want** comprehensive tests for auth router
**So that** notifications, IP parsing, and password flows are verified

**Background:**
`app/routers/auth.py` has 56% coverage. Missing tests for Slack notifications, IP parsing, signup disabled flow, password change.

**Acceptance Criteria:**
- [x] Tests for `send_signup_notification()` (mocked Slack)
- [x] Tests for `send_blocked_signup_notification()` (mocked Slack)
- [x] Tests for `_get_client_ip()` X-Forwarded-For parsing
- [x] Tests for signup disabled flow (403 response)
- [x] Tests for password change endpoint
- [x] Coverage for auth.py reaches 75%+
- [x] Typecheck passes
- [x] All tests pass

**Note:** Added TestGetClientIp class (6 tests) for _get_client_ip() X-Forwarded-For parsing: single IP, multiple IPs (picks first), whitespace handling, client.host fallback, unknown when client is None, precedence over client.host. Added TestChangePassword class (6 tests) for password change endpoint: success flow, wrong current password (400), requires authentication (401), weak new password (422), missing current_password (422), missing new_password (422). Existing tests already covered: send_signup_notification, send_blocked_signup_notification, signup disabled flow. All 86 auth tests pass, mypy clean.

#### US-60.3: Add jellyfin service tests
**As a** developer
**I want** comprehensive tests for jellyfin service
**So that** connection validation and settings are verified

**Background:**
`app/services/jellyfin.py` has 42% coverage. Missing tests for validate_connection, save_settings, decrypt_api_key.

**Acceptance Criteria:**
- [x] Tests for `validate_jellyfin_connection()` success path
- [x] Tests for `validate_jellyfin_connection()` failure path (timeout, invalid response)
- [x] Tests for `save_jellyfin_settings()` create new settings
- [x] Tests for `save_jellyfin_settings()` update existing settings
- [x] Tests for `get_decrypted_jellyfin_api_key()` null handling
- [x] Coverage for jellyfin.py reaches 75%+
- [x] Typecheck passes
- [x] All tests pass

**Note:** Created tests/test_jellyfin_service.py with 24 tests: TestValidateJellyfinConnection (11 tests: success, endpoint validation, API key header, trailing slash, 401/403/404/500 responses, timeout, connection error, DNS error), TestGetUserJellyfinSettings (3 tests), TestSaveJellyfinSettings (5 tests: create, update, trailing slash, encryption, user isolation), TestGetDecryptedJellyfinApiKey (5 tests: None key, decryption, empty string, special chars, unicode). Coverage: 100% for jellyfin.py. All 754 tests pass, mypy clean.

#### US-60.4: Add nicknames service tests
**As a** developer
**I want** comprehensive tests for nicknames service
**So that** CRUD operations are verified

**Background:**
`app/services/nicknames.py` has 36% coverage. Missing tests for all CRUD operations.

**Acceptance Criteria:**
- [x] Tests for `create_nickname()` success and duplicate detection
- [x] Tests for `get_nicknames()` ordering
- [x] Tests for `update_nickname()` success and not found case
- [x] Tests for `delete_nickname()` success and not found case
- [x] Coverage for nicknames.py reaches 80%+
- [x] Typecheck passes
- [x] All tests pass

**Note:** Created tests/test_nicknames_service.py with 17 tests covering all 4 functions: TestCreateNickname (4 tests: success, duplicate detection, user isolation, created_at set), TestGetNicknames (5 tests: empty list, alphabetical ordering, user isolation, all fields, ISO format), TestUpdateNickname (4 tests: success, not found, user isolation, field preservation), TestDeleteNickname (4 tests: success, not found, user isolation, only affects specified item). All 771 tests pass, mypy clean.

#### US-60.5: Add sonarr service tests
**As a** developer
**I want** comprehensive tests for sonarr service
**So that** connection and API handling are verified

**Background:**
`app/services/sonarr.py` has 43% coverage. Missing tests for validate_connection, save_settings, API error handling.

**Acceptance Criteria:**
- [x] Tests for `validate_sonarr_connection()` timeout handling
- [x] Tests for `save_sonarr_settings()` create vs update paths
- [x] Tests for `get_sonarr_series_by_tmdb_id()` API error handling
- [x] Tests for `get_sonarr_tmdb_to_slug_map()` empty response handling
- [x] Coverage for sonarr.py reaches 70%+
- [x] Typecheck passes
- [x] All tests pass

**Note:** Created tests/test_sonarr_service.py with 54 tests covering all 8 functions: TestValidateSonarrConnection (11 tests: success, endpoint, API key header, trailing slash, 401/403/404/500, timeout, connection error, DNS error), TestGetUserSonarrSettings (3 tests), TestSaveSonarrSettings (5 tests: create, update, trailing slash, encryption, user isolation), TestGetDecryptedSonarrApiKey (5 tests), TestGetSonarrSeriesByTmdbId (10 tests: match, not found, empty, non-200, timeout, connection error, endpoint, trailing slash, missing tmdbId, None id), TestGetSonarrTmdbToSlugMap (9 tests: success, empty, non-200, timeout, connection error, missing fields, empty slug, trailing slash), TestDeleteSonarrSeries (7 tests: success, URL, delete_files params, non-200, timeout, connection error), TestDeleteSeriesByTmdbId (4 tests: success, not found, delete fails, delete_files param). All 788 tests pass, mypy clean.

#### US-60.6: Add radarr service tests
**As a** developer
**I want** comprehensive tests for radarr service
**So that** connection and settings are verified

**Background:**
`app/services/radarr.py` has 54% coverage. Missing tests for validate_connection, save_settings update path.

**Acceptance Criteria:**
- [x] Tests for `validate_radarr_connection()` network errors
- [x] Tests for `save_radarr_settings()` update existing settings
- [x] Coverage for radarr.py reaches 75%+
- [x] Typecheck passes
- [x] All tests pass

**Note:** Created tests/test_radarr_service.py with 46 tests covering all 7 functions: TestValidateRadarrConnection (11 tests: success, endpoint, API key header, trailing slash, 401/403/404/500, timeout, connection error, DNS error), TestGetUserRadarrSettings (3 tests), TestSaveRadarrSettings (5 tests: create, update, trailing slash, encryption, user isolation), TestGetDecryptedRadarrApiKey (5 tests), TestGetRadarrMovieByTmdbId (9 tests: match, empty, non-200, timeout, connection error, endpoint, trailing slash, None id, multiple matches), TestDeleteRadarrMovie (8 tests), TestDeleteMovieByTmdbId (5 tests). All 834 tests pass, mypy clean.

#### US-60.7: Add tasks module tests
**As a** developer
**I want** comprehensive tests for background tasks
**So that** sync and notification handling are verified

**Background:**
`app/tasks.py` has 58% coverage. Missing tests for get_configured_user_ids, sync_failure_notification, exception handling.

**Acceptance Criteria:**
- [ ] Tests for `get_configured_user_ids()` database query
- [ ] Tests for `send_sync_failure_notification_for_celery()` error handling path
- [ ] Tests for `sync_user()` exception handling and notification
- [ ] Coverage for tasks.py reaches 75%+
- [ ] Typecheck passes
- [ ] All tests pass

### Epic 61: Documentation Updates

#### US-61.1: Fix CLAUDE.md port documentation
**As a** developer setting up the project
**I want** consistent port documentation
**So that** I can access the backend correctly

**Background:**
Backend port documented as `localhost:8000` in "Running the Project" section, but docker-compose maps to `8080:8000`. Curl examples correctly use `8080`.

**Acceptance Criteria:**
- [ ] Update "Running the Project" section to show `localhost:8080` for Docker
- [ ] Clarify that `localhost:8000` is for running backend directly (without Docker)
- [ ] All port references are consistent

#### US-61.2: Update CLAUDE.md skills list
**As a** developer using skills
**I want** accurate skills documentation
**So that** I can find available skills

**Background:**
Skills list is incomplete (missing 15 skills) and references non-existent `/original-script`. Project structure tree shows only 5 skills but there are 20.

**Acceptance Criteria:**
- [ ] List all 20 skills in the "Skills" section
- [ ] Remove reference to `/original-script`
- [ ] Update project structure tree to reflect actual skill count
- [ ] Group skills by category (QA, PRD management, etc.)

#### US-61.3: Fix README.md git clone URLs
**As a** developer cloning the repo
**I want** consistent git URLs
**So that** I can clone the repository

**Background:**
Quick Start has `jimmmydore/media-janitor` but Installation has `jimmy/media-janitor` - inconsistent usernames.

**Acceptance Criteria:**
- [ ] Both URLs use the correct GitHub username
- [ ] URLs are consistent across the README

### Epic 62: Infrastructure Improvements

#### US-62.1: Add Celery container health checks
**As an** operator
**I want** health checks on Celery containers
**So that** I know when background tasks are failing

**Background:**
Only backend and redis have health checks. Celery worker and celery-beat could silently fail without detection.

**Acceptance Criteria:**
- [ ] Add health check to celery-worker in docker-compose.yml
- [ ] Add health check to celery-beat in docker-compose.yml
- [ ] Health checks verify Celery is processing tasks
- [ ] Container restarts if health check fails

#### US-62.2: Add container resource limits
**As an** operator
**I want** memory limits on containers
**So that** a runaway process doesn't crash the VPS

**Background:**
No `deploy.resources.limits.memory` configured. A memory leak could consume all VPS memory.

**Acceptance Criteria:**
- [ ] Add memory limits to all containers in docker-compose.yml
- [ ] Backend: 512MB limit
- [ ] Celery worker: 512MB limit
- [ ] Frontend: 256MB limit
- [ ] Redis: 256MB limit
- [ ] Document recommended limits in CLAUDE.md

#### US-62.3: Configure log rotation
**As an** operator
**I want** automatic log rotation
**So that** logs don't fill the disk

**Background:**
No `logging.driver` options configured. Logs could grow indefinitely and fill disk.

**Acceptance Criteria:**
- [ ] Add logging config to docker-compose.yml for all containers
- [ ] Use json-file driver with max-size (10MB) and max-file (3)
- [ ] Verify logs rotate correctly

#### US-62.4: Add deployment rollback mechanism
**As an** operator
**I want** automatic rollback on failed deploys
**So that** failed builds don't leave the app down

**Background:**
deploy.yml does `docker-compose down` then `build --no-cache` and `up -d`. If build fails, no automatic rollback.

**Acceptance Criteria:**
- [ ] Tag current images before building new ones
- [ ] If new build fails, restore previous images
- [ ] Add health check after deployment
- [ ] If health check fails, rollback to previous version

#### US-62.5: Use proper health endpoint in deploy
**As an** operator
**I want** deploy to use the /health endpoint
**So that** health checks are meaningful

**Background:**
deploy.yml uses `/api/hello` but backend has proper `/health` endpoint.

**Acceptance Criteria:**
- [ ] Update deploy.yml to use `/health` endpoint
- [ ] Verify health check works during deployment

#### US-62.6: Implement rolling deployment
**As a** user
**I want** zero-downtime deployments
**So that** I can use the app during updates

**Background:**
`docker-compose down` takes all services offline before rebuild. Users experience downtime.

**Acceptance Criteria:**
- [ ] Use `docker-compose up -d --no-deps --build <service>` pattern
- [ ] Rebuild services one at a time
- [ ] Backend starts new container before stopping old
- [ ] Frontend starts new container before stopping old
- [ ] Document rolling deployment process

#### US-62.7: Enhance health endpoint with dependency checks
**As an** operator
**I want** the health endpoint to verify dependencies
**So that** I know all services are working

**Background:**
`/health` only returns `{"status": "healthy"}` without checking DB or Redis connectivity.

**Acceptance Criteria:**
- [ ] `/health` checks database connectivity
- [ ] `/health` checks Redis connectivity (if configured)
- [ ] Returns detailed status for each dependency
- [ ] Returns 503 if any dependency is down
- [ ] Typecheck passes
- [ ] Unit tests pass

### Epic 63: Episode-Level Recently Available

#### Overview

Enhance the "Recently Available" feature to show episode-level granularity using Sonarr's history API. Currently, the feature only shows series-level info ("Seasons 1-3 added") because Jellyseerr only provides episode `airDate` (broadcast date), not when content was actually downloaded. Sonarr's history API provides actual download timestamps per episode.

**Goals:**
- Show what specific episodes were added and when
- Smart grouping: full season added together → "Season 2", partial → "S2E5-E8"
- Graceful fallback when Sonarr not configured (current behavior)
- Movies unchanged (no Radarr integration)

**Architecture Decision:** Sonarr history is fetched during the **background sync**, not on-demand when viewing the page. This is consistent with how Jellyfin/Jellyseerr data is handled.

**Data flow:**
1. During sync: Fetch Sonarr history → Match by TMDB ID → Store in `CachedJellyseerrRequest.raw_data.sonarr_history`
2. On page view: Read from cached data → Apply smart grouping → Display

#### US-63.1: Fetch Sonarr history during sync
**As a** user with Sonarr configured
**I want** my sync to fetch episode download history from Sonarr
**So that** I can see when specific episodes were added

**Background:**
Sonarr's `GET /api/v3/history/since` returns download events with episode details and timestamps. Fetch history for the same window as "recently available" (default 7 days) and store with cached Jellyseerr requests.

**Acceptance Criteria:**
- [ ] Add `get_sonarr_history_since()` to `services/sonarr.py`
- [ ] Call Sonarr API: `GET /api/v3/history/since?date={cutoff}&eventType=downloadFolderImported&includeSeries=true&includeEpisode=true`
- [ ] Build map: `{tmdb_id: [{season, episode, title, added_at}, ...]}`
- [ ] During sync, if user has Sonarr configured, fetch history
- [ ] Store in `CachedJellyseerrRequest.raw_data` as `sonarr_history` key
- [ ] Gracefully skip if Sonarr not configured (no error)
- [ ] Gracefully handle Sonarr API failures (log warning, continue sync)
- [ ] Typecheck passes
- [ ] Unit tests pass

#### US-63.2: Smart episode grouping logic
**As a** user viewing Recently Available
**I want** episodes grouped intelligently
**So that** full season drops show as "Season 2" instead of listing every episode

**Background:**
When many episodes are added at once, grouping improves readability:
- All episodes of a season → "Season 2"
- Consecutive episodes → "S2E5-E8"
- Non-consecutive → "S2E3, S2E5, S2E7"
- Single episode → "S2E5"

**Acceptance Criteria:**
- [ ] Add `group_episodes_for_display()` to content service
- [ ] Input: list of episode additions for a series, total episodes per season
- [ ] If all episodes of a season added same day → "Season X"
- [ ] If consecutive episodes same day → "SXEY-EZ" format
- [ ] If non-consecutive → comma-separated list
- [ ] If single episode → "SXEY" format
- [ ] Returns structured data with: display_text, season, episode_numbers, is_full_season
- [ ] Typecheck passes
- [ ] Unit tests pass

#### US-63.3: Update Recently Available API response
**As a** frontend developer
**I want** the `/api/info/recent` endpoint to return episode-level data
**So that** I can display it in the UI

**Background:**
Add new field `episode_additions` to `RecentlyAvailableItem` for TV shows that have Sonarr history data.

**Acceptance Criteria:**
- [ ] Add `EpisodeAddition` model: added_date, display_text, season, episode_numbers, is_full_season
- [ ] Add `episode_additions: list[EpisodeAddition] | None` to `RecentlyAvailableItem`
- [ ] In `get_recently_available()`, check for `sonarr_history` in cached request's raw_data
- [ ] Apply smart grouping to generate `episode_additions` for TV shows
- [ ] Status 5 (fully available) shows: keep current `season_info` display (no episode granularity)
- [ ] Status 4 (partial) shows: include `episode_additions` if Sonarr data available
- [ ] If no Sonarr data: `episode_additions` is null (frontend uses fallback)
- [ ] Typecheck passes
- [ ] Unit tests pass

#### US-63.4: Display episode-level info in frontend
**As a** user viewing Recently Available
**I want** to see which episodes were added when
**So that** I know what new content is available

**Background:**
Update the Recently Available page to display episode-level information when available, falling back to current season-level display when not.

**Acceptance Criteria:**
- [ ] Add `EpisodeAddition` TypeScript interface
- [ ] Update `getDetails()` to use `episode_additions` when available
- [ ] Display format: "S2E5-E8" or "Season 2" (from display_text)
- [ ] If multiple addition dates, show most recent first
- [ ] One row per show (grouped), not per episode
- [ ] Fallback to current `season_info` display when `episode_additions` is null
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: TV shows with Sonarr data show episode-level details

#### Non-Goals
- Radarr integration for movies (movies keep current behavior)
- Real-time Sonarr API calls (data comes from sync)
- Episode-level data for status 5 (fully available) shows
- Individual rows per episode (one row per show, grouped)

#### Technical Considerations
- Sonarr API: `GET /api/v3/history/since` with `includeSeries=true&includeEpisode=true`
- Match series by TMDB ID (common key between Jellyseerr and Sonarr)
- Store in existing `raw_data` JSON field (no schema migration needed)
- Existing Sonarr integration in `services/sonarr.py` handles auth/connection

#### Verification Plan
1. **Unit tests**: `cd backend && uv run pytest -v`
2. **Frontend tests**: `cd frontend && npm run test`
3. **Integration test**:
   - Configure Sonarr credentials in settings
   - Trigger sync
   - Visit /info/recent
   - Verify TV shows display episode-level additions like "S2E5-E8"
4. **Fallback test**: User without Sonarr sees current behavior (no errors)
