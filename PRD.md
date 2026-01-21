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

See [ARCHIVED_PRD.md](./ARCHIVED_PRD.md) for the complete list of **191 completed user stories** across **47 epics**.

---

## Pending Stories

---

## Epic 48: Ultra.cc Storage & Traffic Monitoring

### Overview

Integrate Ultra.cc API to monitor seedbox storage and traffic usage. Display stats on the dashboard above issues, with configurable warning thresholds. This helps users proactively manage their seedbox resources before running out of storage or traffic.

### Goals

- Allow users to configure Ultra.cc API credentials in settings
- Fetch storage/traffic stats during the existing sync process
- Display stats prominently on dashboard with visual warning indicators
- Let users set their own warning thresholds

### Non-Goals

- Slack/email notifications (future enhancement)
- Automatic actions when thresholds are exceeded
- Historical tracking of storage/traffic over time

### Technical Considerations

- Ultra API endpoint: `{base_url}/total-stats` with Bearer token auth
- Response includes: `service_stats_info.free_storage_gb` and `service_stats_info.traffic_available_percentage`
- Store encrypted auth token like existing Jellyfin/Jellyseerr keys
- Stats should be cached in database (fetched during sync, not on every page load)

---

### US-48.1: Ultra API Settings - Backend

**As a** user
**I want** to configure my Ultra.cc API credentials
**So that** the app can fetch my storage and traffic stats

**Acceptance Criteria:**

- [ ] Add `ultra_api_url` (String, nullable) and `ultra_api_key_encrypted` (String, nullable) columns to UserSettings model
- [ ] Create Alembic migration for new columns
- [ ] PATCH `/api/settings` accepts `ultra_api_url` and `ultra_api_key` fields
- [ ] Ultra API key is encrypted before storage (like Jellyfin/Jellyseerr keys)
- [ ] GET `/api/settings` returns `ultra_api_configured: bool` (not the actual key)
- [ ] Typecheck passes
- [ ] Unit tests pass

---

### US-48.2: Ultra API Settings - Frontend

**As a** user
**I want** to enter my Ultra.cc API URL and token in the settings page
**So that** I can connect my seedbox monitoring

**Acceptance Criteria:**

- [ ] Settings page has a new "Seedbox Monitoring" section with Ultra API URL and API Token fields
- [ ] Fields are optional (form submits without them)
- [ ] Shows "Connected" badge when `ultra_api_configured` is true
- [ ] Shows masked "••••••••" for token field when already configured
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

### US-48.3: Ultra Warning Thresholds - Settings

**As a** user
**I want** to set my own warning thresholds for storage and traffic
**So that** I get alerts relevant to my usage patterns

**Acceptance Criteria:**

- [ ] Add `ultra_storage_warning_gb` (Integer, default 100) and `ultra_traffic_warning_percent` (Integer, default 20) columns to UserSettings
- [ ] Create Alembic migration for new columns
- [ ] PATCH `/api/settings` accepts threshold values
- [ ] GET `/api/settings` returns current threshold values
- [ ] Settings page has number inputs for both thresholds in the "Seedbox Monitoring" section
- [ ] Inputs show defaults (100 GB, 20%) when not set
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

### US-48.4: Fetch Ultra Stats During Sync

**As a** user
**I want** my seedbox stats fetched when I sync
**So that** I always see current storage and traffic info

**Acceptance Criteria:**

- [ ] Create `ultra_service.py` with `fetch_ultra_stats(url, api_key)` function
- [ ] Function calls `{url}/total-stats` with Bearer token authentication
- [ ] Returns dict with `free_storage_gb` (float) and `traffic_available_percentage` (float), or None if API fails
- [ ] Add `ultra_free_storage_gb` (Float, nullable), `ultra_traffic_available_percent` (Float, nullable), `ultra_last_synced_at` (DateTime, nullable) columns to UserSettings
- [ ] Create Alembic migration for new columns
- [ ] Sync process (`/api/sync`) calls Ultra API if credentials are configured
- [ ] Stats are stored in UserSettings after successful fetch
- [ ] Sync succeeds even if Ultra API call fails (non-blocking)
- [ ] Typecheck passes
- [ ] Unit tests pass

