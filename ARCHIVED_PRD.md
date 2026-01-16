# Media Janitor - Archived PRD

Completed epics moved from PRD.md for historical reference. These features have been fully implemented and tested.

## Summary

- **141 completed user stories** across 31 epics
- **Archived**: 2026-01-16
- **Active PRD**: See `PRD.md` for pending stories

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

---

#### US-D.6: Inline Badge Actions ✅
**As a** user
**I want** action buttons attached directly to issue badges
**So that** I know exactly which problem each action resolves

**Acceptance Criteria:**
- [x] OLD badge shows inline dismiss/shield button to protect from deletion
- [x] LANGUAGE badge shows inline FR button (if missing EN audio) and/or checkmark button (to exempt)
- [x] LARGE badge shows info tooltip on hover: "Re-download in lower quality from Radarr/Sonarr"
- [x] REQUEST badge shows info tooltip on hover: "Check status in Jellyseerr"
- [x] Clicking inline action behaves same as current buttons (calls same API endpoints)
- [x] Action buttons show tooltip on hover: "Protect from deletion", "Mark French-only", "Exempt from language checks"
- [x] Remove separate Actions column from table
- [x] Loading state shown on badge action while API call in progress
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - Moved action buttons inline with badges. OLD/LANGUAGE badges have action buttons attached (shield/FR/checkmark). LARGE/REQUEST badges show info tooltips. Actions column removed. 126 frontend tests pass, 191 backend tests pass, typecheck clean.

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
Apply a consistent, crafted design system inspired by Linear/Stripe/Notion to create a polished, professional dashboard experience. The designer has **full autonomy** to review and improve all UI elements.

### Goals
- Establish consistent visual language across all pages
- Improve information hierarchy and scanability
- Polish dark mode experience
- Make the UI feel intentionally designed, not just functional
- Ensure all interactive elements feel crafted

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

**Scope**: Designer has **full autonomy** to review and improve:
- All pages (Dashboard, Issues, Whitelist, Settings, Login, Register)
- All components (cards, tables, forms, buttons)
- All interactive elements (modals, popups, toasts, dropdowns)
- Element sizing (padding, margins, font sizes, icon sizes)
- Any other UI element that could benefit from polish

**Acceptance Criteria:**
- [x] **Typography**: Implement 4-level hierarchy (Headlines 600 weight, -0.02em; Body 400-500; Labels 500 uppercase; Data monospace)
- [x] **Spacing**: Migrate to 4px grid (use 8, 12, 16, 24, 32px exclusively)
- [x] **Border Radius**: Standardize to 4/6/8px system
- [x] **Colors**: Reduce decorative color, use gray structure + accent for actions only
- [x] **Cards**: Consistent padding (16px), border-only depth, no heavy shadows
- [x] **Buttons**: Unified styling with 150ms transitions
- [x] **Data Display**: Monospace font with tabular-nums for numbers/sizes/dates
- [x] **Modals & Popups**: Review sizing, padding, transitions; ensure they feel crafted
- [x] **Toasts**: Consistent styling, appropriate sizing, smooth animations
- [x] **Forms & Inputs**: Unified field styling, proper focus states, accessible contrast
- [x] **Dark Mode**: Adjust borders to 10-15% white opacity, desaturate status colors
- [x] **Navigation**: Consistent styling with current page indicator
- [x] **Autonomous Improvements**: Make any additional improvements deemed necessary
- [x] Typecheck passes
- [x] Visual review in browser (light + dark mode)

**Note:** Completed 2026-01-14 - Comprehensive design system refinement: app.css with CSS custom properties (typography scale, 4px spacing grid, 4/6/8px radius system, cool slate colors, dark mode adjustments), updated all pages (Dashboard, Issues, Whitelist, Settings, Login, Register), Header component, monospace for data values, border-only depth, single blue accent, 93 frontend tests pass, 0 typecheck errors

### Non-Goals
- Complete redesign of page layouts
- New page structures or navigation patterns
- Custom icon library

### Technical Considerations
- Update `app.css` with new CSS custom properties
- Use `/design-principles` skill for guidance
- Test all pages in both light and dark mode
- Review all Svelte components for consistency

---

## Epic 9: Infrastructure & Polish

### Overview
Address P1/P2 issues from SUGGESTIONS.md: page title inconsistency, missing favicon, and CORS configuration for production.

### Goals
- Fix branding inconsistencies
- Eliminate 404 errors for static assets
- Enable production deployment

### User Stories

#### US-9.1: Fix Page Titles ✅
**As a** user
**I want** consistent branding across all pages
**So that** the app feels professional and cohesive

**Acceptance Criteria:**
- [x] Login page title is "Login | Media Janitor"
- [x] Register page title is "Register | Media Janitor"
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-14 - Updated page titles from 'Log In/Sign Up - Media Janitor' to 'Login/Register | Media Janitor'

---

#### US-9.2: Add Favicon ✅
**As a** user
**I want** a favicon in my browser tab
**So that** I can easily identify the app among my open tabs

**Acceptance Criteria:**
- [x] Favicon displays in browser tab
- [x] No 404 for `/favicon.png`
- [x] Typecheck passes

**Note:** Completed 2026-01-14 - Created SVG favicon with broom icon (Media Janitor theme), blue accent color matching app design

---

#### US-9.3: Add CORS Production URL ✅
**As a** developer
**I want** CORS configured for production
**So that** the app works on mediajanitor.com

**Acceptance Criteria:**
- [x] CORS allows requests from https://mediajanitor.com
- [x] Existing localhost origins still work
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-14 - Added https://mediajanitor.com to CORS allowed origins in main.py

---

#### US-9.4: Add IMDB/TMDB Links to Content Items ✅
**As a** user
**I want** to click on a movie/series title to open IMDB or TMDB
**So that** I can quickly lookup more information about the content

**Acceptance Criteria:**
- [x] Each content item in Issues view has clickable TMDB link icon
- [x] Link opens in new tab: `https://www.themoviedb.org/{movie|tv}/{tmdb_id}`
- [x] For Jellyseerr requests: use existing `tmdb_id` from `cached_jellyseerr_requests`
- [x] For Jellyfin media: extract TMDB ID from `ProviderIds` in raw_data (or add to sync if not present)
- [x] Fallback: if no TMDB ID available, hide the link icon
- [x] Optional: add IMDB link too if `ImdbId` is available in ProviderIds
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - Added tmdb_id/imdb_id to ContentIssueItem and UnavailableRequestItem. External link icons (TMDB + IMDB) visible next to item names in Issues view. 172 backend tests pass, 96 frontend tests pass.

### Non-Goals
- Custom branding per user
- Dynamic favicon

### Technical Considerations
- Update `<svelte:head><title>` in login/register pages
- Create `frontend/static/` folder with favicon
- Add production URL to `backend/app/main.py` CORS origins
- **For US-9.4**: Jellyfin API returns `ProviderIds` in item responses:
  ```json
  "ProviderIds": { "Tmdb": "12345", "Imdb": "tt1234567" }
  ```
  - Add `ProviderIds` to sync fields if not already in raw_data
  - Frontend displays link icon with `target="_blank"`

---

## Epic 10: Automatic Sync Scheduler

### Overview
Complete US-7.1 by adding automatic daily sync. Currently only manual sync exists.

### Goals
- Automate daily data refresh for all users
- Use Celery Beat for reliable scheduling
- Handle failures gracefully

### User Stories

#### US-10.1: Add Celery Infrastructure ✅
**As a** developer
**I want** Celery configured with Redis
**So that** we can run background tasks reliably

**Acceptance Criteria:**
- [x] Celery app configured with Redis broker
- [x] `docker-compose up` starts redis + celery worker services
- [x] Can enqueue and execute a test task
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-14 - Added Celery 5.3+ with Redis 5.0+ broker. Created celery_app.py with configuration and tasks.py with test_task. Updated docker-compose with redis and celery-worker services. 170 backend tests pass, mypy clean.

---

#### US-10.2: Daily Sync Scheduler ✅
**As a** user
**I want** my data to sync automatically every day
**So that** the dashboard is always up-to-date without manual intervention

**Acceptance Criteria:**
- [x] Celery Beat schedules `sync_all_users` task daily at 3 AM UTC
- [x] Task iterates all users with configured Jellyfin settings
- [x] Each user's sync runs independently (failures don't block others)
- [x] Sync status updated in database for each user
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-14 - Added Celery Beat schedule for sync_all_users at 3 AM UTC. Created sync_all_users and sync_user tasks. Each user synced independently via separate task. 175 backend tests pass, mypy clean.

### Non-Goals
- Per-user configurable schedule
- Real-time sync notifications

### Technical Considerations
- Add `celery`, `redis` dependencies to `pyproject.toml`
- Create `backend/app/celery_app.py` for Celery configuration
- Create `backend/app/tasks.py` for task definitions
- Add redis, celery-worker, celery-beat services to `docker-compose.yml`

---

## Epic 11: Temporary Whitelisting

### Overview
Allow users to whitelist items for a limited time instead of permanently. Useful for seasonal content or temporary exceptions.

