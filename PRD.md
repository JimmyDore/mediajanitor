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

#### US-2.1.5: Backend Cleanup
**As a** developer
**I want** to remove premature code that was created but not needed
**So that** the codebase only contains code for completed stories

**Acceptance Criteria:**
- [ ] Delete unused Pydantic models: `models/content.py`, `models/jellyseerr.py`, `models/whitelist.py`
- [ ] Update `models/__init__.py` to only export `user.py` and `settings.py` models
- [ ] Remove premature SQLAlchemy tables from `database.py`: `WhitelistContent`, `WhitelistFrenchOnly`, `WhitelistFrenchSubsOnly`, `WhitelistLanguageExempt`, `WhitelistEpisodeExempt`, `AppSettings`
- [ ] Run `uv run pytest` - all tests pass
- [ ] Run `uv run mypy app` - no type errors
- [ ] Typecheck passes
- [ ] Unit tests pass

---

#### US-2.2: Configure Jellyseerr Connection
**As a** user
**I want** to input my Jellyseerr API key and URL
**So that** the app can fetch my requests data

**Acceptance Criteria:**
- [ ] Settings page shows Jellyseerr section below Jellyfin
- [ ] Form fields for Jellyseerr URL and API key
- [ ] Backend validates connection by calling Jellyseerr API
- [ ] Credentials stored encrypted in database (using existing encryption service)
- [ ] Toast notification shows "Jellyseerr connected" on success or error message on failure
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-2.3: Navigation Header
**As a** user
**I want** a consistent navigation header across all pages
**So that** I can easily move between dashboard, settings, and log out

**Acceptance Criteria:**
- [ ] Header component with app logo/name on the left
- [ ] User menu on the right with: Settings link, Logout button
- [ ] Header appears on dashboard, settings, and all authenticated pages
- [ ] Current page highlighted in navigation
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

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

#### US-7.1: Automatic Daily Data Sync
**As a** user
**I want** my data to refresh automatically every day
**So that** the dashboard is always up-to-date

**Acceptance Criteria:**
- [ ] **Refer to `original_script.py` functions: `setup_jellyfin_client`, `fetch_jellyseer_requests`, `aggregate_all_user_data`, `get_movies_and_shows_for_user`**
- [ ] **Use API keys from `backend/.env` file for testing** (JELLYFIN_API_KEY, JELLYFIN_SERVER_URL, JELLYSEERR_API_KEY, JELLYSEERR_BASE_URL)
- [ ] **All cached data is tied to a user_id** - each user's sync is independent
- [ ] Background task can be triggered manually (for testing) or scheduled daily
- [ ] Uses the user's own stored API keys (from UserSettings) to fetch their data
- [ ] Fetches data from Jellyfin API: all movies/series with UserData, MediaSources
- [ ] Fetches data from Jellyseerr API: all requests with status
- [ ] Stores raw results in database cache tables with `user_id` FK (e.g., `cached_media_items`, `cached_jellyseerr_requests`)
- [ ] Dashboard shows "Last synced: [timestamp]" for the current user
- [ ] Failed syncs logged but don't crash the app
- [ ] Typecheck passes
- [ ] Unit tests pass

---

#### US-7.2: Manual Data Refresh
**As a** user
**I want** to manually trigger a data refresh
**So that** I can see changes immediately

**Acceptance Criteria:**
- [ ] "Refresh" button on dashboard header
- [ ] Button shows loading spinner during refresh
- [ ] Data updates on page after refresh completes
- [ ] Rate limited: max 1 refresh per 5 minutes per user
- [ ] Toast notification shows result (success or rate limit message)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

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

#### US-3.1: View Old Unwatched Content
**As a** user
**I want** to see a list of content not watched in 4+ months
**So that** I can decide what to delete

