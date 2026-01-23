---
name: review-suggestions
description: Interactive triage of SUGGESTIONS.md items - drop, promote to PRD, or skip each suggestion.
---

# Review Suggestions

## Overview

Interactively review each item in SUGGESTIONS.md and decide its fate:
- **Drop** - Not needed; strike through with `~~` to prevent QA skills from re-adding it
- **Promote to PRD** - Refine into user story using `/prd` skill, then delete from SUGGESTIONS.md
- **Skip** - Leave for future review

**Why strikethrough for dropped items?** QA skills scan SUGGESTIONS.md before adding new findings. Struck-through items tell them "this was already reviewed and rejected" so they won't re-add the same suggestion.

**Why delete promoted items?** Once an item is in PRD.md, it's being tracked and worked on. No need to keep it in SUGGESTIONS.md - QA won't re-add issues that are actively being addressed.

## Workflow

### Step 1: Read SUGGESTIONS.md

Read the current SUGGESTIONS.md file to get all items.

### Step 2: Process Each Item

For each suggestion item (lines starting with `- [P1]`, `- [P2]`, or `- [P3]`):

1. Display the item with its priority and full description
2. **Skip struck-through items** - Lines starting with `~~` have already been triaged
3. Use AskUserQuestion to present three options:

```
Question: "What should we do with this suggestion?"
Header: "Triage"
Options:
  - "Drop" - Strike through (not needed or already done)
  - "Promote to PRD" - Create a user story for this item
  - "Skip" - Leave it in SUGGESTIONS.md for now
```

4. Based on the answer:
   - **Drop**: Edit SUGGESTIONS.md to wrap the line in `~~strikethrough~~`
   - **Promote to PRD**:
     - **FIRST**: Note down the full suggestion text
     - **THEN**: Edit SUGGESTIONS.md to delete the line completely
     - **FINALLY**: Invoke the `/prd` skill with the suggestion as context
   - **Skip**: Continue to next item without changes

### Step 3: Summary

After processing all items, display a summary:
- Number of items dropped (struck through)
- Number of items promoted to PRD (deleted)
- Number of items skipped (unchanged)
- Remaining active items in SUGGESTIONS.md

## Item Format Reference

SUGGESTIONS.md items follow this format:
```markdown
- [P1] Short title - Detailed description
- [P2] Short title - Detailed description
- [P3] Short title - Detailed description
```

Struck-through items (dropped - already reviewed and rejected):
```markdown
- ~~[P2] Already reviewed - This was dropped~~
```

Priority levels:
- **P1** - Critical, should be reviewed for PRD promotion
- **P2** - Should do, important but not critical
- **P3** - Nice to have, low priority

## Example Session

**User**: `/review-suggestions`

**Claude**: Reading SUGGESTIONS.md...

Found 8 suggestions to review.

---

**Item 1/8** [P2] Add rate limiting to auth endpoints

> Add rate limiting to auth endpoints (login, register) - vulnerable to brute force attacks

*Asks user: Remove / Promote to PRD / Skip*

**User selects**: Promote to PRD

**Claude**: Removing from SUGGESTIONS.md and invoking `/prd` skill...

*After PRD update completes*

Done. Moving to next item...

---

**Item 2/8** [P3] Add breadcrumb navigation

> Add breadcrumb navigation for multi-page flows

*Asks user: Remove / Promote to PRD / Skip*

**User selects**: Skip

**Claude**: Keeping in SUGGESTIONS.md. Moving to next item...

---

*...continues for all items...*

---

**Summary**:
- Dropped: 2 items (struck through)
- Promoted to PRD: 3 items (deleted, now in PRD.md)
- Skipped: 3 items (still active)

## Notes

- Process items in the order they appear in the file
- Skip lines that are already struck through (`~~...~~`) - they were previously dropped
- When promoting to PRD, pass the full suggestion text as context to `/prd`
- If user cancels mid-review, preserve all unprocessed items
- Periodically clean up old struck-through items (e.g., after a few months) by deleting them entirely
