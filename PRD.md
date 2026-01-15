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

## Epic 17: Bug Fixes

### Overview
Critical bug fixes that affect core functionality and data accuracy.

### User Stories

#### US-17.1: Multi-User Watch Data Aggregation
**As a** user
**I want** my watched content to reflect plays from ALL Jellyfin users
**So that** the Old/Unwatched content detection is accurate

**Problem:**
- Current sync only fetches watch data from the first Jellyfin user (`users[0]`)
- If User B watched a movie but User A didn't, it shows as "Never watched"
- Example: "La Chambre de Mariana" shows "Never" but was watched on 2025-09-14 by another user

**Acceptance Criteria:**
- [ ] Sync fetches media items from ALL Jellyfin users (not just first user)
- [ ] Watch data is aggregated: `played = True` if ANY user has watched
- [ ] `last_played_date` uses the MOST RECENT date across all users
- [ ] `play_count` sums all users' play counts
- [ ] Uses `asyncio.gather()` to parallelize user fetches (6-15 users expected)
- [ ] Progress logging shows which user is being synced (e.g., "Fetching user 3/10: John")
- [ ] Existing sync tests still pass
- [ ] New test verifies multi-user aggregation logic
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify "La Chambre de Mariana" shows correct watch date after sync

**Files:**
- `backend/app/services/sync.py` - Modify `fetch_jellyfin_media()` to loop through all users and aggregate
- `backend/tests/test_sync_service.py` - Add test for multi-user aggregation

---

#### US-17.2: Sync Progress Visibility
**As a** user
**I want** to see detailed sync progress in the UI
**So that** I know what's happening during the longer sync

**Acceptance Criteria:**
- [ ] Backend stores sync progress details (current step, current user being fetched)
- [ ] `GET /api/sync/status` returns progress info: `current_step`, `total_steps`, `current_user_name`
- [ ] Frontend displays progress during sync (e.g., "Fetching user 3/10: John...")
- [ ] Progress updates while sync is running (poll every 2-3 seconds)
- [ ] Shows "Syncing media..." or "Syncing requests..." as appropriate
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: trigger sync and see progress updates

**Files:**
- `backend/app/database.py` - Add progress fields to SyncStatus model (or use separate table)
- `backend/app/services/sync.py` - Update progress during sync steps
- `backend/app/routers/sync.py` - Return progress in status endpoint
- `frontend/src/routes/dashboard/+page.svelte` - Display progress during sync

### Non-Goals
- Storing per-user play data (only aggregated data needed)
- Displaying which user watched what (just aggregated status)
- WebSocket real-time updates (polling is sufficient for now)

### Technical Considerations
- **Original script reference:** `aggregate_all_user_data()` at line 1499 in `original_script.py`
- **Parallelization:** Use `asyncio.gather()` to fetch all users concurrently
- **Performance:** With 6-15 users, parallel fetches should complete in ~30-60 seconds vs 3-5 minutes sequential
- **Progress tracking:** Store in SyncStatus table with fields like `progress_step`, `progress_total`, `progress_message`

---

#### US-17.3: Fix Mobile Sidebar Visual Overlap
**As a** mobile user
**I want** the sidebar to be completely hidden when closed
**So that** I don't see visual artifacts on the dashboard

**Problem:**
A thin blue strip is visible on the left edge of the mobile dashboard when the sidebar is closed, suggesting the sidebar isn't fully off-screen.

**Acceptance Criteria:**
- [ ] On mobile (viewport < 768px), when sidebar is closed, no part of it is visible
- [ ] No blue strip or other visual artifacts on left edge
- [ ] Sidebar still opens/closes correctly with hamburger menu
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using mobile viewport (Chrome DevTools device mode)

**Files:**
- `frontend/src/lib/components/Sidebar.svelte` - Fix CSS transform/position values for mobile

---

## Epic 18: Onboarding Flow

### Overview
Guide new users through service configuration and first sync via an enhanced dashboard experience. After signup/login, users see a setup checklist that disappears once Jellyfin is configured and first sync completes.

### Goals
- Guide new users to configure Jellyfin immediately after signup
- Auto-trigger first sync once Jellyfin is configured
- Show clear progress through setup steps
- Disappear gracefully once onboarding is complete

### User Stories

#### US-18.1: Show Setup Checklist for New Users
**As a** new user who just signed up
**I want** to see a clear checklist of what to do next
**So that** I know how to get started with the app

**Acceptance Criteria:**
- [ ] Dashboard shows "Setup Checklist" card when Jellyfin not configured OR never synced
- [ ] Checklist shows 2 steps: "Connect Jellyfin" and "Run First Sync"
- [ ] Each step shows status: pending (gray), in-progress (blue), complete (green)
- [ ] "Connect Jellyfin" step has button linking to /settings
- [ ] Checklist hides when both steps are complete
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser

**Files:**
- `frontend/src/routes/+page.svelte` - Add SetupChecklist component
- `frontend/src/lib/components/SetupChecklist.svelte` - New component

---

#### US-18.2: Auto-Sync After Jellyfin Configuration
**As a** user who just configured Jellyfin
**I want** the first sync to start automatically
**So that** I don't have to figure out how to trigger it manually

