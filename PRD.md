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
- [x] Sync fetches media items from ALL Jellyfin users (not just first user)
- [x] Watch data is aggregated: `played = True` if ANY user has watched
- [x] `last_played_date` uses the MOST RECENT date across all users
- [x] `play_count` sums all users' play counts
- [x] Uses `asyncio.gather()` to parallelize user fetches (6-15 users expected)
- [x] Progress logging shows which user is being synced (e.g., "Fetching user 3/10: John")
- [x] Existing sync tests still pass
- [x] New test verifies multi-user aggregation logic
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify "La Chambre de Mariana" shows correct watch date after sync

**Note:** Implemented multi-user watch data aggregation with asyncio.gather() parallelization, aggregate_user_watch_data() for combining watch data, and progress logging per user

**Files:**
- `backend/app/services/sync.py` - Modify `fetch_jellyfin_media()` to loop through all users and aggregate
- `backend/tests/test_sync_service.py` - Add test for multi-user aggregation

---

#### US-17.2: Sync Progress Visibility
**As a** user
**I want** to see detailed sync progress in the UI
**So that** I know what's happening during the longer sync

**Acceptance Criteria:**
- [x] Backend stores sync progress details (current step, current user being fetched)
- [x] `GET /api/sync/status` returns progress info: `current_step`, `total_steps`, `current_user_name`
- [x] Frontend displays progress during sync (e.g., "Fetching user 3/10: John...")
- [x] Progress updates while sync is running (poll every 2-3 seconds)
- [x] Shows "Syncing media..." or "Syncing requests..." as appropriate
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: trigger sync and see progress updates

**Note:** Added progress tracking fields to SyncStatus model, update_sync_progress() function, modified fetch_jellyfin_media_with_progress() to update per-user progress during batch processing, frontend polls /api/sync/status every 2s during sync and displays progress message

**Files:**
- `backend/app/database.py` - Add progress fields to SyncStatus model (or use separate table)
- `backend/app/services/sync.py` - Update progress during sync steps
- `backend/app/routers/sync.py` - Return progress in status endpoint
- `frontend/src/routes/dashboard/+page.svelte` - Display progress during sync

---

#### US-17.2.1: Populate Sync Progress User Names
**As a** user
**I want** to see which Jellyfin user is being synced
**So that** I can understand the progress in detail

**Problem:**
US-17.2 implementation shows generic "Syncing media..." instead of detailed progress like "Fetching user 3/10: John...". The `current_user_name` parameter is never passed to `update_sync_progress()` in `fetch_jellyfin_media_with_progress()`.

**Acceptance Criteria:**
- [x] Backend: `fetch_jellyfin_media_with_progress()` passes `current_user_name` to `update_sync_progress()`
- [x] During batch processing, extract current user's display name from Jellyfin users list
- [x] Pass display name (e.g., "John", "Admin") to progress update function
- [x] Frontend displays "Fetching user 3/10: John..." instead of "Syncing media..."
- [x] Progress message updates with each user's name during sync
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: trigger sync and see user names in progress messages

**Note:** Implementation already complete. Backend sync.py:456-460 extracts user name and passes to update_sync_progress(). Frontend +page.svelte:159-160 displays 'Fetching user X/Y: Name...' format.

**Files:**
- `backend/app/services/sync.py` - Add `current_user_name` parameter to `update_sync_progress()` calls
- `backend/tests/test_sync_service.py` - Add test for user name in progress

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
- [x] On mobile (viewport < 768px), when sidebar is closed, no part of it is visible
- [x] No blue strip or other visual artifacts on left edge
- [x] Sidebar still opens/closes correctly with hamburger menu
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using mobile viewport (Chrome DevTools device mode)

**Note:** Added visibility: hidden when sidebar is closed on mobile, visibility: visible when open. This ensures the sidebar is completely hidden when translated off-screen.

**Files:**
- `frontend/src/lib/components/Sidebar.svelte` - Fix CSS transform/position values for mobile

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
- [x] Add `aria-busy="true"` to parent containers during loading
- [x] Loading spinners have `aria-label="Loading"` or equivalent
- [x] Add `aria-live="polite"` regions for dynamic content updates
- [x] Dashboard loading state is accessible
- [x] Issues page loading state is accessible
- [x] Settings page loading state is accessible
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify with screen reader or accessibility inspector

**Note:** Added aria-busy to parent containers (dashboard, issues-page, settings-page, library-page, whitelist-page, page), aria-label/role='status' to loading divs, aria-hidden to spinners, and aria-live='polite' to dynamic content regions.

**Files:**
- `frontend/src/routes/+page.svelte` - Dashboard accessibility
- `frontend/src/routes/issues/+page.svelte` - Issues page accessibility
- `frontend/src/routes/settings/+page.svelte` - Settings page accessibility

### Non-Goals
- Full WCAG 2.1 compliance audit
- High contrast theme

---

## Epic 33: Total Series Size in Library

### Overview
Display the total size of TV series in the library. Currently, series show "Unknown size" because the sync process only calculates the largest season size (`largest_season_size_bytes`) but not the total series size (`size_bytes`). This epic extends the existing season size calculation to also track total series size.

### Goals
- Show actual series sizes instead of "Unknown size" in the library
- Enable size filtering and sorting for series
- Include series sizes in total library size calculations
- Leverage existing episode API calls (no additional overhead)

### User Stories

#### US-33.1: Calculate and Store Total Series Size
**As a** media server owner
**I want** to see the total size of each series in my library
**So that** I can understand how much storage each series consumes

**Acceptance Criteria:**
- [x] `calculate_season_sizes()` calculates both largest season size AND total series size
- [x] Total series size is stored in `CachedMediaItem.size_bytes` for series
- [x] Library page displays actual series sizes instead of "Unknown size"
- [x] Size filter works correctly for series (e.g., min_size_gb, max_size_gb)
- [x] Size sort works correctly for series
- [x] Total library size header includes series sizes
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in Docker using local integration test

**Note:** Modified calculate_season_sizes() to accumulate total_series_size across all seasons and store in size_bytes. Added unit tests to verify total series size calculation.

**Implementation Details:**

Backend changes in `backend/app/services/sync.py`:
1. Update `calculate_season_sizes()` function (line 736-817)
2. Track `total_series_size` variable that accumulates ALL episode sizes
3. After processing all seasons for a series, set both:
   - `series.size_bytes = total_series_size` (NEW)
   - `series.largest_season_size_bytes = max(season_sizes)` (existing)

**Size Calculation Logic:**
For each series:
1. Fetch all seasons (already done)
2. For each season, fetch all episodes (already done)
3. Calculate season total size (already done)
4. **NEW:** Accumulate episode sizes into `total_series_size`
5. After all seasons processed:
   - Set `series.largest_season_size_bytes = max(season_sizes)` (existing)
   - **NEW:** Set `series.size_bytes = total_series_size`

**Edge Cases:**
- Series with no episodes: `size_bytes` remains NULL (correct - no data to calculate)
- Series with missing episode sizes: Sum only episodes with valid sizes
- API failures for specific seasons: Log warning, continue to next season (existing behavior)

**Files:**
- `backend/app/services/sync.py` - Update `calculate_season_sizes()` function
- `backend/tests/test_sync.py` - Add tests for total series size calculation

### Non-Goals
- Displaying per-season sizes in the UI (out of scope)
- Recalculating sizes for existing cached series (will be updated on next sync)
- Adding "Average episode size" metric (not requested)
- Backend API changes (frontend already displays size_bytes correctly)

### Technical Considerations
- **No additional API calls:** Reuses existing episode fetches for season size calculation
- **Database:** No migration needed - `size_bytes` column already exists, just not populated for series
- **Performance:** No impact - calculation happens in background after main sync
- **Data source:** Episode sizes from Jellyfin API `MediaSources[0].Size`

### Verification Plan

1. **Unit Tests:**
   ```bash
   cd backend
   uv run pytest tests/test_sync.py::test_calculate_season_sizes -v
   ```

2. **Integration Test (Local Docker):**
   ```bash
   # Start local Docker
   docker-compose up --build -d

   # Login as test user
   APP_USER_EMAIL=$(grep '^APP_USER_EMAIL=' .env.example | cut -d'=' -f2)
   APP_USER_PASSWORD=$(grep '^APP_USER_PASSWORD=' .env.example | cut -d'=' -f2)
   TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
     -H "Content-Type: application/json" \
     -d "{\"email\":\"$APP_USER_EMAIL\",\"password\":\"$APP_USER_PASSWORD\"}" \
     | jq -r '.access_token')

   # Trigger sync
   curl -s -X POST http://localhost:8080/api/sync/trigger \
     -H "Authorization: Bearer $TOKEN"

   # Wait for sync to complete, then verify series sizes
   curl -s http://localhost:8080/api/library?type=series \
     -H "Authorization: Bearer $TOKEN" | jq '.items[] | {name, size_formatted}'
   ```

3. **Manual UI Verification:**
   - Navigate to http://localhost:5173/library
   - Filter by "Series" tab
   - Verify "Size (GB)" column shows actual sizes (not "Unknown size")
   - Verify sort by size works
   - Verify header shows correct total size including series

---

## Epic 34: Unavailable Requests Table UX

### Overview
Improve the usability and visual consistency of the Unavailable requests table. Currently, the table has several UX issues: the Name column is truncated too aggressively, the Issues column wastes space showing the same "REQUEST" badge for every item, column headers have inconsistent casing, and not all columns are sortable.

### Goals
- Give more space to the Name column by removing redundant Issues column
- Create consistent visual design with uniform header casing
- Enable sorting on all columns (Requester, Release)
- Improve overall table readability and professionalism

### User Stories

#### US-34.1: Hide Issues Column on Unavailable Tab
**As a** user viewing unavailable requests
**I want** the Issues column hidden on the Unavailable tab
**So that** I have more space for useful information like the content name

**Problem:**
The Issues column takes up ~30% of table width but only shows "REQUEST" badge for every item on the Unavailable tab. This is redundant since being on this tab already implies all items are requests.

