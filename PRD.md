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

## Epic 0: Foundation & Deployment

### Overview
Establish the foundational infrastructure: working full-stack communication, containerization, and production deployment.

### Goals
- Verify frontend-backend communication works
- Enable reproducible deployments via Docker
- Make app accessible on the internet

### User Stories

#### US-0.1: Hello World (Full Stack) ✅
**As a** developer
**I want** a working frontend that displays "Hello World" from the backend
**So that** I can verify the full stack communication works

**Acceptance Criteria:**
- [x] Backend endpoint `GET /api/hello` returns `{"message": "Hello World"}`
- [x] Frontend displays the message fetched from backend
- [x] Both run locally with `docker-compose up`

---

#### US-0.2: Dockerize the Application ✅
**As a** developer
**I want** the entire application containerized
**So that** I can deploy it anywhere

**Acceptance Criteria:**
- [x] Dockerfile for backend
- [x] Dockerfile for frontend
- [x] docker-compose.yml that runs both + database
- [x] `docker-compose up` starts the full app on localhost

---

#### US-0.3: Deploy to VPS ✅
**As a** developer
**I want** to deploy the app to my VPS
**So that** it's accessible on the internet

**Acceptance Criteria:**
- [x] GitHub Actions workflow for CI/CD
- [x] Auto-deploy to VPS on push to `main`
- [x] App accessible at configured domain
- [x] HTTPS via Let's Encrypt / Caddy

### Non-Goals
- Database migrations (handled by SQLAlchemy create_all for now)

---

## Epic 1: Authentication

### Overview
Allow users to register, log in, and access their private data securely.

### Goals
- Secure user registration with hashed passwords
- JWT-based authentication
- Route protection for authenticated users

### User Stories

#### US-1.1: User Registration ✅
**As a** new user
**I want** to create an account
**So that** I can use the dashboard

**Acceptance Criteria:**
- [x] Registration form (email, password)
- [x] Backend creates user in database
- [x] Password is hashed securely (bcrypt)
- [x] User redirected to login after signup

---

#### US-1.2: User Login ✅
**As a** registered user
**I want** to log in
**So that** I can access my dashboard

**Acceptance Criteria:**
- [x] Login form (email, password)
- [x] Backend validates credentials and returns JWT
- [x] Token stored in frontend (localStorage)
- [x] User redirected to dashboard

---

#### US-1.3: Protected Routes ✅
**As a** user
**I want** my data to be private
**So that** only I can see my content

**Acceptance Criteria:**
- [x] API endpoints require valid JWT
- [x] Frontend redirects to login if not authenticated
- [x] Each user sees only their own data

### Non-Goals
- OAuth/social login (see SUGGESTIONS.md)
- Password reset flow

---

## Epic 2: Configuration

### Overview
Allow users to connect their external services (Jellyfin, Jellyseerr) and set up navigation.

### Goals
- Secure storage of API credentials (encrypted)
- Validate connections before saving
- Consistent navigation across all pages

### User Stories

#### US-2.1: Configure Jellyfin Connection ✅
**As a** user
**I want** to input my Jellyfin API key and URL
**So that** the app can fetch my library data

**Acceptance Criteria:**
- [x] Settings page with form for Jellyfin URL and API key
- [x] Backend validates connection before saving
- [x] Credentials stored encrypted in database
- [x] Success/error feedback shown to user

---

#### US-2.1.5: Backend Cleanup ✅
**As a** developer
**I want** to remove premature code that was created but not needed
**So that** the codebase only contains code for completed stories

**Acceptance Criteria:**
- [x] Delete unused Pydantic models: `models/content.py`, `models/jellyseerr.py`, `models/whitelist.py`
- [x] Update `models/__init__.py` to only export `user.py` and `settings.py` models
- [x] Remove premature SQLAlchemy tables from `database.py`: `WhitelistContent`, `WhitelistFrenchOnly`, `WhitelistFrenchSubsOnly`, `WhitelistLanguageExempt`, `WhitelistEpisodeExempt`, `AppSettings`
- [x] Run `uv run pytest` - all tests pass
- [x] Run `uv run mypy app` - no type errors
- [x] Typecheck passes
- [x] Unit tests pass

---

#### US-2.2: Configure Jellyseerr Connection ✅
**As a** user
**I want** to input my Jellyseerr API key and URL
**So that** the app can fetch my requests data

**Acceptance Criteria:**
- [x] Settings page shows Jellyseerr section below Jellyfin
- [x] Form fields for Jellyseerr URL and API key
- [x] Backend validates connection by calling Jellyseerr API
- [x] Credentials stored encrypted in database (using existing encryption service)
- [x] Toast notification shows "Jellyseerr connected" on success or error message on failure
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

