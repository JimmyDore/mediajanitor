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

### Step 4: Mark Completed Stories

Check PRD.md for already completed stories (marked with `[x]`).
Set `passes: true` for those stories in the JSON.

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

```json
{
  "project": "Plex Dashboard",
  "branchName": "ralph/jellyfin-config",
  "userStories": [
    {
      "id": "US-2.1",
      "title": "Configure Jellyfin Connection",
      "story": "As a user, I want to input my Jellyfin API key and URL, so that the app can fetch my library data",
      "acceptanceCriteria": [
        "Form accepts server URL and API key",
        "Connection validated before saving",
        "Credentials stored encrypted in database",
        "Success/error feedback shown to user",
        "Typecheck passes",
        "Unit tests pass",
        "Verify in browser using browser tools"
      ],
      "priority": 20,
      "passes": true,
      "notes": "Completed 2026-01-12"
    }
  ]
}
```

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