**Acceptance Criteria:**
- [x] Issues column is not rendered when `activeFilter === 'requests'`
- [x] Name column expands to use the freed space (increase from 35% to ~45%)
- [x] Other tabs (All, Old, Large, Language) still show the Issues column
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added conditional rendering for Issues column header and cells using {#if activeFilter !== 'requests'}. Added requests-view class to table and CSS rule to expand .col-name from 35% to 45% when in requests view.

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Conditionally hide Issues column and header

---

#### US-34.2: Normalize Table Header Casing
**As a** user
**I want** consistent header casing across all columns
**So that** the table looks professional and cohesive

**Problem:**
Current headers have inconsistent casing:
- "Name" - Title case
- "REQUESTER" - ALL CAPS
- "Issues" - Title case
- "Size" - Title case
- "Added" - Title case
- "RELEASE" - ALL CAPS
- "Requested" - Title case

**Acceptance Criteria:**
- [x] All headers use Title Case: Name, Requester, Issues, Size, Added, Release, Requested/Watched
- [x] No ALL CAPS headers remain in the table
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Removed text-transform: uppercase from .issues-table th CSS rule. Headers now display in Title Case as written in HTML.

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Update header text in `<th>` elements

---

#### US-34.3: Add Sorting to Requester and Release Columns
**As a** user viewing unavailable requests
**I want** to sort by Requester or Release date
**So that** I can find requests from specific users or by upcoming releases

**Problem:**
Looking at the current implementation, Requester and Release column headers don't have sort buttons. Only Name, Issues, Size, Added, and Watched/Requested have sorting enabled.

**Acceptance Criteria:**
- [x] Requester column header is wrapped in a sort button and clickable
- [x] Release column header is wrapped in a sort button and clickable
- [x] Sort indicators (↑/↓) appear on active sort column
- [x] Add 'requester' and 'release' to the `SortField` type
- [x] Sorting logic added to `getSortedItems()` for 'requester' (alphabetical) and 'release' (date comparison)
- [x] Requester sorts alphabetically (ascending by default)
- [x] Release sorts by date (descending by default - newest first)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added 'requester' and 'release' to SortField type. Implemented sorting logic: requester sorts alphabetically with nulls last, release sorts by date with nulls last. Both column headers wrapped in sort buttons with sort indicators.

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Update SortField type, add sort buttons to headers, extend getSortedItems()

### Non-Goals
- Changing the overall table layout or column order
- Modifying badge styling or colors
- Backend API changes (all changes are frontend-only)
- Adding filtering by requester (future enhancement)

### Technical Considerations
- **Frontend-only changes** to `frontend/src/routes/issues/+page.svelte`
- Update `SortField` type to include `'requester' | 'release'`
- Follow existing sort button pattern from other headers
- Requester sort: `a.requested_by?.localeCompare(b.requested_by ?? '') ?? 0`
- Release sort: Compare `release_date` as dates, handle null values

---

## Epic 35: Issues Table Watch Data Fixes

### Overview
Fix two related bugs in the Issues table related to watch data display and sorting. First, the Watched column sorting is incorrect - it should order by most recent → oldest → "Watched" (no date) → "Never", but currently mixes up the order. Second, series display only "Watched" status without showing the actual last watched date like movies do.

### Goals
- Fix Watched column sort order to be chronologically correct
- Display last watched dates for series (not just "Watched" status)
- Improve consistency between movie and series watch data display

### User Stories

#### US-35.1: Fix Watched Column Sort Order
**As a** media server owner
**I want** the Watched column to sort chronologically from newest to oldest
**So that** I can easily find recently watched content or identify never-watched items

**Problem:**
When sorting by the Watched column, the order is incorrect. Currently, "Never" and "Watched" entries are mixed up. The correct order should be:
1. Most recent watched date (newest first)
2. Older watched dates
3. "Watched" (no specific date)
4. "Never" (never watched)

**Acceptance Criteria:**
- [x] Clicking Watched column header sorts items in correct order: date DESC → "Watched" → "Never"
- [x] Items with last_played_date display in descending order (newest first)
- [x] Items with played=true but no last_played_date show "Watched" and sort after dated items
- [x] Items with played=false show "Never" and sort last
- [x] Clicking the column again reverses the order: "Never" → "Watched" → date ASC
- [x] Sort works correctly for both movies and series
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added 'watched' sort field to SortField type. Implemented three-tier sorting in getSortedItems: priority 1 (has date) → priority 2 (played=true, no date) → priority 3 (never watched). Descending shows most recent first, ascending shows never-watched first. Column header now uses 'watched' field instead of 'date' for non-requests tabs.

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Fix `getSortedItems()` logic for 'watched' field

---

#### US-35.2: Display Last Watched Date for Series
**As a** media server owner
**I want** to see the last watched date for series, not just "Watched" status
**So that** I can understand when I last engaged with each series

**Problem:**
Currently, the Watched column shows:
- Movies: "Jan 15, 2025" or "Never" (correctly shows last_played_date)
- Series: "Watched" or "Never" (only shows boolean status, missing date)

This is inconsistent and less useful for series. Series should display their last_played_date just like movies.

**Acceptance Criteria:**
- [ ] Series with last_played_date display formatted date (e.g., "Jan 15, 2025")
- [ ] Series with played=true but no last_played_date display "Watched"
- [ ] Series with played=false display "Never"
- [ ] Display logic matches movies exactly (same formatting function)
- [ ] Backend API already provides last_played_date for series (verify in API response)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: series show dates instead of generic "Watched"

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Update `formatWatched()` or display logic to handle series dates

### Non-Goals
- Changing the watched date format (keep existing format)
- Displaying per-episode watch history for series
- Backend API changes (data is already available)

### Technical Considerations
- **Sort Order Logic**: Use null-safe comparison that handles:
  - Date strings (sort chronologically)
  - `played=true, last_played_date=null` (sort after all dates)
  - `played=false` (sort last)
- **Frontend-only changes**: No backend modifications needed - API already returns correct data
- **Consistency**: Both movies and series should use identical display/sort logic

---


## Epic 36: Settings Page Refactoring

### Overview
The Settings page has grown to **2,130 lines** and contains four distinct sections that are conceptually separate: Connections (API integrations), Thresholds (analysis preferences), Users (nickname mappings), and Display (UI preferences). This epic splits the monolithic page into separate routes with a shared layout for better maintainability and navigation.

### Goals
- Reduce cognitive load by splitting settings into focused pages
- Improve navigation with dedicated URLs for each section
- Enable direct linking to specific settings sections
- Make the codebase more maintainable with smaller, focused components
- Follow the pattern used by Linear, GitHub Settings, etc.

### User Stories

#### US-36.1: Settings Layout with Sidebar Navigation
**As a** user
**I want** a sidebar navigation within Settings
**So that** I can easily navigate between different settings sections

**Acceptance Criteria:**
- [ ] Create `/settings/+layout.svelte` with sidebar navigation
- [ ] Sidebar shows 4 nav items: Connections, Thresholds, Users, Display
- [ ] Each nav item links to its respective route (`/settings/connections`, etc.)
- [ ] Active nav item is visually highlighted
- [ ] Breadcrumb shows: Dashboard > Settings > [Section Name]
- [ ] `/settings` redirects to `/settings/connections` (default section)
- [ ] Layout is responsive: sidebar collapses to horizontal tabs on mobile
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/settings/+layout.svelte` - New layout with sidebar
- `frontend/src/routes/settings/+page.svelte` - Redirect to /settings/connections

---

#### US-36.2: Extract Connections Page
**As a** user
**I want** to manage API connections on a dedicated page
**So that** I can focus on configuring my services without distraction

**Acceptance Criteria:**
- [ ] Create `/settings/connections/+page.svelte` with all connection forms
- [ ] Includes Jellyfin, Jellyseerr, Radarr, Sonarr connection cards
- [ ] All existing functionality preserved: expand/collapse, validation, save, status indicators
- [ ] Form state is local to the page (not shared with other settings pages)
- [ ] Loading states work correctly on initial page load
- [ ] Success/error messages display inline as before
- [ ] Remove connections section from old settings page
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: all connection flows work correctly

**Files:**
- `frontend/src/routes/settings/connections/+page.svelte` - New page
- `frontend/src/routes/settings/+page.svelte` - Remove connections section

---

#### US-36.3: Extract Thresholds Page
**As a** user
**I want** to configure analysis thresholds on a dedicated page
**So that** I can adjust detection settings without scrolling through other options

**Acceptance Criteria:**
- [ ] Create `/settings/thresholds/+page.svelte` with threshold inputs
- [ ] Includes: Old content months, Min age months, Large movie size, Large season size
- [ ] Save and Reset buttons work correctly
- [ ] Help text shows which feature uses each threshold
- [ ] Loading state on initial fetch
- [ ] Success/error messages display inline
- [ ] Remove thresholds section from old settings page
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: threshold changes save and persist

**Files:**
- `frontend/src/routes/settings/thresholds/+page.svelte` - New page
- `frontend/src/routes/settings/+page.svelte` - Remove thresholds section

---

#### US-36.4: Extract Users Page
**As a** user
**I want** to manage user nicknames on a dedicated page
**So that** I can easily configure display names for requesters

**Acceptance Criteria:**
- [ ] Create `/settings/users/+page.svelte` with nickname management
- [ ] Table displays existing mappings: Jellyseerr Username → Display Name
- [ ] Add, edit, delete functionality preserved
- [ ] Delete confirmation flow works
- [ ] Empty state message with call to action
- [ ] Toast feedback on CRUD operations
- [ ] Remove nicknames section from old settings page
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: all nickname CRUD operations work

**Files:**
- `frontend/src/routes/settings/users/+page.svelte` - New page
- `frontend/src/routes/settings/+page.svelte` - Remove nicknames section

---

#### US-36.5: Extract Display Page
**As a** user
**I want** to configure display preferences on a dedicated page
**So that** I can customize my viewing experience

**Acceptance Criteria:**
- [ ] Create `/settings/display/+page.svelte` with display options
- [ ] Includes: Theme selector (Light/Dark/System), Recently available days, Show unreleased requests toggle
- [ ] Theme changes apply immediately (no save button needed)
- [ ] Days input saves on change
- [ ] Toggle saves on change
- [ ] Remove display section from old settings page
- [ ] Delete the original `/settings/+page.svelte` (now empty)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: all display settings work correctly

**Files:**
- `frontend/src/routes/settings/display/+page.svelte` - New page
- `frontend/src/routes/settings/+page.svelte` - DELETE (redirect only remains in layout)

### Non-Goals
- Backend API changes (all existing endpoints are reused)
- Changing any settings functionality (just reorganizing)
- Adding new settings options
- Persistent form state across navigation (each page is independent)

### Technical Considerations

**Route Structure:**
```
frontend/src/routes/settings/
├── +layout.svelte         # Sidebar navigation + breadcrumb
├── +page.svelte           # Redirect to /settings/connections
├── connections/
│   └── +page.svelte       # Jellyfin, Jellyseerr, Radarr, Sonarr
├── thresholds/
│   └── +page.svelte       # Analysis thresholds
├── users/
│   └── +page.svelte       # User nicknames
└── display/
    └── +page.svelte       # Theme, days, toggles
```

**Shared Components (consider extracting):**
- Connection card component (used 4x for different services)
- Inline form error/success message component

**API Calls per Page:**
- Connections: `/api/settings/jellyfin`, `/api/settings/jellyseerr`, `/api/settings/radarr`, `/api/settings/sonarr`, `/api/sync/status`
- Thresholds: `/api/settings/analysis`
- Users: `/api/settings/nicknames`
- Display: `/api/settings/display`

**Migration Strategy:**
1. Create layout first (US-36.1)
2. Extract pages one by one (US-36.2-36.5), each removing its section from the old page
3. Final story deletes the now-empty original page

**Testing Strategy:**
- Move existing settings tests to page-specific test files
- Add navigation tests in layout test file
- Verify E2E that settings flows still work end-to-end


## Epic 37: Prefill Jellyfin Users for Nickname Mapping

### Overview

The user nickname mapping feature currently requires manual entry of Jellyseerr usernames. Since the app already syncs Jellyfin user data, we should automatically prefill the nicknames table with all Jellyfin users, making it faster to set up friendly display names for "Recently Available" notifications.

### Goals

- Reduce manual data entry - users shouldn't have to type usernames that the app already knows
- Surface all Jellyfin users for nickname configuration without requiring manual discovery
- Detect and warn about Jellyfin users who don't have Jellyseerr accounts (common edge case)
- Respect existing nickname mappings - don't overwrite user customizations

### User Stories

#### US-37.1: Prefill Nicknames During Sync (Backend)

**As a** developer
**I want** to automatically create nickname records for all Jellyfin users during sync
**So that** the nicknames table is prepopulated without user intervention

**Acceptance Criteria:**
- [x] During sync, after fetching Jellyfin users, upsert UserNickname records for each user
- [x] Use Jellyfin username as `jellyseerr_username` (assumption: same username across systems)
- [x] Leave `display_name` empty (user will fill in their preferred friendly name)
- [x] If nickname record already exists for a username, skip it (preserve existing mappings)
- [x] Add `has_jellyseerr_account` boolean field to UserNickname model (default False)
- [x] Query Jellyseerr users API during sync and mark matching usernames as `has_jellyseerr_account=True`
- [x] Typecheck passes
- [x] Unit tests pass

**Technical Notes:**
- Fetch Jellyseerr users: `GET /api/v1/user` (requires admin permissions)
- Use bulk insert/upsert pattern to avoid N+1 queries
- Run after both Jellyfin and Jellyseerr data fetched (so we have both user lists)

**Files to modify:**
- `backend/app/database.py` - Add `has_jellyseerr_account` field to UserNickname model
- `backend/app/services/sync.py` - Add `prefill_user_nicknames()` function, call from `sync_user_data()`
- `backend/app/services/external_apis/jellyseerr.py` - Add `fetch_jellyseerr_users()` function
- `backend/tests/test_sync.py` - Add test for nickname prefilling
- Create new Alembic migration for `has_jellyseerr_account` column

#### US-37.2: Display Prefilled Users in UI

**As a** user
**I want** to see all my Jellyfin users already listed in the nicknames table
**So that** I can immediately add display names without typing usernames

**Acceptance Criteria:**
- [ ] When users page loads, prefilled Jellyfin users appear in the table
- [ ] Prefilled rows show username in "Jellyseerr Username" column
- [ ] Display name column is empty (awaiting user input)
- [ ] Users with `has_jellyseerr_account=False` show warning badge next to username
- [ ] Warning badge tooltip: "This Jellyfin user was not found in Jellyseerr. They may not be able to request content."
- [ ] Users can still edit/delete prefilled rows normally
- [ ] Empty state only shows if NO nicknames exist (not even prefilled ones)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Technical Notes:**
- Use existing `GET /api/settings/nicknames` endpoint
- Add `has_jellyseerr_account` field to NicknameResponse schema
- Frontend filters out rows without display_name when grouping in Recently Available copy function

**Files to modify:**
- `backend/app/models/settings.py` - Add `has_jellyseerr_account` to NicknameResponse
- `frontend/src/routes/settings/users/+page.svelte` - Display warning badge for users without Jellyseerr account
- `frontend/tests/settings-users.test.ts` - Add tests for prefilled users display

#### US-37.3: Manual Refresh Button for Jellyfin Users

**As a** user
**I want** to manually refresh the Jellyfin users list
**So that** I can add newly created Jellyfin users to nicknames without waiting for next sync

**Acceptance Criteria:**
- [x] Users page has "Refresh users" button above the table
- [x] Button triggers backend endpoint to fetch Jellyfin users and prefill nicknames
- [x] Shows loading spinner while fetching
- [x] On success: toast "X new users added", table updates
- [x] On error: toast with error message
- [x] Button disabled during refresh
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added POST /api/settings/nicknames/refresh endpoint to fetch Jellyfin users and prefill nicknames. Frontend settings page has 'Refresh users' button (only shown when Jellyfin is configured) with loading state, success/error toasts.

**Technical Notes:**
- Create new endpoint: `POST /api/settings/nicknames/refresh`
- Reuse nickname prefilling logic from sync service
- Returns count of newly added users

**Files to modify:**
- `backend/app/routers/settings.py` - Add `POST /api/settings/nicknames/refresh` endpoint
- `backend/app/services/settings.py` - Extract nickname prefilling into reusable function
- `frontend/src/routes/settings/users/+page.svelte` - Add refresh button with loading state
- `frontend/tests/settings-users.test.ts` - Add tests for refresh functionality

### Non-Goals

- Automatic deletion of nickname records for Jellyfin users who no longer exist (user must manually clean up)
- Syncing display names from Jellyfin (users want custom nicknames, not system usernames)
- Validating that Jellyseerr usernames actually exist (warning badge is informational only)
- Auto-filling display name field (user should intentionally choose friendly names)

### Technical Considerations

**Database Changes:**
- Add `has_jellyseerr_account` boolean column to `user_nicknames` table
- Requires new Alembic migration

**API Dependencies:**
- Jellyfin users: Already fetched during sync via `GET /Users` (public users only)
- Jellyseerr users: Need new API call `GET /api/v1/user` (admin only)

**Edge Cases:**
- Jellyfin username differs from Jellyseerr username: User must manually edit the mapping
- User deleted from Jellyfin: Nickname record remains (user can delete manually)
- User added to Jellyseerr after sync: Warning badge persists until next sync/refresh

**Performance:**
- Prefilling runs during sync (already async background task)
- Manual refresh is synchronous but fast (typically <10 users)
- Use bulk upsert to avoid N+1 database queries

### Success Metrics

- Users page shows prefilled usernames immediately after first sync
- Reduced manual data entry: users only fill display names, not both fields
- Warning badges help users identify Jellyfin users who can't request content

---

## Epic 38: Title Language Preference for Recently Available

### Overview

Add a user setting to choose between English and French for the Recently Available page. When French is selected, movie/TV show titles are displayed in French (fetched from TMDB) both in the table and in the copy output. This mirrors the original script's behavior where French titles were used for the "Recently Available" WhatsApp messages.

### Goals

- Allow users to view and copy Recently Available content with French titles
- Store French titles during sync to avoid API delays when copying
- Provide seamless fallback to English when French titles are unavailable

### User Stories

#### US-38.1: Add Title Language User Setting

**As a** media server owner
**I want** to choose my preferred language (English or French) for content titles
**So that** I can view and copy titles in my preferred language

**Acceptance Criteria:**
- [x] Settings > Display Preferences has "Title language" dropdown with options: English (default), French
- [x] Add `title_language` column to `UserSettings` table (String(2), default='en')
- [x] Create database migration for new column
- [x] GET `/api/settings/display` returns `title_language` field
- [x] POST `/api/settings/display` accepts `title_language` field
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: dropdown appears in Settings > Display and persists

**Files:**
- `backend/app/database.py` - Add `title_language` column to UserSettings
- `backend/alembic/versions/` - Create migration for new column
- `backend/app/models/settings.py` - Add `title_language` to DisplayPreferencesResponse/Create
- `backend/app/routers/settings.py` - Handle `title_language` in display endpoints
- `frontend/src/routes/settings/+page.svelte` - Add Title Language dropdown

---

#### US-38.2: Store French Titles During Sync

**As a** media server owner
**I want** French titles to be fetched and stored during sync
**So that** I can view content in French without API delays

**Acceptance Criteria:**
- [x] Add `title_fr` column to `CachedJellyseerrRequest` model (String(500), nullable)
- [x] Create database migration for new column
- [x] Sync service fetches French titles from TMDB (`language=fr` parameter)
- [x] Add `language` parameter to `fetch_media_details()` function
- [x] During sync, fetch both English and French titles (two API calls per media item)
- [x] French titles stored in `title_fr` column
- [x] Sync handles missing French titles gracefully (stores None)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify after sync: `title_fr` column populated in database

**Files:**
- `backend/app/database.py` - Add `title_fr` column to CachedJellyseerrRequest
- `backend/alembic/versions/` - Create migration for new column
- `backend/app/services/sync.py` - Update `fetch_media_details()` and sync loop to fetch French titles

---

#### US-38.3: Recently Available Uses Language Preference

**As a** user who prefers French
**I want** the Recently Available page to show French titles
**So that** I can view and share content lists in French

**Acceptance Criteria:**
- [ ] `RecentlyAvailableItem` model includes `title_fr` field (nullable string)
- [ ] API `/api/info/recent` returns both `title` and `title_fr` for each item
- [ ] Frontend reads user's `title_language` preference from display settings
- [ ] Table displays titles in preferred language
- [ ] Copy button outputs titles in preferred language
- [ ] If French title unavailable, falls back to English title
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: table shows French titles when setting is French
- [ ] Verify in browser: copy output contains French titles when setting is French

**Files:**
- `backend/app/models/content.py` - Add `title_fr` to `RecentlyAvailableItem`
- `backend/app/services/content.py` - Include `title_fr` in `get_recently_available()`
- `frontend/src/routes/info/recent/+page.svelte` - Use language preference for display and copy

### Non-Goals

- Translating other UI text (only media titles)
- Changing any other page's display language
- Supporting languages other than English/French
- Fetching French titles on-demand (always prefetch during sync)

### Technical Considerations

**Database Changes:**
```python
# UserSettings - add column
title_language: Mapped[str | None] = mapped_column(String(2), nullable=True)  # 'en' or 'fr', default 'en'

# CachedJellyseerrRequest - add column
title_fr: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

**Sync Service Changes:**
- `fetch_media_details()` gains optional `language: str = "en"` parameter
- During sync, call TMDB twice per media item: once for 'en', once for 'fr'
- Cache both results to avoid duplicate lookups

**API Response Changes:**
```python
class RecentlyAvailableItem(BaseModel):
    jellyseerr_id: int
    title: str
    title_fr: str | None  # NEW
    media_type: str
    availability_date: str
    requested_by: str | None
    display_name: str | None
```

**Frontend Changes:**
- Settings page: Add dropdown to Display Preferences section
- Recently Available page: Read `title_language` from settings and use `item.title_fr || item.title` when French selected

**Original Script Reference:**
Lines 2796-2804 in `original_script.py` show how French titles were fetched:
```python
if media_type == 'movie':
    details = fetch_movie_details(tmdb_id, 'fr')
    if details:
        title = details.get('title', title)
elif media_type == 'tv':
    details = fetch_tv_details(tmdb_id, 'fr')
    if details:
        title = details.get('name', title)
```

### Verification Plan

1. **After US-38.1:** Go to Settings > Display, verify dropdown appears and persists
2. **After US-38.2:** Trigger sync, verify `title_fr` column populated in database
3. **After US-38.3:**
   - Set language to French in Settings
   - Go to Recently Available page
   - Verify table shows French titles (e.g., "Le Robot Sauvage" instead of "The Wild Robot")
   - Click Copy, verify clipboard contains French titles

---

## Epic 39: Toast Notifications UX Improvements

### Overview

Enhance toast notifications with manual dismiss buttons and visual type indicators (icons) to improve usability and message comprehension. Currently, toasts auto-dismiss after 3 seconds with no way for users to keep them visible or manually close them. This epic adds user control and visual polish without changing core functionality.

### Goals

- Add manual dismiss capability to all toast types
- Provide visual indicators (icons) to distinguish toast types at a glance
- Maintain current 3-second auto-dismiss behavior
- Keep implementation simple and consistent across all toast types

### User Stories

#### US-39.1: Add Manual Dismiss Button to Toasts

**As a** user
**I want** to manually dismiss toast notifications
**So that** I can control when messages disappear

**Acceptance Criteria:**
- [ ] All toasts (success, error, info) display an "X" close button in the top-right corner
- [ ] Clicking the close button immediately removes the toast
- [ ] Close button is keyboard accessible (Tab to focus, Enter/Space to activate)
- [ ] Close button has `aria-label="Close notification"`
- [ ] Toasts still auto-dismiss after 3 seconds if not manually closed
- [ ] Close button is visually distinct but doesn't dominate the toast
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/lib/components/Toast.svelte` - Add close button with click handler
- `frontend/src/lib/stores/toastStore.ts` - Ensure dismiss function is exported/accessible
- `frontend/tests/toast.test.ts` - Add tests for manual dismiss

---

#### US-39.2: Add Type Icons to Toasts

**As a** user
**I want** to see an icon indicating the toast type
**So that** I can quickly understand the message severity at a glance

**Acceptance Criteria:**
- [ ] Success toasts show ✓ (checkmark) icon
- [ ] Error toasts show ✕ (X) icon
- [ ] Info toasts show ℹ (info) icon
- [ ] Warning toasts show ⚠ (warning triangle) icon (if warning type exists)
- [ ] Icons are positioned on the left side of the message text
- [ ] Icons use semantic colors matching toast background (green for success, red for error, etc.)
- [ ] Icons have appropriate `aria-hidden="true"` (decorative, message text conveys meaning)
- [ ] Icon size is proportional to text size (~16-20px)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

**Files:**
- `frontend/src/lib/components/Toast.svelte` - Add icon rendering based on toast type
- `frontend/src/lib/stores/toastStore.ts` - Ensure toast type is passed to component
- `frontend/tests/toast.test.ts` - Add tests for icon display per type

### Non-Goals

- Changing auto-dismiss timing (stays 3 seconds)
- Adding toast stacking or queue management
- Persistent toast notifications (all still auto-dismiss)
- Toast positioning or animation changes
- Adding new toast types beyond existing ones

### Technical Considerations

**Toast Component Structure:**
```svelte
<div class="toast {type}" role="status" aria-live="polite">
  <span class="toast-icon" aria-hidden="true">{icon}</span>
  <span class="toast-message">{message}</span>
  <button class="toast-close" aria-label="Close notification" on:click={dismiss}>
    ×
  </button>
</div>
```

**Icon Mapping:**
```typescript
const iconMap = {
  success: '✓',
  error: '✕',
  info: 'ℹ',
  warning: '⚠'
};
```

**Accessibility:**
- Close button must be keyboard accessible (native `<button>` handles this)
- Icon is decorative (`aria-hidden="true"`) since toast type is conveyed by color and text
- Toast container has `role="status"` and `aria-live="polite"` for screen reader announcements

**Testing Strategy:**
- Unit tests: Verify icon rendered for each toast type, verify dismiss button click handler
- Browser verification: Trigger all toast types (success, error, info), verify icons and close button work

**Current Toast Implementation:**
Check existing toast code in:
- `frontend/src/lib/components/Toast.svelte` (if exists)
- `frontend/src/lib/stores/toastStore.ts`
- Usage sites: Login, Register, Settings, Dashboard, etc.

---

## Epic 40: Help Page Fixes

### Overview

Fix incorrect links on the Help page. Currently, the Help page links to the claude-code GitHub repository instead of the actual Media Janitor project repository, preventing users from reporting issues or viewing project-specific documentation.

### Goals

- Correct the GitHub repository link to point to the Media Janitor project
- Ensure users can find the correct place to report issues or view code

### User Stories

#### US-40.1: Fix GitHub Repository Link

**As a** user seeking help
**I want** the Help page to link to the correct project repository
**So that** I can report issues or view the project code

**Problem:**
The Help page currently links to `https://github.com/anthropics/claude-code/issues` (Claude Code CLI tool) instead of the actual Media Janitor project repository at `https://github.com/jimmydore/mediajanitor`.

**Acceptance Criteria:**
- [ ] Help page link points to `https://github.com/jimmydore/mediajanitor`
- [ ] Link opens in a new tab (`target="_blank" rel="noopener noreferrer"`)
- [ ] Link text clearly indicates it's the project repository (e.g., "View project on GitHub" or "Report an issue")
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: clicking link opens correct repository

**Files:**
- `frontend/src/routes/help/+page.svelte` - Update GitHub link URL

### Non-Goals

- Adding additional help content or documentation links
- Redesigning the Help page layout
- Adding contact/support information

### Technical Considerations

**Current Link (Incorrect):**
```
https://github.com/anthropics/claude-code/issues
```

**Correct Link:**
```
https://github.com/jimmydore/mediajanitor
```

**Link Attributes:**
- Use `target="_blank"` to open in new tab
- Include `rel="noopener noreferrer"` for security

---

## Epic 41: Modal Keyboard Accessibility

### Overview

Improve keyboard accessibility for modal dialogs by adding Escape key support and proper focus management. Currently, modals can only be closed by clicking Cancel or the overlay, and they have accessibility warnings for missing keyboard trap and focus management.

### Goals

- Enable Escape key to close all modals
- Implement proper keyboard focus trap (prevent tabbing to background)
- Auto-focus first interactive element when modal opens
- Restore focus to trigger element when modal closes
- Remove a11y svelte-ignore warnings

### User Stories

#### US-41.1: Add Escape Key to Close Modals

**As a** keyboard user
**I want** to press Escape to close modals
**So that** I can quickly dismiss dialogs without using the mouse

**Acceptance Criteria:**
- [ ] Pressing Escape key closes the whitelist duration picker modal
- [ ] Pressing Escape key closes the delete confirmation modal
- [ ] Escape key has same effect as clicking Cancel (doesn't trigger destructive actions)
- [ ] Event listener is added when modal opens, removed when modal closes
- [ ] Escape key only closes the topmost modal (if multiple modals exist)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: open each modal, press Escape, verify it closes

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Add keydown event listener for Escape

---

#### US-41.2: Implement Keyboard Focus Trap

**As a** keyboard user
**I want** Tab/Shift+Tab to stay within the modal
**So that** I don't accidentally tab to background content

**Acceptance Criteria:**
- [ ] When modal is open, Tab moves focus to next focusable element within modal
- [ ] When on last focusable element, Tab wraps to first focusable element
- [ ] Shift+Tab moves focus to previous focusable element within modal
- [ ] When on first focusable element, Shift+Tab wraps to last focusable element
- [ ] Focus trap works for both duration picker and delete modals
- [ ] Focusable elements: buttons, inputs, select (if any)
- [ ] Remove `svelte-ignore a11y_interactive_supports_focus` comments
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: open modal, tab through elements, verify focus stays in modal

**Technical Notes:**
- Use `keydown` event listener on modal overlay or container
- Detect Tab/Shift+Tab, prevent default, manually move focus
- Query focusable elements: `modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')`

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Add focus trap logic

---

#### US-41.3: Auto-Focus and Restore Focus

**As a** keyboard user
**I want** focus to automatically move into the modal when it opens
**So that** I can immediately interact with it using keyboard

**As a** keyboard user
**I want** focus to return to the trigger button when modal closes
**So that** I don't lose my place in the page

**Acceptance Criteria:**
- [ ] When duration picker opens, first focusable element (first duration button) receives focus
- [ ] When delete modal opens, Cancel button receives focus (safer default for destructive action)
- [ ] Store reference to the element that triggered the modal (e.g., "Add to whitelist" button)
- [ ] When modal closes (Escape, Cancel, or Confirm), focus returns to trigger element
- [ ] Focus restoration works whether modal is closed by keyboard or mouse
- [ ] Remove `svelte-ignore a11y_click_events_have_key_events` comments
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: open modal with keyboard (Tab + Enter), verify focus moves into modal
- [ ] Verify in browser: close modal, verify focus returns to trigger button

**Technical Notes:**
- Store `document.activeElement` before opening modal
- Use `element.focus()` when modal opens and closes
- For duration picker: focus first `.duration-option button`
- For delete modal: focus `.btn-secondary` (Cancel button)

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Add focus management to modal open/close functions

### Non-Goals

- Adding keyboard navigation for duration option selection (arrow keys)
- Creating a reusable Modal component (keep inline for now)
- Changing modal visual design or animations
- Adding ARIA live regions for modal state changes

### Technical Considerations

**Existing Modals:**
1. **Whitelist Duration Picker** (`showDurationPicker`)
   - Opened by: "Add to whitelist" button in table row
   - Contains: Duration option buttons (1 week, 1 month, 3 months, etc.) + Cancel/Confirm
   - Should focus: First duration button on open

2. **Delete Confirmation** (`showDeleteModal`)
   - Opened by: "Delete" button in table row
   - Contains: Warning text + Cancel/Delete buttons
   - Should focus: Cancel button on open (safer for destructive action)

**Event Listeners:**
```typescript
function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    closeModal();
  }
  // Focus trap logic for Tab/Shift+Tab
}

// Add listener when modal opens
$effect(() => {
  if (showDurationPicker || showDeleteModal) {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }
});
```

**Focus Management Pattern:**
```typescript
let triggerElement: HTMLElement | null = null;

function openModal() {
  triggerElement = document.activeElement as HTMLElement;
  showModal = true;
  // Next tick: focus first element
  setTimeout(() => {
    const firstFocusable = modal.querySelector('button');
    firstFocusable?.focus();
  }, 0);
}

function closeModal() {
  showModal = false;
  triggerElement?.focus();
  triggerElement = null;
}
```

**A11y Warnings to Remove:**
- `svelte-ignore a11y_click_events_have_key_events` (overlay click)
- `svelte-ignore a11y_no_static_element_interactions` (overlay)
- `svelte-ignore a11y_interactive_supports_focus` (modal div)

After implementing proper keyboard support, these can be removed since the elements will have proper keyboard handling.

---

## Epic 42: Search Input Accessibility

### Overview

Improve accessibility for search inputs by adding proper aria-label attributes. Currently, search inputs on Issues and Library pages lack accessible labels, making them difficult for screen reader users to identify. This epic creates a reusable SearchInput component with built-in accessibility.

### Goals

- Add aria-label to all search inputs
- Create reusable SearchInput component
- Ensure screen readers can identify search functionality
- Maintain consistent search UX across pages

### User Stories

#### US-42.1: Create SearchInput Component

**As a** developer
**I want** a reusable SearchInput component with built-in accessibility
**So that** search inputs are consistently accessible across the app

**Acceptance Criteria:**
- [ ] Create `frontend/src/lib/components/SearchInput.svelte`
- [ ] Component accepts props: `value`, `placeholder`, `oninput`, `aria-label`
- [ ] Input has `type="text"` and `class="search-input"`
- [ ] aria-label is applied to the input element
- [ ] Clear button appears when value is not empty
- [ ] Clear button has aria-label="Clear search"
- [ ] Component uses same HTML structure as existing search inputs
- [ ] Component uses same CSS classes as existing search inputs (no visual changes)
- [ ] Typecheck passes
- [ ] Unit tests pass (test component renders, accepts props, handles input/clear)

**Technical Notes:**
- Props interface: `{ value: string; placeholder: string; oninput: (e: Event) => void; 'aria-label': string; }`
- Use Svelte 5 `$props()` rune for component props
- Emit input events to parent via oninput prop
- Clear button should call a `clearSearch` function that sets value to empty and calls oninput

**Files:**
- `frontend/src/lib/components/SearchInput.svelte` (new file)
- `frontend/tests/SearchInput.test.ts` (new file)

---

#### US-42.2: Use SearchInput in Library Page

**As a** screen reader user
**I want** the search input on Library page to have a descriptive label
**So that** I know what the input is for

**Acceptance Criteria:**
- [ ] Import SearchInput component in `frontend/src/routes/library/+page.svelte`
- [ ] Replace existing search input with `<SearchInput>` component
- [ ] Set aria-label="Search library by title or year"
- [ ] Pass existing `searchQuery`, `placeholder`, and `handleSearchInput` as props
- [ ] Remove old inline search input HTML
- [ ] Search functionality works identically to before (debounced input, clear button)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: search input appears and functions correctly

**Files:**
- `frontend/src/routes/library/+page.svelte` - Replace search input with component

---

#### US-42.3: Use SearchInput in Issues Page

**As a** screen reader user
**I want** the search input on Issues page to have a descriptive label
**So that** I know what the input is for

**Acceptance Criteria:**
- [ ] Import SearchInput component in `frontend/src/routes/issues/+page.svelte`
- [ ] Replace existing search input with `<SearchInput>` component
- [ ] Set aria-label="Search issues by title or year"
- [ ] Pass existing `searchQuery`, `placeholder`, and `handleSearchInput` as props
- [ ] Remove old inline search input HTML
- [ ] Search functionality works identically to before (debounced input, clear button)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: search input appears and functions correctly

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Replace search input with component

### Non-Goals

- Adding role="search" or other ARIA attributes beyond aria-label
- Adding aria-labels to ALL form inputs in the app (just search inputs)
- Creating search input functionality (already exists)
- Changing visual design of search inputs

### Technical Considerations

**Existing Search Input Structure:**
Both pages currently use:
```svelte
<div class="search-container">
  <input
    type="text"
    class="search-input"
    placeholder="Search by title, year..."
    value={searchQuery}
    oninput={handleSearchInput}
  />
  {#if searchQuery}
    <button class="search-clear" onclick={clearSearch} aria-label="Clear search">×</button>
  {/if}
</div>
```

**SearchInput Component API:**
```svelte
<SearchInput
  value={searchQuery}
  placeholder="Search by title, year..."
  oninput={handleSearchInput}
  aria-label="Search library by title or year"
/>
```

**CSS Classes:**
- `.search-container` - Wrapper div for input + clear button
- `.search-input` - Input element styles
- `.search-clear` - Clear button (X) styles

All CSS is already defined in the page files. The component should reuse these classes without modification.

---

## Epic 43: Warning Text Color Contrast

### Overview

Improve color contrast for warning text to meet WCAG AA accessibility standards. The current warning color (`#ca8a04` in light mode, `#eab308` in dark mode) may not meet the 4.5:1 contrast ratio required for normal text on light backgrounds.

### Goals

- Ensure warning text meets WCAG AA contrast standards (4.5:1 for normal text)
- Maintain visual distinction of warning color from other status colors
- Apply consistent warning colors in both light and dark modes
- Preserve existing design aesthetic while improving accessibility

### User Stories

#### US-43.1: Audit Warning Color Contrast

**As a** developer
**I want** to verify current warning color contrast ratios
**So that** I know what needs to be fixed

**Acceptance Criteria:**
- [ ] Use browser DevTools (Chrome/Firefox) contrast checker on warning text instances
- [ ] Document current contrast ratios for light mode:
  - Warning text on light background (e.g., `--warning` on `--bg-primary`)
  - Warning text on warning-light background (e.g., `--warning` on `--warning-light`)
- [ ] Document current contrast ratios for dark mode
- [ ] Identify which combinations fail WCAG AA (< 4.5:1 for normal text)
- [ ] Create a list of files using `var(--warning)` that need testing (already identified in Grep results)

**Technical Notes:**
Current warning colors:
- Light mode: `--warning: #ca8a04` (yellow-700)
- Dark mode: `--warning: #eab308` (yellow-500)

Files using warning colors:
- `frontend/src/routes/issues/+page.svelte` (4 instances)
- `frontend/src/routes/register/+page.svelte` (2 instances)
- `frontend/src/routes/library/+page.svelte` (1 instance)
- `frontend/src/app.css` (badge-warning class)

**Files:**
- `frontend/src/app.css` - Warning color variables

---

#### US-43.2: Fix Warning Color for WCAG AA Compliance

**As a** user with visual impairments
**I want** warning text to have sufficient contrast
**So that** I can easily read important warnings

**Acceptance Criteria:**
- [ ] Update `--warning` color in light mode to meet WCAG AA (4.5:1 contrast)
- [ ] Update `--warning` color in dark mode if needed for WCAG AA compliance
- [ ] Maintain visual distinction from other status colors (success, danger, info)
- [ ] Warning color remains recognizable as "yellow/amber" (don't shift to orange/brown)
- [ ] Test updated colors in browser DevTools contrast checker
- [ ] Verify contrast on all instances:
  - Issues page warning text
  - Register page warning elements
  - Library page warning text
  - badge-warning class (even if unused, for future use)
- [ ] Typecheck passes
- [ ] Unit tests pass (if any color-related tests exist)
- [ ] Verify in browser: warning text is readable and meets WCAG AA

**Technical Notes:**
Potential WCAG AA compliant alternatives:
- Light mode: Consider darker yellows like `#a16207` (yellow-800) or `#854d0e` (yellow-900)
- Dark mode: Current `#eab308` is likely compliant against dark backgrounds, verify first

Use WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/) or browser DevTools to validate.

**Files:**
- `frontend/src/app.css` - Update CSS variables for --warning

### Non-Goals

- Auditing ALL color combinations app-wide (only warning colors)
- Achieving WCAG AAA compliance (7:1 ratio)
- Adding automated accessibility testing tools (future enhancement)
- Changing visual design or placement of warning elements
- Updating success, danger, or info colors (separate epic if needed)

### Technical Considerations

**CSS Variables to Update:**
```css
:root {
  /* Current - may fail WCAG AA */
  --warning: #ca8a04;
  --warning-light: rgba(202, 138, 4, 0.1);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --warning: #eab308;
    --warning-light: rgba(234, 179, 8, 0.15);
  }
}

:root[data-theme="dark"] {
  --warning: #eab308;
  --warning-light: rgba(234, 179, 8, 0.15);
}
```

**WCAG AA Requirements:**
- Normal text (< 18px or < 14px bold): 4.5:1 contrast ratio
- Large text (≥ 18px or ≥ 14px bold): 3:1 contrast ratio

**Testing Process:**
1. Open browser DevTools (Chrome: F12 → Elements → Styles → Color picker)
2. Click on warning color
3. Expand "Contrast ratio" section
4. Verify green checkmark for "AA" (not "AAA")
5. If red X, adjust color until AA passes

**Background Colors to Test Against:**
- Light mode: `--bg-primary: #ffffff` (white)
- Dark mode: `--bg-primary: var(--gray-900)` which is `#111827`
- Warning-light backgrounds (badge-warning class)

---

## Epic 44: Password Reset and Change

### Overview

Implement password reset (forgot password) and password change functionality. Users who forget their password can request a reset link via email, and logged-in users can change their password in settings. Email delivery uses SMTP2GO configured via environment variables.

### Goals

- Allow users to reset forgotten passwords via email
- Enable authenticated users to change their password in settings
- Use secure, time-limited reset tokens (15 minutes)
- Send professional email notifications via SMTP2GO
- Prevent brute force attacks on reset requests

### User Stories

#### US-44.1: Password Reset Token Model

**As a** developer
**I want** a database model to store password reset tokens
**So that** we can securely track and validate reset requests

**Acceptance Criteria:**
- [x] Create `PasswordResetToken` model in `backend/app/database.py`
- [x] Fields: `id`, `user_id` (FK to users), `token` (hashed), `expires_at`, `created_at`, `used` (boolean)
- [x] Add index on `token` for fast lookup
- [x] Add foreign key constraint to `users` table with cascade delete
- [x] Create Alembic migration for new table
- [x] Migration applies successfully: `alembic upgrade head`
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Created PasswordResetToken model with all required fields. Token stored as token_hash (indexed). Foreign key to users with CASCADE delete. Migration 98891c396773 created and verified.

**Technical Notes:**
```python
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # Hashed token
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    used: Mapped[bool] = mapped_column(default=False)
```

**Files:**
- `backend/app/database.py` - Add PasswordResetToken model
- `backend/alembic/versions/XXXX_add_password_reset_tokens.py` (generated)

---

#### US-44.2: Email Service with SMTP2GO

**As a** developer
**I want** an email service to send password reset emails
**So that** users can receive reset links

**Acceptance Criteria:**
- [x] Create `backend/app/services/email.py` with `send_password_reset_email()` function
- [x] Function accepts: `to_email: str`, `reset_url: str`, `user_email: str`
- [x] Email subject: "Reset Your Media Janitor Password"
- [x] Email body includes: reset link (clickable), expiration time (15 minutes), user's email for reference
- [x] Use SMTP2GO API via SMTP (not HTTP API) with environment variables
- [x] Environment variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`
- [x] Add email config to `backend/app/config.py` Settings class
- [x] Handle SMTP errors gracefully (log error, raise HTTPException 500)
- [x] Typecheck passes
- [x] Unit tests pass (mock smtplib.SMTP)

**Note:** Created email service using smtplib with STARTTLS. HTML and plain text email formats. Raises HTTPException 500 on SMTP errors. 18 unit tests with mocked smtplib.SMTP. Config added: smtp_host, smtp_port, smtp_username, smtp_password, smtp_from_email, frontend_url.

**Technical Notes:**
```python
# backend/app/config.py
class Settings(BaseSettings):
    # Existing fields...
    smtp_host: str = "mail.smtp2go.com"
    smtp_port: int = 587  # TLS
    smtp_username: str
    smtp_password: str
    smtp_from_email: str = "noreply@mediajanitor.com"
    smtp_from_name: str = "Media Janitor"

# backend/app/services/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_password_reset_email(to_email: str, reset_url: str) -> None:
    settings = get_settings()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Your Media Janitor Password"
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email

    # HTML and plain text versions
    # Include reset_url with 15 minute expiration notice
    # ...
```

**Files:**
- `backend/app/services/email.py` (new file)
- `backend/app/config.py` - Add SMTP settings
- `backend/tests/test_email.py` (new file)
- `.env.example` - Add SMTP environment variables

---

#### US-44.3: Request Password Reset Endpoint

**As a** user who forgot my password
**I want** to request a password reset link via my email
**So that** I can regain access to my account

**Acceptance Criteria:**
- [x] Create `POST /api/auth/request-password-reset` endpoint
- [x] Request body: `{ "email": "user@example.com" }`
- [x] Generate secure random token (32 bytes, URL-safe base64)
- [x] Hash token with bcrypt before storing in database
- [x] Store token with expiration (15 minutes from now)
- [x] Delete any existing unused tokens for this user before creating new one
- [x] Send email with reset URL: `{FRONTEND_URL}/reset-password?token={raw_token}`
- [x] Return 200 OK even if email doesn't exist (prevent email enumeration)
- [x] Rate limit: max 3 requests per email per hour (use in-memory dict or Redis if available)
- [x] Typecheck passes
- [x] Unit tests pass (mock email sending)
- [x] Test in Docker: request reset, verify email sent (check logs if SMTP not configured)

**Note:** Added POST /api/auth/request-password-reset endpoint. Generates secure token (secrets.token_urlsafe(32)), hashes with bcrypt, stores in PasswordResetToken table with 15-min expiration. Rate limited to 3 requests/email/hour. Returns 200 for any email to prevent enumeration. 10 new unit tests + 3 integration tests.

**Technical Notes:**
```python
import secrets
import bcrypt
from datetime import datetime, timedelta

@router.post("/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    # Find user by email
    user = await db.execute(select(User).where(User.email == request.email))
    user = user.scalar_one_or_none()

    if not user:
        # Return success to prevent email enumeration
        return {"message": "If that email exists, a reset link has been sent"}

    # Generate token
    raw_token = secrets.token_urlsafe(32)
    hashed_token = bcrypt.hashpw(raw_token.encode(), bcrypt.gensalt()).decode()

    # Delete old tokens
    await db.execute(delete(PasswordResetToken).where(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ))

    # Create new token
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=hashed_token,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    db.add(reset_token)
    await db.commit()

    # Send email
    reset_url = f"{settings.frontend_url}/reset-password?token={raw_token}"
    send_password_reset_email(user.email, reset_url)

    return {"message": "If that email exists, a reset link has been sent"}
```

**Files:**
- `backend/app/routers/auth.py` - Add endpoint
- `backend/app/models/auth.py` - Add PasswordResetRequest schema
- `backend/tests/test_auth.py` - Add tests

---

#### US-44.4: Reset Password Endpoint

**As a** user with a reset token
**I want** to submit a new password using the token
**So that** I can access my account again

**Acceptance Criteria:**
- [x] Create `POST /api/auth/reset-password` endpoint
- [x] Request body: `{ "token": "abc123...", "new_password": "newPass123!" }`
- [x] Validate new password meets requirements (8+ chars, uppercase, lowercase, number)
- [x] Find token in database (hash incoming token, compare with stored hashes)
- [x] Verify token is not expired (expires_at > now)
- [x] Verify token is not already used
- [x] Update user's password (hash with bcrypt)
- [x] Mark token as used
- [x] Return 200 OK with success message
- [x] Return 400 if token is invalid, expired, or already used
- [x] Typecheck passes
- [x] Unit tests pass (test valid token, expired token, used token, invalid token)
- [x] Test in Docker: full flow from request to reset

**Note:** Added POST /api/auth/reset-password endpoint. Validates password strength (8+ chars, uppercase, lowercase, number) with Pydantic validator. Compares incoming token against bcrypt hashes of non-expired, unused tokens. Updates user password and marks token as used. 11 new unit tests + 3 integration tests.

**Technical Notes:**
```python
@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Find all unused tokens (need to check hash against each)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        )
    )
    tokens = result.scalars().all()

    # Find matching token by comparing hashes
    matching_token = None
    for token_record in tokens:
        if bcrypt.checkpw(request.token.encode(), token_record.token.encode()):
            matching_token = token_record
            break

    if not matching_token:
        raise HTTPException(400, "Invalid or expired reset token")

    # Update password
    user = await db.get(User, matching_token.user_id)
    user.hashed_password = bcrypt.hashpw(request.new_password.encode(), bcrypt.gensalt()).decode()
    matching_token.used = True
    await db.commit()

    return {"message": "Password reset successful"}
```

**Files:**
- `backend/app/routers/auth.py` - Add endpoint
- `backend/app/models/auth.py` - Add ResetPasswordRequest schema
- `backend/tests/test_auth.py` - Add tests

---

#### US-44.5: Forgot Password UI

**As a** user who forgot my password
**I want** a UI to request a password reset
**So that** I can easily reset my password

**Acceptance Criteria:**
- [ ] Add "Forgot password?" link below login form on `/login` page
- [ ] Link navigates to `/forgot-password` route
- [ ] Create `frontend/src/routes/forgot-password/+page.svelte`
- [ ] Page has: email input, "Send Reset Link" button, back to login link
- [ ] On submit: call `POST /api/auth/request-password-reset`
- [ ] Show success message: "If that email exists, a reset link has been sent. Check your inbox."
- [ ] Show error toast if request fails
- [ ] Disable button while request is in flight
- [ ] Typecheck passes
- [ ] Unit tests pass (test form submission, success/error states)
- [ ] Verify in browser: navigate to forgot password, enter email, see success message

**Files:**
- `frontend/src/routes/login/+page.svelte` - Add "Forgot password?" link
- `frontend/src/routes/forgot-password/+page.svelte` (new file)
- `frontend/tests/forgot-password.test.ts` (new file)

---

#### US-44.6: Reset Password UI

**As a** user who clicked a reset link
**I want** a UI to enter my new password
**So that** I can complete the password reset

**Acceptance Criteria:**
- [ ] Create `frontend/src/routes/reset-password/+page.svelte`
- [ ] Page reads token from URL query param: `/reset-password?token=abc123`
- [ ] Page has: new password input, confirm password input, "Reset Password" button
- [ ] Password inputs are type="password" with show/hide toggle (eye icon)
- [ ] Validate passwords match before submission
- [ ] On submit: call `POST /api/auth/reset-password` with token and new password
- [ ] On success: show success message, redirect to `/login` after 2 seconds
- [ ] On error (400): show "Invalid or expired token" error
- [ ] On error (network): show generic error toast
- [ ] If no token in URL, show error: "Invalid reset link"
- [ ] Typecheck passes
- [ ] Unit tests pass (test validation, success/error states)
- [ ] Verify in browser: use reset link from email, enter new password, redirect to login

**Files:**
- `frontend/src/routes/reset-password/+page.svelte` (new file)
- `frontend/tests/reset-password.test.ts` (new file)

---

#### US-44.7: Change Password in Settings

**As a** logged-in user
**I want** to change my password from settings
**So that** I can update my password without resetting it

**Acceptance Criteria:**
- [ ] Create `POST /api/auth/change-password` endpoint (requires authentication)
- [ ] Request body: `{ "current_password": "old", "new_password": "new" }`
- [ ] Verify current password is correct
- [ ] Validate new password meets requirements
- [ ] Update user's password
- [ ] Return 200 OK on success
- [ ] Return 400 if current password is wrong
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Add "Change Password" section to `/settings` page (or new `/settings/security` page)
- [ ] Section has: current password input, new password input, confirm new password input, "Change Password" button
- [ ] Show success toast on password change
- [ ] Show error toast if current password is wrong
- [ ] Verify in browser: change password, logout, login with new password

**Files:**
- `backend/app/routers/auth.py` - Add change-password endpoint
- `backend/app/models/auth.py` - Add ChangePasswordRequest schema
- `backend/tests/test_auth.py` - Add tests
- `frontend/src/routes/settings/+page.svelte` - Add change password section (or new security page)
- `frontend/tests/settings.test.ts` - Add tests

### Non-Goals

- OAuth password reset (Google Sign-In users don't have passwords)
- Password reset via SMS or 2FA
- Password history (preventing reuse of old passwords)
- Account lockout after failed reset attempts
- Admin-initiated password resets
- Customizable email templates (hardcoded for now)

### Technical Considerations

**SMTP2GO Configuration:**
Sign up at https://www.smtp2go.com/, get SMTP credentials, add to `.env`:
```env
SMTP_HOST=mail.smtp2go.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-api-key
SMTP_FROM_EMAIL=noreply@mediajanitor.com
SMTP_FROM_NAME=Media Janitor
```

**Frontend URL:**
Need to know frontend URL for reset links. Add to backend config:
```env
FRONTEND_URL=http://localhost:5173  # dev
FRONTEND_URL=https://mediajanitor.com  # prod
```

**Token Security:**
- Raw token (sent in email): 32 bytes URL-safe base64 = 43 chars
- Stored token: bcrypt hash of raw token
- Never store raw tokens in database
- Compare using `bcrypt.checkpw()` on reset

**Rate Limiting:**
Simple in-memory rate limit for reset requests:
```python
# In-memory store: { email: [timestamp1, timestamp2, ...] }
reset_requests: dict[str, list[datetime]] = {}

def check_rate_limit(email: str) -> bool:
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    # Clean old requests
    if email in reset_requests:
        reset_requests[email] = [ts for ts in reset_requests[email] if ts > one_hour_ago]
    else:
        reset_requests[email] = []

    # Check limit
    if len(reset_requests[email]) >= 3:
        raise HTTPException(429, "Too many reset requests. Try again later.")

    # Add new request
    reset_requests[email].append(now)
```

**Email HTML Template:**
```html
<p>Hello,</p>
<p>You requested to reset your password for <strong>{{user_email}}</strong>.</p>
<p>Click the link below to reset your password:</p>
<p><a href="{{reset_url}}">Reset My Password</a></p>
<p>This link will expire in <strong>15 minutes</strong>.</p>
<p>If you didn't request this, you can safely ignore this email.</p>
```

**Database Cleanup:**
Consider adding a background task to delete expired tokens:
```python
# Run daily
async def cleanup_expired_tokens(db: AsyncSession):
    await db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.expires_at < datetime.utcnow()
        )
    )
    await db.commit()
