# Suggestions & Observations

Items spotted during development that should be addressed but aren't blocking current stories.
Mark items with priority: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

---

## ACTION NEEDED: Review P1 items for PRD promotion

The following P1 items were identified during integration reviews:
- **[P1] Production deployment outdated** - Landing page (US-M.1-5), marketing CTAs, and recent fixes are NOT deployed to production. Visitors to https://mediajanitor.com/ are redirected to /login instead of seeing the landing page.

**Resolved since last review:**
- ~~Manual sync button missing~~ - Dashboard now has "Refresh" button (US-7.2 completed)
- ~~US-7.1 was not tested with real APIs~~ - US-7.1.5 completed: 324 media items, 244 requests synced
- ~~Page title inconsistency~~ - Fixed in US-9.1, all pages now use "Media Janitor" branding
- ~~No automatic scheduler for daily sync~~ - Implemented in US-10.2 with Celery Beat
- ~~Temporary whitelisting~~ - Implemented in US-11.1-11.3 with duration picker modal
- ~~Missing favicon~~ - Fixed in US-9.2 with SVG broom icon
- ~~CORS missing production URL~~ - Fixed in US-9.3

---

## UI/UX
- ~~[P2] Add navigation header with logo and user menu~~ → Added as US-2.3 in PRD (COMPLETED)
- ~~[P2] Add loading spinner/skeleton on settings page~~ → Settings page now shows "Loading settings..." state
- ~~[P2] Add favicon~~ → Fixed in US-9.2, SVG broom icon implemented
- [P3] Add breadcrumb navigation for multi-page flows
- [P3] Extract common form components (FormGroup, Input, Button) - used in login, register, settings
- [P3] Consider adding toast notifications for successful operations (toast store exists but not used on all pages)
- [P3] Add password confirmation field on registration form
- [P3] Navigation header shows user avatar (first letter of email) - works well

## Data/Sync
- ~~[P2] **Bug: "Unknown" titles in Recently Available**~~ - FIXED in US-V.4. Now fetches titles from `/api/v1/movie/{id}` or `/api/v1/tv/{id}` endpoints during sync.
- [P2] **TV Series season analysis not implemented** - Original script does complex TMDB-based season analysis to exclude TV series that are "complete for released seasons" (only missing future seasons) and track "currently airing" shows separately. App uses simpler status-based filtering which may include more TV requests than original script. This is a known simplification. Full implementation would require TMDB API calls per TV series.

## Architecture
- ~~[P1] US-7.1 delivered sync service but NO scheduler~~ → Implemented in US-10.2 with Celery Beat (3 AM UTC daily)
- [P2] Frontend api.ts defines endpoints for future features (contentApi, languageApi, etc.) that don't exist yet - should match actual backend endpoints
- [P2] Add sync retry mechanism with exponential backoff for transient API failures
- [P2] Add sync queue/throttling to prevent overloading Jellyfin/Jellyseerr when multiple users sync
- [P3] Consider extracting sync status display into reusable component for dashboard

## Security
- [P2] Add rate limiting to auth endpoints (login, register) - vulnerable to brute force attacks
- [P2] Consider httpOnly cookies instead of localStorage for JWT storage (XSS protection)
- ~~[P2] Add rate limiting to sync endpoint~~ → Sync endpoint has 5-minute rate limit per user (COMPLETED)
- ~~[P2] CORS missing production URL~~ → Fixed in US-9.3, mediajanitor.com added
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

## Exploratory QA Review (2026-01-13)

### What's Working Well
- Authentication flow (register, login, logout, protected routes)
- Navigation header with active state indication and correct highlighting
- Settings page with Jellyfin/Jellyseerr connection badges
- Unified Issues view with filter tabs (All, Old, Large, Language, Requests, Multi-Issue)
- FR Only button appears correctly for language issues
- Protect button works for old content
- Whitelists page shows both Protected and French-Only sections
- Manual sync with rate limiting and toast notifications
- Consistent dark theme across all pages
- **Mobile responsiveness excellent** - Dashboard and Issues pages adapt well to 375px width
- Dashboard summary cards with correct counts and navigation

