# Suggestions & Observations

Items spotted during development. Mark with: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

---

## ACTION NEEDED: Review P1 items for PRD promotion

- **[P1] Production deployment outdated** - Landing page (US-M.1-5) and recent fixes NOT deployed to mediajanitor.com. Visitors redirected to /login instead of seeing landing page.

---

## Security

- [P2] Add rate limiting to auth endpoints (login, register) - vulnerable to brute force attacks
- [P2] Consider httpOnly cookies instead of localStorage for JWT storage (XSS protection)
- [P2] Default SECRET_KEY in config.py is insecure - should validate/warn if using default in production
- [P3] Add CSRF protection for state-changing operations
- [P3] Consider adding password strength indicator on registration

## Architecture

- [P2] TV series season analysis not implemented - Original script does complex TMDB-based season analysis; app uses simpler status-based filtering
- [P2] Add sync retry mechanism with exponential backoff for transient API failures
- [P2] Add sync queue/throttling to prevent overloading Jellyfin/Jellyseerr when multiple users sync
- [P3] Consider extracting sync status display into reusable component for dashboard

## UI/UX

- [P3] Add breadcrumb navigation for multi-page flows
- [P3] Extract common form components (FormGroup, Input, Button) - used in login, register, settings
- [P3] Add password confirmation field on registration form
- [P3] Mobile dashboard has slight visual overlap - thin blue strip visible on left edge when sidebar closed

## Database

- [P3] Add database indexes on CachedMediaItem for common queries (media_type, played, size_bytes)

## Testing

- [P2] E2E tests should cover the full auth flow (register -> login -> dashboard -> settings -> logout)
- [P3] Add integration tests for sync service with mocked external APIs

## Accessibility

- [P3] Old content table needs `role="table"` and proper ARIA attributes for screen readers
- [P3] Loading spinner should have `aria-busy="true"` on parent container
- [P3] Form error messages should use `aria-describedby` to associate with inputs

## Features (Future Scope)

- [P3] Google Sign Up - OAuth 2.0 flow with "Continue with Google" button
- [P3] Dark/light mode toggle (CSS variables already support both)
- [P3] Remember me checkbox on login to extend token expiry