```

---

## Epic 45: Responsive Layout for Large Screens (27"+)

### Overview

Optimize the application layout for large screens (27" monitors and ultrawide displays). Currently, the UI has significant wasted space on large screens: the sidebar is fixed at 220px, content is capped at 1200px max-width, and table columns don't expand to utilize available space. This epic adds CSS breakpoints and progressive enhancements for screens ≥1440px and ≥1920px.

### Goals

- Better utilize horizontal space on 27"+ monitors
- Expand sidebar width progressively on larger screens
- Increase content max-width to reduce empty margins
- Allow tables to display full content (no truncated titles)
- Maintain existing mobile/tablet experience (no regressions)
- Keep changes purely CSS-based where possible (minimal JS)

### User Stories

#### US-45.1: Add CSS Breakpoints and Variables for Large Screens

**As a** developer
**I want** CSS custom properties for large screen breakpoints
**So that** responsive styles can be applied consistently across the app

**Problem:**
Current CSS only has breakpoints for mobile (≤768px) and small mobile (≤640px). No breakpoints exist for large screens (≥1440px, ≥1920px), leaving large monitors with a centered 1200px content area surrounded by empty space.

**Acceptance Criteria:**
- [ ] Add CSS custom properties in `frontend/src/app.css` for breakpoints:
  - `--breakpoint-lg: 1440px` (large desktop)
  - `--breakpoint-xl: 1920px` (ultrawide/4K)
- [ ] Add CSS custom properties for responsive layout values:
  - `--sidebar-width: 220px` (default)
  - `--sidebar-width-lg: 260px` (≥1440px)
  - `--sidebar-width-xl: 300px` (≥1920px)
  - `--content-max-width: 1200px` (default)
  - `--content-max-width-lg: 1600px` (≥1440px)
  - `--content-max-width-xl: 1800px` (≥1920px)
- [ ] Document breakpoint strategy in CSS comments
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: variables are accessible in DevTools

**Technical Notes:**
```css
/* frontend/src/app.css */