---

## Epic 49: Fix Deletion Cache Persistence

### Overview

When users delete content from Radarr/Sonarr/Jellyseerr via the Issues page, the item disappears due to optimistic UI updates but reappears after a page refresh. This happens because the internal cache (`CachedMediaItem`, `CachedJellyseerrRequest` tables) is not updated after deletion - items only disappear after a full sync. This creates a confusing user experience.

### Goals

- Delete items from internal cache immediately after successful external API deletion
- Prevent deleted items from reappearing on page refresh
- Handle partial deletion failures gracefully (delete from cache if primary deletion succeeds)

### Non-Goals

- Changing the sync behavior (sync will still replace entire cache)
- Adding undo/restore functionality for deleted items
- Changing the optimistic UI update pattern (it works well)

### Technical Considerations

- Three delete endpoints need modification: `DELETE /api/content/movie/{tmdb_id}`, `DELETE /api/content/series/{tmdb_id}`, `DELETE /api/content/request/{jellyseerr_id}`
- For movies/series: delete from `CachedMediaItem` by TMDB ID (need to match via `raw_data` JSON field)
- For requests: delete from `CachedJellyseerrRequest` by Jellyseerr ID
- Cache deletion should happen after successful external API deletion
- If Radarr/Sonarr deletion succeeds but Jellyseerr fails, still delete from cache

---

### US-49.1: Delete Movies from Cache After Deletion

**As a** user
**I want** deleted movies to stay deleted after page refresh
**So that** I don't see ghost items that are already removed from my library

**Acceptance Criteria:**

- [ ] After successful Radarr deletion, delete matching `CachedMediaItem` from database
- [ ] Match by TMDB ID stored in `raw_data` JSON field (key: `ProviderIds.Tmdb`)
- [ ] If Radarr deletion succeeds but Jellyseerr fails, still delete from cache
- [ ] If Radarr deletion fails, do NOT delete from cache
- [ ] Also delete matching `CachedJellyseerrRequest` if it exists (by TMDB ID)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in Docker: delete a movie, refresh page, item stays deleted

---

### US-49.2: Delete Series from Cache After Deletion

**As a** user
**I want** deleted TV series to stay deleted after page refresh
**So that** I don't see ghost items that are already removed from my library

**Acceptance Criteria:**

- [ ] After successful Sonarr deletion, delete matching `CachedMediaItem` from database
- [ ] Match by TMDB ID stored in `raw_data` JSON field (key: `ProviderIds.Tmdb`)
- [ ] If Sonarr deletion succeeds but Jellyseerr fails, still delete from cache
- [ ] If Sonarr deletion fails, do NOT delete from cache
- [ ] Also delete matching `CachedJellyseerrRequest` if it exists (by TMDB ID)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in Docker: delete a series, refresh page, item stays deleted

---

### US-49.3: Delete Requests from Cache After Deletion

**As a** user
**I want** deleted Jellyseerr requests to stay deleted after page refresh
**So that** I don't see ghost requests in the Unavailable Requests tab

**Acceptance Criteria:**

- [ ] After successful Jellyseerr media deletion, delete matching `CachedJellyseerrRequest` from database
- [ ] Match by Jellyseerr ID (existing lookup already works)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in Docker: delete a request, refresh page, request stays deleted

---

### US-48.5: Display Ultra Stats on Dashboard

**As a** user
**I want** to see my seedbox storage and traffic stats on the dashboard
**So that** I can monitor my resources at a glance

**Acceptance Criteria:**

- [ ] GET `/api/settings` returns `ultra_free_storage_gb`, `ultra_traffic_available_percent`, `ultra_last_synced_at` (if configured)
- [ ] Dashboard shows "Seedbox Status" card above issues section (only when Ultra is configured)
- [ ] Card displays: free storage (GB), traffic available (%)
- [ ] Card shows last synced timestamp
- [ ] Storage value turns yellow/warning when below `ultra_storage_warning_gb` threshold
- [ ] Storage value turns red/danger when below 50% of threshold
- [ ] Traffic value turns yellow/warning when below `ultra_traffic_warning_percent` threshold
- [ ] Traffic value turns red/danger when below 50% of threshold
- [ ] Card is hidden entirely when Ultra API is not configured
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

