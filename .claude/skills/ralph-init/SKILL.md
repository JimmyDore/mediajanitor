---
name: ralph-init
description: Convert PRD.md to machine-readable prd.json for Ralph execution
---

# Ralph Init Skill

Convert PRD.md to prd.json for machine-readable task tracking.

## Purpose

Transform human-readable PRD into structured JSON that Ralph can:
- Query for next incomplete story
- Track completion status
- Detect when all stories are done
- **Understand full context without needing to read PRD.md again**

## Workflow

### Step 1: Read PRD.md

Parse the PRD.md file to extract:
- Project name
- **Epic-level context** (Overview, Technical Considerations, Goals, Non-Goals)
- User stories with IDs, titles, descriptions
- Acceptance criteria for each story

### Step 2: Extract Epic Context (CRITICAL)

**For each Epic, capture contextual information that Ralph needs:**

1. **Technical Considerations** - API endpoints, data structures, implementation hints
2. **Overview** - What problem this epic solves
3. **Goals/Non-Goals** - Scope boundaries
4. **Related information** - References to existing code patterns, external APIs, etc.

This context is often buried between the Epic header and the first user story. **Do NOT skip it.**

Example from PRD.md:
```markdown
## Epic 48: Ultra.cc Storage Monitoring

### Technical Considerations

- Ultra API endpoint: `{base_url}/total-stats` with Bearer token auth
- Response includes: `service_stats_info.free_storage_gb` and `service_stats_info.traffic_available_percentage`
- Store encrypted auth token like existing Jellyfin/Jellyseerr keys
```

This context MUST be captured in the `context` field of related stories.

### Step 3: Validate Stories

Before generating JSON, validate each story:

**Size Check:**
- Story should be completable in one session
- If too big, STOP and ask user to split it first

**Acceptance Criteria Check:**
- Must have "Typecheck passes"
- UI stories must have "Verify in browser"
- All criteria must be specific and verifiable

**Dependency Check:**
- Stories ordered by dependency (data → backend → UI)
- No story depends on a later story

### Step 4: Generate prd.json

Create `prd.json` with this structure:

```json
{
  "project": "Project Name",
  "branchName": "ralph/feature-name",
  "userStories": [
    {
      "id": "US-X.1",
      "title": "Story Title",
      "story": "As a [user], I want [capability], so that [benefit]",
      "acceptanceCriteria": [
        "Criterion 1",
        "Criterion 2",
        "Typecheck passes",
        "Unit tests pass"
      ],
      "context": "Epic context here. Technical notes: API uses Bearer auth at /total-stats endpoint. Response has service_stats_info.free_storage_gb field. Follow existing pattern from Jellyfin settings encryption.",
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

### Step 5: Filter to Incomplete Stories Only

**Only include stories where the checkbox is unchecked `[ ]` in PRD.md.**

Stories marked with `[x]` are excluded from prd.json entirely. This keeps the file small and focused on work that needs to be done.

Benefits:
- Smaller prd.json = less context for Ralph to process
- No stale data about completed work
- Re-running `/ralph-init` automatically removes newly completed stories

---

## Field Definitions

| Field | Description |
|-------|-------------|
| `project` | Project name from PRD header |
| `branchName` | Git branch for this feature (ralph/kebab-case) |
| `id` | Story identifier (US-1.1, US-2.3, etc.) |
| `title` | Short story title |
| `story` | Full "As a... I want... So that..." |
| `acceptanceCriteria` | Array of verifiable criteria |
| `context` | **Epic-level context: technical notes, API details, implementation hints, references to existing patterns** |
| `priority` | Execution order (1 = first) |
| `passes` | Completion status (false until done) |
| `notes` | Implementation notes (filled by Ralph after completion) |

---

## Priority Assignment

Assign priorities based on dependencies:

1. **Database/Model changes** (priority 1-10)
2. **Backend services/APIs** (priority 11-50)
3. **Frontend pages/components** (priority 51-90)
4. **Integration/polish** (priority 91-100)

Example:
- US-1.1: User Model → priority 1
- US-1.2: Register API → priority 10
- US-1.3: Register Page → priority 50
- US-1.4: Login API → priority 11
- US-1.5: Login Page → priority 51

---

## Validation Errors

Stop and report if:

1. **Missing typecheck**: Story lacks "Typecheck passes" in AC
2. **Missing browser verify**: UI story lacks browser verification
3. **Vague criteria**: AC contains "works correctly", "good UX", etc.
4. **Story too big**: Story appears to need multiple sessions
5. **Circular dependency**: Story depends on later story

---

## Example Input (PRD.md)

```markdown
## Epic 48: Ultra.cc Storage & Traffic Monitoring

### Overview

Integrate Ultra.cc API to monitor seedbox storage and traffic usage...

### Technical Considerations

- Ultra API endpoint: `{base_url}/total-stats` with Bearer token auth
- Response includes: `service_stats_info.free_storage_gb` and `service_stats_info.traffic_available_percentage`
- Store encrypted auth token like existing Jellyfin/Jellyseerr keys
- Stats should be cached in database (fetched during sync, not on every page load)

---

