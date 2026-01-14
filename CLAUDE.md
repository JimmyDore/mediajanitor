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
├── PRD.md                 # User Stories & Acceptance Criteria (human-readable)
├── prd.json               # Machine-readable task tracking for Ralph
├── progress.txt           # Completed tasks log + Codebase Patterns
├── SUGGESTIONS.md         # Observations with [P1]/[P2]/[P3] priorities
├── CLAUDE.md              # This file - project context
├── prompt.md              # Ralph execution loop prompt
├── ralph-once.sh          # Single iteration Ralph script
├── afk-ralph.sh           # Autonomous loop Ralph script
├── .claude/
│   └── skills/
│       ├── prd/SKILL.md           # /prd skill - PRD creation
│       ├── ralph-init/SKILL.md    # /ralph-init skill - PRD to JSON
│       ├── prd-sync/SKILL.md      # /prd-sync skill - Sync prd.json to PRD.md
│       ├── improve-claude-md/SKILL.md  # /improve-claude-md skill - Extract learnings
│       └── exploratory-qa/SKILL.md     # /exploratory-qa skill - Periodic QA review
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

**Phase**: Epic 7 - Background Tasks & Refresh (In Progress)
**Completed**: US-0.1 through US-2.3, US-7.1 (11 stories)
**Next US**: US-7.1.5 - Local Integration Test for Sync

**Production URL**: https://mediajanitor.com

Query status: `cat prd.json | jq '.userStories[] | {id, title, passes}'`

## Ralph Workflow

### Skills (Human-driven, before Ralph)

1. **`/prd`** - Create well-structured PRD with right-sized stories
   - Location: `.claude/skills/prd/SKILL.md`
   - Ensures stories fit in one context window
   - Adds verifiable acceptance criteria

2. **`/ralph-init`** - Convert PRD.md to prd.json
   - Location: `.claude/skills/ralph-init/SKILL.md`
   - Creates machine-readable task tracking
   - Validates story sizing and dependencies

3. **`/prd-sync`** - Sync prd.json back to PRD.md
   - Location: `.claude/skills/prd-sync/SKILL.md`
   - Updates checkbox status and notes in PRD.md
   - Keeps human-readable doc in sync after Ralph completes stories

4. **`/improve-claude-md`** - Extract learnings from current session
   - Location: `.claude/skills/improve-claude-md/SKILL.md`
   - Captures new patterns for CLAUDE.md
   - Called after completing implementation work

5. **`/exploratory-qa`** - Periodic QA review
   - Location: `.claude/skills/exploratory-qa/SKILL.md`
   - Reviews app for cross-cutting concerns
   - Updates SUGGESTIONS.md with observations

6. **`/original-script`** - Debug using original script as source of truth
   - Location: `.claude/skills/original-script/SKILL.md`
   - Run original_script.py functions to validate app behavior
   - Compare output counts/items between original and app
   - Use when app results don't match expectations

### Ralph Loop (Autonomous execution)

Run `./ralph-once.sh` (human-in-the-loop) or `./afk-ralph.sh N` (autonomous N iterations)

Prompt location: `prompt.md`

Workflow:
1. Pick next story where `passes: false` from prd.json
2. Implement with TDD (test first)
3. Run quality checks (pytest, mypy, npm test, npm run check)
4. Verify in Docker if backend changed
5. Update prd.json → `passes: true`
6. Commit, log to progress.txt, update CLAUDE.md
7. Add observations to SUGGESTIONS.md with [P1]/[P2]/[P3] priorities

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

**Test Database**: Use **async** SQLAlchemy sessions in tests to match production
```python
# tests/conftest.py - override get_db with async session (MUST match production)
async_engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
TestingAsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)
```

### Database Migrations (Alembic) - CRITICAL WORKFLOW

**⚠️ EVERY database model change MUST have a migration. No exceptions.**

Production database schema diverges from models if migrations are missing. This causes:
- 500 errors: `OperationalError: no such column`
- Docker startup failures: `duplicate column name` (if migration created after column exists)

#### The Correct Workflow (MUST FOLLOW)