/* Breakpoint tokens (reference only, use in media queries) */
/* --breakpoint-md: 768px - tablet/mobile */
/* --breakpoint-lg: 1440px - large desktop (27" at 100% scale) */
/* --breakpoint-xl: 1920px - ultrawide/4K */

/* Layout tokens - default (mobile-first) */
:root {
  --sidebar-width: 220px;
  --content-max-width: 1200px;
}

/* Large desktop (≥1440px) */
@media (min-width: 1440px) {
  :root {
    --sidebar-width: 260px;
    --content-max-width: 1600px;
  }
}

/* Ultrawide (≥1920px) */
@media (min-width: 1920px) {
  :root {
    --sidebar-width: 300px;
    --content-max-width: 1800px;
  }
}
```

**Files:**
- `frontend/src/app.css` - Add breakpoint and layout CSS variables

---

#### US-45.2: Expand Main Content Max-Width on Large Screens

**As a** user on a large screen
**I want** the content area to expand beyond 1200px
**So that** I can use more of my screen space

**Problem:**
Currently, `.content` in `+layout.svelte` has `max-width: 1200px` hardcoded. On a 27" monitor at 2560px width, this leaves ~680px of unused space on each side (after sidebar).

**Acceptance Criteria:**
- [ ] Update `frontend/src/routes/+layout.svelte` to use `var(--content-max-width)` instead of hardcoded `1200px`
- [ ] Content expands to 1600px on screens ≥1440px
- [ ] Content expands to 1800px on screens ≥1920px
- [ ] Content remains centered with auto margins
- [ ] No horizontal scrollbar appears on any screen size
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: resize window, see content width change at breakpoints

**Files:**
- `frontend/src/routes/+layout.svelte` - Use CSS variable for max-width

---

#### US-45.3: Responsive Sidebar Width

**As a** user on a large screen
**I want** a wider sidebar with more readable navigation
**So that** navigation items aren't cramped on large displays

**Problem:**
The sidebar is fixed at 220px regardless of screen size. On large screens, this looks disproportionately narrow. A wider sidebar provides better visual balance and room for longer nav labels if needed.

**Acceptance Criteria:**
- [ ] Update `frontend/src/lib/components/Sidebar.svelte` to use `var(--sidebar-width)`
- [ ] Update `frontend/src/routes/+layout.svelte` margin-left to use `var(--sidebar-width)`
- [ ] Sidebar grows to 260px on screens ≥1440px
- [ ] Sidebar grows to 300px on screens ≥1920px
- [ ] Nav items remain properly aligned and spaced
- [ ] User info section at bottom doesn't overflow
- [ ] Mobile sidebar behavior unchanged (still 220px overlay)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: sidebar width changes at breakpoints

**Technical Notes:**
```css
/* Sidebar.svelte */
.sidebar {
  width: var(--sidebar-width);
  /* ... rest unchanged ... */
}

