# Suggestions & Observations

Items spotted during development that should be addressed but aren't blocking current stories.
Mark items with priority: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

## UI/UX
- ~~[P2] Add navigation header with logo and user menu~~ → Added as US-2.3 in PRD
- [P3] Add breadcrumb navigation for multi-page flows
- [P3] Extract common form components (FormGroup, Input, Button) - used in login, register, settings

## Architecture
<!-- Example: [P2] Extract reusable form input components -->

## Security
- [P2] Add rate limiting to auth endpoints (login, register)
- [P2] Consider httpOnly cookies instead of localStorage for JWT storage (XSS protection)

## Database
- ~~[P1] Add user_id foreign keys to whitelist tables for multi-tenancy~~ → Addressed in US-2.1.5 (cleanup) and all whitelist stories now require user_id FK

## Performance
<!-- Add observations here -->

## Testing
<!-- Add observations here -->

## Features (Future Scope)
- [P2] Delete content directly from dashboard (requires Radarr/Sonarr API integration for proper removal)
- [P3] Google Sign Up - OAuth 2.0 flow with "Continue with Google" button