### US-48.1: Ultra API Settings - Backend

**As a** user
**I want** to configure my Ultra.cc API credentials
**So that** the app can fetch my storage and traffic stats

**Acceptance Criteria:**

- [ ] Add `ultra_api_url` and `ultra_api_key_encrypted` columns to UserSettings model
- [ ] Create Alembic migration for new columns
- [ ] PATCH `/api/settings` accepts `ultra_api_url` and `ultra_api_key` fields
- [ ] Ultra API key is encrypted before storage (like Jellyfin/Jellyseerr keys)
- [ ] GET `/api/settings` returns `ultra_api_configured: bool` (not the actual key)
- [ ] Typecheck passes
- [ ] Unit tests pass
```

## Example Output (prd.json)

**Note the `context` field capturing Epic-level information:**

```json
{
  "project": "Media Janitor",
  "branchName": "ralph/ultra-monitoring",
  "userStories": [
    {
      "id": "US-48.1",
      "title": "Ultra API Settings - Backend",
      "story": "As a user, I want to configure my Ultra.cc API credentials, so that the app can fetch my storage and traffic stats",
      "acceptanceCriteria": [
        "Add `ultra_api_url` and `ultra_api_key_encrypted` columns to UserSettings model",
        "Create Alembic migration for new columns",
        "PATCH `/api/settings` accepts `ultra_api_url` and `ultra_api_key` fields",
        "Ultra API key is encrypted before storage (like Jellyfin/Jellyseerr keys)",
        "GET `/api/settings` returns `ultra_api_configured: bool` (not the actual key)",
        "Typecheck passes",
        "Unit tests pass"
      ],
      "context": "Ultra.cc seedbox monitoring integration. API endpoint: {base_url}/total-stats with Bearer token auth. Response fields: service_stats_info.free_storage_gb, service_stats_info.traffic_available_percentage. Follow existing pattern: encrypt API key like Jellyfin/Jellyseerr keys in UserSettings. Stats are cached in DB, fetched during sync (not on page load).",
      "priority": 13,
      "passes": false,
      "notes": ""
    }
  ]
}
```

**Key: The `context` field includes:**
- What the epic is about (seedbox monitoring)
- API details (endpoint path, auth method, response structure)
- Implementation hints (follow existing encryption pattern)
- Architecture notes (cached in DB, fetched during sync)

This context is ESSENTIAL for Ralph to implement correctly without needing to re-read PRD.md.

---

## What to Include in the `context` Field

**ALWAYS extract and include these when present in the PRD:**

| Source Section | What to Extract |
|----------------|-----------------|
| Technical Considerations | API endpoints, auth methods, response schemas, data structures |
| Overview | Problem being solved, why this feature exists |
| Goals | What's in scope |
| Non-Goals | What's explicitly out of scope (prevents over-engineering) |
| Related stories | Dependencies on other stories or existing code |
| Code references | Files, functions, patterns to follow (e.g., "like Jellyfin settings encryption") |

**Format as a concise paragraph, not bullet points.** Keep it under ~500 characters but include ALL critical technical details.

**Bad context (too vague):**
```json
"context": "Add Ultra.cc integration to settings."
```

**Good context (specific and actionable):**
```json
"context": "Ultra.cc seedbox monitoring. API: {base_url}/total-stats with Bearer auth. Response: service_stats_info.free_storage_gb (float), traffic_available_percentage (float). Encrypt API key like Jellyfin. Cache stats in UserSettings, fetch during sync. NON-GOAL: No Slack/email notifications, no historical tracking."
```

**Multiple stories in same epic share similar context** - copy relevant parts to each story so Ralph doesn't need to cross-reference.

---

### When All Stories Are Complete

If all stories in PRD.md are checked `[x]`, prd.json will have an empty `userStories` array:

```json
{
  "project": "Plex Dashboard",
  "branchName": "main",
  "userStories": []
}
```

This signals to Ralph that there's no work to do. Add new stories to PRD.md and re-run `/ralph-init` to continue.

---

## Usage

After running this skill:

1. Review the generated `prd.json`
2. Verify priorities make sense
3. Run `task ralph:once` or `task ralph:run -- N` to start autonomous execution

Query status anytime:
```bash
cat prd.json | jq '.userStories[] | {id, title, passes}'
```

---

## Self-Validation Checklist

Before finalizing prd.json, verify:

- [ ] **Every story has a non-empty `context` field** (unless the PRD truly has no technical context)
- [ ] **API details are captured** - endpoints, auth methods, request/response formats
- [ ] **Implementation hints are captured** - "follow existing pattern", "like X feature"
- [ ] **Non-goals are mentioned** - prevents over-engineering
- [ ] **Acceptance criteria are complete** - copied exactly, including checkboxes removed
- [ ] **Only unchecked `[ ]` stories are included** - no completed stories

**Common mistakes to avoid:**

1. **Empty context field** - Epic has "Technical Considerations" but context is `""`
2. **Vague context** - "Integrate Ultra API" instead of specific endpoint/auth details
3. **Missing response schema** - API endpoints listed but response fields not captured
4. **Ignoring Non-Goals** - These scope boundaries prevent wasted effort