/* +layout.svelte */
.app.with-sidebar {
  margin-left: var(--sidebar-width);
}

/* Mobile override (unchanged) */
@media (max-width: 768px) {
  .app.with-sidebar {
    margin-left: 0;
  }
  .sidebar {
    width: 220px; /* Keep fixed on mobile overlay */
  }
}
```

**Files:**
- `frontend/src/lib/components/Sidebar.svelte` - Use CSS variable for width
- `frontend/src/routes/+layout.svelte` - Use CSS variable for margin-left

---

#### US-45.4: Responsive Table Columns on Issues Page

**As a** user viewing the Issues table on a large screen
**I want** columns to expand and show full content
**So that** I can see complete titles without truncation

**Problem:**
The Issues page table has hardcoded column widths (Name: 35%, Issues: 30%, etc.). On a 1800px content area, the Name column could be ~630px wide instead of ~420px, reducing truncation of long titles like "The Lord of the Rings: The Return of the King".

**Acceptance Criteria:**
- [ ] On ≥1440px: Name column expands, other columns use more space
- [ ] On ≥1920px: Name column expands further, all columns comfortable
- [ ] Columns use `min-width` + `flex-grow` pattern instead of fixed percentages
- [ ] Text truncation (ellipsis) still applies for very long titles
- [ ] Table header widths match content widths
- [ ] Mobile column hiding unchanged (Size, Added, Watched hidden)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: table columns expand at breakpoints, no overflow

**Technical Notes:**
```css
/* issues/+page.svelte */