## Epic 50: Update Whitelist Duration Options

### Overview

Update the whitelist duration picker to offer more granular short-term options. Currently the options are: Permanent, 3 Months, 6 Months, 1 Year, Custom Date. Users want shorter durations like 1 Week and 1 Month for temporary whitelisting, and the 1 Year option is rarely used.

### Goals

- Replace current duration options with: Permanent, 1 Week, 1 Month, 3 Months, 6 Months, Custom Date
- Apply to all whitelist types (content, french-only, language-exempt, large, requests)
- No backend changes needed (expires_at is already a flexible datetime)

### Non-Goals

- Adding more duration options beyond the specified set
- Changing how expiration is stored or processed in the backend

### Technical Considerations

- Frontend-only change in `frontend/src/routes/issues/+page.svelte`
- The `getExpirationDate()` function needs new cases for `1week` and `1month`
- The `durationOptions` array needs to be updated
- The `DurationOption` type needs to be updated

---

### US-50.1: Update Whitelist Duration Options

**As a** user
**I want** shorter whitelist duration options (1 Week, 1 Month)
**So that** I can temporarily whitelist content without long commitments

**Acceptance Criteria:**

- [ ] Duration options are: Permanent, 1 Week, 1 Month, 3 Months, 6 Months, Custom Date (in that order)
- [ ] 1 Year option is removed
- [ ] `DurationOption` type updated to include `1week` and `1month`, remove `1year`
- [ ] `getExpirationDate()` function handles `1week` (adds 7 days) and `1month` (adds 1 month)
- [ ] Duration picker displays correctly on Issues page
- [ ] Duration picker displays correctly on Unavailable page
- [ ] Existing frontend unit tests updated to reflect new options
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: whitelist an item with 1 Week duration, confirm expiration date is 7 days from now

---

## Epic 51: Recently Available - Show New Episodes from Ongoing Series

### Overview

The "Recently Available" page currently doesn't show new episodes from ongoing TV series. When a series is partially available (status 4 in Jellyseerr) and new episodes air, they don't appear because the app only checks `mediaAddedAt` date, which doesn't update when new episodes are added.

Additionally, the page only shows the title without any season/episode context. Users want to see:
- For fully available content: Which seasons are available (e.g., "Seasons 1-3 (30 eps)")
- For partially available series: Which episodes recently aired (e.g., "S4: 5/12 episodes")

### Goals

- Include ongoing series with recently aired episodes in the "Recently Available" list
- Display season and episode counts for all TV content
- Fetch and cache episode air dates during sync
- No additional API calls at page load time

### Non-Goals

- Showing individual episode entries (one entry per series)
- Episode-level details like episode titles or descriptions
- Push notifications for new episodes

### Technical Considerations

- During sync, fetch episode details from Jellyseerr API for status 4 TV shows: `GET /api/v1/tv/{tmdb_id}/season/{season_number}`
- Store episode list in `raw_data.media.seasons[].episodes` (already a JSON field)
- Episode data includes `episodeNumber`, `name`, `airDate`
- For display, calculate episode counts from cached data
- Reference implementation: `original_script.py` lines 714-792 (`fetch_season_episodes`, `get_recent_episodes_for_season`)

---

### US-51.1: Fetch Episode Details During Sync

**As a** user
**I want** episode air dates to be cached during sync
**So that** the Recently Available page can detect new episodes without API calls

**Acceptance Criteria:**

- [ ] Add `fetch_jellyseerr_season_episodes(client, server_url, api_key, tmdb_id, season_number)` function to `sync.py`
- [ ] Function calls `GET /api/v1/tv/{tmdb_id}/season/{season_number}` endpoint
- [ ] Returns list of `{episodeNumber, name, airDate}` dicts
- [ ] Graceful failure: returns empty list on API error (logged as warning)
- [ ] In `fetch_jellyseerr_requests()`, for status 4 TV shows, fetch episodes for each partially available season
- [ ] Store episode data in `raw_data.media.seasons[].episodes` array
- [ ] Typecheck passes
- [ ] Unit tests pass

