# Suggestions & Observations

Items spotted during development that should be addressed but aren't blocking current stories.
Mark items with priority: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

## UI/UX
- [P2] Add navigation header with logo and user menu (currently logout button is on dashboard only)
- [P3] Add breadcrumb navigation for multi-page flows
- [P3] Extract common form components (FormGroup, Input, Button) - used in login, register, settings

## Architecture
<!-- Example: [P2] Extract reusable form input components -->

## Security
- [P2] Add rate limiting to auth endpoints (login, register)
- [P2] Consider httpOnly cookies instead of localStorage for JWT storage (XSS protection)

## Database
- [P1] Add user_id foreign keys to whitelist tables for multi-tenancy (currently global)

## Performance
<!-- Add observations here -->

## Testing
<!-- Add observations here -->
