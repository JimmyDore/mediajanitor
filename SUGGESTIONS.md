# Suggestions & Observations

Items spotted during development. Mark with: **[P1]** critical, **[P2]** should do, **[P3]** nice to have.

P1 items should be reviewed and manually added to PRD.md if deemed necessary.

---

## Security

- [P2] Default SECRET_KEY in config.py is insecure - should validate/warn if using default in production
- [P3] Add CSRF protection for state-changing operations

## UI/UX

### Settings Page (reviewed 2026-01-16)

- [P2] Inconsistent save patterns: Connections need explicit Save, Theme auto-saves on click, Recent Days auto-saves on blur, Toggle auto-saves. Users can't predict behavior. Standardize to auto-save with toast feedback everywhere.
- [P2] Connection inline editing is jarring - form expands and pushes content down. Consider modal/drawer or animated expand.
- [P2] "Thresholds" help text ("Used by: Old tab") assumes users know app structure. Use more descriptive text like "Used to identify content for deletion".
- [P3] Section titles are ALL CAPS with letter-spacing - feels dated. Use sentence case ("Connections" not "CONNECTIONS").
- [P3] Nickname table "→" arrow column is decorative clutter - remove it, use visual proximity.
- [P3] Connection status dots (8px green) are too subtle - add "Connected" text label or badge.
- [P3] Theme selector has icons + text making it wide/busy - use icons-only with tooltips or text-only.
- [P3] Dark mode contrast issues: Edit buttons and input borders blend in slightly.
- [P3] No page navigation for 4 sections - consider sticky headers or tabs for longer settings pages.
- [P3] Nickname action icons (edit/delete) have small touch targets - increase to 32px.

## Accessibility

## Architecture

- [P3] Consider extracting sync status display into reusable component for dashboard

## Database

- [P3] Add database indexes on CachedMediaItem for common queries (media_type, played, size_bytes)

## Features (Future Scope)

- [P3] Google Sign Up - OAuth 2.0 flow with "Continue with Google" button