**Step 1: Modify the model** in `app/database.py`
```python
# Add your new column
class UserSettings(Base):
    new_column: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

**Step 2: Create migration IMMEDIATELY** (before any Docker runs)
```bash
cd backend
uv run alembic revision --autogenerate -m "add_new_column_to_user_settings"
```

**Step 3: Review the generated migration** in `backend/alembic/versions/`
- Column types are correct
- Nullable settings match your model
- No unintended changes (alembic sometimes detects phantom changes)

**Step 4: Test migration locally**
```bash
cd backend
uv run alembic upgrade head
```

**Step 5: THEN run Docker** (Docker applies migrations on startup)
```bash
docker-compose up --build -d
```

#### Common Mistakes to Avoid

| Mistake | Result | Fix |
|---------|--------|-----|
| Add column to model, run Docker, THEN create migration | `duplicate column` error | Delete local DB, recreate migration |
| Forget to create migration | Works locally (create_all), fails in prod | Create migration before deploying |
| Create migration but don't commit it | Prod schema mismatch | Always commit migrations with model changes |

#### If You Get "duplicate column" Error

The database already has the column (from a previous run or create_all). Fix:
```bash
# Option 1: Reset local database
rm -f data/plex_dashboard.db
docker-compose down -v
docker-compose up --build -d

# Option 2: Stamp to skip the broken migration (if column exists)
cd backend
uv run alembic stamp head
```

#### Migration Commands Reference
```bash
# Create new migration
uv run alembic revision --autogenerate -m "describe_change"

# Apply all pending migrations
uv run alembic upgrade head

# Check current revision
uv run alembic current

# View migration history
uv run alembic history --verbose

# Stamp database (mark as migrated without running)
uv run alembic stamp head
```

**Docker handles migrations automatically**: The entrypoint script runs `alembic upgrade head` before starting the app.

**Migration best practices**:
- One migration per logical change
- Use descriptive names: `add_expires_at_to_whitelists`, `create_notifications_table`
- Commit migration file in SAME commit as model change
- Never edit a migration after it's been applied to production
- If you need to fix a migration, create a new one

**⚠️ NEVER DELETE MIGRATIONS THAT EXIST IN PRODUCTION**

If you delete a migration file that production has applied, production will fail with:
```
Can't locate revision identified by 'XXXXX'
```

To check what revision production is at:
```bash
ssh vpsjim "sqlite3 /home/jimmydore/mediajanitor/data/plex_dashboard.db 'SELECT * FROM alembic_version;'"
```

If you MUST delete a migration, first update production's alembic_version:
```bash
ssh vpsjim
cd /home/jimmydore/mediajanitor
sudo sqlite3 data/plex_dashboard.db "UPDATE alembic_version SET version_num = 'NEW_REVISION';"
docker-compose up -d
```

### Async/Sync Consistency (CRITICAL)

**Always use async sessions in tests to match production:**
- Production uses `AsyncSession` via `get_db()`
- Tests MUST also use `AsyncSession` via async `override_get_db()`
- Never mix sync endpoints (`def`) with async database sessions

**Pattern for async endpoints:**
```python
# Router - always use async def with AsyncSession
async def endpoint(db: AsyncSession = Depends(get_db)):
    result = await service_async(db, ...)

# Service - provide async version
async def service_async(db: AsyncSession, ...):
    result = await db.execute(...)
    return result.scalar_one_or_none()
```

**Why this matters:** Using sync test sessions masks async bugs. Tests pass but production fails with `'coroutine' object has no attribute 'scalar_one_or_none'`.

### Protected Routes Pattern

**Backend - get_current_user dependency:**
```python
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    # Validate token, get user from DB
    # Raises HTTPException 401 if invalid
```

**Frontend - Auth store pattern:**
```typescript
// Store with checkAuth(), logout(), setUser() methods
// Layout checks auth on mount, redirects to /login if not authenticated
// Public routes: /login, /register (no redirect)
```

### Encrypted User Settings Pattern

**Storing sensitive per-user data (API keys):**
```python
# app/services/encryption.py - Fernet symmetric encryption
from cryptography.fernet import Fernet

def encrypt_value(value: str) -> str:
    """Encrypt using app's secret_key as Fernet key."""
    fernet = _get_fernet()  # Derives key from settings.secret_key
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()

# app/database.py - UserSettings model
class UserSettings(Base):
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    jellyfin_server_url: Mapped[str | None]
    jellyfin_api_key_encrypted: Mapped[str | None]  # Store encrypted!
