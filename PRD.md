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

See [ARCHIVED_PRD.md](./ARCHIVED_PRD.md) for the complete list of **245 completed user stories** across **62 epics**.

---

## Pending Stories

### Epic 64: Pre-Sync Library Refresh

**Overview:**
Automatically trigger Jellyfin library scans and Jellyseerr library sync at the START of each background sync. This ensures the cached data in Media Janitor reflects the latest content downloaded to the media server, eliminating the need for manual refresh actions in Jellyfin/Jellyseerr before syncing.

**Goals:**
- Eliminate manual steps required before syncing (triggering library scans)
- Ensure freshest possible data when sync completes
- Gracefully handle refresh failures without blocking the main sync

**API Reference (Verified 2026-02-02):**

**Jellyfin:**
- Trigger scan: `POST /Library/Refresh` with `X-Emby-Token` header → returns 204
- Poll status: `GET /ScheduledTasks` → find task with `Key == "RefreshLibrary"`, check `State` field
- States: `Idle` (done), `Running` (in progress), `Cancelling`

**Jellyseerr:**
- Trigger sync: `POST /api/v1/settings/jellyfin/sync` with `X-Api-Key` + `Content-Type: application/json` headers, body: `{"start": true}` → returns `{running: true, ...}`
- Poll status: `GET /api/v1/settings/jellyfin/sync` → check `running` field (true/false) and `progress`/`total`

---

#### US-64.1: Trigger Jellyfin Library Refresh Before Sync
**As a** media server owner
**I want** the sync to automatically trigger a Jellyfin library scan before fetching data
**So that** newly downloaded content appears in my Media Janitor dashboard without manual intervention

**Background:**
Currently, when new movies/series are downloaded, users must:
1. Go to Jellyfin → Right-click Movies → "Actualiser les métadonnées"
2. Go to Jellyfin → Right-click Shows → "Actualiser les métadonnées"
3. Then trigger sync in Media Janitor

This story automates step 1 & 2 by calling `POST /Library/Refresh` at sync start.

**Acceptance Criteria:**
- [ ] Create `trigger_jellyfin_library_refresh(server_url, api_key)` function in `sync.py`
- [ ] Function calls `POST {server_url}/Library/Refresh` with `X-Emby-Token` header
- [ ] Function returns True on 204 response, False on failure
- [ ] Failures are logged as warnings (not exceptions)
- [ ] Add unit tests with mocked httpx responses
- [ ] Typecheck passes
- [ ] Unit tests pass

---

#### US-64.2: Poll Jellyfin Library Scan Completion
**As a** media server owner
**I want** the sync to wait for the Jellyfin library scan to complete
**So that** the data fetched reflects all newly scanned content

**Background:**
After triggering a library refresh, Jellyfin runs the scan asynchronously. We need to poll the ScheduledTasks API to check when the "Scan Media Library" task transitions from "Running" to "Idle".

**Acceptance Criteria:**
- [ ] Create `wait_for_jellyfin_scan_completion(server_url, api_key, timeout_seconds=300)` function
- [ ] Function calls `GET {server_url}/ScheduledTasks` with `X-Emby-Token` header
- [ ] Function finds the task with `Key == "RefreshLibrary"` (not Name - Name is localized)
- [ ] Function polls every 5 seconds until `State == "Idle"` or timeout reached
- [ ] Returns True if scan completed, False if timed out
- [ ] Timeout is configurable (default 5 minutes)
- [ ] Add logging for scan progress (every poll iteration)
- [ ] Add unit tests with mocked httpx responses simulating Running → Idle transition
- [ ] Typecheck passes
- [ ] Unit tests pass

---

#### US-64.3: Trigger Jellyseerr Library Sync Before Sync
**As a** media server owner
**I want** the sync to automatically trigger a Jellyseerr library sync
**So that** Jellyseerr knows about all content in Jellyfin before I fetch request statuses

**Background:**
Jellyseerr maintains its own knowledge of what's in Jellyfin. Without syncing, new Jellyfin content won't be marked as "available" in Jellyseerr requests. The "Commencer le scan" button in Jellyseerr settings triggers this sync.

**Acceptance Criteria:**
- [ ] Create `trigger_jellyseerr_library_sync(server_url, api_key)` function in `sync.py`
- [ ] Function calls `POST {server_url}/api/v1/settings/jellyfin/sync`
- [ ] Headers: `X-Api-Key: {api_key}`, `Content-Type: application/json`
- [ ] Body: `{"start": true}` (required to trigger the sync)
- [ ] Function returns True on 200 response with `running: true`, False on failure
- [ ] Failures are logged as warnings (not exceptions)
- [ ] Add unit tests with mocked httpx responses
- [ ] Typecheck passes
- [ ] Unit tests pass

---

#### US-64.4: Poll Jellyseerr Sync Completion
**As a** media server owner
**I want** the sync to wait for the Jellyseerr library sync to complete
**So that** request availability statuses are accurate

**Background:**
Similar to Jellyfin, Jellyseerr's library sync runs asynchronously. We need to poll until it completes. Check the API docs for a status endpoint or use the same endpoint with a GET to check running state.

**Acceptance Criteria:**
- [ ] Create `wait_for_jellyseerr_sync_completion(server_url, api_key, timeout_seconds=300)` function
- [ ] Function calls `GET {server_url}/api/v1/settings/jellyfin/sync` with `X-Api-Key` header
- [ ] Response includes `{running: bool, progress: int, total: int}`
- [ ] Polls every 5 seconds until `running == false` or timeout
- [ ] Returns True if sync completed, False if timed out
- [ ] Add logging for progress (e.g., "Jellyseerr sync: 45/69 items")
- [ ] Add unit tests with mocked httpx responses
- [ ] Typecheck passes
- [ ] Unit tests pass

---

#### US-64.5: Integrate Library Refresh into Sync Flow
**As a** media server owner
**I want** the library refresh to happen automatically at the start of every sync
**So that** I don't have to remember to do it manually

**Background:**
Integrate the refresh functions into `run_user_sync()`. Order should be:
1. Trigger Jellyfin refresh + wait for completion
2. Trigger Jellyseerr sync + wait for completion
3. Fetch Jellyfin media (existing)
4. Fetch Jellyseerr requests (existing)

**Acceptance Criteria:**
- [ ] Modify `run_user_sync()` to call refresh functions BEFORE fetching data
- [ ] Update sync progress UI to show "refreshing_libraries" step
- [ ] If Jellyfin refresh fails, log warning and continue with sync
- [ ] If Jellyseerr sync fails, log warning and continue with sync
- [ ] Works for both scheduled syncs (Celery) and manual sync triggers
- [ ] Integration test: verify refresh calls happen before data fetch
- [ ] Docker verification: test full flow with real Jellyfin/Jellyseerr
- [ ] Typecheck passes
- [ ] Unit tests pass

---

### Non-Goals (Epic 64)
- Selective library refresh (only Movies OR Shows) - we refresh all
- User-configurable refresh toggle (always enabled)
- Refresh without waiting (we always wait for completion)

### Technical Considerations
- Jellyfin library scans can take 1-10+ minutes depending on library size
- Timeout should be configurable but default to 5 minutes
- All refresh failures are non-blocking (sync continues without fresh data)
- Progress UI should indicate when waiting for library refresh

---

<!-- Example format for new stories:

### Epic XX: Feature Name

#### US-XX.1: Story Title
**As a** [user role]
**I want** [feature]
**So that** [benefit]

**Background:**
[Context and details]

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Typecheck passes
- [ ] Unit tests pass

-->
