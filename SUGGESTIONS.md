# Suggestions & Observations

Items spotted during development that should be addressed but aren't blocking current stories.
Mark items with priority: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

---

## ACTION NEEDED: Review P1 items for PRD promotion

The following P1 items were identified during integration review on 2026-01-13:
- **[P1] Page title inconsistency** - Login/Register pages use "Plex Dashboard" but app is named "Media Janitor" (Dashboard/Settings/Old Content pages are correct)
- **[P1] No automatic scheduler for daily sync** - US-7.1 "Automatic Daily Data Sync" has no automatic component (only manual trigger exists)
- **[P1] US-7.1 was not tested with real APIs** - Only unit tests with mocks exist; need manual integration test

**Resolved since last review:**
- ~~Manual sync button missing~~ - Dashboard now has "Refresh" button (US-7.2 completed)

---

## UI/UX
- ~~[P2] Add navigation header with logo and user menu~~ → Added as US-2.3 in PRD (COMPLETED)
- ~~[P2] Add loading spinner/skeleton on settings page~~ → Settings page now shows "Loading settings..." state
- [P2] Add favicon - browser shows 404 for `/favicon.png` (no `frontend/static/` folder exists)
- [P3] Add breadcrumb navigation for multi-page flows
- [P3] Extract common form components (FormGroup, Input, Button) - used in login, register, settings
- [P3] Consider adding toast notifications for successful operations (toast store exists but not used on all pages)
- [P3] Add password confirmation field on registration form
- [P3] Navigation header could show user email or avatar for better UX

## Architecture
- [P1] US-7.1 delivered sync service but NO scheduler - "Automatic Daily Data Sync" has no automatic component. Need APScheduler, Celery Beat, or system cron to trigger `/api/sync` for all users daily.
- [P2] Frontend api.ts defines endpoints for future features (contentApi, languageApi, etc.) that don't exist yet - should match actual backend endpoints
- [P2] Add sync retry mechanism with exponential backoff for transient API failures
- [P2] Add sync queue/throttling to prevent overloading Jellyfin/Jellyseerr when multiple users sync
- [P3] Consider extracting sync status display into reusable component for dashboard

## Security
- [P2] Add rate limiting to auth endpoints (login, register) - vulnerable to brute force attacks
- [P2] Consider httpOnly cookies instead of localStorage for JWT storage (XSS protection)
- ~~[P2] Add rate limiting to sync endpoint~~ → Sync endpoint has 5-minute rate limit per user (COMPLETED)
- [P2] CORS only allows localhost origins - need to add production URL (mediajanitor.com) to `main.py`
- [P2] Default SECRET_KEY in config.py is insecure - should validate/warn if using default in production
- [P3] Add CSRF protection for state-changing operations
- [P3] Consider adding password strength indicator on registration

## Database
- ~~[P1] Add user_id foreign keys to whitelist tables for multi-tenancy~~ → Addressed in US-2.1.5 (cleanup) and all whitelist stories now require user_id FK
- [P3] Add database indexes on CachedMediaItem for common queries (media_type, played, size_bytes)

## Performance
- [P2] Auth check on page load can cause noticeable "Loading..." delay - consider optimistic rendering for public routes
- [P3] Consider caching user settings in frontend store to avoid re-fetching on settings page visits

## Testing
- ~~[P1] US-7.1 was not manually tested with real API keys~~ → Moved to ACTION NEEDED section above
- [P2] E2E tests should cover the full auth flow (register -> login -> dashboard -> settings -> logout)
- [P3] Add integration tests for sync service with mocked external APIs

## Accessibility
- [P3] Old content table needs `role="table"` and proper aria attributes for screen readers
- [P3] Loading spinner should have `aria-busy="true"` on parent container
- [P3] Form error messages should use `aria-describedby` to associate with inputs

## Features (Future Scope)
- [P2] Delete content directly from dashboard (requires Radarr/Sonarr API integration for proper removal)
- [P3] Google Sign Up - OAuth 2.0 flow with "Continue with Google" button
- [P3] Dark/light mode toggle (CSS variables already support both)
- [P3] Remember me checkbox on login to extend token expiry

---

## Integration Review Summary (2026-01-13)

### What's Working Well
- Authentication flow (register, login, logout, protected routes)
- Navigation header with active state indication
- Settings page with Jellyfin/Jellyseerr connection management
- Old/Unwatched content page with sorting by size
- Manual sync with rate limiting and toast notifications
- Consistent dark theme across all pages
- Responsive design on mobile for content table

### Key Issues to Address
1. **P1**: Page titles say "Plex Dashboard" on login/register (should be "Media Janitor")
2. **P1**: No automatic daily sync scheduler exists
3. **P2**: Missing favicon causes 404
4. **P2**: CORS needs production URL
5. **P2**: Auth endpoints have no rate limiting