### Key Issues Found (2026-01-13)
1. ~~**P1**: Page titles say "Plex Dashboard"~~ - Fixed in US-9.1
2. ~~**P1**: No automatic daily sync scheduler~~ - Fixed in US-10.2
3. ~~**P2**: "Unknown" titles in Recently Available~~ - Fixed in US-V.4
4. ~~**P2**: Missing favicon~~ - Fixed in US-9.2
5. ~~**P2**: CORS needs production URL~~ - Fixed in US-9.3
6. **P2**: Auth endpoints have no rate limiting
7. **P2**: TV series season analysis not implemented

### Pages Verified (2026-01-13)
- `/login` - Works correctly
- `/register` - Works correctly
- `/` (Dashboard) - Working with summary cards, sync status, refresh button
- `/issues` - Filter tabs work, Protect/FR Only/Exempt buttons functional
- `/whitelist` - Shows all three sections (Protected, French-Only, Language-Exempt)
- `/settings` - Jellyfin/Jellyseerr badges showing connected status
- `/info/recent` - Working correctly
- `/info/airing` - Shows empty state correctly (placeholder)

---

## Exploratory QA Review (2026-01-14)

### Production Deployment Issue (CRITICAL)
**Production at https://mediajanitor.com is outdated and missing all recent features:**
- Landing page (US-M.1-5) NOT deployed - visitors redirected to /login instead of seeing marketing page
- Register page shows "Create Account" instead of "Get Started Free" (US-M.5)
- Register button shows "Sign Up" instead of "Create Free Account"
- Favicon, CORS updates, and all Epic 10/11 features likely missing

**Recommendation**: Deploy latest `main` branch to production immediately.

### Codebase Review - What's Working Well
- **Design System (US-UI.1)**: Comprehensive CSS custom properties with:
  - Cool slate color palette (gray-50 to gray-900)
  - 4px spacing grid system
  - Sharp corner radius system (4/6/8px)
  - Monospace font for data values
  - Dark mode with proper contrast adjustments
- **Navigation Header**: User avatar shows first letter of email, dropdown menu with sign out
- **Issues Page**: Duration picker modal for whitelist expiration works well
- **Whitelist Page**: Shows expiration dates and "Expired" badge for expired items
- **Mobile Responsiveness**: Login page adapts well to 375px width

### New Issues Found
1. **[P1] Production deployment outdated** - See above. Latest code is NOT in production.
2. **[P2] Auth endpoints have no rate limiting** - Vulnerable to brute force attacks (carried over from previous review)

### Code Quality Observations
- **Clean separation of concerns**: Backend services in `/app/services/`, routers in `/app/routers/`
- **Type safety**: Pydantic models for all API requests/responses
- **Testing**: 191 backend tests, 102 frontend tests (good coverage)
- **CSS organization**: Global design tokens in `app.css`, component-scoped styles in Svelte files

### Accessibility Observations (P3)
- Forms have proper labels with `for` attributes
- Error messages have `role="alert"`
- Buttons have `aria-expanded` for dropdown states
- Loading spinners could use `aria-busy` on parent containers
- Tables could benefit from `role="table"` and ARIA attributes

### Pages Verified (Production)
| Page | Status | Notes |
|------|--------|-------|
| `/login` | ✅ Works | Dark theme, mobile responsive |
| `/register` | ⚠️ Outdated | Shows old copy (not "Get Started Free") |
| `/` | ❌ Broken | Redirects to /login instead of landing page |

### Recommendations
1. **URGENT**: Deploy latest code to production
2. **P2**: Add rate limiting to auth endpoints before public launch
3. **P3**: Review accessibility attributes on tables and loading states
