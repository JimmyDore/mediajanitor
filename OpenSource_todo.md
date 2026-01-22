# Open Source Launch Checklist

## Phase 1: Security (Do First - Secrets Are Exposed!)

### Scan Git History First
- [X] Run `truffleHog` or `git-secrets` to scan for leaked secrets in history
- [X] Document which secrets (if any) were actually committed to git
- [X] If secrets found in history, consider `git filter-repo` to rewrite history

### Rotate Credentials (only if leaked)
- [X] Rotate Jellyfin API key (if found in git history)
- [X] Rotate Jellyseerr API key (if found in git history)
- [X] Rotate Radarr API key (if found in git history)
- [X] Rotate Sonarr API key (if found in git history)
- ~~Change test Gmail account password~~ (not needed - local testing only)

### Clean Environment Files
- [X] Replace credentials in `.env.example` with placeholders
- [X] Replace credentials in `backend/tests/test_integration.py`
- [X] Replace credentials in `backend/tests/test_large_movies_validation.py`

### Cleanup (Post-Release)
- [ ] Remove `APP_USER_EMAIL`/`APP_USER_PASSWORD` from `.env.example` (only used for local AI testing, not needed for users)
- [ ] Remove test credential references from README/CLAUDE.md

---

## Phase 2: Required Files

### LICENSE
- [X] Create `LICENSE` file with MIT license text

### README.md
- [X] Project description and purpose
- [X] Screenshots of the dashboard
- [X] Features overview (what it does):
  - Old/unwatched content detection
  - Large movies identification
  - Language issues (missing audio/subtitles)
  - Jellyseerr unavailable requests
  - Recently available content
  - Whitelists for protected content
- [X] How to run locally (Docker setup)
- [X] How to contribute (link to CONTRIBUTING.md)
- [X] License section

### Demo Video (Optional)
- [ ] Record demo video showing app walkthrough
- [ ] Upload to YouTube or embed in repo
- [ ] Add to README.md

---

## Phase 3: Sanitize Documentation

> **Solution:** Created `.claude/local.md` (gitignored) for personal values. Public docs use generic placeholders.

### CLAUDE.md
- [X] Replace `ssh vpsjim` with `ssh your-server`
- [X] Replace `/home/jimmydore/mediajanitor` with `~/mediajanitor` or `<install-path>`
- ~~Replace `jimmydore.eclipse.usbx.me` URLs~~ (not present in CLAUDE.md)

### .claude/skills/qa-infra/SKILL.md
- [X] Replace SSH commands with generic examples

### .claude/skills/original-script/SKILL.md
- ~~Replace paths~~ (file doesn't exist)

### .github/workflows/deploy.yml
- [X] Already uses `~/mediajanitor` which is generic

---

## Phase 4: Production Prep

### Shutdown Signups
- [X] Add feature flag or config to disable new user registration
- [X] Keep existing users working
- [X] Add "Signups closed" message on registration page

---

## Phase 5: Nice to Have (Post-Launch)

### Documentation
- [ ] Video of the app with zoom
- [ ] Architecture overview doc
- [ ] API documentation
- [ ] Database schema doc
- [ ] `CHANGELOG.md`

---

## Phase 6: Launch

### Reddit Post
- [ ] Draft post for r/selfhosted
- [ ] Draft post for r/jellyfin
- [ ] Include:
  - What the project does
  - Link to demo video
  - GitHub repo link
  - Screenshots
  - Note that it's new/looking for feedback
  - Be humble, explain that it's solving my main use cases that some maybe don't have (language issues, for example, I have french friends on it and I make sure as much as possible to have the original versions and the french versions)
  - Also explain that I'll try improving it based on feedbacks if there are, but I may not be the fastest man alive to solve issues, lots of stuff on the side.
  - Hosted it myself on a VPS but closed sign ups for now, runnning on a very cheap VPS that won't be able to handle a lot of users. And anyway, I think you may not want to share your jellyfin/jellyseer/radarr/sonarr API keys with everyone (but it's obviously encrypted in the database). I encourage everone to self host, really easy set up with docker compose.

---

## Files with Sensitive Data (Reference)

| File | Issue | Status |
|------|-------|--------|
| `.env` | Active API keys | ✅ gitignored |
| `.env.example:7-8` | Test credentials | ✅ Placeholders (AI testing only, can remove) |
| `backend/tests/test_integration.py` | Hardcoded credentials | ✅ Placeholders |
| `backend/tests/test_large_movies_validation.py` | Hardcoded credentials | ✅ Placeholders |
| `CLAUDE.md` | SSH commands, production paths | ✅ Generic placeholders (personal in local.md) |
| `.claude/skills/qa-infra/SKILL.md` | SSH commands | ✅ Generic placeholders |
| `.github/workflows/deploy.yml` | Production path | ✅ Already generic (`~/mediajanitor`) |
| `.claude/local.md` | Personal SSH/paths | ✅ gitignored |
