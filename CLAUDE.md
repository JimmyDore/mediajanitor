# Plex Dashboard - Project Context

## Project Vision

A **SaaS web application** for media server owners to manage their Plex/Jellyfin libraries. Users sign up, connect their own Jellyfin/Jellyseerr instances, and get actionable insights.

## Original Script Reference

The project is based on `../jellyfin_monitor.py` which provides:

### 5 Main Features
1. **Old/Unwatched Content** - Content not watched in 4+ months (configurable)
2. **Large Movies** - Movies >13GB for potential re-download
3. **Language Issues** - Missing EN/FR audio or FR subtitles
4. **Jellyseerr Unavailable Requests** - Pending/unavailable requests
5. **Recently Available** - New content in past 7 days

### Whitelists from Original Script
- `CONTENT_ALLOWLIST` - Protected from deletion (~130 items)
- `FRENCH_ONLY_ALLOWLIST` - French content, no EN audio needed (~100 items)
- `FRENCH_SUBS_ONLY_ALLOWLIST` - Only FR subs required (~5 items)
- `LANGUAGE_CHECK_ALLOWLIST` - Exempt from language checks (~17 items)
- `LANGUAGE_CHECK_EPISODE_ALLOWLIST` - Specific episodes exempt

### Configuration Values from Script
```python
OLD_CONTENT_MONTHS_CUTOFF = 4      # Content not watched in X months
MIN_AGE_MONTHS = 3                 # Don't flag recently added content
LARGE_MOVIE_SIZE_THRESHOLD_GB = 13
RECENT_ITEMS_DAYS_BACK = 1500
FILTER_FUTURE_RELEASES = True
FILTER_RECENT_RELEASES = True
RECENT_RELEASE_MONTHS_CUTOFF = 3
```

### External APIs Used
- **Jellyfin API** - Media library data, user watch history
- **Jellyseerr API** - Media requests, availability status

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: SvelteKit + TypeScript
- **Database**: PostgreSQL (prod) / SQLite (dev)
- **Background Tasks**: FastAPI BackgroundTasks or Celery
- **Deployment**: Docker + GitHub Actions + VPS
- **Auth**: JWT-based authentication

## Architecture Decisions

### 1. Background Data Fetching
Jellyfin/Jellyseerr APIs are slow. Data is:
- Fetched daily via background tasks
- Cached in database
- Users can trigger manual refresh

### 2. Multi-tenant SaaS
- Each user has isolated data
- Users store their own API keys (encrypted)
- Per-user whitelists and settings

### 3. Full-stack User Stories
Each story delivers end-to-end value (API + UI together).

## Development Guidelines

### TDD Workflow
1. **Red**: Write a failing test first
2. **Green**: Implement minimum code to pass
3. **Refactor**: Clean up while tests pass
4. **Commit**: Clear commit message describing the change

### Commit Message Format
```
feat(scope): short description

- Detail 1
- Detail 2
```

Examples:
- `feat(api): add hello world endpoint`
- `feat(ui): display hello message from backend`
- `chore(docker): add Dockerfile for backend`

### Code Style
- **Python**: PEP 8, type hints everywhere
- **TypeScript**: Strict mode, explicit types
- **Tests**: One test file per module, descriptive test names

## Project Structure

```
plex-dashboard/
├── PRD.md                 # User Stories & Acceptance Criteria
├── progress.txt           # Completed tasks log
├── CLAUDE.md              # This file - project context
├── ralph-once.sh          # Single iteration Ralph script
├── afk-ralph.sh           # Autonomous loop Ralph script
├── docker-compose.yml     # Local development
├── .env.example           # Environment template
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py        # FastAPI app
│   │   ├── config.py      # Pydantic Settings
│   │   ├── database.py    # SQLAlchemy models
│   │   ├── models/        # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── routers/       # API endpoints
│   └── tests/
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── svelte.config.js
│   ├── src/
│   │   ├── routes/        # SvelteKit pages
│   │   ├── lib/           # Shared code
│   │   └── app.css        # Global styles
│   └── tests/
│
└── .github/
    └── workflows/
        └── deploy.yml     # CI/CD pipeline
```

## Current Status

**Phase**: Epic 1 - Authentication (In Progress)
**Completed**: US-0.1, US-0.2, US-0.3, US-1.1 (User Registration)
**Next US**: US-1.2 - User Login

**Production URL**: https://mediajanitor.com

## Learnings & Patterns

### Backend (FastAPI + SQLAlchemy)

**Package Management**: Use `uv` for Python dependency management
```bash
cd backend
uv sync --extra dev          # Install dependencies
uv run pytest                # Run tests
uv run uvicorn app.main:app --reload  # Run server
```

**Password Hashing**: Use `bcrypt` directly (not passlib) for Python 3.12+ compatibility
```python
import bcrypt
hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
```

**Test Database**: Use sync SQLAlchemy sessions in tests with in-memory SQLite
```python
# tests/conftest.py - override get_db with sync session
engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
```

### Frontend (SvelteKit + Svelte 5)

**Svelte 5 Runes**: Use `$state()` for reactive state, `$props()` for component props
```svelte
<script lang="ts">
  let value = $state('');
  let { children } = $props();
</script>
```

**E2E Testing**: Playwright with webServer config auto-starts dev server
```bash
npm run test:e2e            # Run E2E tests
npm run test:e2e:ui         # Interactive mode
```

**CSS Variables**: Defined in `src/app.css` with light/dark mode support
- Use `--text-primary`, `--bg-primary`, `--accent`, etc.

### Testing Strategy

1. **Backend Unit Tests**: pytest with TestClient, in-memory SQLite
2. **Frontend Unit Tests**: vitest for logic/API contract tests
3. **E2E Tests**: Playwright for UI smoke tests (form renders, can fill, links work)
   - E2E tests should work without backend (test UI only)
   - Use HTML5 validation attributes for form validation where possible

## Environment Variables

```env
# Backend
DATABASE_URL=sqlite:///./plex_dashboard.db
SECRET_KEY=your-secret-key-here

# Jellyfin (per-user, stored in DB)
# JELLYFIN_API_KEY=xxx
# JELLYFIN_SERVER_URL=https://server/jellyfin

# Jellyseerr (per-user, stored in DB)
# JELLYSEER_API_KEY=xxx
# JELLYSEER_BASE_URL=https://server/jellyseerr
```

## Running the Project

### Development (Docker)
```bash
docker-compose up
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

### Backend Only
```bash
cd backend
uv sync --extra dev                 # Install dependencies
uv run pytest                       # Run tests
uv run uvicorn app.main:app --reload  # Run server
```

### Frontend Only
```bash
cd frontend
npm install
npm run test                       # Run unit tests
npm run test:e2e                   # Run E2E tests
npm run dev                        # Run dev server
```