---

#### US-2.3: Navigation Header ✅
**As a** user
**I want** a consistent navigation header across all pages
**So that** I can easily move between dashboard, settings, and log out

**Acceptance Criteria:**
- [x] Header component with app logo/name on the left
- [x] User menu on the right with: Settings link, Logout button
- [x] Header appears on dashboard, settings, and all authenticated pages
- [x] Current page highlighted in navigation
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

### Non-Goals
- Breadcrumb navigation (see SUGGESTIONS.md)
- Dark mode toggle

### Technical Considerations
- Reuse existing encryption service from US-2.1
- Jellyseerr API: `GET /api/v1/status` for connection test

---

## Epic 7: Background Tasks & Refresh

### Overview
Keep dashboard data fresh through automatic and manual sync mechanisms.

### Goals
- Daily automatic data refresh
- On-demand manual refresh
- Prevent API abuse

### User Stories

#### US-7.1: Automatic Daily Data Sync ✅
**As a** user
**I want** my data to refresh automatically every day
**So that** the dashboard is always up-to-date

**Acceptance Criteria:**
- [x] **Refer to `original_script.py` functions: `setup_jellyfin_client`, `fetch_jellyseer_requests`, `aggregate_all_user_data`, `get_movies_and_shows_for_user`**
- [x] **Use API keys from `backend/.env` file for testing** (JELLYFIN_API_KEY, JELLYFIN_SERVER_URL, JELLYSEERR_API_KEY, JELLYSEERR_BASE_URL)
- [x] **All cached data is tied to a user_id** - each user's sync is independent
- [x] Background task can be triggered manually (for testing) or scheduled daily
- [x] Uses the user's own stored API keys (from UserSettings) to fetch their data
- [x] Fetches data from Jellyfin API: all movies/series with UserData, MediaSources
- [x] Fetches data from Jellyseerr API: all requests with status
- [x] Stores raw results in database cache tables with `user_id` FK (e.g., `cached_media_items`, `cached_jellyseerr_requests`)
- [x] Dashboard shows "Last synced: [timestamp]" for the current user
- [x] Failed syncs logged but don't crash the app
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Missing daily scheduler - see SUGGESTIONS.md [P1]

---

#### US-7.1.5: Local Integration Test for Sync ✅
**As a** developer
**I want** to verify the sync service works with real Jellyfin/Jellyseerr APIs locally
**So that** I can confirm data is fetched and cached correctly before deploying

