# Plex Dashboard - Product Requirements Document

## Vision

A SaaS web application that helps media server owners manage their Plex/Jellyfin libraries. Users can sign up, connect their own Jellyfin/Jellyseerr instances, and get insights about content to delete, language issues, and pending requests.

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: SvelteKit + TypeScript
- **Database**: PostgreSQL (production) / SQLite (dev)
- **Background Tasks**: Celery or FastAPI BackgroundTasks
- **Deployment**: Docker + GitHub Actions + VPS
- **Auth**: JWT-based authentication

## Architecture Decisions

- **Background data fetching**: Jellyfin/Jellyseerr APIs are slow. Data is fetched daily via background tasks and cached in DB. Users can trigger manual refresh.
- **Multi-tenant SaaS**: Each user has their own API keys and data, isolated from others.
- **Full-stack user stories**: Each story delivers end-to-end value (API + UI).

---

## User Stories

### Epic 0: Foundation & Deployment

#### US-0.1: Hello World (Full Stack)
**As a** developer
**I want** a working frontend that displays "Hello World" from the backend
**So that** I can verify the full stack communication works

**Acceptance Criteria:**
- [x] Backend endpoint `GET /api/hello` returns `{"message": "Hello World"}`
- [x] Frontend displays the message fetched from backend
- [x] Both run locally with `docker-compose up`

---

#### US-0.2: Dockerize the Application
**As a** developer
**I want** the entire application containerized
**So that** I can deploy it anywhere

**Acceptance Criteria:**
- [x] Dockerfile for backend
- [x] Dockerfile for frontend
- [x] docker-compose.yml that runs both + database
- [x] `docker-compose up` starts the full app on localhost

---

#### US-0.3: Deploy to VPS
**As a** developer
**I want** to deploy the app to my VPS
**So that** it's accessible on the internet

**Acceptance Criteria:**
- [x] GitHub Actions workflow for CI/CD
- [x] Auto-deploy to VPS on push to `main`
- [x] App accessible at configured domain
- [x] HTTPS via Let's Encrypt / Caddy

---

### Epic 1: Authentication

#### US-1.1: User Registration
**As a** new user
**I want** to create an account
**So that** I can use the dashboard

**Acceptance Criteria:**
- [x] Registration form (email, password)
- [x] Backend creates user in database
- [x] Password is hashed securely
- [x] User redirected to login after signup

---

#### US-1.2: User Login
**As a** registered user
**I want** to log in
**So that** I can access my dashboard

**Acceptance Criteria:**
- [x] Login form (email, password)
- [x] Backend validates credentials and returns JWT
- [x] Token stored in frontend (httpOnly cookie or localStorage)
- [x] User redirected to dashboard

---

#### US-1.3: Protected Routes
**As a** user
**I want** my data to be private
**So that** only I can see my content

**Acceptance Criteria:**
- [ ] API endpoints require valid JWT
- [ ] Frontend redirects to login if not authenticated
- [ ] Each user sees only their own data

---

### Epic 2: Configuration

#### US-2.1: Configure Jellyfin Connection
**As a** user
**I want** to input my Jellyfin API key and URL
**So that** the app can fetch my library data

**Acceptance Criteria:**
- [ ] Settings page with form for Jellyfin URL and API key
- [ ] Backend validates connection before saving
- [ ] Credentials stored encrypted in database
- [ ] Success/error feedback shown to user

---

#### US-2.2: Configure Jellyseerr Connection
**As a** user
**I want** to input my Jellyseerr API key and URL
**So that** the app can fetch my requests data

**Acceptance Criteria:**
- [ ] Settings page with form for Jellyseerr URL and API key
- [ ] Backend validates connection before saving
- [ ] Credentials stored encrypted in database
- [ ] Success/error feedback shown to user

---

### Epic 3: Old/Unwatched Content

#### US-3.1: View Old Unwatched Content
**As a** user
**I want** to see a list of content not watched in 4+ months
**So that** I can decide what to delete

**Acceptance Criteria:**
- [ ] Dashboard shows list of old/unwatched movies and series
- [ ] Each item shows: name, type, year, size, last watched date, path
- [ ] List sorted by size (largest first)
- [ ] Total count and total size displayed

---

#### US-3.2: Delete Content from Jellyfin
**As a** user
**I want** to delete a movie/series directly from the dashboard
**So that** I don't have to go to Jellyfin

**Acceptance Criteria:**
- [ ] Delete button on each content item
- [ ] Confirmation modal before deletion
- [ ] Backend calls Jellyfin API to delete
- [ ] Item removed from list after deletion
- [ ] Success/error toast notification

---

#### US-3.3: Protect Content from Deletion
**As a** user
**I want** to add content to a whitelist
**So that** it won't appear in the "to delete" list

**Acceptance Criteria:**
- [ ] "Protect" button on each content item
- [ ] Item added to user's content whitelist
- [ ] Protected items no longer appear in old/unwatched list
- [ ] Visual indicator for protected items

