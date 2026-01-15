# Suggestions & Observations

Items spotted during development. Mark with: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

---

## Security

- [P2] Default SECRET_KEY in config.py is insecure - should validate/warn if using default in production
- [P3] Add CSRF protection for state-changing operations

## Architecture

- [P3] Consider extracting sync status display into reusable component for dashboard

## UI/UX

- [P3] Extract common form components (FormGroup, Input, Button) - used in login, register, settings

## Database

- [P3] Add database indexes on CachedMediaItem for common queries (media_type, played, size_bytes)

## Features (Future Scope)

- [P3] Google Sign Up - OAuth 2.0 flow with "Continue with Google" button