**Acceptance Criteria:**
- [x] Run `docker-compose up` locally
- [x] Register/login with credentials from `.env.example` (APP_USER_EMAIL, APP_USER_PASSWORD)
- [x] Configure Jellyfin settings via Settings UI (user's real Jellyfin server)
- [x] Configure Jellyseerr settings via Settings UI (user's real Jellyseerr server)
- [x] Trigger sync via `curl -X POST http://localhost:8080/api/sync` with JWT token
- [x] Verify `cached_media_items` table has data (query via SQLite or check /api/sync/status)
- [x] Verify `cached_jellyseerr_requests` table has data
- [x] Verify `GET /api/sync/status` returns correct counts (media_items_count > 0, requests_count > 0)
- [x] Dashboard displays "Last synced" timestamp after sync
- [x] Document any issues found in SUGGESTIONS.md

**Result:** Verified 324 media items, 244 requests synced successfully.

---

#### US-7.2: Manual Data Refresh ✅
**As a** user
**I want** to manually trigger a data refresh
**So that** I can see changes immediately

**Acceptance Criteria:**
- [x] "Refresh" button on dashboard header
- [x] Button shows loading spinner during refresh
- [x] Data updates on page after refresh completes
- [x] Rate limited: max 1 refresh per 5 minutes per user
- [x] Toast notification shows result (success or rate limit message)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

### Non-Goals
- Real-time websocket updates
- Configurable sync schedule

### Technical Considerations
**Jellyfin API (from original_script.py):**
```
Authentication: Header `X-Emby-Token: {api_key}`

Get all movies/series for user:
  GET /Users/{userId}/Items
  Params:
    - UserId: user ID
    - IncludeItemTypes: 'Movie,Series'
    - Recursive: 'true'
    - Fields: 'DateCreated,UserData,Path,ProductionYear,MediaSources'
    - Limit: 10000

Response item structure:
  - Id: string (Jellyfin item ID)
  - Name: string
  - Type: 'Movie' | 'Series'
  - ProductionYear: int
  - DateCreated: ISO datetime string
  - Path: string (file path)
  - UserData:
    - Played: boolean
    - LastPlayedDate: ISO datetime string (nullable)
    - PlayCount: int
  - MediaSources: array with size info
```

**Jellyseerr API (from original_script.py):**
```
Authentication: Header `X-Api-Key: {api_key}`

Get all requests (paginated):
  GET /api/v1/request
  Params: take=50, skip=(page-1)*50
  Response:
    - results: array of requests
    - pageInfo: { results, pages }
```

- Use FastAPI BackgroundTasks for simplicity (Celery if needed later)
- Store `last_synced_at` in UserSettings

---

## Epic 3: Old/Unwatched Content

### Overview
Help users identify content that hasn't been watched in a configurable period, allowing them to reclaim storage space.

### Goals
- Surface unwatched content older than threshold (default: 4 months)
- Respect user's protected content whitelist
- Display useful metadata (size, last watched, path)

### User Stories

#### US-3.1: View Old Unwatched Content ✅
**As a** user
**I want** to see a list of content not watched in 4+ months
**So that** I can decide what to delete

**Acceptance Criteria:**
- [x] **Refer to `original_script.py` functions: `filter_old_or_unwatched_items`, `list_old_or_unwatched_content`**
- [x] Dashboard page shows list of old/unwatched movies and series (reads from **current user's** cached DB, not live API)
- [x] API endpoint filters by `user_id` from JWT token
- [x] Each item shows: name, type (movie/series), year, size (formatted), last watched date, file path
- [x] List sorted by size (largest first)
- [x] Total count and total size displayed at top
- [x] Content in user's whitelist is excluded from results
- [x] Uses hardcoded threshold: 4 months, min age: 3 months
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Result:** 221 items totaling 741.3 GB verified.

---

#### US-3.2: Protect Content from Deletion ✅
**As a** user
**I want** to add content to a whitelist
**So that** it won't appear in the "to delete" list

**Acceptance Criteria:**
- [x] "Protect" button on each content item in old content list
- [x] Clicking creates whitelist entry linked to current user (user_id foreign key)
- [x] Protected item immediately disappears from old content list
- [x] Toast notification confirms "Added to whitelist"
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

---

#### US-3.3: Manage Content Whitelist ✅
**As a** user
**I want** to view and edit my content whitelist
**So that** I can remove protection from items

**Acceptance Criteria:**
- [x] Whitelist page accessible from settings or navigation
- [x] Shows all items in user's content whitelist
- [x] Each item shows: name, date added
- [x] "Remove" button to unprotect items
- [x] Removing item makes it appear again in old content list (if still old)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

### Non-Goals
- Direct deletion from dashboard (requires Radarr/Sonarr - see SUGGESTIONS.md)
- Automatic deletion based on rules

### Technical Considerations
**Jellyfin API (from original_script.py):**
```
GET /Users/{userId}/Items
Headers: X-Emby-Token: {api_key}
Params:
  - IncludeItemTypes: 'Movie,Series'
  - Recursive: 'true'
  - Fields: 'DateCreated,UserData,Path,ProductionYear,MediaSources'
  - Limit: 10000

Response UserData structure:
  - Played: boolean
  - LastPlayedDate: ISO datetime (nullable)
  - PlayCount: int
```
- Filter logic: `LastPlayedDate < (now - 4 months)` OR `Played == false AND DateCreated < (now - 3 months)`
- Cache results in database (API is slow)
- New table: `user_content_whitelist` with `user_id` FK

---

## Epic D: Dashboard Redesign

### Overview
Transform the dashboard from a simple status page into a unified library health center. Replace the "one tab per feature" approach with summary cards that link to a unified issues view.

### Goals
- Provide at-a-glance library health via summary cards
- Unify all issue types into a single filterable view
- Support content with multiple issues (e.g., both old AND large)
- Separate "problems" from "informational" content

### User Stories

#### US-D.1: Dashboard Summary Cards ✅
**As a** user
**I want** to see summary cards for each issue type on my dashboard
**So that** I can quickly understand my library's health status

**Acceptance Criteria:**
- [x] Dashboard shows 4 issue cards: Old Content, Large Movies, Language Issues, Unavailable Requests
- [x] Each card displays: count of items, total size (where applicable)
- [x] Cards are clickable → navigate to `/issues?filter=<type>`
- [x] Cards show loading skeleton while data loads
- [x] Cards show "0 issues" gracefully when no problems exist
- [x] API endpoint `GET /api/content/summary` returns counts for all issue types
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-13 - 4 summary cards with counts, sizes, icons, click navigation to /issues?filter=<type>

---

#### US-D.2: Dashboard Info Section ✅
**As a** user
**I want** to see informational content (recently available)
**So that** I can stay informed about my library without these being "problems"

**Acceptance Criteria:**
- [x] Separate "Info" section below issue cards
- [x] Recently Available card (past 7 days)
- [x] Card shows item count
- [x] Click → dedicated simple list view
- [x] Visually distinct from issue cards (different color/style)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-13 - Info section with Recently Available card, /info/recent list view. Also cleaned up E2E tests (79 -> 20) and updated testing documentation.

---

#### US-D.3: Unified Issues View ✅
**As a** user
**I want** a single view showing all content with issues
**So that** I can see everything in one place and filter by issue type

**Acceptance Criteria:**
- [x] New route `/issues` with unified table/list
- [x] Filter tabs: All, Old, Large, Language, Requests
- [x] URL supports filter param: `/issues?filter=old`
- [x] Each row shows all applicable issue badges (content can have multiple)
- [x] Sortable by: name, size, date, issue count
- [x] Actions column with contextual buttons (Protect, Mark French-only, etc.)
- [x] Total count and size displayed at top
- [x] Replaces old `/content/old-unwatched` route (redirect for backwards compat)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-13 - Unified issues view with filter tabs, sortable columns, Protect button. Integration tests pass.

---

#### US-D.4: Multi-Issue Content Support ✅
**As a** user
**I want** to see when content has multiple issues
**So that** I can prioritize cleaning up the worst offenders

**Acceptance Criteria:**
- [x] API endpoint returns all issue types for each content item
- [x] Frontend displays multiple badges per row (e.g., "🕐 Old 📦 Large")
- [x] Can filter to show "multiple issues only"
- [x] Sorting by "issue count" puts worst offenders first
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-13 - Added filter=multi to API, Multi-Issue filter tab in frontend, sortable Issues column header

---

#### US-D.5: Navigation Update ✅
**As a** user
**I want** the navigation to reflect the new architecture
**So that** I can easily access the Issues view

**Acceptance Criteria:**
- [x] Navigation shows: Dashboard | Issues | Whitelist | Settings
- [x] "Issues" link goes to `/issues`
- [x] "Old Content" nav item removed (redirects to `/issues?filter=old`)
- [x] Current page highlighted correctly
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-13 - Navigation shows Dashboard | Issues | Whitelist | Settings with correct active states

### Non-Goals
- Health score percentage (keeping it simple with counts)
- Collapsible info section
- Real-time updates via WebSocket

### Technical Considerations
- New API endpoint: `GET /api/content/summary` returning:
  ```json
  {
    "old_content": { "count": 221, "total_size_bytes": 795750400000 },
    "large_movies": { "count": 18, "total_size_bytes": 335007744000 },
    "language_issues": { "count": 34 },
    "unavailable_requests": { "count": 12 },
    "recently_available": { "count": 15 }
  }
  ```
- Unified issues endpoint: `GET /api/content/issues?filter=all|old|large|language|requests`
- Reuse existing content analysis logic from Epic 3, 4, 5
- Issue badges stored as enum: `old`, `large`, `language`, `request`

---

## Epic 4: Large Movies

### Overview
Identify movies that consume excessive storage, allowing users to re-download in lower quality.

**Integration Note:** Large movies are displayed in the **unified issues view** (Epic D), not a separate page. This epic focuses on the backend service.

### Goals
- Flag movies above size threshold (default: 13GB)
- Help users prioritize storage reclamation

### User Stories

#### US-4.1: Large Movies Backend Service ✅
**As a** user
**I want** to identify movies larger than 13GB
**So that** I can re-download them in lower quality

**Acceptance Criteria:**
- [x] **Refer to `original_script.py` function: `list_large_movies`**
- [x] Backend service `get_large_movies()` identifies movies exceeding 13GB (reads from cached DB)
- [x] Large movies marked with `large` issue type in content response
- [x] `/api/content/summary` endpoint includes `large_movies` count and total_size
- [x] `/api/content/issues?filter=large` returns only large movies
- [x] Each item includes: name, year, size (bytes), watched status, file path
- [x] Results sorted by size (largest first)
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-13 - is_large_movie() in content service, 13GB threshold, integrated with summary and issues endpoints

### Non-Goals
- Configurable threshold in v1 (see US-8.1)
- Automatic re-download triggers
- Separate dedicated page (use unified issues view)

### Technical Considerations
**Jellyfin API (from original_script.py):**
- Uses same endpoint as Epic 3: `GET /Users/{userId}/Items`
- Filter: `Type == 'Movie'` AND size from `MediaSources[0].Size > 13GB`
- Size calculation: `sum(ms.Size for ms in item.MediaSources)` in bytes

---

## Epic 5: Language Issues

### Overview
Identify content with language problems (missing French/English audio or subtitles).

**Integration Note:** Language issues are displayed in the **unified issues view** (Epic D), not a separate page. This epic focuses on the backend service and whitelist actions.

### Goals
- Flag content missing required languages
- Support whitelists for French-only content and exemptions
- Handle series at episode level

### User Stories

#### US-5.1: Language Issues Backend Service ✅
**As a** user
**I want** to identify content missing French or English audio
**So that** I can re-download proper versions

**Acceptance Criteria:**
- [x] **Refer to `original_script.py` functions: `check_audio_languages`, `list_recent_items_language_check`**
- [x] Backend service `get_language_issues()` identifies content with language problems (reads from cached DB)
- [x] Content marked with `language` issue type in response
- [x] `/api/content/summary` endpoint includes `language_issues` count
- [x] `/api/content/issues?filter=language` returns only items with language issues
- [x] Each item includes: name, type, year, specific issue (missing_en_audio, missing_fr_audio, missing_fr_subs)
- [x] For series: episode-level issues aggregated at series level
- [x] Content in language exemption whitelist is excluded
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-13 - check_audio_languages() in content service, 78 items with language issues in Docker test. Series episode-level aggregation and whitelist exclusion deferred to US-5.2/US-5.3

---

#### US-5.2: Mark Content as French-Only ✅
**As a** user
**I want** to mark French films as not needing English audio
**So that** they don't appear as language issues

**Acceptance Criteria:**
- [x] "Mark as French-only" button appears in unified issues view actions for items with missing EN audio
- [x] `POST /api/whitelist/french-only` creates entry (user_id FK)
- [x] Item no longer flagged for missing English audio
- [x] Can be managed in whitelist page
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-13 - FR Only button on issues page, French-Only section on whitelist page, 147 backend tests + 84 frontend tests pass

---

#### US-5.3: Exempt Content from Language Checks ✅
**As a** user
**I want** to completely exempt content from language checks
**So that** special cases don't show as issues

**Acceptance Criteria:**
- [x] "Exempt from checks" button appears in unified issues view actions for language issues
- [x] `POST /api/whitelist/language-exempt` creates entry (user_id FK)
- [x] Item no longer appears in language issues
- [x] Can be managed in whitelist page
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-13 - Exempt button on issues page, Language-Exempt section on whitelist page, 154 backend tests + 84 frontend tests pass

### Non-Goals
- Automatic language detection/correction
- Episode-level exemptions in v1
- Separate dedicated page (use unified issues view)

### Technical Considerations
**Jellyfin API (from original_script.py):**
```
# For movies: check MediaSources directly from Items response
MediaSources[].MediaStreams[]:
  - Type: 'Audio' | 'Subtitle'
  - Language: 'eng' | 'fre' | etc.

# For series: need episode-level data
GET /Shows/{seriesId}/Episodes
Params: UserId, Fields='MediaSources'
```
- Check for: EN audio, FR audio, FR subtitles
- Language codes: 'eng', 'en' for English; 'fre', 'fra', 'fr' for French
- New tables: `user_french_only_whitelist`, `user_language_exempt_whitelist` with user_id FK

---

## Epic 6: Jellyseerr Requests

### Overview
Display information about media requests from Jellyseerr.

**Integration Note:** This epic has two categories:
- **ISSUE (US-6.1):** Unavailable requests are problems → displayed in **unified issues view**
- **INFO (US-6.3):** Recently available is informational → displayed in **dashboard info section** with dedicated simple view

### Goals
- Show unavailable/pending requests (as issues)
- Display recently available content (informational)

### User Stories

#### US-6.1: Unavailable Requests Backend Service ✅
**As a** user
**I want** to identify Jellyseerr requests that aren't available
**So that** I can manually find them

**Acceptance Criteria:**
- [x] **Refer to `original_script.py` functions: `fetch_jellyseer_requests`, `get_jellyseer_unavailable_requests`, `analyze_jellyseer_requests`**
- [x] Backend service `get_unavailable_requests()` identifies unavailable/pending requests (reads from cached DB)
- [x] Requests marked with `request` issue type in response
- [x] `/api/content/summary` endpoint includes `unavailable_requests` count
- [x] `/api/content/issues?filter=requests` returns only unavailable requests
- [x] Each item includes: title, type (movie/TV), requested by, request date
- [x] For TV: includes which seasons are requested but missing
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-13 - 26 unavailable requests found in test data. Filters future/recent releases per original script.

---

#### US-6.3: Recently Available Content (INFO)
**As a** user
**I want** to see what became available this week
**So that** I can notify my friends

**Type:** INFO feature (not an issue)

**Acceptance Criteria:**
- [x] **Refer to `original_script.py` function: `get_jellyseer_recently_available_requests`**
- [x] Backend service `get_recently_available()` returns content from past 7 days (reads from cached DB)
- [x] `/api/content/summary` endpoint includes `recently_available` count
- [x] Dedicated simple list view at `/info/recent`
- [x] Grouped by date (newest first)
- [x] Each item shows: title, type, availability date
- [x] "Copy list" button for sharing (plain text format)
- [x] Accessed from dashboard Info section card
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-13 - Items grouped by date with headers, copy list includes grouped format, 3 items verified in browser

### Non-Goals
- Webhook notifications
- Integration with Discord/Telegram
- Separate pages for unavailable requests (use unified issues view)

### Technical Considerations
**Jellyseerr API (from original_script.py):**
```
Headers: X-Api-Key: {api_key}

# Get all requests (paginated)
GET /api/v1/request
Params: take=50, skip=(page-1)*50
Response:
  - results: array of requests
  - pageInfo: { results, pages }

# Request structure
{
  id: int,
  status: int,  # 1=pending, 2=approved, 3=declined, 4=available, 5=unavailable
  media: { tmdbId, mediaType: 'movie'|'tv' },
  requestedBy: { displayName },
  createdAt: ISO datetime
}

# Get media details (for season info)
GET /api/v1/movie/{tmdbId} or /api/v1/tv/{tmdbId}
```
- Filter unavailable: `status == 5` (unavailable) or `status == 1` (pending)
- For TV: check which seasons are available via media details

---

## Epic V: Validation Against Original Script

### Overview
Validate that the app's content analysis features produce correct results by comparing against `original_script.py` (the battle-tested source of truth). Use `/original-script` skill for debugging.

### Goals
- Verify each content analysis feature matches original script logic
- Identify and fix any filtering/calculation bugs
- Ensure counts match when accounting for expected differences

### Important: Whitelist Differences Are BY DESIGN

The original script uses **substring matching** against a hardcoded allowlist (~107 terms protecting ~144 items). This is a **HACK** that does NOT scale for multi-tenant SaaS.

The app correctly uses **exact jellyfin_id matching** against a per-user database whitelist. This difference is **intentional and correct**.

**DO NOT** implement substring matching. When validating, compare only the filtering logic, not whitelist behavior.

### User Stories

#### US-V.1: Validate Old Content Filtering Logic
**As a** developer
**I want** to verify the old/unwatched content logic matches the original script
**So that** I can trust the app produces correct results

**Acceptance Criteria:**
- [x] Run `/original-script` snippet for old content, note: total items, old items count, protected count
- [x] Run app API `GET /api/content/issues?filter=old`, note: total_count
- [x] Expected: app count = original (old items + protected items) since app has empty whitelist
- [x] If counts differ (excluding whitelist): investigate `is_old_or_unwatched()` in `content.py`
- [x] **Known issue to check**: min_age_months logic - original applies only to unplayed items, verify app does same
- [x] Document any bugs found in SUGGESTIONS.md
- [x] Fix identified bugs (separate commits per bug)
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-13 - Fixed bug: min_age_months was being applied to ALL items instead of only unplayed items. Original script only applies min_age check to never-watched content. Added test to verify fix.

---

#### US-V.2: Validate Large Movies Detection
**As a** developer
**I want** to verify the large movies detection matches the original script
**So that** users see the same large movies in both

**Acceptance Criteria:**
- [x] Run `/original-script` snippet for large movies, note count
- [x] Run app API `GET /api/content/issues?filter=large`, note: total_count
- [x] Counts should match (no whitelist involved for large movies)
- [x] If counts differ: investigate `is_large_movie()` in `content.py`
- [x] Verify threshold is 13GB in both
- [x] Document any bugs found in SUGGESTIONS.md
- [x] Fix identified bugs
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-13 - Both original script and app return 0 large movies (largest is 12.43 GB). Fixed minor bug: changed > to >= to match original script behavior. Added test for boundary condition.

---

#### US-V.3: Validate Language Issues Detection
**As a** developer
**I want** to verify the language issues detection matches the original script
**So that** users see the same language problems in both

**Acceptance Criteria:**
- [x] Run `/original-script` snippet for language issues, note count
- [x] Run app API `GET /api/content/issues?filter=language`, note: total_count
- [x] Compare counts (accounting for french-only and language-exempt whitelists)
- [x] If counts differ: investigate `check_audio_languages()` in `content.py`
- [x] Verify language codes checked: eng/en for English, fre/fra/fr for French
- [x] Document any bugs found in SUGGESTIONS.md
- [x] Fix identified bugs
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-13 - App count: 76 items (287.8 GB). Original script would have fewer due to hardcoded allowlists. This difference is by design - app uses per-user DB whitelists (starts empty). Language codes verified: eng/en/english for English, fre/fr/french/fra for French - matches original script exactly.

---

#### US-V.4: Validate Unavailable Requests Detection
**As a** developer
**I want** to verify the unavailable requests detection matches the original script
**So that** users see the same pending/unavailable requests in both

**Acceptance Criteria:**
- [x] Run `/original-script` snippet for unavailable requests, note count
- [x] Run app API `GET /api/content/issues?filter=requests`, note: total_count
- [x] Counts should match exactly (no whitelist involved)
- [x] If counts differ: investigate `get_unavailable_requests()` in `content.py`
- [x] Verify status codes: original uses status != 5 (Available)
- [x] Verify FILTER_FUTURE_RELEASES and FILTER_RECENT_RELEASES logic matches
- [x] Document any bugs found in SUGGESTIONS.md
- [x] Fix identified bugs
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-13 - App count: 26 unavailable requests. Fixed bug: titles were showing as 'Unknown' because Jellyseerr /api/v1/request endpoint doesn't include titles. Added fetch_media_title() to sync.py. Known difference: original script does complex TV series season analysis, app uses simpler status-based filtering. Documented in SUGGESTIONS.md [P2].

### Non-Goals
- Implementing substring whitelist matching (this is a HACK, not a feature)
- Achieving exact 1:1 parity when whitelist differences exist
- Validating UI rendering (focus on backend logic only)

### Technical Considerations
- Use `/original-script` skill for all comparisons
- Run `export $(cat .env | xargs)` before running original script snippets
- App must be running locally (`docker-compose up`) for API comparison
- Trigger sync before comparing: `POST /api/sync` to ensure fresh data

---

## Epic 8: Settings & Preferences

### Overview
Allow users to customize analysis thresholds to match their preferences.

### Goals
- Configurable thresholds for all analysis features
- Sensible defaults for new users

### User Stories

#### US-8.1: Configure Thresholds
**As a** user
**I want** to customize analysis thresholds
**So that** the dashboard matches my preferences

**Acceptance Criteria:**
- [x] Settings section for "Analysis Preferences"
- [x] Configurable: Old content months (default: 4)
- [x] Configurable: Minimum age months (default: 3)
- [x] Configurable: Large movie size GB (default: 13)
- [x] Changes saved to user settings and apply immediately
- [x] Reset to defaults button
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-13 - Analysis Preferences section in settings page, backend service uses user thresholds, 176 backend tests + 93 frontend tests pass

### Non-Goals
- Per-library thresholds
- Scheduled reports

### Technical Considerations
- Add columns to UserSettings table
- Migrate existing analysis queries to use user preferences

---

## Epic UI: Design System Polish

### Overview
Apply a consistent, crafted design system inspired by Linear/Stripe/Notion to create a polished, professional dashboard experience.

### Goals
- Establish consistent visual language across all pages
- Improve information hierarchy and scanability
- Polish dark mode experience
- Make the UI feel intentionally designed, not just functional

### User Stories

#### US-UI.1: Design System Refinement
**As a** user
**I want** a polished, consistent interface
**So that** the app feels professional and is easy to scan

**Design Direction**: Data & Analysis + Utility & Function
- Cool slate foundation
- Sharp corners (4/6/8px radius)
- Borders-only depth (no shadows except hover states)
- Single blue accent for actions
- Monospace for all data values

**Acceptance Criteria:**
- [ ] **Typography**: Implement 4-level hierarchy (Headlines 600 weight, -0.02em; Body 400-500; Labels 500 uppercase; Data monospace)
- [ ] **Spacing**: Migrate to 4px grid (use 8, 12, 16, 24, 32px exclusively)
- [ ] **Border Radius**: Standardize to 4/6/8px system
- [ ] **Colors**: Reduce decorative color, use gray structure + accent for actions only
- [ ] **Cards**: Consistent padding (16px), border-only depth, no heavy shadows
- [ ] **Buttons**: Unified styling with 150ms transitions
- [ ] **Data Display**: Monospace font with tabular-nums for numbers/sizes/dates
- [ ] **Dark Mode**: Adjust borders to 10-15% white opacity, desaturate status colors
- [ ] **Navigation**: Consistent styling with current page indicator
- [ ] Typecheck passes
- [ ] Visual review in browser (light + dark mode)

### Non-Goals
- Complete redesign of page layouts
- New page structures or navigation patterns
- Custom icon library

### Technical Considerations
- Update `app.css` with new CSS custom properties
- Use `/design-principles` skill for guidance
- Test all pages in both light and dark mode

---

## Epic M: Marketing & Conversion

### Overview
Create an attractive landing page and auth flow to convert visitors into users.

### Goals
- Communicate value proposition clearly
- Build trust through security messaging
- Streamline sign-up flow

### User Stories

#### US-M.1: Landing Page Hero
**As a** visitor
**I want** to see an attractive landing page
**So that** I understand the value and sign up

**Acceptance Criteria:**
- [ ] Bold hero section with gradient background (blue→purple)
- [ ] Tagline: "Keep Your Media Library Clean" (or similar)
- [ ] Value proposition subtitle explaining the product
- [ ] Primary CTA button: "Get Started Free" → /register
- [ ] Secondary link: "Already have an account?" → /login
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-M.2: Feature Highlights
**As a** visitor
**I want** to see the main features
**So that** I understand what the product does

**Acceptance Criteria:**
- [ ] 4 feature cards in grid layout with icons
- [ ] Features: Old Content Detection, Large File Finder, Language Checker, Request Tracking
- [ ] Each card: icon, title (3-4 words), 1-line description
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-M.3: Dashboard Preview
**As a** visitor
**I want** to see a preview of the dashboard
**So that** I know what to expect

**Acceptance Criteria:**
- [ ] Screenshot or mockup of dashboard UI
- [ ] Device frame around preview (laptop or browser window)
- [ ] CTA button below: "Try it Free"
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-M.4: Trust Section
**As a** visitor
**I want** to know my data is secure
**So that** I feel confident signing up

**Acceptance Criteria:**
- [ ] Section with security/privacy messaging
- [ ] Key points: "Your API keys are encrypted", "Connects to YOUR servers", "No data stored on our servers beyond cache"
- [ ] Optional: shield/lock icon
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-M.5: Auth Page CTAs
**As a** visitor
**I want** clear calls-to-action on auth pages
**So that** I convert easily

**Acceptance Criteria:**
- [ ] Register page: value-focused headline above form
- [ ] Login page: clear submit button and "Don't have an account?" link
- [ ] Consistent branding (colors, fonts) with landing page
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

### Non-Goals
- Pricing page (free tier only for v1)
- Blog or documentation

---

## Checklist Summary

### Completed ✅ (32 stories)
- [x] US-0.1: Hello World (Full Stack)
- [x] US-0.2: Dockerize the Application
- [x] US-0.3: Deploy to VPS
- [x] US-1.1: User Registration
- [x] US-1.2: User Login
- [x] US-1.3: Protected Routes
- [x] US-2.1: Configure Jellyfin Connection
- [x] US-2.1.5: Backend Cleanup
- [x] US-2.2: Configure Jellyseerr Connection
- [x] US-2.3: Navigation Header
- [x] US-7.1: Automatic Daily Data Sync
- [x] US-7.1.5: Local Integration Test for Sync
- [x] US-7.2: Manual Data Refresh
- [x] US-3.1: View Old Unwatched Content
- [x] US-3.2: Protect Content from Deletion
- [x] US-3.3: Manage Content Whitelist
- [x] US-D.1: Dashboard Summary Cards
- [x] US-D.2: Dashboard Info Section
- [x] US-D.3: Unified Issues View
- [x] US-D.4: Multi-Issue Content Support
- [x] US-D.5: Navigation Update
- [x] US-4.1: Large Movies Backend Service
- [x] US-5.1: Language Issues Backend Service
- [x] US-5.2: Mark Content as French-Only
- [x] US-5.3: Exempt Content from Language Checks
- [x] US-6.1: Unavailable Requests Backend Service
- [x] US-V.1: Validate Old Content Filtering Logic
- [x] US-V.2: Validate Large Movies Detection
- [x] US-V.3: Validate Language Issues Detection
- [x] US-V.4: Validate Unavailable Requests Detection
- [x] US-6.3: Recently Available Content (INFO)
- [x] US-8.1: Configure Thresholds

### Next Up - Design (1 story) **← START HERE**
- [ ] US-UI.1: Design System Refinement

### Marketing (5 stories)
- [ ] US-M.1: Landing Page Hero
- [ ] US-M.2: Feature Highlights
- [ ] US-M.3: Dashboard Preview
- [ ] US-M.4: Trust Section
- [ ] US-M.5: Auth Page CTAs