---

### US-51.2: Include Ongoing Series in Recently Available

**As a** user
**I want** to see ongoing series with new episodes in the Recently Available list
**So that** I know when new episodes of my shows become available

**Acceptance Criteria:**

- [ ] Add `_get_recent_episodes_from_cached_data(request, days_back)` helper function in `content.py`
- [ ] Function checks `raw_data.media.seasons[].episodes[].airDate` for episodes within `days_back` window
- [ ] Returns `{season_num: [episode_nums]}` dict if recent episodes found, None otherwise
- [ ] Modify `get_recently_available()` to check for recent episodes on status 4 TV shows
- [ ] If recent episodes found, use today's date as `availability_date` to force inclusion
- [ ] Series appears once (not per episode) in the list
- [ ] Typecheck passes
- [ ] Unit tests pass

---

### US-51.3: API Response with Season/Episode Details

**As a** frontend developer
**I want** the Recently Available API to return season and episode information
**So that** the UI can display episode counts

**Acceptance Criteria:**

- [ ] Add optional fields to `RecentlyAvailableItem` model:
  - `season_info: str | None` - e.g., "Seasons 1-3" or "Season 4 in progress"
  - `episode_count: int | None` - total episodes for fully available
  - `available_episodes: int | None` - episodes available so far (for partial)
  - `total_episodes: int | None` - total episodes in current season (for partial)
- [ ] For status 5 TV shows: populate with total seasons and episode count from `raw_data`
- [ ] For status 4 TV shows: populate with current season progress
- [ ] Movies return `None` for all these fields
- [ ] Typecheck passes
- [ ] Unit tests pass

---

### US-51.4: Display Episode Details in UI

**As a** user
**I want** to see season and episode information on the Recently Available page
**So that** I understand what content is actually new

**Acceptance Criteria:**

- [ ] Add "Details" column to the table (between Title and Type)
- [ ] For fully available TV: display "Seasons 1-3 (30 eps)" format
- [ ] For partially available TV: display "S4: 5/12 episodes" format
- [ ] For movies: display "—" or leave empty
- [ ] Update the "Copy" feature to include episode details in the copied text
- [ ] Responsive: hide Details column on mobile (like Requested By)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

## Epic 52: TV Series Language Detection & Per-Episode Whitelisting

### Overview

Language detection currently only flags movies, never TV series episodes. The root cause is that `check_audio_languages()` reads `MediaSources` from Series-level `raw_data`, which doesn't contain individual episode audio tracks. Additionally, users need the ability to whitelist specific episodes (not entire series) from language checks - matching the original script's `LANGUAGE_CHECK_EPISODE_ALLOWLIST` behavior.

### Goals

- Detect language issues (missing EN/FR audio) at the episode level for TV series
- Cache episode language check results during sync to keep UI responses fast
- Allow users to whitelist individual episodes from language checks
- Display which specific episodes have language issues in the Issues page

### Non-Goals

- Changing how movie language detection works (already working)
- Adding subtitles-only exemption at episode level (only audio for now)
- Automatic detection of intentionally monolingual content

### Technical Considerations

- Reuse existing `calculate_season_sizes()` loop which already fetches all episodes
- Store language check results in new JSON fields on `CachedMediaItem`
- Create new `EpisodeLanguageExempt` table for per-episode whitelisting
- Episode exemptions checked during sync, not at display time

---

### US-52.1: Cache Episode Language Data During Sync

**As a** user with a Jellyfin server configured
**I want** the sync process to check language tracks for all TV series episodes
**So that** series with missing audio tracks are correctly flagged in the Issues page

**Acceptance Criteria:**