**Acceptance Criteria:**
- [ ] **Refer to `original_script.py` functions: `filter_old_or_unwatched_items`, `list_old_or_unwatched_content`**
- [ ] Dashboard page shows list of old/unwatched movies and series (reads from **current user's** cached DB, not live API)
- [ ] API endpoint filters by `user_id` from JWT token
- [ ] Each item shows: name, type (movie/series), year, size (formatted), last watched date, file path
- [ ] List sorted by size (largest first)
- [ ] Total count and total size displayed at top
- [ ] Content in user's whitelist is excluded from results
- [ ] Uses hardcoded threshold: 4 months, min age: 3 months
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-3.2: Protect Content from Deletion
**As a** user
**I want** to add content to a whitelist
**So that** it won't appear in the "to delete" list

**Acceptance Criteria:**
- [ ] "Protect" button on each content item in old content list
- [ ] Clicking creates whitelist entry linked to current user (user_id foreign key)
- [ ] Protected item immediately disappears from old content list
- [ ] Toast notification confirms "Added to whitelist"
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-3.3: Manage Content Whitelist
**As a** user
**I want** to view and edit my content whitelist
**So that** I can remove protection from items

**Acceptance Criteria:**
- [ ] Whitelist page accessible from settings or navigation
- [ ] Shows all items in user's content whitelist
- [ ] Each item shows: name, date added
- [ ] "Remove" button to unprotect items
- [ ] Removing item makes it appear again in old content list (if still old)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

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

## Epic 4: Large Movies

### Overview
Identify movies that consume excessive storage, allowing users to re-download in lower quality.

### Goals
- Flag movies above size threshold (default: 13GB)
- Help users prioritize storage reclamation

### User Stories

#### US-4.1: View Large Movies
**As a** user
**I want** to see movies larger than 13GB
**So that** I can re-download them in lower quality

**Acceptance Criteria:**
- [ ] **Refer to `original_script.py` function: `list_large_movies`**
- [ ] Page shows movies exceeding 13GB threshold (reads from cached DB, not live API)
- [ ] Each item shows: name, year, size (formatted), watched status, file path
- [ ] List sorted by size (largest first)
- [ ] Total count and total size displayed at top
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

### Non-Goals
- Configurable threshold in v1 (see US-8.1)
- Automatic re-download triggers

### Technical Considerations
**Jellyfin API (from original_script.py):**
- Uses same endpoint as Epic 3: `GET /Users/{userId}/Items`
- Filter: `Type == 'Movie'` AND size from `MediaSources[0].Size > 13GB`
- Size calculation: `sum(ms.Size for ms in item.MediaSources)` in bytes

---

## Epic 5: Language Issues

### Overview
Identify content with language problems (missing French/English audio or subtitles).

### Goals
- Flag content missing required languages
- Support whitelists for French-only content and exemptions
- Handle series at episode level

### User Stories

#### US-5.1: View Content with Language Issues
**As a** user
**I want** to see content missing French or English audio
**So that** I can re-download proper versions

**Acceptance Criteria:**
- [ ] **Refer to `original_script.py` functions: `check_audio_languages`, `list_recent_items_language_check`**
- [ ] Page shows content with language problems (reads from cached DB, not live API)
- [ ] Each item shows: name, type, year, issue type (missing EN audio, missing FR audio, missing FR subs)
- [ ] For series: expandable to show which episodes have issues
- [ ] Filter dropdown by issue type
- [ ] Content in language exemption whitelist is excluded
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-5.2: Mark Content as French-Only
**As a** user
**I want** to mark French films as not needing English audio
**So that** they don't appear as language issues

**Acceptance Criteria:**
- [ ] "Mark as French-only" button on items flagged for missing EN audio
- [ ] Creates entry in user's french-only whitelist (user_id FK)
- [ ] Item no longer flagged for missing English audio
- [ ] Can be managed in whitelist page
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-5.3: Exempt Content from Language Checks
**As a** user
**I want** to completely exempt content from language checks
**So that** special cases don't show as issues

**Acceptance Criteria:**
- [ ] "Exempt from checks" button on language issue items
- [ ] Creates entry in user's language-exempt whitelist (user_id FK)
- [ ] Item no longer appears in language issues list
- [ ] Can be managed in whitelist page
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

### Non-Goals
- Automatic language detection/correction
- Episode-level exemptions in v1

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

### Goals
- Show unavailable/pending requests
- Track currently airing series
- Display recently available content

### User Stories

#### US-6.1: View Unavailable Requests
**As a** user
**I want** to see Jellyseerr requests that aren't available
**So that** I can manually find them

**Acceptance Criteria:**
- [ ] **Refer to `original_script.py` functions: `fetch_jellyseer_requests`, `get_jellyseer_unavailable_requests`, `analyze_jellyseer_requests`**
- [ ] Page shows requests with unavailable/pending status (reads from cached DB, not live API)
- [ ] Each item shows: title, type (movie/TV), requested by, request date
- [ ] For TV: shows which seasons are requested but missing
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-6.2: View Currently Airing Series
**As a** user
**I want** to see series that are currently airing
**So that** I know new episodes are coming

**Acceptance Criteria:**
- [ ] **Refer to `original_script.py` function: `analyze_tv_series_seasons` (in_progress_seasons)**
- [ ] Section/page shows in-progress series (reads from cached DB)
- [ ] Each item shows: title, current season, episodes aired vs total
- [ ] Sorted by next air date
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

---

#### US-6.3: View Recently Available Content
**As a** user
**I want** to see what became available this week
**So that** I can notify my friends

**Acceptance Criteria:**
- [ ] **Refer to `original_script.py` function: `get_jellyseer_recently_available_requests`**
- [ ] Page shows content that became available in past 7 days (reads from cached DB)
- [ ] Grouped by date (newest first)
- [ ] Each item shows: title, type, availability date
- [ ] "Copy list" button for sharing (plain text format)
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

### Non-Goals
- Webhook notifications
- Integration with Discord/Telegram

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
- [ ] Settings section for "Analysis Preferences"
- [ ] Configurable: Old content months (default: 4)
- [ ] Configurable: Minimum age months (default: 3)
- [ ] Configurable: Large movie size GB (default: 13)
- [ ] Changes saved to user settings and apply immediately
- [ ] Reset to defaults button
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

### Non-Goals
- Per-library thresholds
- Scheduled reports

### Technical Considerations
- Add columns to UserSettings table
- Migrate existing analysis queries to use user preferences

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

### Completed ✅
- [x] US-0.1: Hello World (Full Stack)
- [x] US-0.2: Dockerize the Application
- [x] US-0.3: Deploy to VPS
- [x] US-1.1: User Registration
- [x] US-1.2: User Login
- [x] US-1.3: Protected Routes
- [x] US-2.1: Configure Jellyfin Connection

### In Progress / Next (REORDERED: Sync before dashboard pages)
- [ ] US-2.1.5: Backend Cleanup
- [ ] US-2.2: Configure Jellyseerr Connection
- [ ] US-2.3: Navigation Header
- [ ] **US-7.1: Automatic Daily Data Sync** ← MOVED UP (must cache data before pages)
- [ ] **US-7.2: Manual Data Refresh** ← MOVED UP
- [ ] US-3.1: View Old Unwatched Content (reads from cached DB)
- [ ] US-3.2: Protect Content from Deletion
- [ ] US-3.3: Manage Content Whitelist
- [ ] US-4.1: View Large Movies (reads from cached DB)
- [ ] US-5.1: View Content with Language Issues (reads from cached DB)
- [ ] US-5.2: Mark Content as French-Only
- [ ] US-5.3: Exempt Content from Language Checks
- [ ] US-6.1: View Unavailable Requests (reads from cached DB)
- [ ] US-6.2: View Currently Airing Series (reads from cached DB)
- [ ] US-6.3: View Recently Available Content (reads from cached DB)
- [ ] US-8.1: Configure Thresholds
- [ ] US-M.1: Landing Page Hero
- [ ] US-M.2: Feature Highlights
- [ ] US-M.3: Dashboard Preview
- [ ] US-M.4: Trust Section
- [ ] US-M.5: Auth Page CTAs