```

**Settings endpoint pattern:**
- POST validates connection BEFORE saving (call external API)
- GET returns masked info (api_key_configured: bool, not the actual key)
- Mock external API calls in tests using `@patch("app.routers.settings.function_name")`

### Production Debugging (VPS)

**Accessing production logs:**
```bash
ssh vpsjim "docker logs mediajanitor_backend_1 --tail 100 2>&1"
```

**Checking database schema in production:**
```bash
ssh vpsjim "docker exec mediajanitor_backend_1 python3 -c \"
import sqlite3
conn = sqlite3.connect('/app/data/plex_dashboard.db')
cursor = conn.execute('PRAGMA table_info(TABLE_NAME)')
print([row[1] for row in cursor])
\""
```

**Common 500 errors:** Usually caused by missing database columns. Check logs for `OperationalError: no such column`. Fix by creating a migration.

**Deployment workflow - NEVER do both:**
1. **Option A**: Push migration and WAIT for GitHub Actions deployment to complete
2. **Option B**: Apply fix manually on VPS without pushing

Doing both causes conflicts - the automated deployment may restart containers mid-manual-fix.

**Production location:** `/home/jimmydore/mediajanitor`

**Nginx config:** `/etc/nginx/sites-enabled/mediajanitor*`
- Frontend: `localhost:5173`
- Backend API: `localhost:8080`

### Docker Verification (CRITICAL)

**Unit tests passing is NOT enough.** Before marking a backend task complete:
1. Run `task docker:up:build` (or `docker-compose up --build -d`)
2. Test the feature manually via curl: `curl -X POST http://localhost:8080/api/...`
3. Check Docker logs for errors: `docker-compose logs backend`
4. If errors appear, fix and re-run tests

### Integration Testing with Real APIs

**For features that interact with Jellyfin/Jellyseerr**, use the test account in `.env.example`:
- **Email**: `APP_USER_EMAIL` from `.env.example`
- **Password**: `APP_USER_PASSWORD` from `.env.example`

This account has Jellyfin and Jellyseerr already configured in the app settings. Use it for:
- Testing sync functionality with real data
- Verifying cached data is stored correctly
- Testing any feature that reads from cached media/requests

**Integration test workflow:**
```bash
# 1. Start local environment
docker-compose up -d

# 2. Read credentials from .env.example
APP_USER_EMAIL=$(grep '^APP_USER_EMAIL=' .env.example | cut -d'=' -f2)
APP_USER_PASSWORD=$(grep '^APP_USER_PASSWORD=' .env.example | cut -d'=' -f2)

# 3. Login to get JWT token
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$APP_USER_EMAIL\",\"password\":\"$APP_USER_PASSWORD\"}" \
  | jq -r '.access_token')

# 4. Verify token was obtained
echo "Token: $TOKEN"

# 5. Test authenticated endpoints
curl -s http://localhost:8080/api/sync/status \
  -H "Authorization: Bearer $TOKEN" | jq .
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

### Testing Strategy (Testing Pyramid)

**Target ratio: 70% unit tests, 20% integration, 10% E2E**

**Note on "Integration Tests":**
- **Python integration tests**: `cd backend && uv run pytest tests/test_integration.py -v`
  - Uses httpx to call real Docker endpoints
  - Create new tests here for features that need real API verification
- **Manual curl QA**: Quick sanity checks after Docker is running
- Credentials are hardcoded in `test_integration.py` (from `.env.example`)

1. **Backend Unit Tests** (pytest): Test API endpoints, services, database operations
   - Location: `backend/tests/`
   - Run: `cd backend && uv run pytest`

2. **Frontend Unit Tests** (vitest): Test API contracts, business logic, UI state
   - Location: `frontend/tests/`
   - Run: `cd frontend && npm run test`
   - **REQUIRED** for any page that makes API calls
   - Pattern: Mock `fetch`, verify request format and response handling
   - **Test here**: Form validation, API responses, loading states, toasts, error handling

3. **E2E Tests** (Playwright): **MINIMAL** smoke tests only (~20 tests max)
   - Location: `frontend/e2e/`
   - Run: `cd frontend && npm run test:e2e`
   - **ONLY test**: Page loads, navigation works, auth redirects work
   - **DO NOT test**: Form validation, API responses, loading states, toasts
   - Keep E2E count LOW - they are slow and flaky
   - No mock delays (`setTimeout`), no `waitForTimeout()`

**When to write each:**
- Backend changed → Backend unit tests (always)
- Frontend API calls added → Frontend unit tests (always)
- **New route/page added** → ONE E2E smoke test (page renders)
- Frontend UI state/validation → Frontend unit tests (NOT E2E)

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
