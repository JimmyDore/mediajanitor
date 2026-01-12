# Suggestions & Observations

Items spotted during development that should be addressed but aren't blocking current stories.
Mark items with priority: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

---

## ACTION NEEDED: Review P1 items for PRD promotion

The following P1 items were identified during the integration review on 2026-01-12:
- **[P1] Manual sync button missing from dashboard** - US-7.2 requires a "Refresh" button but dashboard only shows sync status
- **[P1] Page title inconsistency** - Login/Register pages use "Plex Dashboard" but app is named "Media Janitor"

---

## UI/UX
- ~~[P2] Add navigation header with logo and user menu~~ → Added as US-2.3 in PRD
- [P3] Add breadcrumb navigation for multi-page flows
- [P3] Extract common form components (FormGroup, Input, Button) - used in login, register, settings
- [P2] Add loading spinner/skeleton on settings page while fetching current settings
- [P2] Add favicon - browser shows 404 for `/favicon.png`
- [P3] Consider adding toast notifications for successful operations (toast store exists but not used)
- [P3] Add password confirmation field on registration form

## Architecture
- [P2] Frontend api.ts defines endpoints for future features (contentApi, languageApi, etc.) that don't exist yet - should match actual backend endpoints
- [P3] Consider extracting sync status display into reusable component for dashboard

## Security
- [P2] Add rate limiting to auth endpoints (login, register)
- [P2] Consider httpOnly cookies instead of localStorage for JWT storage (XSS protection)
- [P2] Add rate limiting to sync endpoint (currently no protection against API abuse per US-7.2)
- [P3] Add CSRF protection for state-changing operations
- [P3] Consider adding password strength indicator on registration

## Database
- ~~[P1] Add user_id foreign keys to whitelist tables for multi-tenancy~~ → Addressed in US-2.1.5 (cleanup) and all whitelist stories now require user_id FK
- [P3] Add database indexes on CachedMediaItem for common queries (media_type, played, size_bytes)

## Performance
- [P2] Auth check on page load can cause noticeable "Loading..." delay - consider optimistic rendering for public routes
- [P3] Consider caching user settings in frontend store to avoid re-fetching on settings page visits

## Testing
- [P2] E2E tests should cover the full auth flow (register -> login -> dashboard -> settings -> logout)
- [P3] Add integration tests for sync service with mocked external APIs

## Features (Future Scope)
- [P2] Delete content directly from dashboard (requires Radarr/Sonarr API integration for proper removal)
- [P3] Google Sign Up - OAuth 2.0 flow with "Continue with Google" button
- [P3] Dark/light mode toggle (CSS variables already support both)
- [P3] Remember me checkbox on login to extend token expiry