/* Default column widths (percentage for smaller screens) */
.col-name { width: 35%; min-width: 200px; }
.col-issues { width: 30%; min-width: 150px; }
.col-size { width: 12%; min-width: 80px; }
.col-added { width: 12%; min-width: 100px; }
.col-watched { width: 13%; min-width: 100px; }

/* Large screens: let columns breathe */
@media (min-width: 1440px) {
  .col-name { width: auto; flex: 2; min-width: 300px; }
  .col-issues { width: auto; flex: 1.5; min-width: 180px; }
  .col-size { width: auto; flex: 0.5; min-width: 100px; }
  .col-added { width: auto; flex: 0.5; min-width: 120px; }
  .col-watched { width: auto; flex: 0.5; min-width: 120px; }

  table { display: flex; flex-direction: column; }
  thead, tbody, tr { display: flex; width: 100%; }
  th, td { display: flex; align-items: center; }
}
```

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Add responsive column styles

---

#### US-45.5: Responsive Table Columns on Library Page

**As a** user viewing the Library table on a large screen
**I want** columns to expand similar to the Issues page
**So that** I have a consistent experience across pages

**Problem:**
The Library page has similar column width constraints. Apply the same responsive patterns as US-45.4 for consistency.

**Acceptance Criteria:**
- [ ] Column widths expand on large screens (≥1440px, ≥1920px)
- [ ] Name/Title column gets more space
- [ ] Columns use same pattern as Issues page (min-width + flex)
- [ ] Mobile column hiding preserved
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: library table columns expand at breakpoints

**Files:**
- `frontend/src/routes/library/+page.svelte` - Add responsive column styles

---

#### US-45.6: Responsive Dashboard Stats Grid

**As a** user viewing the Dashboard on a large screen
**I want** the stats grid to make better use of space
**So that** stat cards aren't cramped on large displays

**Problem:**
Dashboard has `max-width: 800px` and a fixed 4-column grid. On large screens, this wastes significant space and makes the dashboard feel empty.

**Acceptance Criteria:**
- [ ] Dashboard max-width increases on large screens (use `var(--content-max-width)` or page-specific value)
- [ ] On ≥1440px: max-width increases to 1000px
- [ ] On ≥1920px: max-width increases to 1200px (or full width if grid handles it)
- [ ] Stats grid remains 4 columns but cards are larger
- [ ] Spacing between cards increases proportionally
- [ ] Mobile grid unchanged (2 columns on ≤640px)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: dashboard cards grow at breakpoints

**Technical Notes:**
```css
/* +page.svelte (dashboard) */
.dashboard {
  max-width: 800px;
}