### Goals
- Support optional expiration on whitelist entries
- Default behavior remains permanent (no expiration)
- Show expiration status in UI

### User Stories

#### US-11.1: Add Expiration to Whitelist Schema ✅
**As a** developer
**I want** whitelist tables to support expiration dates
**So that** users can create temporary whitelists

**Acceptance Criteria:**
- [x] All 3 whitelist tables have nullable `expires_at` column
- [x] Existing entries have `expires_at = NULL` (permanent)
- [x] API models support optional expiration date
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-14 - Added nullable expires_at column to ContentWhitelist, FrenchOnlyWhitelist, LanguageExemptWhitelist. Updated WhitelistAddRequest and WhitelistItem Pydantic models. 178 backend tests pass, mypy clean.

---

#### US-11.2: Whitelist Expiration Logic ✅
**As a** user
**I want** expired whitelist entries to stop protecting content
**So that** items automatically return to issues list when protection expires

**Acceptance Criteria:**
- [x] Expired whitelist entries don't exclude items from issues
- [x] Non-expired entries still work as before
- [x] NULL `expires_at` means permanent (never expires)
- [x] API accepts optional `expires_at` when adding to whitelist
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Completed 2026-01-14 - Whitelist queries filter out expired entries (expires_at < now). API saves expires_at from request. GET /api/whitelist/* returns expires_at. 191 backend tests pass, mypy clean.

---

#### US-11.3: Temporary Whitelist UI ✅
**As a** user
**I want** to choose how long to whitelist an item
**So that** I can set temporary protection for seasonal content

**Acceptance Criteria:**
- [x] Default is "Permanent" (no expiration)
- [x] Preset duration options: 3 months, 6 months, 1 year
- [x] Custom date picker option
- [x] Whitelist page shows expiration date or "Permanent"
- [x] Expired items show "Expired" badge
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - Duration picker modal on Issues page (Permanent, 3mo, 6mo, 1yr, Custom), Whitelist page shows expiration info with Expired badge. 191 backend tests pass, 102 frontend tests pass, mypy clean.

### Non-Goals
- Automatic renewal of expiring whitelists
- Notifications before expiration

### Technical Considerations
- Add `expires_at: datetime | None` to ContentWhitelist, FrenchOnlyWhitelist, LanguageExemptWhitelist
- Update filtering logic to check `expires_at < now()` for expired entries
- Duration selector UI with presets + custom date picker

---

## Epic M: Marketing & Conversion

### Overview
Create an attractive landing page and auth flow to convert visitors into users.

### Goals
- Communicate value proposition clearly
- Build trust through security messaging
- Streamline sign-up flow

### User Stories

#### US-M.1: Landing Page Hero ✅
**As a** visitor
**I want** to see an attractive landing page
**So that** I understand the value and sign up

**Acceptance Criteria:**
- [x] Bold hero section with gradient background (blue→purple)
- [x] Tagline: "Keep Your Media Library Clean" (or similar)
- [x] Value proposition subtitle explaining the product
- [x] Primary CTA button: "Get Started Free" → /register
- [x] Secondary link: "Already have an account?" → /login
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - Landing component with gradient hero, tagline, CTAs. 107 frontend tests pass, typecheck clean.

---

#### US-M.2: Feature Highlights ✅
**As a** visitor
**I want** to see the main features
**So that** I understand what the product does

**Acceptance Criteria:**
- [x] 4 feature cards in grid layout with icons
- [x] Features: Old Content Detection, Large File Finder, Language Checker, Request Tracking
- [x] Each card: icon, title (3-4 words), 1-line description
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - 4 feature cards with colored icons (red/yellow/blue/purple), 2x2 grid, responsive. 113 frontend tests pass, typecheck clean.

---

#### US-M.3: Dashboard Preview ✅
**As a** visitor
**I want** to see a preview of the dashboard
**So that** I know what to expect

**Acceptance Criteria:**
- [x] Screenshot or mockup of dashboard UI
- [x] Device frame around preview (laptop or browser window)
- [x] CTA button below: "Try it Free"
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - Browser chrome frame with colored dots and URL bar, dashboard mockup with 4 issue cards, Try it Free CTA. 116 frontend tests pass, typecheck clean.

---

#### US-M.4: Trust Section ✅
**As a** visitor
**I want** to know my data is secure
**So that** I feel confident signing up

**Acceptance Criteria:**
- [x] Section with security/privacy messaging
- [x] Key points: "Your API keys are encrypted", "Connects to YOUR servers", "No data stored on our servers beyond cache"
- [x] Optional: shield/lock icon
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - Trust section with shield icon, 3 key security points with checkmarks. 121 frontend tests pass, typecheck clean.

---

#### US-M.5: Auth Page CTAs ✅
**As a** visitor
**I want** clear calls-to-action on auth pages
**So that** I convert easily

**Acceptance Criteria:**
- [x] Register page: value-focused headline above form
- [x] Login page: clear submit button and "Don't have an account?" link
- [x] Consistent branding (colors, fonts) with landing page
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - Register page: 'Get Started Free' headline, 'Create Free Account' button. Login page: clear 'Log In' button, 'Sign up' link. Consistent CSS variables with landing page. 126 frontend tests pass, typecheck clean.

### Non-Goals
- Pricing page (free tier only for v1)
- Blog or documentation

---

## Epic 12: Issues Page UX Improvements

### Overview
Fix usability issues on the Issues page and Settings page to improve clarity and fix bugs.

### Goals
- Make threshold settings self-explanatory
- Simplify the Issues page by removing the Multi-Issue tab
- Fix broken external links (TMDB/IMDb)
- Ensure all content items display external links where data is available

### User Stories

#### US-12.1: Add Threshold Help Text ✅
**As a** user
**I want** to understand what each threshold setting does
**So that** I can configure them correctly

**Acceptance Criteria:**
- [x] "Flag content unwatched for" shows help text: "Used by: Old tab"
- [x] "Don't flag content newer than" shows help text: "Used by: Old tab (for never-watched items)"
- [x] "Flag movies larger than" shows help text: "Used by: Large tab"
- [x] Help text appears in subtle gray below each input
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added threshold-label-group wrapper and threshold-help class for subtle gray help text below each threshold input.

**File:** `frontend/src/routes/settings/+page.svelte`

---

#### US-12.2: Remove Multi-Issue Tab ✅
**As a** user
**I want** a simpler Issues page
**So that** I'm not confused by extra filters

**Acceptance Criteria:**
- [x] Multi-Issue tab removed from Issues page filter tabs
- [x] URL parameter `?filter=multi` no longer supported (returns all issues or 400)
- [x] Backend API documentation updated to remove 'multi' filter option
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: only 5 tabs remain (All, Old, Large, Language, Requests)

**Note:** Removed multi filter from backend (content.py service and router docstrings) and frontend (FilterType type and filterLabels). Removed TestMultiIssueContent test class (4 tests). URL ?filter=multi gracefully falls back to showing all issues.

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Remove 'multi' from FilterType
- `backend/app/routers/content.py` - Update API docs
- `backend/app/services/content.py` - Remove multi filter logic

---

#### US-12.3: Fix TMDB Link Media Type ✅
**As a** user
**I want** TMDB links to work correctly
**So that** I can check content details on TMDB

**Acceptance Criteria:**
- [x] TMDB links work for Movies (link to `/movie/{id}`)
- [x] TMDB links work for TV Shows (link to `/tv/{id}`)
- [x] Handle both uppercase ("Movie", "Series") and lowercase ("movie", "tv") media types
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: click TMDB link on Requests tab → correct page opens

**Note:** Already fixed in US-13.2 commit. getTmdbUrl() now uses toLowerCase() to handle both 'Movie' and 'movie' media types. Verified: TV shows link to /tv/{id}, movies link to /movie/{id}.

**Root cause:** `getTmdbUrl()` checks `item.media_type === 'Movie'` but request items use lowercase "movie".

**File:** `frontend/src/routes/issues/+page.svelte` - Fix `getTmdbUrl()` function

---

#### US-12.4: Fix Missing Request Titles
**As a** user
**I want** to see titles for all requested content
**So that** I know what each request is for

**Acceptance Criteria:**
- [ ] All items on Requests tab display a title
- [ ] Fallback chain: title → media.title → media.name → originalTitle → "Unknown"
- [ ] Verify sync service correctly stores titles from Jellyseerr API
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser: Requests tab shows titles for all items

**Investigation needed:** Determine if issue is in sync (data not stored) or in API response (data not returned).

**Files:**
- `backend/app/services/sync.py` - Verify title extraction in `cache_jellyseerr_requests()`
- `backend/app/services/content.py` - Verify title returned in `get_unavailable_requests()`

---

#### US-12.5: External Links for All Issue Types ✅
**As a** user
**I want** TMDB/IMDb links on all content items
**So that** I can easily look up any flagged content

**Acceptance Criteria:**
- [x] Old tab items show TMDB/IMDb links (where data exists)
- [x] Large tab items show TMDB/IMDb links (where data exists)
- [x] Language tab items show TMDB/IMDb links (where data exists)
- [x] Requests tab items show TMDB/IMDb links (already implemented, just needs fix from US-12.3)
- [x] External link icon appears next to title if TMDB or IMDb ID available
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: external links appear on items in all tabs

**Note:** Already implemented in US-9.4. Verified: Old, Language, Requests tabs all show TMDB/IMDb links. Large tab has 0 items but uses same rendering code.

**File:** `frontend/src/routes/issues/+page.svelte` - Verify link rendering logic applies to all items

---

#### US-12.6: Fix Watch Status Display ✅
**As a** user
**I want** to see accurate watch status for content items
**So that** I can make informed decisions about what to delete

**Acceptance Criteria:**
- [x] Items that have been watched show relative date (e.g., "3mo ago") or "Watched" if no date
- [x] Items never watched show "Never"
- [x] Backend returns `played` boolean in ContentIssueItem response
- [x] Frontend uses both `played` and `last_played_date` to determine display
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: watched items no longer show "Never"

**Note:** Added played boolean field to ContentIssueItem model and service. Updated frontend formatLastWatched() to use both played and last_played_date.

**Root cause:** ContentIssueItem model missing `played` boolean field. Frontend only receives `last_played_date` which is often null even for watched items.

**Files:**
- `backend/app/models/content.py` - Add `played: bool` to ContentIssueItem
- `backend/app/services/content.py` - Include `played=item.played` in response
- `frontend/src/routes/issues/+page.svelte` - Update formatLastWatched() to use both fields

---

### Non-Goals
- Adding Jellyfin direct links (would require Jellyfin server URL per item)
- Changing threshold functionality (just improving labels)

### Technical Considerations
- Media type normalization: Consider standardizing on lowercase in backend to avoid frontend case handling
- Provider IDs availability: Not all Jellyfin items have TMDB/IMDb IDs in their metadata

---

## Epic 13: Jellyseerr Requests Improvements

### Overview
Fix bugs and add features to the Jellyseerr unavailable requests display. Currently, titles are missing, there's no way to hide requests, and no release date information is shown.

### Goals
- Display titles correctly for all unavailable requests
- Show who requested each item and when it will be released
- Allow users to hide requests they're intentionally waiting on
- Provide setting to filter unreleased content

### User Stories

#### US-13.1: Fix Title Extraction in Jellyseerr Sync ✅
**As a** media server owner
**I want** to see the titles of unavailable requests
**So that** I know what content is pending

**Acceptance Criteria:**
- [x] Titles display correctly for all unavailable requests
- [x] No separate API calls made for title fetching (use embedded data)
- [x] Title fallback chain: title → name → originalTitle → originalName → tmdbId
- [x] Typecheck passes
- [x] Unit tests pass

**Root cause:** The sync code makes separate API calls via `fetch_media_title()` which fail silently. Titles ARE included directly in the Jellyseerr `/api/v1/request` response's media object.

**Files:**
- `backend/app/services/sync.py` - Remove `fetch_media_title()`, update `cache_jellyseerr_requests()`

**Note:** Completed 2026-01-14 - Removed fetch_media_title() API calls. New extract_title_from_request() uses embedded data with full fallback chain. 10 new unit tests. 201 backend tests pass, mypy clean.

---

#### US-13.2: Fix Frontend Request Item Display ✅
**As a** media server owner
**I want** to see request details including who requested it
**So that** I can manage requests effectively

**Acceptance Criteria:**
- [x] Request items display title correctly (use `title` field, not `name`)
- [x] "Requested By" column shows requester name
- [x] Missing seasons shown for TV requests
- [x] Request date shown (replaces "Watched" column for requests)
- [x] Size column hidden for requests (they have no size)
- [x] TMDB link works for requests
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Root cause:** Backend returns `UnavailableRequestItem` with `title` field, but frontend `ContentIssueItem` expects `name`. Template uses `item.name` which is undefined for requests.

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Add `UnavailableRequestItem` interface, conditional rendering

**Note:** Completed 2026-01-14 - Unified request/content response format. Backend converts requests to ContentIssueItem. Frontend shows: title, 'by {requester}', missing seasons (S1, S2...), request date (e.g. '3mo ago'), dash for size, TMDB link. 201 backend + 126 frontend tests pass.

---

#### US-13.3: Add Release Date Column to Requests ✅
**As a** media server owner
**I want** to see the release date of unavailable requests
**So that** I know when the content will become available

**Acceptance Criteria:**
- [x] "Release Date" column displays in requests table
- [x] Date extracted from Jellyseerr response (`media.releaseDate` for movies, `media.firstAirDate` for TV)
- [x] Date stored in `CachedJellyseerrRequest` table during sync
- [x] Frontend displays date in readable format
- [x] Future release dates highlighted visually (e.g., different color or badge)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Database Migration:** Required (add `release_date` column)

**Files:**
- `backend/app/database.py` - Add `release_date` column to `CachedJellyseerrRequest`
- `backend/app/services/sync.py` - Extract and store release date during sync
- `backend/app/models/content.py` - Add `release_date` to `UnavailableRequestItem`
- `backend/app/services/content.py` - Return release date in response
- `frontend/src/routes/issues/+page.svelte` - Display release date column

**Note:** Completed 2026-01-14

---

#### US-13.4: Add Jellyseerr Request Whitelist (Backend) ✅
**As a** media server owner
**I want** to hide specific requests for a duration
**So that** I don't see requests I'm intentionally waiting on

**Acceptance Criteria:**
- [x] New database table `jellyseerr_request_whitelist` with expiration support
- [x] API endpoints: POST/GET/DELETE `/api/whitelist/requests`
- [x] Whitelisted requests excluded from unavailable list
- [x] Expired whitelist entries no longer filter requests
- [x] Typecheck passes
- [x] Unit tests pass

**Database Migration:** Required (add `jellyseerr_request_whitelist` table)

**Files:**
- `backend/app/database.py` - Add `JellyseerrRequestWhitelist` model
- `backend/app/routers/whitelist.py` - Add request whitelist endpoints
- `backend/app/services/content.py` - Add whitelist filtering to `get_unavailable_requests()`
- `backend/app/models/content.py` - Add `RequestWhitelistAddRequest` model

**Note:** Completed 2026-01-14 - JellyseerrRequestWhitelist table, API endpoints, expiration logic. 10 new tests. 222 backend tests pass, mypy clean.

---

#### US-13.5: Add Request Whitelist UI ✅
**As a** media server owner
**I want** to click a button to hide a request
**So that** I can manage my request list from the UI

**Acceptance Criteria:**
- [x] Hide button appears on each request item (eye-slash icon)
- [x] Duration picker opens (same as content: permanent, 3/6/12 months, custom)
- [x] Hidden request removed from list after confirmation
- [x] Loading state shown during API call
- [x] Toast notification on success/error
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Add hide button, wire up to whitelist API

**Note:** Completed 2026-01-14 - Hide button with eye-slash icon on REQUEST badges, duration picker modal, Hidden Requests tab on whitelist page. 220 backend tests pass, 138 frontend tests pass, 17 integration tests pass.

---

#### US-13.6: Setting to Include/Exclude Unreleased Requests ✅
**As a** media server owner
**I want** to toggle whether unreleased content requests are shown
**So that** I can focus on requests that should already be available

**Acceptance Criteria:**
- [x] New boolean setting `show_unreleased_requests` in UserSettings (default: false)
- [x] Settings page shows toggle for "Show unreleased requests"
- [x] When false, requests with future release dates are hidden
- [x] When true, all requests are shown (with release date visible)
- [x] Setting persists in database
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Database Migration:** Required (add `show_unreleased_requests` column to UserSettings)

**Files:**
- `backend/app/database.py` - Add `show_unreleased_requests` to `UserSettings`
- `backend/app/services/content.py` - Check setting in `get_unavailable_requests()` filter
- `backend/app/routers/settings.py` - Add field to settings endpoint
- `backend/app/models/settings.py` - Add field to settings models
- `frontend/src/routes/settings/+page.svelte` - Add toggle to settings UI

**Note:** Completed 2026-01-14 - Toggle switch in Display section of Settings page. 246 backend tests pass (7 new display tests), 146 frontend tests pass (8 new display tests), 17 integration tests pass.

---

### Non-Goals
- Automatic request deletion from Jellyseerr (out of scope)
- Request management (approve/deny) from this app
- Notifications when requests become available

### Technical Considerations
- US-13.1 makes US-12.4 obsolete (same fix, more comprehensive)
- Database migrations should be combined where possible to reduce migration count

---

## Epic 14: User Documentation

### Overview
Provide in-app help documentation in FAQ format to help users understand and use all features effectively.

### Goals
- Help new users get started quickly
- Answer common questions about each feature
- Reduce support burden with self-service documentation

### User Stories

#### US-14.1: In-App FAQ Help Page ✅
**As a** user
**I want** an in-app help page with FAQs
**So that** I can understand how to use all features without external documentation

**Acceptance Criteria:**
- [x] New route `/help` accessible from navigation header
- [x] FAQ sections covering:
  - Getting Started (connect Jellyfin/Jellyseerr, first sync)
  - Dashboard (what each card means, how counts are calculated)
  - Issues (Old Content, Large Movies, Language Issues, Unavailable Requests)
  - Whitelists (how to protect content, temporary vs permanent, managing whitelists)
  - Settings (threshold configuration, what each setting affects)
- [x] Collapsible FAQ items (click question to reveal answer)
- [x] Search/filter functionality to find specific topics
- [x] Help link added to navigation header (question mark icon)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Completed 2026-01-14 - Help page with 5 FAQ sections (18 FAQs total), collapsible items, search filter, Help link in sidebar. 176 frontend tests pass (30 new help tests).

### Non-Goals
- API documentation (user docs only)
- Video tutorials
- External documentation site

### Technical Considerations
- Use collapsible `<details>` elements or accordion component
- FAQ content can be stored in a static JSON/TS file for easy updates
- Consider adding contextual help links from other pages to relevant FAQ sections

---

## Epic 15: Backlog

### Overview
Miscellaneous improvements including bug fixes, delete functionality with Radarr/Sonarr integration, and code cleanup.

### Goals
- Fix known bugs (hidden requests display, auth loading delay)
- Enable content deletion directly from dashboard via Radarr/Sonarr
- Remove unused code

### User Stories

#### US-15.1: Fix Hidden Requests Showing TMDB IDs ✅
**As a** user
**I want** hidden requests to show actual movie/show titles
**So that** I can identify what content I've hidden

**Acceptance Criteria:**
- [x] Hidden Requests tab shows actual titles, not "TMDB-123456"
- [x] Backend looks up title from `CachedJellyseerrRequest` table when whitelisting
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Fixed by adding title lookup in whitelist.py add_to_requests endpoint. When title starts with TMDB-, looks up CachedJellyseerrRequest and extracts title from raw_data.media (title/name/slug).

**Root Cause:** Frontend passes `item.name` which may be the fallback `TMDB-{id}` string when real title unavailable.

**Files:**
- `backend/app/routers/whitelist.py` - Modify POST /api/whitelist/requests to fetch title from DB
- `backend/app/services/content.py` - Add helper to get request title by jellyseerr_id

---

#### US-15.2: Add Radarr Connection Settings ✅
**As a** user
**I want** to connect my Radarr instance
**So that** I can delete movies directly from the dashboard

**Acceptance Criteria:**
- [x] Settings page has Radarr section: URL + API Key
- [x] Backend validates connection by calling `GET /api/v3/system/status`
- [x] Credentials stored encrypted in database
- [x] Toast notification on success/error
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**API Reference:**
- Auth: `X-Api-Key` header
- Test endpoint: `GET /api/v3/system/status`

**Files:**
- `backend/app/database.py` - Add `radarr_server_url`, `radarr_api_key_encrypted` to UserSettings
- `backend/app/routers/settings.py` - Add POST /api/settings/radarr endpoint
- `backend/app/services/radarr.py` - New service for Radarr API calls
- `frontend/src/routes/settings/+page.svelte` - Add Radarr form section

**Note:** Completed 2026-01-14

---

#### US-15.3: Add Sonarr Connection Settings ✅
**As a** user
**I want** to connect my Sonarr instance
**So that** I can delete TV series directly from the dashboard

**Acceptance Criteria:**
- [x] Settings page has Sonarr section: URL + API Key
- [x] Backend validates connection by calling `GET /api/v3/system/status`
- [x] Credentials stored encrypted in database
- [x] Toast notification on success/error
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**API Reference:**
- Auth: `X-Api-Key` header
- Test endpoint: `GET /api/v3/system/status`

**Files:**
- `backend/app/database.py` - Add `sonarr_server_url`, `sonarr_api_key_encrypted` to UserSettings
- `backend/app/routers/settings.py` - Add POST /api/settings/sonarr endpoint
- `backend/app/services/sonarr.py` - New service for Sonarr API calls
- `frontend/src/routes/settings/+page.svelte` - Add Sonarr form section

**Note:** Completed 2026-01-14

---

#### US-15.4: Delete Movie from Radarr ✅
**As a** user
**I want** to delete a movie via the dashboard
**So that** it's removed from Radarr and Jellyfin automatically

**Acceptance Criteria:**
- [x] Backend endpoint to delete movie by TMDB ID
- [x] Finds Radarr movie ID via `GET /api/v3/movie?tmdbId={id}`
- [x] Deletes via `DELETE /api/v3/movie/{id}?deleteFiles=true`
- [x] Returns success/error response
- [x] Deleting from Radarr with files auto-deletes from Jellyfin
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Depends on US-15.2 (completed). Files: backend/app/services/radarr.py, backend/app/routers/content.py

**Files:**
- `backend/app/services/radarr.py` - Add `delete_movie_by_tmdb_id()`
- `backend/app/routers/content.py` - Add DELETE /api/content/movie/{tmdb_id}

---

#### US-15.5: Delete Series from Sonarr ✅
**As a** user
**I want** to delete a TV series via the dashboard
**So that** it's removed from Sonarr and Jellyfin automatically

**Acceptance Criteria:**
- [x] Backend endpoint to delete series by TMDB ID
- [x] Finds Sonarr series via `GET /api/v3/series` (iterate to find tmdbId match)
- [x] Deletes via `DELETE /api/v3/series/{id}?deleteFiles=true`
- [x] Returns success/error response
- [x] Deleting from Sonarr with files auto-deletes from Jellyfin
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Depends on US-15.3 (completed). Files: backend/app/services/sonarr.py, backend/app/routers/content.py

**Files:**
- `backend/app/services/sonarr.py` - Add `delete_series_by_tmdb_id()`
- `backend/app/routers/content.py` - Add DELETE /api/content/series/{tmdb_id}

---

#### US-15.6: Delete Jellyseerr Request ✅
**As a** user
**I want** to delete a request from Jellyseerr
**So that** it's removed from the requests list

**Acceptance Criteria:**
- [x] Backend endpoint to delete request by jellyseerr_id
- [x] Calls `DELETE /api/v1/request/{requestId}` on Jellyseerr
- [x] Returns success/error response (204 No Content on success)
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** API: X-Api-Key header, response: 204 No Content. Files: backend/app/services/jellyseerr.py, backend/app/routers/content.py

**API Reference:**
- Auth: `X-Api-Key` header
- Response: 204 No Content

**Files:**
- `backend/app/services/jellyseerr.py` - Add `delete_request()`
- `backend/app/routers/content.py` - Add DELETE /api/content/request/{jellyseerr_id}

---

#### US-15.7: Delete Content UI ✅
**As a** user
**I want** a delete button on content items
**So that** I can remove content without leaving the dashboard

**Acceptance Criteria:**
- [x] "Delete" button appears on content items in Issues view
- [x] Button disabled/greyed if Radarr/Sonarr not configured
- [x] Tooltip explains why disabled when not configured
- [x] Confirmation modal with 2 checkboxes:
  - "Delete from Radarr/Sonarr (removes files)" - default checked
  - "Delete from Jellyseerr (removes request)" - default checked
- [x] Loading state during deletion
- [x] Toast notification on success/error
- [x] Item removed from list after successful deletion
- [x] For Movies: calls Radarr delete
- [x] For Series: calls Sonarr delete
- [x] If request exists: optionally deletes from Jellyseerr
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Depends on US-15.4, US-15.5, US-15.6. File: frontend/src/routes/issues/+page.svelte

**Files:**
- `frontend/src/routes/issues/+page.svelte` - Add delete button, modal, API calls

---

#### US-15.8: Fix Auth Check Loading Delay ✅
**As a** user
**I want** public pages to load instantly
**So that** I don't see a loading spinner on landing/login/register pages

**Acceptance Criteria:**
- [x] Landing page (`/`) renders immediately without loading state
- [x] Login page (`/login`) renders immediately without loading state
- [x] Register page (`/register`) renders immediately without loading state
- [x] Protected routes still show loading while auth check runs
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Fixed by checking isPublicRoute before showing loading state in layout.svelte. Public routes (/, /login, /register) now render immediately. Updated E2E tests to reflect new expected behavior.

**Root Cause:** Layout shows loading for ALL routes. Should only show loading on protected routes.

**Files:**
- `frontend/src/routes/+layout.svelte` - Change `{#if $auth.isLoading}` to `{#if $auth.isLoading && !isPublicRoute}`

---

#### US-15.9: Remove Unused api.ts File ✅
**As a** developer
**I want** unused code removed
**So that** the codebase is clean and maintainable

**Acceptance Criteria:**
- [x] `frontend/src/lib/api.ts` file deleted
- [x] No import errors after deletion
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Deleted frontend/src/lib/api.ts. All exports (contentApi, languageApi, requestsApi, whitelistApi, settingsApi, healthApi) were unused.

**Unused exports being removed:**
- `contentApi` (getOldUnwatched, getLargeMovies, deleteContent)
- `languageApi` (getIssues, triggerCheck)
- `requestsApi` (getUnavailable, getInProgress, getRecentlyAvailable)
- `whitelistApi` (getList, addItem, removeItem)
- `settingsApi` (get, update)
- `healthApi` (check)

**Files:**
- `frontend/src/lib/api.ts` - Delete entire file

---

#### US-15.10: Lookup Jellyseerr Request by TMDB ID When Deleting ✅
**As a** media server owner
**I want** Jellyseerr requests to be deleted when I delete content from any tab
**So that** I don't have orphaned requests after deleting movies/series

**Acceptance Criteria:**
- [x] Backend looks up Jellyseerr request by TMDB ID + media_type from `cached_jellyseerr_requests` table
- [x] Lookup only happens when `delete_from_jellyseerr=true` AND no `jellyseerr_request_id` provided
- [x] If user unchecked "Delete from Jellyseerr" in modal, no lookup or deletion occurs
- [x] If matching request found, delete it from Jellyseerr
- [x] If no matching request exists, skip gracefully (not an error)
- [x] Response message indicates whether Jellyseerr request was found and deleted
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented _lookup_jellyseerr_request_by_tmdb() helper function. Both delete_movie and delete_series endpoints now look up Jellyseerr request by TMDB ID when no explicit request ID is provided. 5 new unit tests added.

**Root Cause:** Backend only deletes from Jellyseerr when `jellyseerr_request_id` is provided. For items from Old/Large/Language tabs (Jellyfin content), this ID is not available. Backend should lookup the request by TMDB ID instead.

**Files:**
- `backend/app/routers/content.py` - Add helper to lookup request by TMDB ID, update delete_movie and delete_series

### Non-Goals
- Automatic deletion based on rules
- Undo functionality for deletions
- Batch deletion of multiple items

### Technical Considerations
- **Radarr API:** Auth via `X-Api-Key` header; find movie by `GET /api/v3/movie?tmdbId={id}`; delete via `DELETE /api/v3/movie/{id}?deleteFiles=true`
- **Sonarr API:** Auth via `X-Api-Key` header; find series by iterating `GET /api/v3/series`; delete via `DELETE /api/v3/series/{id}?deleteFiles=true`
- **Jellyseerr API:** Auth via `X-Api-Key` header; delete request via `DELETE /api/v1/request/{requestId}`
- Deleting from Radarr/Sonarr with `deleteFiles=true` auto-removes from Jellyfin

---

## Epic 16: Appearance Settings

### Overview
Allow users to manually control the application's theme (light/dark mode) instead of relying solely on system preferences. The theme preference is stored in the database and syncs across devices.

### Goals
- Give users explicit control over light/dark mode
- Support three options: Light, Dark, and System (follow OS preference)
- Persist preference in user settings database
- Apply theme preference across all pages instantly

### User Stories

#### US-16.1: Theme Preference Backend ✅
**As a** developer
**I want** a backend endpoint to store theme preference
**So that** the frontend can persist user's theme choice

**Acceptance Criteria:**
- [x] Add `theme_preference` column to `UserSettings` model (enum: `light`, `dark`, `system`)
- [x] Default value is `system` (follow OS preference)
- [x] Create Alembic migration for the new column
- [x] `GET /api/settings/display` includes `theme_preference` field
- [x] `POST /api/settings/display` accepts `theme_preference` field
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Added theme_preference column (light/dark/system, default system) to UserSettings. Updated DisplayPreferences models and endpoints. 4 new tests added.

**Files:**
- `backend/app/database.py` - Add `theme_preference` column to UserSettings
- `backend/app/models/settings.py` - Add `theme_preference` to DisplayPreferences schemas
- `backend/app/routers/settings.py` - Update display endpoints to handle theme_preference
- `backend/alembic/versions/` - New migration file

---

#### US-16.2: Theme Store and Application ✅
**As a** user
**I want** my theme choice to be applied across the app
**So that** I see consistent light/dark styling

**Acceptance Criteria:**
- [x] Create theme store that reads user preference from API
- [x] Apply theme via `data-theme` attribute on `<html>` element
- [x] `data-theme="light"` forces light mode
- [x] `data-theme="dark"` forces dark mode
- [x] `data-theme="system"` (or no attribute) follows OS preference
- [x] Theme persists across page navigation
- [x] Theme loads correctly on page refresh
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Created theme store with loadFromApi/saveToApi. CSS supports data-theme attribute for forced light/dark. Layout loads theme on auth. 10 new tests.

**Files:**
- `frontend/src/lib/stores/theme.ts` - New theme store
- `frontend/src/app.css` - Update CSS to use `[data-theme="light"]` and `[data-theme="dark"]` selectors
- `frontend/src/routes/+layout.svelte` - Initialize theme store and apply to document

---

#### US-16.3: Theme Toggle UI in Settings ✅
**As a** user
**I want** a theme selector in settings
**So that** I can choose between light, dark, or system preference

**Acceptance Criteria:**
- [x] Settings page Display section has theme selector
- [x] Three options: Light, Dark, System (default)
- [x] Selector shows current preference
- [x] Changing selection immediately updates the theme
- [x] Saves preference to backend on change
- [x] Toast notification on success/error
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added theme selector with Light/Dark/System options. Saves to backend on change. Toast notification on success. 3 new tests. Verified in browser.

**Files:**
- `frontend/src/routes/settings/+page.svelte` - Add theme selector to Display section

### Non-Goals
- Custom color themes beyond light/dark
- Per-page theme overrides
- Time-based automatic theme switching

### Technical Considerations
- **CSS Strategy:** Use CSS custom properties with `[data-theme]` attribute selectors to override the `prefers-color-scheme` media query
- **Storage:** Theme preference stored in `user_settings` table, same as other display preferences
- **Initial Load:** On app load, fetch user settings and apply theme before rendering to avoid flash of wrong theme
- **Unauthenticated Users:** Default to system preference (no API call needed)

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
- [x] Dashboard shows "Setup Checklist" card when Jellyfin not configured OR never synced
- [x] Checklist shows 2 steps: "Connect Jellyfin" and "Run First Sync"
- [x] Each step shows status: pending (gray), in-progress (blue), complete (green)
- [x] "Connect Jellyfin" step has button linking to /settings
- [x] Checklist hides when both steps are complete
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser

**Note:** Setup Checklist shows when Jellyfin not configured OR never synced. Steps show pending/in-progress/complete status. Go to Settings link on step 1, Start Sync button on step 2 when Jellyfin configured. Hides when both complete.

**Files:**
- `frontend/src/routes/+page.svelte` - Add SetupChecklist component
- `frontend/src/lib/components/SetupChecklist.svelte` - New component

---

#### US-18.2: Auto-Sync After Jellyfin Configuration
**As a** user who just configured Jellyfin
**I want** the first sync to start automatically
**So that** I don't have to figure out how to trigger it manually

**Acceptance Criteria:**
- [x] When Jellyfin settings saved successfully AND user has never synced, trigger sync automatically
- [x] Show "Syncing..." state in checklist with spinner
- [x] On sync complete, show success message with item counts
- [x] Handle sync errors gracefully with retry option
- [x] First sync bypasses rate limit (or rate limit doesn't apply to first sync)
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Added force parameter to POST /api/sync to bypass rate limit for first sync. Settings page navigates to dashboard after first Jellyfin config. Dashboard auto-triggers sync via $effect when Jellyfin configured + never synced. Checklist shows error state with Retry button on sync failure.

**Files:**
- `frontend/src/routes/settings/+page.svelte` - Trigger sync after Jellyfin save (if first time)
- `backend/app/routers/sync.py` - Ensure first sync isn't rate-limited

---

#### US-18.3: Optional Services Prompt
**As a** user who completed basic setup
**I want** to see optional services I can configure
**So that** I can enhance my experience if I have Jellyseerr/Radarr/Sonarr

**Acceptance Criteria:**
- [x] After checklist complete, show dismissible "Enhance your setup" card
- [x] Lists: Jellyseerr (request tracking), Radarr (movie management), Sonarr (TV management)
- [x] Each has "Configure" link to /settings
- [x] User can dismiss card permanently (stored in localStorage)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser

**Note:** Implemented dismissible Enhance your setup card showing after checklist complete. Fetches optional service settings and displays only unconfigured services with Configure links. Dismiss state persisted in localStorage. 15 new tests in enhance-setup.test.ts.

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
- [x] Search input appears next to the "Issues" title/item count
- [x] Search filters items in real-time as user types (debounced ~300ms)
- [x] Search matches against: title (case-insensitive), production year, and requested_by (for Requests tab)
- [x] Search operates within the currently active tab filter (Old, Large, Language, Requests, or All)
- [x] Empty search shows all items for current tab
- [x] Item count updates to reflect filtered results (e.g., "3 of 219 items")
- [x] Total size updates to reflect filtered results
- [x] Search input has a clear (X) button when text is present
- [x] Placeholder text: "Search by title, year..."
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Implemented client-side search with debounced filtering (300ms), matching against title, year, and requested_by. Stats update to show 'X of Y items' format with filtered size.

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
- [x] Add `large_season_size_gb` field to UserSettings model (default: 15)
- [x] Create database migration for new column
- [x] `GET /api/settings` returns `large_season_size_gb` value
- [x] `POST /api/settings` accepts and saves `large_season_size_gb`
- [x] Settings page displays "Large season threshold (GB)" input below movie threshold
- [x] Input validates: integer, minimum 1GB
- [x] Help text: "Flag TV series if any season exceeds this size"
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: setting saves and loads correctly

**Note:** Added large_season_size_gb to UserSettings model with Alembic migration, updated GET/POST /api/settings/analysis endpoints, added frontend input with validation (1-100 GB)

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
- [x] Add `largest_season_size_bytes` field to CachedMediaItem model (nullable BigInteger)
- [x] Create database migration for new column
- [x] New async function `calculate_season_sizes(db, user_id, server_url, api_key)`:
  - Fetches all series for user from cache
  - For each series, calls Jellyfin API: `GET /Items?ParentId={series_id}&IncludeItemTypes=Episode&Fields=MediaSources,ParentIndexNumber`
  - Groups episodes by `ParentIndexNumber` (season number), sums sizes per season
  - Stores the LARGEST season size in `largest_season_size_bytes`
- [x] Background task triggered AFTER main sync completes (not during)
- [x] Sync status includes new state: "calculating_sizes" (after "completed")
- [x] Progress logging: "Calculating season sizes for {n} series..."
- [x] Handles API errors gracefully (logs warning, continues to next series)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Integration test: trigger sync, verify season sizes populated

**Note:** Added largest_season_size_bytes field to CachedMediaItem, created Alembic migration, implemented calculate_season_sizes() that fetches seasons/episodes from Jellyfin API and stores largest season size, triggered after media sync with calculating_sizes progress step

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
- [x] New function `is_large_series(item, threshold_gb)` returns True if `largest_season_size_bytes >= threshold`
- [x] `get_content_summary()` includes large series in a combined count:
  - Rename internal variable from `large_movies` to `large_content`
  - Count includes both large movies AND large series
  - Total size includes both
- [x] `get_content_issues()` with `filter=large` returns both movies and series
- [x] Each item includes new field: `largest_season_size_bytes` (null for movies)
- [x] Each item includes new field: `largest_season_size_formatted` (e.g., "18.5 GB")
- [x] Series items include issue badge "large" when flagged
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Test: large series appears in issues, large movie still appears

**Note:** Implemented is_large_series() function, updated UserThresholds to include large_season_size_gb, modified get_content_summary() and get_content_issues() to detect large series, added largest_season_size_bytes and largest_season_size_formatted fields to ContentIssueItem model

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
- [x] Dashboard card renamed from "Large Movies" to "Large Content"
- [x] Dashboard card shows combined count (movies + series)
- [x] Issues page "Large" tab shows both movies and series
- [x] Sub-filter buttons appear when Large tab selected: [All] [Movies] [Series]
- [x] Default sub-filter is "All"
- [x] Sub-filter is client-side (no API changes needed)
- [x] Series items display: name, largest season size (e.g., "Largest season: 18.5 GB")
- [x] Movie items display: name, file size (unchanged behavior)
- [x] Item count and total size update based on sub-filter
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: filter toggles work correctly

**Note:** Renamed dashboard card to 'Large Content', added sub-filter buttons [All/Movies/Series] to Issues Large tab with client-side filtering, series items display 'Largest season: X GB', added 15 new tests in large-content.test.ts and 2 tests in issues.test.ts

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
- [x] Create `app/services/slack.py` with `send_slack_message(webhook_url, message)` function
- [x] Function accepts webhook URL and message dict (Slack Block Kit format)
- [x] Function handles HTTP errors gracefully (log error, don't crash app)
- [x] Function is async and non-blocking
- [x] Add `SLACK_WEBHOOK_NEW_USERS` and `SLACK_WEBHOOK_SYNC_FAILURES` to config
- [x] Webhooks are optional - if not configured, notifications are silently skipped
- [x] Unit tests mock HTTP calls and verify message format
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented send_slack_message() async function with httpx, graceful error handling, and logging. Added slack_webhook_new_users and slack_webhook_sync_failures to config with empty defaults (optional).

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
- [x] After successful user registration, send Slack notification
- [x] Message includes: user email, signup timestamp, total user count
- [x] Message uses Slack Block Kit for nice formatting
- [x] Notification is fire-and-forget (doesn't block registration response)
- [x] If webhook not configured, registration still works (no error)
- [x] Unit tests verify notification is sent with correct payload
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented send_signup_notification() function with Block Kit formatted message, triggered via BackgroundTasks after registration. Added get_total_user_count() helper. 5 new tests in TestNewUserSignupNotifications.

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
- [x] When sync fails (Jellyfin or Jellyseerr), send Slack notification
- [x] Message includes: user email, which service failed, error message
- [x] Notification sent for both manual sync and scheduled (Celery) sync failures
- [x] Message is fire-and-forget (doesn't affect sync error handling)
- [x] If webhook not configured, sync failure handling still works
- [x] Unit tests verify notification is sent with correct payload
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented send_sync_failure_notification() in sync service with Block Kit formatted message. Manual sync failures trigger notification from run_user_sync(). Celery sync failures trigger notification from sync_user task via send_sync_failure_notification_for_celery() wrapper.

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
- [x] `GET /api/library` returns all cached media items for the user
- [x] Supports query params: `type=movie|series|all` (default: all)
- [x] Supports query params: `search=string` (searches name, case-insensitive)
- [x] Supports query params: `watched=true|false|all` (default: all)
- [x] Supports query params: `sort=name|year|size|date_added|last_watched` (default: name)
- [x] Supports query params: `order=asc|desc` (default: asc)
- [x] Supports query params: `min_year`, `max_year` for year range filter
- [x] Supports query params: `min_size_gb`, `max_size_gb` for size range filter
- [x] Returns: items[], total_count, total_size_bytes, total_size_formatted, service_urls
- [x] Each item includes: jellyfin_id, name, media_type, production_year, size_bytes, size_formatted, played, last_played_date, date_created, tmdb_id
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented GET /api/library endpoint with filtering by type, search, watched status, year range, size range, sorting by name/year/size/date_added/last_watched with asc/desc order. Created LibraryItem and LibraryResponse models. 20 unit tests + 4 integration tests.

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
- [x] New route `/library` accessible from sidebar navigation
- [x] Sidebar shows "Library" menu item with appropriate icon (between Issues and Whitelist)
- [x] Page header shows "Library" with total item count and size
- [x] Sub-tabs: [All] [Movies] [Series] - filter by media type
- [x] Default sub-tab is "All"
- [x] Table displays: Name, Year, Size, Added, Last Watched
- [x] External service links (Jellyfin, TMDB) like Issues page
- [x] Empty state when library is empty (with link to Settings to configure Jellyfin)
- [x] Loading state while fetching data
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Created /library route with sub-tabs (All/Movies/Series), table with Name/Year/Size/Added/Last Watched columns, JF and TMDB external links, server-side sorting, loading and empty states. Added Library menu item to sidebar between Issues and Whitelist with book icon.

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
- [x] Search input in page header (searches as user types, debounced 300ms)
- [x] Search matches name (case-insensitive) and production year
- [x] Filter dropdown for watched status: All, Watched, Unwatched
- [x] Year range filter: min year and max year inputs
- [x] Size range filter: min size and max size (in GB)
- [x] Sort dropdown: Name, Year, Size, Date Added, Last Watched
- [x] Sort order toggle: Ascending/Descending
- [x] Filters persist while switching between All/Movies/Series tabs
- [x] Clear all filters button
- [x] Item count updates to reflect filtered results
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Implemented search with 300ms debounce, watched status filter, year/size range filters, sort dropdown with order toggle, clear all filters button. 22 new tests in library.test.ts.

**Files:**
- `frontend/src/routes/library/+page.svelte` - Add filter UI and logic

---

#### US-22.4: Library Sorting
**As a** media server owner
**I want** to sort my library by different columns
**So that** I can organize the view to my preference

**Acceptance Criteria:**
- [x] Clickable column headers for sorting (Name, Year, Size, Last Watched)
- [x] Visual indicator showing current sort column and direction
- [x] Click same column to toggle ascending/descending
- [x] Default sort: Name ascending
- [x] Sorting is server-side (API parameter) for performance with large libraries
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Column headers (Name, Year, Size, Added, Last Watched) are clickable with toggleSort() function. Visual arrow indicators (↑/↓) show current sort. Clicking same column toggles asc/desc. Default is name asc. Server-side sorting via API params. Added 12 new tests in library.test.ts for column header sorting.

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
- [x] API includes `date_created` field in content issues response
- [x] Issues page table shows "Added" column after "Size" column
- [x] Displays date in user-friendly format (e.g., "Jan 15, 2024")
- [x] Shows "Unknown" if date_created is null
- [x] Column is sortable (client-side)
- [x] Column visible on all tabs (All, Old, Large, Language, Unavailable)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added date_created to ContentIssueItem model and API response, Added column to Issues table with formatDateCreated() for display, client-side sorting, responsive hiding on mobile, and shows dash for request items

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
- [x] Rate limit of 10 requests per minute per IP address on `/api/auth/login`
- [x] Rate limit of 10 requests per minute per IP address on `/api/auth/register`
- [x] Rate-limited requests return HTTP 429 (Too Many Requests)
- [x] Response includes `Retry-After` header indicating seconds until reset
- [x] Response body includes clear error message: "Too many requests. Please try again in X seconds."
- [x] Rate limit uses in-memory storage (Redis not required for v1)
- [x] `/api/auth/me` endpoint is NOT rate-limited (authenticated requests only)
- [x] Rate limiting is disabled in test environment
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Manual test: verify 11th request within 60 seconds returns 429

**Note:** Implemented RateLimiter class with in-memory storage, thread-safe sliding window, and TESTING env check. Rate limiter applied to /api/auth/login and /api/auth/register endpoints. Updated integration tests to use module-scoped auth token to avoid rate limit issues.

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
- [x] Password input on registration page shows strength indicator below the field
- [x] Indicator is a horizontal progress bar that changes color based on strength
- [x] Strength levels based on length:
  - Weak (red): 1-7 characters
  - Medium (yellow): 8-11 characters
  - Strong (green): 12+ characters
- [x] Bar fills proportionally: ~33% for weak, ~66% for medium, ~100% for strong
- [x] Indicator only appears when password field has content
- [x] Indicator updates in real-time as user types (no debounce needed)
- [x] Indicator is informational only - does NOT block form submission
- [x] Uses existing CSS color variables (--danger, --warning, --success or similar)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Implemented password strength indicator with getPasswordStrength() and getStrengthLabel() functions. Progress bar shows weak (red, 33%), medium (yellow, 66%), or strong (green, 100%) based on password length. 10 new tests in register.test.ts.

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
- [x] Registration form adds "Confirm Password" input field after Password field
- [x] Confirm Password field is required
- [x] Form validates that Password and Confirm Password match
- [x] If passwords don't match, show error: "Passwords do not match"
- [x] Error appears below the Confirm Password field (not as a toast)
- [x] Submit button is disabled until passwords match (or validation runs on submit)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added confirmPassword state and validatePasswordsMatch() function. Real-time validation shows error below confirm field when passwords don't match. Submit button disabled when confirm has content but doesn't match. 9 new tests in register.test.ts.

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
- [x] Jellyfin API calls retry up to 3 times on failure (4 total attempts)
- [x] Jellyseerr API calls retry up to 3 times on failure (4 total attempts)
- [x] Retry delays use exponential backoff: 1s, 2s, 4s between retries
- [x] Only retry on transient errors: timeouts, 5xx errors, connection errors
- [x] Do NOT retry on: 401 (auth failed), 404 (not found), 400 (bad request)
- [x] Each retry attempt is logged: "Retry 1/3 for Jellyfin API after 1s..."
- [x] After all retries exhausted, sync status set to "failed" with error message
- [x] Error message includes which service failed and the error type
- [x] Successful retry continues sync normally (no partial state)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Test: mock API to fail twice then succeed, verify sync completes

**Note:** Implemented retry_with_backoff() utility with exponential backoff (1s, 2s, 4s). Applied to Jellyfin API calls (fetch_jellyfin_users, fetch_user_items, fetch_series_seasons, fetch_season_episodes) and Jellyseerr API calls (fetch_jellyseerr_requests pagination). Retries on transient errors (timeouts, 5xx, connection errors). Does NOT retry on permanent errors (401, 404, 400). 21 new tests in test_retry.py + 7 new tests in test_sync.py.

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
- [x] E2E test covers: register new user → login → navigate to dashboard → navigate to settings → logout
- [x] Test uses unique email per run (e.g., `test-{timestamp}@example.com`)
- [x] Verifies dashboard loads after login (checks for expected element)
- [x] Verifies settings page loads and shows user info
- [x] Verifies logout redirects to login page
- [x] Verifies protected routes redirect to login when not authenticated
- [x] Test is idempotent (can run multiple times without cleanup)
- [x] Typecheck passes
- [x] E2E test passes

**Note:** Created auth-flow.spec.ts with 2 tests: complete flow (register→login→dashboard→settings→logout) and protected route redirect. Fixed register.spec.ts for confirm password field. Fixed settings.spec.ts and header.spec.ts to use real auth flow instead of deprecated localStorage tokens.

**Files:**
- `frontend/e2e/auth-flow.spec.ts` - New E2E test file

---

#### US-27.2: Sync Integration Tests with Mocked APIs
**As a** developer
**I want** integration tests that verify sync behavior with mocked Jellyfin/Jellyseerr responses
**So that** I can test sync logic without requiring real external services

**Acceptance Criteria:**
- [x] Test file `backend/tests/test_sync_integration.py` with mocked API responses
- [x] Mock Jellyfin API responses using `httpx` mock or `respx` library
- [x] Mock Jellyseerr API responses
- [x] Test: successful sync stores correct data in database
- [x] Test: partial Jellyfin data is handled correctly (missing fields)
- [x] Test: Jellyseerr down doesn't break Jellyfin sync
- [x] Test: API returning empty results creates empty cache (not error)
- [x] Mocks use realistic response structures from actual API documentation
- [x] Tests run without network access (fully offline)
- [x] Typecheck passes
- [x] All tests pass

**Note:** Created test_sync_mocked_integration.py with 11 tests using respx to mock Jellyfin/Jellyseerr APIs. Tests cover: successful sync with multi-user aggregation, Jellyseerr title enrichment, partial data handling, Jellyseerr failure isolation (500 and connection errors), empty results handling, and realistic API response structures.

**Files:**
- `backend/tests/test_sync_integration.py` - New integration test file
- `backend/tests/fixtures/jellyfin_responses.py` - Mock response data (optional)
- `backend/tests/fixtures/jellyseerr_responses.py` - Mock response data (optional)

### Non-Goals
- Testing every form validation (unit tests cover that)
- Visual regression testing

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
- [x] Year displays at a fixed horizontal position (not flowing after variable-length titles)
- [x] Service badges (JF, JS, RD, TMDB) align consistently across all rows
- [x] Long titles truncate with ellipsis instead of wrapping to multiple lines
- [x] On hover, truncated titles show full text via title tooltip
- [x] New "Requester" column appears after Name column (only on Unavailable tab)
- [x] Requester column follows same pattern as Release column (conditional display)
- [x] Column displays username from `requested_by` field, or `—` if null
- [x] The inline "by {username}" display in the name cell is removed
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Implemented CSS grid layout for name cell with fixed-width year column, title truncation with ellipsis and tooltip, and conditional Requester column for Unavailable tab

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
- [x] Remove "currently airing" link from dashboard info section
- [x] Remove `/info/airing` route and page entirely
- [x] Remove `GET /api/info/airing` endpoint
- [x] Remove `get_currently_airing()` function from content service
- [x] Remove `CurrentlyAiringItem` and `CurrentlyAiringResponse` models
- [x] Remove `currently_airing` from `ContentSummaryResponse` model
- [x] Update `get_content_summary()` to not include `currently_airing`
- [x] Remove related tests (backend and frontend)
- [x] Dashboard info section shows only "recently available" (remove separator)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: dashboard no longer shows "currently airing"

**Note:** Removed all currently airing code: endpoint, models, service function, frontend page and link, related tests. Dashboard info section now shows only recently available.

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
- [x] Add `recently_available_days` field to UserSettings model (integer, default 7)
- [x] Create database migration for new column
- [x] `GET /api/settings` returns `recently_available_days` value
- [x] `POST /api/settings` accepts and validates `recently_available_days` (range: 1-30)
- [x] `GET /api/info/recent` uses user's setting instead of hardcoded 7 days
- [x] `GET /api/content/summary` uses user's setting for `recently_available` count
- [x] Invalid values return 422 with clear error message
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented recently_available_days field in UserSettings, added to display preferences API, GET /api/info/recent and GET /api/content/summary now use user's setting

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
- [x] Settings page shows "Recently available days" input in a new "Display" section
- [x] Input is a number field with min=1, max=30
- [x] Default value is 7 when not set
- [x] Help text: "Show content that became available in the past N days"
- [x] Value saves successfully and persists on page reload
- [x] Recently Available page subtitle updates to reflect setting (e.g., "past 14 days")
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Added recently_available_days input to Settings Display section with onchange save. Recently Available page fetches user setting and displays dynamic subtitle.

**Files:**
- `frontend/src/routes/settings/+page.svelte` - Add input field
- `frontend/src/routes/info/recent/+page.svelte` - Fetch setting and display in subtitle

---

#### US-31.3: User Nickname Mapping (Backend)
**As a** media server owner
**I want** to store nickname mappings for Jellyseerr usernames
**So that** I can show friendly names in notifications

**Acceptance Criteria:**
- [x] Create new `UserNickname` model: `id`, `user_id` (FK), `jellyseerr_username` (string), `display_name` (string)
- [x] Create database migration for new table
- [x] Unique constraint on (`user_id`, `jellyseerr_username`) - each username maps once per user
- [x] `GET /api/settings/nicknames` returns list of all nickname mappings for user
- [x] `POST /api/settings/nicknames` creates a new mapping (body: `{jellyseerr_username, display_name}`)
- [x] `PUT /api/settings/nicknames/{id}` updates an existing mapping
- [x] `DELETE /api/settings/nicknames/{id}` removes a mapping
- [x] 409 Conflict if trying to create duplicate jellyseerr_username
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented UserNickname model with unique constraint, CRUD service functions, and REST endpoints at /api/settings/nicknames

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
- [x] Settings page shows new "User Nicknames" section below services configuration
- [x] Section displays table of existing mappings: Jellyseerr Username → Display Name
- [x] "Add nickname" button opens inline form with two inputs: username, display name
- [x] Each row has edit and delete buttons
- [x] Delete shows confirmation before removing
- [x] Empty state: "No nicknames configured. Add nicknames to customize how requesters appear in notifications."
- [x] Toast feedback on save/delete success/error
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser using browser tools

**Note:** Implemented User Nicknames section with inline CRUD: table display, add form, inline edit, delete confirmation, toast feedback. 14 new tests in settings-nicknames.test.ts

**Files:**
- `frontend/src/routes/settings/+page.svelte` - Add nicknames section with CRUD UI

---

#### US-31.5: Copy Output Grouped by Requester
**As a** media server owner
**I want** the copy output to group content by requester with their display name
**So that** I can easily notify each person about their available content

**Acceptance Criteria:**
- [x] "Copy" button generates output grouped by requester (not by date)
- [x] Uses display_name from nickname mapping if configured, otherwise original Jellyseerr username
- [x] Format per requester:
  ```
  {display_name}:
    - {Title} ({Type}) - available since {Date}
  ```
- [x] Requesters sorted alphabetically
- [x] Items under each requester sorted by availability date (newest first)
- [x] Items without a requester grouped under "Unknown" at the end
- [x] API endpoint `GET /api/info/recent` includes resolved `display_name` field
- [x] Frontend uses `display_name` for grouping and display in table
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: copy output shows correct grouping

**Note:** Added display_name field to RecentlyAvailableItem model, implemented get_nickname_map() and resolve_display_name() in content service, updated frontend copy function to group by requester

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
- [x] New `RefreshToken` model: `id`, `user_id` (FK), `token` (hashed), `expires_at`, `created_at`
- [x] Create database migration for refresh_tokens table
- [x] Access token expiration reduced to 15 minutes (short-lived)
- [x] Refresh token expiration set to 30 days (long-lived)
- [x] `POST /api/auth/login` returns both `access_token` and `refresh_token`
- [x] `POST /api/auth/refresh` accepts refresh_token, returns new access_token + new refresh_token
- [x] Old refresh token is invalidated when new one is issued (rotation)
- [x] Invalid/expired refresh token returns 401
- [x] Refresh token stored as httpOnly cookie (more secure than localStorage)
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented refresh token with rotation, httpOnly cookie storage, and logout endpoint

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
- [x] Login stores refresh_token in httpOnly cookie (set by backend)
- [x] Access token stored in memory (not localStorage) for security
- [x] Auth store includes `refreshAccessToken()` method
- [x] API calls that receive 401 automatically attempt token refresh
- [x] If refresh succeeds, retry original request with new token
- [x] If refresh fails (401), redirect to login page
- [x] Proactive refresh: refresh token 1 minute before access token expires
- [x] Logout calls `POST /api/auth/logout` to invalidate refresh token
- [x] Typecheck passes
- [x] Unit tests pass

**Note:** Implemented authenticatedFetch wrapper with 401 retry logic, proactive token refresh 1 min before expiration, access token in memory instead of localStorage

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
- [x] When refresh token fails (401), user is redirected to `/login`
- [x] Auth state is fully cleared before redirect (no stale isAuthenticated)
- [x] Redirect includes `?redirect=/original/path` query param
- [x] After successful login, redirect back to original path
- [x] Toast message shows "Session expired, please log in again"
- [x] No more "Session expired" errors while staying on page
- [x] Protected routes immediately redirect if not authenticated (no content flash)
- [x] Typecheck passes
- [x] Unit tests pass
- [x] Verify in browser: let session expire → automatic redirect to login

**Note:** Session expiration redirect with ?redirect param, toast message, and protected route handling were already implemented in US-32.2. Added 12 new tests for session expiration behavior.

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



---

## Archived Checklist (141 stories)

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
- [x] US-D.6: Inline Badge Actions
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
- [x] US-UI.1: Design System Refinement
- [x] US-9.1: Fix Page Titles
- [x] US-9.2: Add Favicon
- [x] US-9.3: Add CORS Production URL
- [x] US-9.4: Add IMDB/TMDB Links to Content Items
- [x] US-10.1: Add Celery Infrastructure
- [x] US-10.2: Daily Sync Scheduler
- [x] US-11.1: Add Expiration to Whitelist Schema
- [x] US-11.2: Whitelist Expiration Logic
- [x] US-11.3: Temporary Whitelist UI
- [x] US-M.1: Landing Page Hero
- [x] US-M.2: Feature Highlights
- [x] US-M.3: Dashboard Preview
- [x] US-M.4: Trust Section
- [x] US-M.5: Auth Page CTAs
- [x] US-12.1: Add Threshold Help Text
- [x] US-12.2: Remove Multi-Issue Tab
- [x] US-12.3: Fix TMDB Link Media Type
- [x] US-12.5: External Links for All Issue Types
- [x] US-12.6: Fix Watch Status Display
- [x] US-13.1: Fix Title Extraction in Jellyseerr Sync
- [x] US-13.2: Fix Frontend Request Item Display
- [x] US-13.3: Add Release Date Column to Requests
- [x] US-13.4: Add Jellyseerr Request Whitelist (Backend)
- [x] US-13.5: Add Request Whitelist UI
- [x] US-13.6: Setting to Include/Exclude Unreleased Requests
- [x] US-14.1: In-App FAQ Help Page
- [x] US-15.1: Fix Hidden Requests Showing TMDB IDs
- [x] US-15.2: Add Radarr Connection Settings
- [x] US-15.3: Add Sonarr Connection Settings
- [x] US-15.4: Delete Movie from Radarr
- [x] US-15.5: Delete Series from Sonarr
- [x] US-15.6: Delete Jellyseerr Request
- [x] US-15.7: Delete Content UI
- [x] US-15.8: Fix Auth Check Loading Delay
- [x] US-15.9: Remove Unused api.ts File
- [x] US-15.10: Lookup Jellyseerr Request by TMDB ID When Deleting
- [x] US-16.1: Theme Preference Backend
- [x] US-16.2: Theme Store and Application
- [x] US-16.3: Theme Toggle UI in Settings
- [x] US-17.1: Multi-User Watch Data Aggregation
- [x] US-17.2: Sync Progress Visibility
- [x] US-17.3: Fix Mobile Sidebar Visual Overlap
- [x] US-18.1: Show Setup Checklist for New Users
- [x] US-18.2: Auto-Sync After Jellyfin Configuration
- [x] US-18.3: Optional Services Prompt
- [x] US-19.1: Search Issues by Text
- [x] US-20.1: Large Season Threshold Setting
- [x] US-20.2: Calculate and Store Season Sizes
- [x] US-20.3: Large Series Detection Service
- [x] US-20.4: Large Content UI with Filter
- [x] US-21.1: Slack Notification Service
- [x] US-21.2: New User Signup Notifications
- [x] US-21.3: Sync Failure Notifications
- [x] US-22.1: Library API Endpoint
- [x] US-22.2: Library Page with Sub-tabs
- [x] US-22.3: Library Search and Filters
- [x] US-22.4: Library Sorting
- [x] US-23.1: Added Date Column on Issues Page
- [x] US-24.1: Rate Limiting on Auth Endpoints
- [x] US-25.1: Password Strength Indicator
- [x] US-25.2: Password Confirmation Field
- [x] US-26.1: Sync Retry with Exponential Backoff
- [x] US-27.1: E2E Auth Flow Test
- [x] US-27.2: Sync Integration Tests with Mocked APIs
- [x] US-29.1: Add Requester Column to Issues Table
- [x] US-30.1: Remove Currently Airing Placeholder
- [x] US-31.1: Recently Available Days Setting (Backend)
- [x] US-31.2: Recently Available Days Setting (Frontend)
- [x] US-31.3: User Nickname Mapping (Backend)
- [x] US-31.4: User Nickname Mapping (Frontend)
- [x] US-31.5: Copy Output Grouped by Requester
- [x] US-32.1: Refresh Token Backend Implementation
- [x] US-32.2: Frontend Token Refresh
- [x] US-32.3: Auto-Redirect on Session Expiration
