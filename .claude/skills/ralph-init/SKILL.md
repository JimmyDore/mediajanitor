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

## Workflow

### Step 1: Read PRD.md

Parse the PRD.md file to extract:
- Project name
- User stories with IDs, titles, descriptions
- Acceptance criteria for each story

### Step 2: Validate Stories

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

### Step 3: Generate prd.json

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
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

### Step 4: Filter to Incomplete Stories Only

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
| `priority` | Execution order (1 = first) |
| `passes` | Completion status (false until done) |
| `notes` | Implementation notes (filled by Ralph) |

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
### US-2.1: Configure Jellyfin Connection
**As a** user
**I want** to input my Jellyfin API key and URL
**So that** the app can fetch my library data

**Acceptance Criteria:**
- [x] Form accepts server URL and API key
- [x] Connection validated before saving
- [x] Credentials stored encrypted in database
- [x] Success/error feedback shown to user
```

## Example Output (prd.json)

Only incomplete stories are included:

```json
{
  "project": "Plex Dashboard",
  "branchName": "ralph/jellyfin-config",
  "userStories": [
    {
      "id": "US-2.2",
      "title": "Configure Jellyseerr Connection",
      "story": "As a user, I want to input my Jellyseerr API key and URL, so that the app can fetch my requests data",
      "acceptanceCriteria": [
        "Settings page shows Jellyseerr section below Jellyfin",
        "Form fields for Jellyseerr URL and API key",
        "Backend validates connection by calling Jellyseerr API",
        "Toast notification shows success or error",
        "Typecheck passes",
        "Unit tests pass",
        "Verify in browser using browser tools"
      ],
      "priority": 22,
      "passes": false,
      "notes": ""
    }
  ]
}
```

Note: If US-2.1 was already marked `[x]` in PRD.md, it would not appear in prd.json.

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
3. Run `./ralph-once.sh` or `./afk-ralph.sh` to start autonomous execution

Query status anytime:
```bash
cat prd.json | jq '.userStories[] | {id, title, passes}'
```