**Acceptance Criteria:**
- [ ] When Jellyfin settings saved successfully AND user has never synced, trigger sync automatically
- [ ] Show "Syncing..." state in checklist with spinner
- [ ] On sync complete, show success message with item counts
- [ ] Handle sync errors gracefully with retry option
- [ ] First sync bypasses rate limit (or rate limit doesn't apply to first sync)
- [ ] Typecheck passes
- [ ] Unit tests pass

**Files:**
- `frontend/src/routes/settings/+page.svelte` - Trigger sync after Jellyfin save (if first time)
- `backend/app/routers/sync.py` - Ensure first sync isn't rate-limited

---

#### US-18.3: Optional Services Prompt
**As a** user who completed basic setup
**I want** to see optional services I can configure
**So that** I can enhance my experience if I have Jellyseerr/Radarr/Sonarr

**Acceptance Criteria:**
- [ ] After checklist complete, show dismissible "Enhance your setup" card
- [ ] Lists: Jellyseerr (request tracking), Radarr (movie management), Sonarr (TV management)
- [ ] Each has "Configure" link to /settings
- [ ] User can dismiss card permanently (stored in localStorage)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser

**Files:**
- `frontend/src/routes/+page.svelte` - Add optional services card
- `frontend/src/lib/components/OptionalServicesCard.svelte` - New component (optional)

### Non-Goals
- No separate /onboarding route (stays on dashboard)
- No changes to signup/login flow itself
- No forced configuration of Jellyseerr/Radarr/Sonarr

### Technical Considerations
- **Backend:** Derive `has_completed_first_sync` from `last_synced != null` in sync status
- **Frontend:** Conditionally render checklist based on: `!jellyfin_configured || !has_synced`
- **Dismissed state:** Store "dismissed optional services" in localStorage (no backend needed)
- **Auto-sync:** Use existing `/api/sync` endpoint after Jellyfin save

---

## Epic 19: Issues Page Search

### Overview
Add a search input to the Issues page that allows users to quickly find specific content by filtering the displayed items. Search is client-side for instant responsiveness.

### Goals
- Allow users to quickly locate specific movies/shows in their issues list
- Search across title, year, and requested_by fields
- Maintain current tab filtering behavior (search operates within active tab)

### User Stories

#### US-19.1: Search Issues by Text
**As a** media server owner
**I want** to search for content on the Issues page
**So that** I can quickly find a specific movie or show without scrolling

**Acceptance Criteria:**
- [ ] Search input appears next to the "Issues" title/item count
- [ ] Search filters items in real-time as user types (debounced ~300ms)
- [ ] Search matches against: title (case-insensitive), production year, and requested_by (for Requests tab)
- [ ] Search operates within the currently active tab filter (Old, Large, Language, Requests, or All)
- [ ] Empty search shows all items for current tab
- [ ] Item count updates to reflect filtered results (e.g., "3 of 219 items")
- [ ] Total size updates to reflect filtered results
- [ ] Search input has a clear (X) button when text is present
- [ ] Placeholder text: "Search by title, year..."
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

### Non-Goals
- Backend API changes (search is client-side only)
- Persistent search state across page navigation
- Advanced search syntax (AND/OR operators, field-specific queries)
- Searching content outside of issues (library-wide search)

### Technical Considerations
- Use Svelte `$state()` for search input value
- Debounce filtering to avoid excessive re-renders (~300ms)
- Filter function should check: `name`, `production_year`, `requested_by`
- Update `filteredItems` computed value that combines tab filter + search filter
- Update displayed count/size based on filtered results

### UI Design Notes
- Search input should be compact, matching the existing design system
- Position: right side of the header, aligned with "219 items · 727.1 GB" text
- Use existing CSS variables for styling consistency

---

## Epic 20: Large Series Detection

### Overview
Extend the "Large Movies" feature to also detect TV series with oversized seasons. Currently, only movies are flagged as "large" (>13GB). This epic adds detection for series where any single season exceeds a configurable threshold (default 15GB).

### Goals
- Flag TV series with any season larger than threshold
- Provide a separate, user-configurable threshold for series (independent from movies)
- Calculate season sizes efficiently via background task (not during main sync)
- Unified "Large Content" view with movie/series filtering

### User Stories

#### US-20.1: Large Season Threshold Setting
**As a** media server owner
**I want** to configure the threshold for large seasons separately from movies
**So that** I can fine-tune detection based on my storage preferences

**Acceptance Criteria:**
- [ ] Add `large_season_size_gb` field to UserSettings model (default: 15)
- [ ] Create database migration for new column
- [ ] `GET /api/settings` returns `large_season_size_gb` value
- [ ] `POST /api/settings` accepts and saves `large_season_size_gb`
- [ ] Settings page displays "Large season threshold (GB)" input below movie threshold
- [ ] Input validates: integer, minimum 1GB
- [ ] Help text: "Flag TV series if any season exceeds this size"
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: setting saves and loads correctly

**Files:**
- `backend/app/database.py` - Add field to UserSettings
- `backend/alembic/versions/` - New migration
- `backend/app/routers/settings.py` - Include in GET/POST
- `backend/app/models/settings.py` - Update Pydantic schemas
- `frontend/src/routes/settings/+page.svelte` - Add input field

---

#### US-20.2: Calculate and Store Season Sizes
**As a** system
**I want** to calculate TV series season sizes after sync completes
**So that** large series detection has accurate data without slowing down the main sync

**Acceptance Criteria:**
- [ ] Add `largest_season_size_bytes` field to CachedMediaItem model (nullable BigInteger)
- [ ] Create database migration for new column
- [ ] New async function `calculate_season_sizes(db, user_id, server_url, api_key)`:
  - Fetches all series for user from cache
  - For each series, calls Jellyfin API: `GET /Items?ParentId={series_id}&IncludeItemTypes=Episode&Fields=MediaSources,ParentIndexNumber`
  - Groups episodes by `ParentIndexNumber` (season number), sums sizes per season
  - Stores the LARGEST season size in `largest_season_size_bytes`
- [ ] Background task triggered AFTER main sync completes (not during)
- [ ] Sync status includes new state: "calculating_sizes" (after "completed")
- [ ] Progress logging: "Calculating season sizes for {n} series..."
- [ ] Handles API errors gracefully (logs warning, continues to next series)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Integration test: trigger sync, verify season sizes populated

**Files:**
- `backend/app/database.py` - Add field to CachedMediaItem
- `backend/alembic/versions/` - New migration
- `backend/app/services/sync.py` - Add `calculate_season_sizes()` function
- `backend/app/services/sync.py` - Trigger after main sync in `run_full_sync()`
- `backend/tests/test_sync_service.py` - Test season size calculation

**Technical Notes:**
- Jellyfin API endpoint: `GET /Items?ParentId={series_id}&IncludeItemTypes=Episode&Recursive=true&Fields=MediaSources,ParentIndexNumber`
- Episode size is at `MediaSources[0].Size`
- Season number is at `ParentIndexNumber`
- Reference: `original_script.py:1582` - `get_series_total_size()` function

---

#### US-20.3: Large Series Detection Service
**As a** user
**I want** large series included in the content issues API
**So that** I can see all my oversized content in one place

**Acceptance Criteria:**
- [ ] New function `is_large_series(item, threshold_gb)` returns True if `largest_season_size_bytes >= threshold`
- [ ] `get_content_summary()` includes large series in a combined count:
  - Rename internal variable from `large_movies` to `large_content`
  - Count includes both large movies AND large series
  - Total size includes both
- [ ] `get_content_issues()` with `filter=large` returns both movies and series
- [ ] Each item includes new field: `largest_season_size_bytes` (null for movies)
- [ ] Each item includes new field: `largest_season_size_formatted` (e.g., "18.5 GB")
- [ ] Series items include issue badge "large" when flagged
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Test: large series appears in issues, large movie still appears

**Files:**
- `backend/app/services/content.py` - Add `is_large_series()`, update `get_content_summary()`, `get_content_issues()`
- `backend/app/models/content.py` - Add fields to response schemas
- `backend/tests/test_content.py` - Test large series detection

---

#### US-20.4: Large Content UI with Filter
**As a** media server owner
**I want** to filter large content by movies or series
**So that** I can focus on one type at a time

**Acceptance Criteria:**
- [ ] Dashboard card renamed from "Large Movies" to "Large Content"
- [ ] Dashboard card shows combined count (movies + series)
- [ ] Issues page "Large" tab shows both movies and series
- [ ] Sub-filter buttons appear when Large tab selected: [All] [Movies] [Series]
- [ ] Default sub-filter is "All"
- [ ] Sub-filter is client-side (no API changes needed)
- [ ] Series items display: name, largest season size (e.g., "Largest season: 18.5 GB")
- [ ] Movie items display: name, file size (unchanged behavior)
- [ ] Item count and total size update based on sub-filter
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: filter toggles work correctly

**Files:**
- `frontend/src/routes/+page.svelte` - Rename card label
- `frontend/src/routes/issues/+page.svelte` - Add sub-filter UI, update display logic
- `frontend/src/lib/components/IssueItem.svelte` - Show season size for series (if applicable)

### Non-Goals
- Per-season breakdown in UI (only show largest season size)
- Deleting individual seasons (out of scope)
- Real-time size calculation (always uses cached values)

### Technical Considerations
- **Jellyfin API:** Episodes don't have a direct "season" endpoint. Must fetch all episodes and group by `ParentIndexNumber`
- **Performance:** With ~100 series, background calculation adds ~100 API calls (acceptable)
- **Sync flow:** Main sync → Complete → Background task calculates sizes → Update status
- **Original script reference:** `get_series_total_size()` at line 1582, but we calculate per-season, not total

---

## Epic 21: Slack Notification Monitoring

### Overview
Add admin monitoring via Slack notifications to track new user signups and sync failures. This helps the admin stay informed about app health and growth without checking logs.

### Goals
- Get notified immediately when new users sign up
- Get notified when sync operations fail for any user
- Keep webhook configuration secure via environment variables

### User Stories

#### US-21.1: Slack Notification Service
**As a** developer
**I want** a reusable Slack notification service
**So that** I can send messages to different Slack channels

**Acceptance Criteria:**
- [ ] Create `app/services/slack.py` with `send_slack_message(webhook_url, message)` function
- [ ] Function accepts webhook URL and message dict (Slack Block Kit format)
- [ ] Function handles HTTP errors gracefully (log error, don't crash app)
- [ ] Function is async and non-blocking
- [ ] Add `SLACK_WEBHOOK_NEW_USERS` and `SLACK_WEBHOOK_SYNC_FAILURES` to config
- [ ] Webhooks are optional - if not configured, notifications are silently skipped
- [ ] Unit tests mock HTTP calls and verify message format
- [ ] Typecheck passes
- [ ] Unit tests pass

**Files:**
- `backend/app/services/slack.py` - New service
- `backend/app/config.py` - Add webhook URL settings
- `backend/tests/test_slack_service.py` - Unit tests

---

#### US-21.2: New User Signup Notifications
**As an** admin
**I want** to receive a Slack notification when someone signs up
**So that** I can track user growth in real-time

**Acceptance Criteria:**
- [ ] After successful user registration, send Slack notification
- [ ] Message includes: user email, signup timestamp, total user count
- [ ] Message uses Slack Block Kit for nice formatting
- [ ] Notification is fire-and-forget (doesn't block registration response)
- [ ] If webhook not configured, registration still works (no error)
- [ ] Unit tests verify notification is sent with correct payload
- [ ] Typecheck passes
- [ ] Unit tests pass

**Message Format:**
```
:wave: New User Signup
Email: user@example.com
Signed up: 2025-01-15 14:30 UTC
Total users: 42
```

**Files:**
- `backend/app/routers/auth.py` - Call Slack service after registration
- `backend/tests/test_auth.py` - Add test for Slack notification

---

#### US-21.3: Sync Failure Notifications
**As an** admin
**I want** to receive a Slack notification when a user's sync fails
**So that** I can investigate and help users with connection issues

**Acceptance Criteria:**
- [ ] When sync fails (Jellyfin or Jellyseerr), send Slack notification
- [ ] Message includes: user email, which service failed, error message
- [ ] Notification sent for both manual sync and scheduled (Celery) sync failures
- [ ] Message is fire-and-forget (doesn't affect sync error handling)
- [ ] If webhook not configured, sync failure handling still works
- [ ] Unit tests verify notification is sent with correct payload
- [ ] Typecheck passes
- [ ] Unit tests pass

**Message Format:**
```
:warning: Sync Failed
User: user@example.com
Service: Jellyfin
Error: Connection timeout after 30s
Time: 2025-01-15 14:30 UTC
```

**Files:**
- `backend/app/services/sync.py` - Call Slack service on failure
- `backend/app/tasks.py` - Call Slack service on Celery task failure
- `backend/tests/test_sync_service.py` - Add test for failure notification

### Non-Goals
- No admin UI to configure webhooks (env vars only)
- No notification preferences per user (admin-only feature)
- No retry logic for failed Slack deliveries
- No rate limiting on notifications

### Technical Considerations
- **Slack Block Kit**: Use blocks for rich formatting (not plain text)
- **Async HTTP**: Use `httpx` async client for non-blocking calls
- **Error handling**: Log failures but never raise - notifications are best-effort
- **Environment variables**:
  - `SLACK_WEBHOOK_NEW_USERS` - Webhook for #new-users channel
  - `SLACK_WEBHOOK_SYNC_FAILURES` - Webhook for #alerts channel

### Environment Variables
```env
# Optional - if not set, notifications are disabled
SLACK_WEBHOOK_NEW_USERS=https://hooks.slack.com/services/XXX/YYY/ZZZ
SLACK_WEBHOOK_SYNC_FAILURES=https://hooks.slack.com/services/AAA/BBB/CCC
```

---

## Epic 22: Library Browser

### Overview
A new Library section that allows users to browse their complete Jellyfin media library. Unlike the Issues page which shows only problematic content, the Library shows everything - giving users a complete view of what's in their collection.

### Goals
- Provide full visibility into the user's Jellyfin library
- Enable quick discovery and search of specific content
- Separate movies and series for easier browsing
- Leverage existing cached data (no new sync logic needed)

### User Stories

#### US-22.1: Library API Endpoint
**As a** developer
**I want** an API endpoint that returns all cached media
**So that** the frontend can display the complete library

**Acceptance Criteria:**
- [ ] `GET /api/library` returns all cached media items for the user
- [ ] Supports query params: `type=movie|series|all` (default: all)
- [ ] Supports query params: `search=string` (searches name, case-insensitive)
- [ ] Supports query params: `watched=true|false|all` (default: all)
- [ ] Supports query params: `sort=name|year|size|date_added|last_watched` (default: name)
- [ ] Supports query params: `order=asc|desc` (default: asc)
- [ ] Supports query params: `min_year`, `max_year` for year range filter
- [ ] Supports query params: `min_size_gb`, `max_size_gb` for size range filter
- [ ] Returns: items[], total_count, total_size_bytes, total_size_formatted, service_urls
- [ ] Each item includes: jellyfin_id, name, media_type, production_year, size_bytes, size_formatted, played, last_played_date, date_created, tmdb_id
- [ ] Typecheck passes
- [ ] Unit tests pass

**Files:**
- `backend/app/routers/library.py` - New router
- `backend/app/services/library.py` - New service
- `backend/app/models/library.py` - Response schemas
- `backend/app/main.py` - Register router
- `backend/tests/test_library.py` - Unit tests

---

#### US-22.2: Library Page with Sub-tabs
**As a** media server owner
**I want** to browse my library with separate Movies and Series tabs
**So that** I can explore my collection by content type

**Acceptance Criteria:**
- [ ] New route `/library` accessible from sidebar navigation
- [ ] Sidebar shows "Library" menu item with appropriate icon (between Issues and Whitelist)
- [ ] Page header shows "Library" with total item count and size
- [ ] Sub-tabs: [All] [Movies] [Series] - filter by media type
- [ ] Default sub-tab is "All"
- [ ] Table displays: Name, Year, Size, Added, Last Watched
- [ ] External service links (Jellyfin, TMDB) like Issues page
- [ ] Empty state when library is empty (with link to Settings to configure Jellyfin)
- [ ] Loading state while fetching data
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/library/+page.svelte` - New page
- `frontend/src/lib/components/Sidebar.svelte` - Add Library nav item
- `frontend/src/lib/types.ts` - Add LibraryItem type

---

#### US-22.3: Library Search and Filters
**As a** media server owner
**I want** to search and filter my library
**So that** I can quickly find specific content

**Acceptance Criteria:**
- [ ] Search input in page header (searches as user types, debounced 300ms)
- [ ] Search matches name (case-insensitive) and production year
- [ ] Filter dropdown for watched status: All, Watched, Unwatched
- [ ] Year range filter: min year and max year inputs
- [ ] Size range filter: min size and max size (in GB)
- [ ] Sort dropdown: Name, Year, Size, Date Added, Last Watched
- [ ] Sort order toggle: Ascending/Descending
- [ ] Filters persist while switching between All/Movies/Series tabs
- [ ] Clear all filters button
- [ ] Item count updates to reflect filtered results
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/library/+page.svelte` - Add filter UI and logic

---

#### US-22.4: Library Sorting
**As a** media server owner
**I want** to sort my library by different columns
**So that** I can organize the view to my preference

**Acceptance Criteria:**
- [ ] Clickable column headers for sorting (Name, Year, Size, Last Watched)
- [ ] Visual indicator showing current sort column and direction
- [ ] Click same column to toggle ascending/descending
- [ ] Default sort: Name ascending
- [ ] Sorting is server-side (API parameter) for performance with large libraries
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/library/+page.svelte` - Add sortable column headers

### Non-Goals
- No whitelist/delete actions (this is browse-only, use Issues page for actions)
- No pagination in v1 (will revisit if performance issues arise with large libraries)
- No grid/poster view (table view only for v1)
- No offline/PWA support
- No export functionality

### Technical Considerations
- **Data Source:** All data comes from `CachedMediaItem` table (already synced)
- **Performance:** With typical libraries of 500-2000 items, server-side filtering/sorting is sufficient
- **Reuse:** Can reuse external link badge components from Issues page
- **API Design:** Server-side filtering for watched status, year range, size range to support large libraries

---

## Epic 23: Added Date Column

### Overview
Display when content was added to the Jellyfin library on the Issues page and Library page. This helps users understand the age of their content and make better decisions about what to keep or remove.

### Goals
- Show "Added" date column on Issues page
- Include "Added" column in Library page (when built)
- Leverage existing `date_created` data from sync

### User Stories

#### US-23.1: Added Date Column on Issues Page
**As a** media server owner
**I want** to see when content was added to my library
**So that** I can understand how long items have been in my collection

**Acceptance Criteria:**
- [ ] API includes `date_created` field in content issues response
- [ ] Issues page table shows "Added" column after "Size" column
- [ ] Displays date in user-friendly format (e.g., "Jan 15, 2024")
- [ ] Shows "Unknown" if date_created is null
- [ ] Column is sortable (client-side)
- [ ] Column visible on all tabs (All, Old, Large, Language, Unavailable)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `backend/app/models/content.py` - Add `date_created` to ContentIssueItem schema
- `backend/app/services/content.py` - Include `date_created` in response
- `frontend/src/routes/issues/+page.svelte` - Add "Added" column to table

### Non-Goals
- No filtering by added date on Issues page (use Library for that)
- No backend sorting by date_created (client-side only for Issues)

### Technical Considerations
- `date_created` already exists in `CachedMediaItem` model and is synced from Jellyfin
- Format: ISO 8601 string from Jellyfin API (e.g., "2024-01-15T10:30:00Z")
- Frontend should format using `toLocaleDateString()` or similar

---

## Epic 24: Auth Security

### Overview
Add rate limiting to authentication endpoints to protect against brute force password attacks. This is a security hardening measure that limits the number of login/register attempts from a single IP address.

### Goals
- Prevent brute force password attacks on login endpoint
- Prevent automated account creation spam on register endpoint
- Provide clear feedback to legitimate users who hit rate limits

### User Stories

#### US-24.1: Rate Limiting on Auth Endpoints
**As a** system administrator
**I want** login and registration endpoints to be rate-limited
**So that** brute force attacks are mitigated

**Acceptance Criteria:**
- [ ] Rate limit of 10 requests per minute per IP address on `/api/auth/login`
- [ ] Rate limit of 10 requests per minute per IP address on `/api/auth/register`
- [ ] Rate-limited requests return HTTP 429 (Too Many Requests)
- [ ] Response includes `Retry-After` header indicating seconds until reset
- [ ] Response body includes clear error message: "Too many requests. Please try again in X seconds."
- [ ] Rate limit uses in-memory storage (Redis not required for v1)
- [ ] `/api/auth/me` endpoint is NOT rate-limited (authenticated requests only)
- [ ] Rate limiting is disabled in test environment
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Manual test: verify 11th request within 60 seconds returns 429

**Files:**
- `backend/app/middleware/rate_limit.py` - New middleware/dependency for rate limiting
- `backend/app/routers/auth.py` - Apply rate limit dependency to login/register
- `backend/tests/test_auth.py` - Add rate limit tests

### Non-Goals
- Redis/distributed rate limiting (in-memory is sufficient for single-instance deployment)
- Per-email rate limiting (IP-based only for v1)
- Gradual backoff/tarpit (simple blocking for v1)
- Admin UI to configure rate limits (hardcoded for now)

### Technical Considerations
- **Implementation option:** Use `slowapi` library (FastAPI-compatible) or custom middleware
- **Storage:** In-memory dict with IP -> (count, window_start) for simplicity
- **Thread safety:** Use `asyncio.Lock` for concurrent request handling
- **Testing:** Mock time or use short windows in tests
- **X-Forwarded-For:** Handle proxy scenarios (get real client IP from headers)

---

## Epic 25: Password Strength Indicator

### Overview
Display visual feedback during registration showing password strength based on length. Helps users create stronger passwords without enforcing any restrictions.

### Goals
- Guide users toward creating better passwords
- Provide immediate visual feedback as they type
- Keep the indicator simple and non-intrusive

### User Stories

#### US-25.1: Password Strength Indicator
**As a** new user registering for an account
**I want** to see a visual indicator of my password strength
**So that** I can understand how secure my password is

**Acceptance Criteria:**
- [ ] Password input on registration page shows strength indicator below the field
- [ ] Indicator is a horizontal progress bar that changes color based on strength
- [ ] Strength levels based on length:
  - Weak (red): 1-7 characters
  - Medium (yellow): 8-11 characters
  - Strong (green): 12+ characters
- [ ] Bar fills proportionally: ~33% for weak, ~66% for medium, ~100% for strong
- [ ] Indicator only appears when password field has content
- [ ] Indicator updates in real-time as user types (no debounce needed)
- [ ] Indicator is informational only - does NOT block form submission
- [ ] Uses existing CSS color variables (--danger, --warning, --success or similar)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/register/+page.svelte` - Add strength indicator component

### Non-Goals
- No backend validation of password strength (purely frontend visual)
- No complex strength algorithms (zxcvbn, etc.) - just length-based
- No blocking weak passwords from submission
- No password requirements checklist

### Technical Considerations
- Use Svelte reactive statements to compute strength from password length
- Color transitions should be smooth (CSS transition)
- Bar width calculated as percentage: `Math.min(100, (length / 12) * 100)`
- Empty password = hidden indicator (not "weak")

---

#### US-25.2: Password Confirmation Field
**As a** new user registering for an account
**I want** to confirm my password by typing it twice
**So that** I don't accidentally create an account with a typo in my password

**Acceptance Criteria:**
- [ ] Registration form adds "Confirm Password" input field after Password field
- [ ] Confirm Password field is required
- [ ] Form validates that Password and Confirm Password match
- [ ] If passwords don't match, show error: "Passwords do not match"
- [ ] Error appears below the Confirm Password field (not as a toast)
- [ ] Submit button is disabled until passwords match (or validation runs on submit)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/register/+page.svelte` - Add confirm password field and validation

---

## Epic 26: Sync Resilience

### Overview
Add retry logic with exponential backoff to handle transient API failures during sync. Jellyfin and Jellyseerr APIs can occasionally fail due to timeouts, rate limits, or temporary network issues. Automatic retries improve sync reliability.

### Goals
- Automatically retry failed API calls during sync
- Use exponential backoff to avoid overwhelming failing services
- Provide clear failure messages when retries are exhausted

### User Stories

#### US-26.1: Sync Retry with Exponential Backoff
**As a** user
**I want** sync to automatically retry on transient failures
**So that** temporary API issues don't require me to manually retry

**Acceptance Criteria:**
- [ ] Jellyfin API calls retry up to 3 times on failure (4 total attempts)
- [ ] Jellyseerr API calls retry up to 3 times on failure (4 total attempts)
- [ ] Retry delays use exponential backoff: 1s, 2s, 4s between retries
- [ ] Only retry on transient errors: timeouts, 5xx errors, connection errors
- [ ] Do NOT retry on: 401 (auth failed), 404 (not found), 400 (bad request)
- [ ] Each retry attempt is logged: "Retry 1/3 for Jellyfin API after 1s..."
- [ ] After all retries exhausted, sync status set to "failed" with error message
- [ ] Error message includes which service failed and the error type
- [ ] Successful retry continues sync normally (no partial state)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Test: mock API to fail twice then succeed, verify sync completes

**Files:**
- `backend/app/services/sync.py` - Add retry wrapper for API calls
- `backend/app/services/jellyfin.py` - Use retry wrapper (if separate)
- `backend/app/services/jellyseerr.py` - Use retry wrapper (if separate)
- `backend/tests/test_sync_service.py` - Add retry tests

### Non-Goals
- Per-item retry (if one movie fails, don't retry the whole sync)
- Configurable retry count/delays via settings
- Circuit breaker pattern (v1 uses simple retry)
- Retry notifications to user (just logging for now)

### Technical Considerations
- Use `tenacity` library for retry logic (cleaner than manual implementation)
- Exponential backoff formula: `2^attempt * base_delay` where base_delay=1s
- Wrap high-level fetch functions (not every HTTP call individually)
- Consider adding jitter to backoff to prevent thundering herd
- Retryable exceptions: `httpx.TimeoutException`, `httpx.ConnectError`, responses with 5xx status

### Example Implementation Pattern
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    before_sleep=lambda retry_state: logger.info(f"Retry {retry_state.attempt_number}/3...")
)
async def fetch_jellyfin_media(...):
    ...
```

---

## Epic 27: Test Coverage

### Overview
Improve automated test coverage with critical E2E tests for core user flows.

### User Stories

#### US-27.1: E2E Auth Flow Test
**As a** developer
**I want** an E2E test covering the complete authentication flow
**So that** regressions in auth are caught automatically

**Acceptance Criteria:**
- [ ] E2E test covers: register new user → login → navigate to dashboard → navigate to settings → logout
- [ ] Test uses unique email per run (e.g., `test-{timestamp}@example.com`)
- [ ] Verifies dashboard loads after login (checks for expected element)
- [ ] Verifies settings page loads and shows user info
- [ ] Verifies logout redirects to login page
- [ ] Verifies protected routes redirect to login when not authenticated
- [ ] Test is idempotent (can run multiple times without cleanup)
- [ ] Typecheck passes
- [ ] E2E test passes

**Files:**
- `frontend/e2e/auth-flow.spec.ts` - New E2E test file

---

#### US-27.2: Sync Integration Tests with Mocked APIs
**As a** developer
**I want** integration tests that verify sync behavior with mocked Jellyfin/Jellyseerr responses
**So that** I can test sync logic without requiring real external services

**Acceptance Criteria:**
- [ ] Test file `backend/tests/test_sync_integration.py` with mocked API responses
- [ ] Mock Jellyfin API responses using `httpx` mock or `respx` library
- [ ] Mock Jellyseerr API responses
- [ ] Test: successful sync stores correct data in database
- [ ] Test: partial Jellyfin data is handled correctly (missing fields)
- [ ] Test: Jellyseerr down doesn't break Jellyfin sync
- [ ] Test: API returning empty results creates empty cache (not error)
- [ ] Mocks use realistic response structures from actual API documentation
- [ ] Tests run without network access (fully offline)
- [ ] Typecheck passes
- [ ] All tests pass

**Files:**
- `backend/tests/test_sync_integration.py` - New integration test file
- `backend/tests/fixtures/jellyfin_responses.py` - Mock response data (optional)
- `backend/tests/fixtures/jellyseerr_responses.py` - Mock response data (optional)

### Non-Goals
- Testing every form validation (unit tests cover that)
- Visual regression testing

---

## Epic 28: Accessibility Improvements

### Overview
Improve accessibility for screen reader users by adding proper ARIA attributes to dynamic content.

### User Stories

#### US-28.1: Loading States Accessibility
**As a** screen reader user
**I want** loading states to be announced
**So that** I know when content is being fetched

**Acceptance Criteria:**
- [ ] Add `aria-busy="true"` to parent containers during loading
- [ ] Loading spinners have `aria-label="Loading"` or equivalent
- [ ] Add `aria-live="polite"` regions for dynamic content updates
- [ ] Dashboard loading state is accessible
- [ ] Issues page loading state is accessible
- [ ] Settings page loading state is accessible
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify with screen reader or accessibility inspector

**Files:**
- `frontend/src/routes/+page.svelte` - Dashboard accessibility
- `frontend/src/routes/issues/+page.svelte` - Issues page accessibility
- `frontend/src/routes/settings/+page.svelte` - Settings page accessibility

### Non-Goals
- Full WCAG 2.1 compliance audit
- High contrast theme

---

## Epic 29: Issues Table UX Improvements

### Overview
Improve the visual alignment and readability of the Issues table. The Name column currently has alignment issues: year and service badges shift horizontally based on title length, creating a ragged, hard-to-scan layout. This epic restructures the Name cell for consistent alignment and adds a dedicated Requester column for the Unavailable tab.

### Goals
- Fix year/badge misalignment across all rows (all tabs)
- Improve table scanability with consistent visual structure
- Separate requester info from title into dedicated column (Unavailable tab only)
- Reduce visual noise from competing badge colors

### User Stories

#### US-29.1: Issues Table Name Column Improvements
**As a** media server owner
**I want** the Issues table to have consistent visual alignment
**So that** I can quickly scan and compare items across rows

**Acceptance Criteria:**
- [ ] Year displays at a fixed horizontal position (not flowing after variable-length titles)
- [ ] Service badges (JF, JS, RD, TMDB) align consistently across all rows
- [ ] Long titles truncate with ellipsis instead of wrapping to multiple lines
- [ ] On hover, truncated titles show full text via title tooltip
- [ ] New "Requester" column appears after Name column (only on Unavailable tab)
- [ ] Requester column follows same pattern as Release column (conditional display)
- [ ] Column displays username from `requested_by` field, or `—` if null
- [ ] The inline "by {username}" display in the name cell is removed
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

### Non-Goals
- Adding requester info to non-request items
- Backend API changes (data already includes `requested_by`)
- Filtering by requester (future enhancement)
- Sorting by requester (future enhancement)
- Changing service badge colors (defer to future enhancement)

### Technical Considerations
- **Frontend-only change** to `frontend/src/routes/issues/+page.svelte`
- Restructure `.name-cell` from flex to CSS Grid with fixed zones: `[Title (1fr)] [Year (auto)] [Badges (auto)]`
- Add `text-overflow: ellipsis` and `white-space: nowrap` to `.item-name` for truncation
- Add `title={item.name}` attribute for hover tooltip on truncated names
- Follow existing pattern from `col-release` for conditional Requester column
- `requested_by` field already exists in `ContentIssueItem` interface

---

## Epic 30: Remove Currently Airing Placeholder

### Overview
Remove the "Currently Airing" feature which was never implemented. The dashboard currently shows "0 currently airing" linking to an empty page, which is confusing to users. This epic cleans up the placeholder code.

### Goals
- Remove confusing "0 currently airing" from dashboard
- Clean up unused backend code, routes, and tests
- Simplify the codebase by removing dead code

### User Stories

#### US-30.1: Remove Currently Airing Placeholder
**As a** user
**I want** the dashboard to only show implemented features
**So that** I'm not confused by links to empty pages

**Acceptance Criteria:**
- [ ] Remove "currently airing" link from dashboard info section
- [ ] Remove `/info/airing` route and page entirely
- [ ] Remove `GET /api/info/airing` endpoint
- [ ] Remove `get_currently_airing()` function from content service
- [ ] Remove `CurrentlyAiringItem` and `CurrentlyAiringResponse` models
- [ ] Remove `currently_airing` from `ContentSummaryResponse` model
- [ ] Update `get_content_summary()` to not include `currently_airing`
- [ ] Remove related tests (backend and frontend)
- [ ] Dashboard info section shows only "recently available" (remove separator)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: dashboard no longer shows "currently airing"

### Non-Goals
- Implementing the feature (can be added later if needed)
- Changing any other dashboard functionality

### Technical Considerations

**Files to modify:**
- `frontend/src/routes/+page.svelte` - Remove currently_airing from info section
- `frontend/src/routes/info/airing/+page.svelte` - DELETE entire file
- `frontend/tests/info.test.ts` - Remove currently_airing tests
- `backend/app/routers/info.py` - Remove `/airing` endpoint
- `backend/app/services/content.py` - Remove `get_currently_airing()` function
- `backend/app/models/content.py` - Remove `CurrentlyAiringItem`, `CurrentlyAiringResponse`, update `ContentSummaryResponse`
- `backend/tests/test_content.py` - Remove currently_airing tests

**Cleanup pattern:**
1. Start with backend models (remove types)
2. Update service (remove function)
3. Update router (remove endpoint)
4. Update frontend (remove UI + route)
5. Clean up tests last

---

## Epic 31: Recently Available Enhancements

### Overview
Improve the "Recently Available" page to better serve its primary purpose: notifying users who requested content that it's now available. This includes configurable time window, user nickname mapping for friendly names in notifications, and copy output grouped by requester.

### Goals
- Make the "days back" threshold configurable per user
- Allow users to map Jellyseerr usernames to friendly display names
- Generate copy output grouped by requester for easy notification
- Improve the notification workflow for media server owners

### User Stories

#### US-31.1: Recently Available Days Setting (Backend)
**As a** media server owner
**I want** to configure how many days back to show recently available content
**So that** I can adjust the view to my notification frequency

**Acceptance Criteria:**
- [ ] Add `recently_available_days` field to UserSettings model (integer, default 7)
- [ ] Create database migration for new column
- [ ] `GET /api/settings` returns `recently_available_days` value
- [ ] `POST /api/settings` accepts and validates `recently_available_days` (range: 1-30)
- [ ] `GET /api/info/recent` uses user's setting instead of hardcoded 7 days
- [ ] `GET /api/content/summary` uses user's setting for `recently_available` count
- [ ] Invalid values return 422 with clear error message
- [ ] Typecheck passes
- [ ] Unit tests pass

**Files:**
- `backend/app/database.py` - Add field to UserSettings
- `backend/alembic/versions/` - New migration
- `backend/app/routers/settings.py` - Include in GET/POST
- `backend/app/models/settings.py` - Update Pydantic schemas
- `backend/app/services/content.py` - Update `get_recently_available()` and `get_content_summary()`
- `backend/tests/test_settings.py` - Validation tests

---

#### US-31.2: Recently Available Days Setting (Frontend)
**As a** media server owner
**I want** to set my "recently available" days preference in the settings page
**So that** I can customize the time window

**Acceptance Criteria:**
- [ ] Settings page shows "Recently available days" input in a new "Display" section
- [ ] Input is a number field with min=1, max=30
- [ ] Default value is 7 when not set
- [ ] Help text: "Show content that became available in the past N days"
- [ ] Value saves successfully and persists on page reload
- [ ] Recently Available page subtitle updates to reflect setting (e.g., "past 14 days")
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/settings/+page.svelte` - Add input field
- `frontend/src/routes/info/recent/+page.svelte` - Fetch setting and display in subtitle

---

#### US-31.3: User Nickname Mapping (Backend)
**As a** media server owner
**I want** to store nickname mappings for Jellyseerr usernames
**So that** I can show friendly names in notifications

**Acceptance Criteria:**
- [ ] Create new `UserNickname` model: `id`, `user_id` (FK), `jellyseerr_username` (string), `display_name` (string)
- [ ] Create database migration for new table
- [ ] Unique constraint on (`user_id`, `jellyseerr_username`) - each username maps once per user
- [ ] `GET /api/settings/nicknames` returns list of all nickname mappings for user
- [ ] `POST /api/settings/nicknames` creates a new mapping (body: `{jellyseerr_username, display_name}`)
- [ ] `PUT /api/settings/nicknames/{id}` updates an existing mapping
- [ ] `DELETE /api/settings/nicknames/{id}` removes a mapping
- [ ] 409 Conflict if trying to create duplicate jellyseerr_username
- [ ] Typecheck passes
- [ ] Unit tests pass

**Files:**
- `backend/app/database.py` - Add UserNickname model
- `backend/alembic/versions/` - New migration
- `backend/app/routers/settings.py` - Add nickname CRUD endpoints
- `backend/app/models/settings.py` - Add NicknameCreate, NicknameResponse schemas
- `backend/tests/test_settings.py` - CRUD tests

---

#### US-31.4: User Nickname Mapping (Frontend)
**As a** media server owner
**I want** to manage nickname mappings in the settings page
**So that** I can assign friendly names to Jellyseerr users

**Acceptance Criteria:**
- [ ] Settings page shows new "User Nicknames" section below services configuration
- [ ] Section displays table of existing mappings: Jellyseerr Username → Display Name
- [ ] "Add nickname" button opens inline form with two inputs: username, display name
- [ ] Each row has edit and delete buttons
- [ ] Delete shows confirmation before removing
- [ ] Empty state: "No nicknames configured. Add nicknames to customize how requesters appear in notifications."
- [ ] Toast feedback on save/delete success/error
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/settings/+page.svelte` - Add nicknames section with CRUD UI

---

#### US-31.5: Copy Output Grouped by Requester
**As a** media server owner
**I want** the copy output to group content by requester with their display name
**So that** I can easily notify each person about their available content

**Acceptance Criteria:**
- [ ] "Copy" button generates output grouped by requester (not by date)
- [ ] Uses display_name from nickname mapping if configured, otherwise original Jellyseerr username
- [ ] Format per requester:
  ```
  {display_name}:
    - {Title} ({Type}) - available since {Date}
  ```
- [ ] Requesters sorted alphabetically
- [ ] Items under each requester sorted by availability date (newest first)
- [ ] Items without a requester grouped under "Unknown" at the end
- [ ] API endpoint `GET /api/info/recent` includes resolved `display_name` field
- [ ] Frontend uses `display_name` for grouping and display in table
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: copy output shows correct grouping

**Example output:**
```
Recently Available (3 items):

Fab:
  - 2 Alone in Paris (Movie) - available since Jan 11
  - The Serpent (TV) - available since Jan 11

John:
  - Inception (Movie) - available since Jan 10
```

**Files:**
- `backend/app/services/content.py` - Add `display_name` resolution to `get_recently_available()`
- `backend/app/models/content.py` - Add `display_name` to `RecentlyAvailableItem`
- `frontend/src/routes/info/recent/+page.svelte` - Update copy function, show display_name in table

### Non-Goals
- Many-to-1 username mapping (multiple usernames → one person)
- Auto-detecting Jellyseerr usernames (user must manually add)
- Actually sending notifications (just copy for manual paste)
- Per-requester filtering on the Recently Available page

### Technical Considerations
- **Database:** New `UserNickname` table with FK to users
- **API pattern:** Follow existing settings endpoint patterns for CRUD
- **Display name resolution:** Done at API level so both table and copy use same resolved name
- **Settings page structure:** Add new "Display" section for recently_available_days, new "User Nicknames" section for mappings

---

## Epic 32: Session Management & Auth UX

### Overview
Improve authentication experience by extending session duration with refresh tokens and automatically redirecting users to login when their session expires. Currently, sessions expire after 30 minutes forcing frequent re-logins, and expired sessions still allow frontend navigation with failing API calls.

### Goals
- Reduce login friction with long-lived sessions (30 days)
- Implement refresh token mechanism for secure session renewal
- Auto-redirect to login on session expiration instead of showing toast errors
- Clean up stale auth state so users can't navigate with expired sessions

### User Stories

#### US-32.1: Refresh Token Backend Implementation
**As a** user
**I want** my session to last 30 days with automatic renewal
**So that** I don't have to log in multiple times a day

**Acceptance Criteria:**
- [ ] New `RefreshToken` model: `id`, `user_id` (FK), `token` (hashed), `expires_at`, `created_at`
- [ ] Create database migration for refresh_tokens table
- [ ] Access token expiration reduced to 15 minutes (short-lived)
- [ ] Refresh token expiration set to 30 days (long-lived)
- [ ] `POST /api/auth/login` returns both `access_token` and `refresh_token`
- [ ] `POST /api/auth/refresh` accepts refresh_token, returns new access_token + new refresh_token
- [ ] Old refresh token is invalidated when new one is issued (rotation)
- [ ] Invalid/expired refresh token returns 401
- [ ] Refresh token stored as httpOnly cookie (more secure than localStorage)
- [ ] Typecheck passes
- [ ] Unit tests pass

**Files:**
- `backend/app/database.py` - Add RefreshToken model
- `backend/alembic/versions/` - New migration
- `backend/app/routers/auth.py` - Update login, add refresh endpoint
- `backend/app/models/user.py` - Add TokenResponse schema with both tokens
- `backend/app/services/auth.py` - New service for token generation/validation
- `backend/tests/test_auth.py` - Refresh token tests

---

#### US-32.2: Frontend Token Refresh
**As a** user
**I want** my session to auto-renew in the background
**So that** I stay logged in without interruption

**Acceptance Criteria:**
- [ ] Login stores refresh_token in httpOnly cookie (set by backend)
- [ ] Access token stored in memory (not localStorage) for security
- [ ] Auth store includes `refreshAccessToken()` method
- [ ] API calls that receive 401 automatically attempt token refresh
- [ ] If refresh succeeds, retry original request with new token
- [ ] If refresh fails (401), redirect to login page
- [ ] Proactive refresh: refresh token 1 minute before access token expires
- [ ] Logout calls `POST /api/auth/logout` to invalidate refresh token
- [ ] Typecheck passes
- [ ] Unit tests pass

**Files:**
- `frontend/src/lib/stores/index.ts` - Update auth store with refresh logic
- `frontend/src/lib/api.ts` - New API wrapper with auto-refresh interceptor
- `frontend/src/routes/login/+page.svelte` - Update to handle new token format
- `backend/app/routers/auth.py` - Add logout endpoint to invalidate refresh token
- `frontend/tests/auth.test.ts` - Token refresh tests

---

#### US-32.3: Auto-Redirect on Session Expiration
**As a** user
**I want** to be automatically redirected to login when my session fully expires
**So that** I don't see broken pages with failed API calls

**Acceptance Criteria:**
- [ ] When refresh token fails (401), user is redirected to `/login`
- [ ] Auth state is fully cleared before redirect (no stale isAuthenticated)
- [ ] Redirect includes `?redirect=/original/path` query param
- [ ] After successful login, redirect back to original path
- [ ] Toast message shows "Session expired, please log in again"
- [ ] No more "Session expired" errors while staying on page
- [ ] Protected routes immediately redirect if not authenticated (no content flash)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: let session expire → automatic redirect to login

**Files:**
- `frontend/src/lib/api.ts` - Handle 401 with redirect
- `frontend/src/routes/+layout.svelte` - Improve route protection
- `frontend/src/routes/login/+page.svelte` - Handle redirect query param
- `frontend/src/lib/stores/index.ts` - Clear auth state properly

---

### Non-Goals
- "Remember me" checkbox (all sessions are 30 days)
- Multiple device session management (revoke other sessions)
- Session activity tracking/listing
- IP-based session binding

### Technical Considerations
- **Security:** Refresh tokens in httpOnly cookies prevent XSS token theft. Access tokens in memory prevent persistence attacks.
- **Token rotation:** Each refresh invalidates old token, limiting damage from token leak.
- **Race conditions:** If multiple tabs refresh simultaneously, handle gracefully (only first succeeds, others retry).
- **Backward compatibility:** First deploy keeps old 30-min tokens working until they expire naturally.
- **Cookie settings:** `SameSite=Strict`, `Secure=true` in production, `Path=/api/auth`.

---

## Checklist Summary

### Completed ✅ (73 stories)

See [ARCHIVED_PRD.md](./ARCHIVED_PRD.md) for completed epics and stories.

### Pending (29 stories)
- [ ] US-32.1: Refresh Token Backend Implementation
- [ ] US-32.2: Frontend Token Refresh
- [ ] US-32.3: Auto-Redirect on Session Expiration
- [ ] US-17.1: Multi-User Watch Data Aggregation
- [ ] US-17.2: Sync Progress Visibility
- [ ] US-18.1: Show Setup Checklist for New Users
- [ ] US-18.2: Auto-Sync After Jellyfin Configuration
- [ ] US-18.3: Optional Services Prompt
- [ ] US-19.1: Search Issues by Text
- [ ] US-20.1: Large Season Threshold Setting
- [ ] US-20.2: Calculate and Store Season Sizes
- [ ] US-20.3: Large Series Detection Service
- [ ] US-20.4: Large Content UI with Filter
- [ ] US-21.1: Slack Notification Service
- [ ] US-21.2: New User Signup Notifications
- [ ] US-21.3: Sync Failure Notifications
- [ ] US-23.1: Added Date Column on Issues Page
- [ ] US-22.1: Library API Endpoint
- [ ] US-22.2: Library Page with Sub-tabs
- [ ] US-22.3: Library Search and Filters
- [ ] US-22.4: Library Sorting
- [ ] US-24.1: Rate Limiting on Auth Endpoints
- [ ] US-25.1: Password Strength Indicator
- [ ] US-26.1: Sync Retry with Exponential Backoff
- [ ] US-25.2: Password Confirmation Field
- [ ] US-17.3: Fix Mobile Sidebar Visual Overlap
- [ ] US-27.1: E2E Auth Flow Test
- [ ] US-27.2: Sync Integration Tests with Mocked APIs
- [ ] US-28.1: Loading States Accessibility
- [ ] US-29.1: Add Requester Column to Issues Table
- [ ] US-30.1: Remove Currently Airing Placeholder
- [ ] US-31.1: Recently Available Days Setting (Backend)
- [ ] US-31.2: Recently Available Days Setting (Frontend)
- [ ] US-31.3: User Nickname Mapping (Backend)
- [ ] US-31.4: User Nickname Mapping (Frontend)
- [ ] US-31.5: Copy Output Grouped by Requester