- [ ] Add `language_check_result` JSON field to `CachedMediaItem` model (structure: `{has_english, has_french, has_french_subs, checked_at}`)
- [ ] Add `problematic_episodes` JSON field to `CachedMediaItem` model (structure: `[{identifier, name, season, episode, missing_languages}]`)
- [ ] Create Alembic migration for new fields
- [ ] Add `check_episode_audio_languages(episode)` helper in `sync.py`
- [ ] Add `check_series_episodes_languages(client, server_url, api_key, series_id, series_name)` function
- [ ] Call language checking in `calculate_season_sizes()` loop after size calculation
- [ ] Add movie language checking in `cache_media_items()` from raw_data MediaSources
- [ ] Typecheck passes
- [ ] Unit tests pass

---

### US-52.2: Use Cached Language Data in Content Service

**As a** user viewing the Issues page
**I want** TV series with language issues to appear in the Language tab
**So that** I can identify and fix series with missing audio tracks

**Acceptance Criteria:**

- [ ] Modify `check_audio_languages()` to use cached `language_check_result` field when available
- [ ] Keep fallback to raw_data parsing for backwards compatibility (movies without cached data)
- [ ] Add `problematic_episodes` field to `ContentIssueItem` response model
- [ ] Include problematic episodes data in `/api/content/issues` response for series with language issues
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in Docker: sync, then check `/api/content/issues` returns series with language issues

---

### US-52.3: Per-Episode Language Whitelist - Backend

**As a** user with specific episodes that have intentional language differences
**I want** to whitelist individual episodes from language checks
**So that** I don't see false positives for episodes that are meant to have limited audio tracks

**Acceptance Criteria:**

- [ ] Create `EpisodeLanguageExempt` model with: `id`, `user_id`, `jellyfin_id` (series ID), `series_name`, `season_number`, `episode_number`, `episode_name`, `created_at`, `expires_at`
- [ ] Add unique constraint on `(user_id, jellyfin_id, season_number, episode_number)`
- [ ] Create Alembic migration for new table
- [ ] Add `add_episode_language_exempt()` service function
- [ ] Add `get_episode_language_exempt()` service function (list all for user)
- [ ] Add `remove_episode_language_exempt()` service function
- [ ] Add `get_episode_exempt_set(db, user_id)` returning set of `(jellyfin_id, season, episode)` tuples
- [ ] Add API endpoints:
  - `GET /api/whitelist/episode-exempt` - List all exemptions
  - `POST /api/whitelist/episode-exempt` - Add exemption (body: `{jellyfin_id, series_name, season_number, episode_number, episode_name, expires_at?}`)
  - `DELETE /api/whitelist/episode-exempt/{id}` - Remove exemption
- [ ] Integrate exemption checking into `check_series_episodes_languages()` - skip exempt episodes
- [ ] Typecheck passes
- [ ] Unit tests pass

---

### US-52.4: Display Problematic Episodes with Whitelist Actions

**As a** user viewing a TV series with language issues
**I want** to see which specific episodes have problems and whitelist them individually
**So that** I can manage language issues at the episode level

**Acceptance Criteria:**

- [ ] Update Issues page to show expandable episode list when a series has `problematic_episodes`
- [ ] Click on series row to expand/collapse episode list
- [ ] Each episode row shows: identifier (S01E05), name, missing languages (badges)
- [ ] Each episode row has a "Whitelist" button with duration picker
- [ ] Whitelisting calls `POST /api/whitelist/episode-exempt` with episode details
- [ ] After successful whitelist, remove episode from displayed list (optimistic update)
- [ ] Show loading state on whitelist button during API call
- [ ] Show toast notification on success/error
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: expand series, whitelist an episode, episode disappears from list

---

### US-52.5: Episode Exemptions Tab in Whitelist Page

**As a** user managing my whitelists
**I want** to see and manage episode-level language exemptions
**So that** I can review and remove exemptions I no longer need

**Acceptance Criteria:**

- [ ] Add "Episode Exempt" tab to Whitelist page (between "Language Exempt" and "Large Content")
- [ ] Tab displays list of exempted episodes with: series name, episode identifier (S01E05), episode name, expiration status
- [ ] Each item has a remove button (trash icon)
- [ ] Remove calls `DELETE /api/whitelist/episode-exempt/{id}`
- [ ] Show empty state when no exemptions exist
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: view exemptions, remove one, list updates

---
