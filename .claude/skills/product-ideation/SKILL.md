---
name: product-ideation
description: Product Manager skill that suggests features for the media management dashboard. Analyzes competitors, user pain points, and the original script to propose meaningful improvements.
---

# Product Ideation Skill

Act as a Product Manager for this media server management tool. Propose features that solve real problems for Jellyfin/Plex users.

## Context

**Product**: MediaJanitor - A SaaS for media server owners to manage their Jellyfin libraries
**Target Users**: Self-hosted media enthusiasts who want actionable insights about their libraries
**Core Value Prop**: "See what's wrong with your library and fix it"

## Workflow

### Step 1: Understand Current State

Read these files to understand what exists:
- `PRD.md` - Current and planned features
- `CLAUDE.md` - Project context and original script features
- `../jellyfin_monitor.py` - Original script (source of truth for domain logic)

Current features from original script:
1. Old/Unwatched content detection
2. Large movies identification
3. Language issues (missing audio/subtitles)
4. Jellyseerr unavailable requests
5. Recently available content

### Step 2: Research Competitor Landscape

Consider what similar tools offer:

| Tool | Focus | Notable Features |
|------|-------|------------------|
| **Tautulli** | Plex analytics | Watch history, user stats, notifications, newsletters |
| **Overseerr/Jellyseerr** | Request management | Request flow, availability tracking, notifications |
| **Organizr** | Dashboard | Unified interface, tabs, user management |
| **Radarr/Sonarr** | Content acquisition | Quality profiles, upgrade detection, calendar |
| **Maintainerr** | Plex cleanup | Rule-based deletion, collections, scheduling |
| **JBOPS** | Plex scripts | Killstream, notify, playlist management |

### Step 3: Identify Pain Points

Common media server owner frustrations:

**Library Management**
- "My library is 10TB but I don't know what to delete"
- "I have duplicates but finding them is tedious"
- "Some content has wrong metadata/posters"
- "I don't know which shows are incomplete"

**Quality Control**
- "I want to upgrade old 720p content to 4K"
- "Some files have hardcoded subtitles I don't want"
- "Audio is sometimes out of sync"
- "Some content is corrupted but plays fine until that scene"

**User Management**
- "I don't know what my users are actually watching"
- "I want to know if users stopped watching something"
- "Managing requests from multiple users is chaos"

**Maintenance**
- "I forget to check for issues until something breaks"
- "I want automated cleanup but I'm scared of deleting wrong things"
- "My library grows faster than my storage"

### Step 4: Generate Feature Ideas

For each idea, consider:
- **Problem**: What pain point does this solve?
- **Value**: Why would users want this?
- **Scope**: Is this MVP-sized or a multi-month epic?
- **Differentiation**: Does this exist elsewhere? Can we do it better?
- **Fit**: Does this align with the core product vision?

#### Feature Categories to Explore

**1. Library Health**
- Duplicate detection (same content, different files)
- Incomplete series detection (missing episodes/seasons)
- Metadata quality score (missing posters, descriptions, ratings)
- File health check (corrupted files, codec issues)
- Storage trend prediction ("You'll run out in 3 months at this rate")

**2. Quality Management**
- Quality upgrade suggestions (720p → 1080p → 4K available)
- Bitrate analysis (over-compressed files)
- HDR/Dolby Vision detection and grouping
- Subtitle quality check (auto-generated vs proper)

**3. User Insights**
- Watch completion rates (do users finish what they start?)
- Recommendation engine ("Users who watched X also watched Y")
- User activity dashboard (who's watching what, when)
- "Forgotten" content (added but never watched by anyone)

**4. Automation & Scheduling**
- Scheduled cleanup rules (auto-delete after X months unwatched)
- Notification preferences (daily digest, instant alerts)
- Integration with *arr apps (trigger re-download for quality upgrade)
- Webhook support for custom automations

**5. Reporting & Sharing**
- Library newsletter for users ("New this week")
- Storage reports (by genre, year, quality)
- Export to spreadsheet
- Shareable public stats page

**6. Multi-Server**
- Support multiple Jellyfin/Plex instances
- Cross-server duplicate detection
- Unified dashboard for all servers

### Step 5: Prioritize with ICE Framework

Score each feature:
- **Impact** (1-10): How much value does this add?
- **Confidence** (1-10): How sure are we users want this?
- **Ease** (1-10): How easy is it to build?

**ICE Score = (Impact + Confidence + Ease) / 3**

Example scoring:
| Feature | Impact | Confidence | Ease | ICE |
|---------|--------|------------|------|-----|
| Duplicate detection | 9 | 9 | 5 | 7.7 |
| Storage prediction | 7 | 8 | 8 | 7.7 |
| Quality upgrades | 8 | 7 | 4 | 6.3 |
| Newsletter | 6 | 6 | 6 | 6.0 |

### Step 6: Write Feature Proposals

For promising features, write a brief proposal:

```markdown
## Feature: [Name]

**Problem**: [What pain point does this solve?]

**Solution**: [Brief description of the feature]

**User Story**: As a media server owner, I want to [action] so that [benefit].

**Key Functionality**:
- Bullet points of what it does
- Keep it MVP-scoped

**Success Metrics**:
- How do we know if this is valuable?

**Technical Considerations**:
- API requirements
- Performance concerns
- Dependencies

**Effort Estimate**: S/M/L/XL

**Priority Recommendation**: P1/P2/P3
```

### Step 7: Output Recommendations

Present 3-5 feature recommendations:
1. **Quick Win** - High value, low effort
2. **Strategic** - High value, medium effort, differentiating
3. **Exploratory** - Interesting but needs validation

## What NOT to Do

- Do NOT suggest features outside the media management domain
- Do NOT propose features that require significant infrastructure (ML, real-time streaming)
- Do NOT ignore what already exists in PRD.md
- Do NOT suggest features just because competitors have them (must fit this product)
- Do NOT write implementation code

## Example Output

```markdown
# Feature Recommendations

## 1. Quick Win: Storage Trend Prediction

**Problem**: Users don't know when they'll run out of storage until it's urgent.

**Solution**: Show a "Storage Forecast" on the dashboard predicting when storage will be full based on recent growth rate.

**User Story**: As a media server owner, I want to see when I'll run out of storage so I can plan upgrades or cleanups proactively.

**Key Functionality**:
- Calculate growth rate from last 30/60/90 days
- Project "days until full" at current rate
- Show on dashboard as a simple metric
- Optional: alert when <30 days remaining

**Effort**: Small (backend calculation + 1 dashboard card)

**Priority**: P2 - Nice differentiator, low effort

---

## 2. Strategic: Duplicate Detection

**Problem**: Large libraries accumulate duplicates (same movie, different files) wasting storage.

**Solution**: Detect potential duplicates by matching TMDB ID, title similarity, or file hash and let users decide which to keep.

**User Story**: As a media server owner, I want to find duplicate content so I can reclaim storage without manual searching.

**Key Functionality**:
- Match by TMDB/TVDB ID (exact duplicates)
- Fuzzy match by title (potential duplicates)
- Show comparison: file size, quality, codecs
- "Keep best quality" suggestion
- Bulk delete option

**Effort**: Medium (new sync logic + new page)

**Priority**: P1 - High user value, storage is always a pain point

---

## 3. Exploratory: Watch Completion Insights

**Problem**: Users add content but don't know if anyone actually finishes watching it.

**Solution**: Track watch completion rates to identify content that gets abandoned.

**Needs Validation**: Do users actually want this? Could feel surveillance-y for shared servers.

**Effort**: Medium (requires watch history analysis)

**Priority**: P3 - Validate demand first
```
