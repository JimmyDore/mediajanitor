---
name: prd-sync
description: Sync completion status from prd.json back to PRD.md checkboxes
---

# PRD Sync Skill

Sync completion status from prd.json back to PRD.md, keeping the human-readable document up-to-date.

## Purpose

After Ralph completes stories (updating `passes: true` and `notes` in prd.json), this skill syncs those changes back to PRD.md so the human-readable document reflects current progress.

**Note:** Since `/ralph-init` only includes incomplete stories in prd.json, this skill syncs Ralph's completions, then you can re-run `/ralph-init` to remove completed stories from prd.json.

## Workflow with /ralph-init

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ /ralph-init │───▶│    Ralph    │───▶│  /prd-sync  │───▶│ /ralph-init │
│ (incomplete │    │ (completes  │    │ (sync to    │    │ (regenerate │
│  stories)   │    │  stories)   │    │  PRD.md)    │    │  clean)     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

1. `/ralph-init` creates prd.json with only `[ ]` (incomplete) stories
2. Ralph completes stories, sets `passes: true`, adds notes
3. `/prd-sync` syncs completed stories to PRD.md (marks `[x]`)
4. `/ralph-init` regenerates prd.json without completed stories

## Workflow

### Step 1: Read Both Files

1. Read `prd.json` and parse the JSON
2. Read `PRD.md` to understand current state
3. Build a map of story ID → prd.json data

### Step 2: Identify Changes

Since prd.json only contains stories that were incomplete when `/ralph-init` ran, we're looking for:

| prd.json | PRD.md State | Action |
|----------|--------------|--------|
| `passes: true` | `[ ]` | Update to `[x]` (Ralph completed it) |
| `passes: false` | `[ ]` | No change needed |
| `notes` present | No note | Append note |

List all stories that need updating before making changes.

### Step 3: Update PRD.md

For each story that needs updating:

1. **Find the story section** by ID (e.g., `#### US-7.1:` or `### US-7.1:`)
2. **Update checkboxes**:
   - If `passes: true` → Change all `[ ]` to `[x]` in that story's Acceptance Criteria
   - If `passes: false` → Change all `[x]` to `[ ]` in that story's Acceptance Criteria
3. **Add notes** (if present in prd.json and not already in PRD.md):
   - Append after the last acceptance criterion: `**Note:** {notes}`

### Step 4: Show Summary

Report what was changed:
```
Updated 3 stories in PRD.md:
- US-7.1: Marked complete (was incomplete)
- US-7.2: Marked complete (was incomplete)
- US-D.1: Added note
```

### Step 5: Save

Write the updated PRD.md file.

---

## Field Mapping

| prd.json | PRD.md |
|----------|--------|
| `passes: true` | All AC checkboxes → `[x]` |
| `notes: "text"` | Appended as `**Note:** text` |

Note: `passes: false` stories don't need updating since they already have `[ ]` in PRD.md.

---

## Example

### Before (PRD.md)
```markdown
#### US-7.1: Sync Status Endpoint
**Acceptance Criteria:**
- [ ] Endpoint returns sync status
- [ ] Shows last sync time
- [ ] Typecheck passes
```

### prd.json
```json
{
  "id": "US-7.1",
  "passes": true,
  "notes": "Verified 2026-01-13"
}
```

### After (PRD.md)
```markdown
#### US-7.1: Sync Status Endpoint
**Acceptance Criteria:**
- [x] Endpoint returns sync status
- [x] Shows last sync time
- [x] Typecheck passes

**Note:** Verified 2026-01-13
```

---

## Edge Cases

1. **Story not found in PRD.md**: Log warning, skip that story
2. **Note already exists**: Don't duplicate - only append if no `**Note:**` line exists
3. **Multiple checkbox formats**: Handle both `- [ ]` and `- [x]` patterns
4. **Nested stories**: Stories may be `####` (Epic structure) or `###` (flat structure)

---

## Do NOT

- Do NOT modify prd.json (this is a one-way sync: prd.json → PRD.md)
- Do NOT reorder or restructure PRD.md sections
- Do NOT change story titles, descriptions, or acceptance criteria text
- Do NOT add new stories to PRD.md (only update existing ones)
- Do NOT commit automatically (let user review changes first)

---

## Usage

After Ralph has completed stories:

```bash
# Check if any stories were completed
cat prd.json | jq '.userStories[] | select(.passes == true) | {id, title}'

# Run this skill to sync to PRD.md
/prd-sync
```

Then review, commit, and regenerate prd.json:
```bash
# Review changes
git diff PRD.md

# Commit the sync
git add PRD.md && git commit -m "docs: sync PRD.md from prd.json"

# Regenerate prd.json to remove completed stories
/ralph-init
```

**Tip:** If prd.json is empty after `/ralph-init`, all stories are complete. Add new stories to PRD.md to continue.