@media (min-width: 1440px) {
  .dashboard {
    max-width: 1000px;
  }
  .stats-grid {
    gap: var(--space-6); /* Increase gap */
  }
}

@media (min-width: 1920px) {
  .dashboard {
    max-width: 1200px;
  }
}
```

**Files:**
- `frontend/src/routes/+page.svelte` - Add responsive dashboard styles

### Non-Goals

- Changing the overall design aesthetic or color scheme
- Adding new content or features to fill the space
- Supporting screens smaller than 320px (edge case)
- Adding user preference for layout density (future enhancement)
- Changing font sizes on large screens (keep current scaling)
- Adding a "compact mode" toggle

### Technical Considerations

**CSS-Only Approach:**
All changes should be achievable with CSS media queries and custom properties. No JavaScript viewport detection needed.

**Testing Strategy:**
- Use Chrome DevTools responsive mode
- Test at: 1366x768 (laptop), 1920x1080 (1080p), 2560x1440 (27" 1440p), 3840x2160 (4K)
- Verify no horizontal scrollbars at any size
- Verify text remains readable (not too spread out)

**Breakpoint Strategy:**
- Mobile: ≤768px (existing)
- Tablet: 769px - 1439px (default desktop, existing)
- Large Desktop: 1440px - 1919px (new)
- Ultrawide: ≥1920px (new)

**Files to Modify:**
1. `frontend/src/app.css` - Global CSS variables and breakpoints
2. `frontend/src/routes/+layout.svelte` - Main layout responsive styles
3. `frontend/src/lib/components/Sidebar.svelte` - Sidebar width
4. `frontend/src/routes/issues/+page.svelte` - Issues table columns
5. `frontend/src/routes/library/+page.svelte` - Library table columns
6. `frontend/src/routes/+page.svelte` - Dashboard grid and max-width

---

## Epic 46: External Service Logos for Media Links

### Overview

Replace text-based external link badges (JF, JS, RD, SN, TMDB) with 16x16px logo icons across all media tables for better visual recognition. Also add missing Radarr/Sonarr links to the Library page.

### User Stories

#### US-46.1: Create ServiceBadge Component with Inline SVG Logos

**As a** user
**I want** to see recognizable service logos instead of text abbreviations
**So that** I can quickly identify which service each link leads to

**Acceptance Criteria:**
- [ ] Create `frontend/src/lib/components/ServiceBadge.svelte` component
- [ ] Component accepts props: `service` (jellyfin|jellyseerr|radarr|sonarr|tmdb), `url`, `title`
- [ ] Embed inline 16x16px SVGs for all 5 services with brand colors:
  - Jellyfin: blue (`#00a4dc`)
  - Jellyseerr: purple (`#7b68ee`)
  - Radarr: yellow (`#ffc230`)
  - Sonarr: green (`#2ecc71`)
  - TMDB: blue (`#01b4e4`)
