---
name: review-suggestions
description: Interactive triage of SUGGESTIONS.md items - remove, promote to PRD, or skip each suggestion.
---

# Review Suggestions

## Overview

Interactively review each item in SUGGESTIONS.md and decide its fate:
- **Remove** - Not needed, delete from file
- **Promote to PRD** - Refine into user story using `/prd` skill, then remove from SUGGESTIONS.md
- **Skip** - Leave for future review

## Workflow

### Step 1: Read SUGGESTIONS.md

Read the current SUGGESTIONS.md file to get all items.

### Step 2: Process Each Item

For each suggestion item (lines starting with `- [P1]`, `- [P2]`, or `- [P3]`):

1. Display the item with its priority and full description
2. Use AskUserQuestion to present three options:

```
Question: "What should we do with this suggestion?"
Header: "Triage"
Options:
  - "Remove" - Delete this suggestion (not needed or already done)
  - "Promote to PRD" - Create a user story for this item
  - "Skip" - Leave it in SUGGESTIONS.md for now
```

3. Based on the answer:
   - **Remove**: Edit SUGGESTIONS.md to delete the line
   - **Promote to PRD**:
     - **FIRST**: Edit SUGGESTIONS.md to delete the line (do this BEFORE invoking /prd to avoid losing track)
     - **THEN**: Invoke the `/prd` skill with the suggestion as context
   - **Skip**: Continue to next item without changes

### Step 3: Summary

After processing all items, display a summary:
- Number of items removed
- Number of items promoted to PRD
- Number of items skipped
- Remaining items in SUGGESTIONS.md

## Item Format Reference

SUGGESTIONS.md items follow this format:
```markdown
- [P1] Short title - Detailed description
- [P2] Short title - Detailed description
- [P3] Short title - Detailed description
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

**Claude**: Invoking `/prd` skill to create user story for rate limiting...

*After PRD update completes*

Removed from SUGGESTIONS.md. Moving to next item...

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
- Removed: 2 items
- Promoted to PRD: 3 items
- Skipped: 3 items
- Remaining in SUGGESTIONS.md: 3 items

## Notes

- Process items in the order they appear in the file
- When promoting to PRD, pass the full suggestion text as context to `/prd`
- Always confirm successful PRD creation before removing from SUGGESTIONS.md
- If user cancels mid-review, preserve all unprocessed items