---

#### US-3.4: Manage Content Whitelist
**As a** user
**I want** to view and edit my content whitelist
**So that** I can remove protection from items

**Acceptance Criteria:**
- [ ] Whitelist page shows all protected items
- [ ] Remove button to unprotect items
- [ ] Add button to manually add items by name

---

### Epic 4: Large Movies

#### US-4.1: View Large Movies
**As a** user
**I want** to see movies larger than 13GB
**So that** I can re-download them in lower quality

**Acceptance Criteria:**
- [ ] Page shows movies exceeding size threshold
- [ ] Each item shows: name, year, size, watched status
- [ ] Configurable threshold in settings
- [ ] Total size of large movies displayed

---

### Epic 5: Language Issues

#### US-5.1: View Content with Language Issues
**As a** user
**I want** to see content missing French or English audio
**So that** I can re-download proper versions

**Acceptance Criteria:**
- [ ] Page shows content with language problems
- [ ] Shows which languages are missing (EN/FR audio, FR subs)
- [ ] For series: shows which episodes have issues
- [ ] Filter by issue type

---

#### US-5.2: Mark Content as French-Only
**As a** user
**I want** to mark French films as not needing English audio
**So that** they don't appear as language issues

**Acceptance Criteria:**
- [ ] "Mark as French-only" button
- [ ] Item added to french-only whitelist
- [ ] Item no longer flagged for missing English

---

#### US-5.3: Exempt Content from Language Checks
**As a** user
**I want** to completely exempt content from language checks
**So that** special cases don't show as issues

**Acceptance Criteria:**
- [ ] "Exempt from checks" button
- [ ] Item no longer appears in language issues
- [ ] Manage exemptions in whitelist page

---

### Epic 6: Jellyseerr Requests

#### US-6.1: View Unavailable Requests
**As a** user
**I want** to see Jellyseerr requests that aren't available
**So that** I can manually find them

**Acceptance Criteria:**
- [ ] Page shows requests with unavailable status
- [ ] Shows: title, type, requested by, request date
- [ ] For TV: shows which seasons are missing

---

#### US-6.2: View Currently Airing Series
**As a** user
**I want** to see series that are currently airing
**So that** I know new episodes are coming

**Acceptance Criteria:**
- [ ] Section shows in-progress series
- [ ] Shows: title, current season, episodes aired/total

---

#### US-6.3: View Recently Available Content
**As a** user
**I want** to see what became available this week
**So that** I can notify my friends

**Acceptance Criteria:**
- [ ] Page shows content available in past 7 days
- [ ] Grouped by date
- [ ] Copy-friendly format for sharing

---

### Epic 7: Background Tasks & Refresh

#### US-7.1: Automatic Daily Data Sync
**As a** user
**I want** my data to refresh automatically every day
**So that** the dashboard is always up-to-date

**Acceptance Criteria:**
- [ ] Background task runs daily per user
- [ ] Fetches data from Jellyfin and Jellyseerr
- [ ] Stores results in database
- [ ] Dashboard shows last sync time

---

#### US-7.2: Manual Data Refresh
**As a** user
**I want** to manually trigger a data refresh
**So that** I can see changes immediately

**Acceptance Criteria:**
- [ ] "Refresh" button on dashboard
- [ ] Shows loading state during refresh
- [ ] Data updates after refresh completes
- [ ] Rate limited to prevent API abuse

---

### Epic 8: Settings & Preferences

#### US-8.1: Configure Thresholds
**As a** user
**I want** to customize analysis thresholds
**So that** the dashboard matches my preferences

**Acceptance Criteria:**
- [ ] Settings for: months cutoff, min age, large movie size
- [ ] Changes apply to user's analysis
- [ ] Defaults provided for new users

---

## Checklist Format for Ralph

Each user story above becomes a checklist item:

- [x] US-0.1: Hello World (Full Stack)
- [x] US-0.2: Dockerize the Application
- [x] US-0.3: Deploy to VPS
- [x] US-1.1: User Registration
- [x] US-1.2: User Login
- [ ] US-1.3: Protected Routes
- [ ] US-2.1: Configure Jellyfin Connection
- [ ] US-2.2: Configure Jellyseerr Connection
- [ ] US-3.1: View Old Unwatched Content
- [ ] US-3.2: Delete Content from Jellyfin
- [ ] US-3.3: Protect Content from Deletion
- [ ] US-3.4: Manage Content Whitelist
- [ ] US-4.1: View Large Movies
- [ ] US-5.1: View Content with Language Issues
- [ ] US-5.2: Mark Content as French-Only
- [ ] US-5.3: Exempt Content from Language Checks
- [ ] US-6.1: View Unavailable Requests
- [ ] US-6.2: View Currently Airing Series
- [ ] US-6.3: View Recently Available Content
- [ ] US-7.1: Automatic Daily Data Sync
- [ ] US-7.2: Manual Data Refresh
- [ ] US-8.1: Configure Thresholds