- [ ] Links open in new tab (`target="_blank"`)
- [ ] Hover effect provides visual feedback
- [ ] Works in both light and dark modes
- [ ] Unit tests pass
- [ ] Typecheck passes

**Files:**
- `frontend/src/lib/components/ServiceBadge.svelte` (new)
- `frontend/tests/service-badge.test.ts` (new)

---

#### US-46.2: Update Issues Page to Use ServiceBadge Component

**As a** user viewing the Issues table
**I want** to see logo icons instead of text badges
**So that** external links are more visually recognizable

**Acceptance Criteria:**
- [ ] Import and use `ServiceBadge` component in Issues page
- [ ] Replace text badge rendering (lines 930-956) with component calls
- [ ] Keep existing URL generation functions unchanged
- [ ] Remove old `.service-badge-text.*` CSS styles
- [ ] All 5 service logos display correctly when URL is available
- [ ] Unit tests pass
- [ ] Typecheck passes
- [ ] Verify in browser

**Files:**
- `frontend/src/routes/issues/+page.svelte`

---

#### US-46.3: Add sonarr_title_slug to Library Backend

**As a** developer
**I want** the Library API to return `sonarr_title_slug` for series
**So that** Sonarr links can be generated on the Library page

**Acceptance Criteria:**
- [ ] Add `sonarr_title_slug: str | None = None` to `LibraryItem` model in `backend/app/models/content.py`
- [ ] Modify `get_library()` in `backend/app/services/content.py` to enrich Series items with Sonarr slug
- [ ] Use existing `build_sonarr_tmdb_slug_map()` pattern from Issues endpoint
- [ ] Movie items return `null` for `sonarr_title_slug`
- [ ] Unit tests pass
- [ ] Typecheck passes

**Files:**
- `backend/app/models/content.py` - Add field to `LibraryItem`
- `backend/app/services/content.py` - Enrich `get_library()` with Sonarr slug lookup
- `backend/tests/test_library.py` - Add test for `sonarr_title_slug` enrichment

---

#### US-46.4: Update Library Page with All Service Badges

**As a** user viewing the Library table
**I want** to see all 5 service logos (Jellyfin, Jellyseerr, Radarr, Sonarr, TMDB)
**So that** I can quickly access any external service from the Library

**Acceptance Criteria:**
- [ ] Update TypeScript interface to include `sonarr_title_slug: string | null`
- [ ] Add missing URL generation functions (copy from Issues page):
  - `getJellyseerrUrl()` - uses `tmdb_id` + media_type
  - `getRadarrUrl()` - uses `tmdb_id` (movies only)
  - `getSonarrUrl()` - uses `sonarr_title_slug` (series only)
- [ ] Import and use `ServiceBadge` component for all 5 services
- [ ] Radarr shows for movies, Sonarr shows for series
- [ ] Remove old text badge CSS
- [ ] Unit tests pass
- [ ] Typecheck passes
- [ ] Verify in browser

**Files:**
- `frontend/src/routes/library/+page.svelte`

### Non-Goals

- Popup menu on title click (user prefers logo approach)
- Adding new external services beyond the 5 already supported
- Changing link URLs or target pages

### Technical Considerations

- **Inline SVGs**: Best approach for small icons - no HTTP requests, scalable, CSS-stylable
- **Brand recognition**: Preserve official brand colors for immediate recognition
- **Sonarr URL pattern**: Uses `titleSlug` field (e.g., "arcane"), not TMDB ID
- **Radarr URL pattern**: Uses TMDB ID for movies

---

## Checklist Summary

### Completed ✅ (141 stories)

See [ARCHIVED_PRD.md](./ARCHIVED_PRD.md) for all completed epics and stories.

### Completed (15 stories)
- [x] US-17.2.1: Populate Sync Progress User Names
- [x] US-28.1: Loading States Accessibility
- [x] US-33.1: Calculate and Store Total Series Size
- [x] US-34.1: Hide Issues Column on Unavailable Tab
- [x] US-34.2: Normalize Table Header Casing
- [x] US-34.3: Add Sorting to Requester and Release Columns
- [x] US-35.1: Fix Watched Column Sort Order
- [x] US-37.1: Prefill Nicknames During Sync (Backend)
- [x] US-37.3: Manual Refresh Button for Jellyfin Users
- [x] US-38.1: Add Title Language User Setting
- [x] US-38.2: Store French Titles During Sync
- [x] US-44.1: Password Reset Token Model
- [x] US-44.2: Email Service with SMTP2GO
- [x] US-44.3: Request Password Reset Endpoint
- [x] US-44.4: Reset Password Endpoint

### Pending (26 stories)
- [ ] US-35.2: Display Last Watched Date for Series
- [ ] US-36.1: Settings Layout with Sidebar Navigation
- [ ] US-36.2: Extract Connections Page
- [ ] US-36.3: Extract Thresholds Page
- [ ] US-36.4: Extract Users Page
- [ ] US-36.5: Extract Display Page
- [ ] US-37.2: Display Prefilled Users in UI
- [ ] US-38.3: Recently Available Uses Language Preference
- [ ] US-39.1: Add Manual Dismiss Button to Toasts
- [ ] US-39.2: Add Type Icons to Toasts
- [ ] US-40.1: Fix GitHub Repository Link
- [ ] US-41.1: Add Escape Key to Close Modals
- [ ] US-41.2: Implement Keyboard Focus Trap
- [ ] US-41.3: Auto-Focus and Restore Focus
- [ ] US-42.1: Create SearchInput Component
- [ ] US-42.2: Use SearchInput in Library Page
- [ ] US-42.3: Use SearchInput in Issues Page
- [ ] US-43.1: Audit Warning Color Contrast
- [ ] US-43.2: Fix Warning Color for WCAG AA Compliance
- [ ] US-44.5: Forgot Password UI
- [ ] US-44.6: Reset Password UI
- [ ] US-44.7: Change Password in Settings
- [ ] US-45.1: Add CSS Breakpoints and Variables for Large Screens
- [ ] US-45.2: Expand Main Content Max-Width on Large Screens
- [ ] US-45.3: Responsive Sidebar Width
- [ ] US-45.4: Responsive Table Columns on Issues Page
- [ ] US-45.5: Responsive Table Columns on Library Page
- [ ] US-45.6: Responsive Dashboard Stats Grid
- [ ] US-46.1: Create ServiceBadge Component with Inline SVG Logos
- [ ] US-46.2: Update Issues Page to Use ServiceBadge Component
- [ ] US-46.3: Add sonarr_title_slug to Library Backend
- [ ] US-46.4: Update Library Page with All Service Badges

---
