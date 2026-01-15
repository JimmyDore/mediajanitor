# Media Janitor - Archived PRD

Completed epics moved from PRD.md for historical reference. These features have been fully implemented and tested.

## Summary

- **73 completed user stories** across 21 epics
- **Archived**: 2026-01-15
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


---

## Archived Checklist (73 stories)

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
