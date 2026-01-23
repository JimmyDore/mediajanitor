---
name: morning-routine
description: Daily morning routine to review Ralph progress, archive completed work, triage suggestions, and prepare for the next development session.
---

# Morning Routine Checklist

**IMPORTANT: This skill only displays the checklist. Do NOT execute any steps automatically. The user will run each step manually.**

Reference guide for your daily workflow to review Ralph progress and prepare for the next session.

## The Flow

```
/prd-sync → Review → /prd-archive → /review-suggestions → Manual QA → /ralph-init
```

---

## Step 1: `/prd-sync`

Sync completed stories from `prd.json` back to `PRD.md` checkboxes.

**Skip if**: No stories completed overnight (prd.json has no `passes: true`)

---

## Step 2: Review What Was Done

1. **Read `progress.txt`** - Recent dated entries show what changed
2. **Check `PRD.md`** - Which stories are now `[x]` complete
3. **Manual QA** (optional) - Test completed features in the app

---

## Step 3: `/prd-archive`

Move completed epics to `ARCHIVED_PRD.md` and old progress logs to `ARCHIVED_PROGRESS.txt`.

**Skip if**: No fully completed epics (all stories in an epic must be `[x]`)

---

## Step 4: `/review-suggestions`

Interactively triage each item in `SUGGESTIONS.md`:
- **Remove** - Not needed or already done
- **Promote to PRD** - Create user story via `/prd`
- **Skip** - Leave for later

**Skip if**: `SUGGESTIONS.md` is empty

---

## Step 5: Manual QA / Handle Promoted Items

- For promoted items: `/prd` creates proper user stories
- For quick fixes: Fix directly and commit

**Skip if**: Nothing promoted in Step 4

---

## Step 6: `/ralph-init`

Generate fresh `prd.json` with only incomplete `[ ]` stories.

**Skip if**: Not running Ralph today

---

## After Routine

```bash
git add PRD.md prd.json SUGGESTIONS.md progress.txt
git commit -m "chore: morning routine sync and cleanup"
```

Then either:
- `task ralph:once` - Human-in-the-loop
- `task ralph:run -- N` - Autonomous N iterations
- Manual work on specific stories
