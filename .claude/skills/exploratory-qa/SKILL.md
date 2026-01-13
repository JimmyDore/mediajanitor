---
name: exploratory-qa
description: Periodic review of application for cross-cutting concerns and SUGGESTIONS.md updates
---

# Exploratory QA Skill

Perform a periodic review of the application and update SUGGESTIONS.md with observations.

## Purpose

This is NOT part of individual story implementation. It's a broader review that runs periodically (e.g., every 3 Ralph iterations) to catch cross-cutting concerns that aren't visible when focused on a single story.

## Workflow

### Step 1: Review Implemented Features

Look at what has been built recently:
- Read `progress.txt` for recently completed stories
- Review the current state of the codebase

### Step 2: Check Cross-Cutting Concerns

Look for gaps in these areas:

| Area | What to Check |
|------|---------------|
| **Navigation** | Can users reach all pages? Is there a consistent nav pattern? |
| **Error Handling** | Are API errors shown to users? Are there loading states? |
| **Auth Guards** | Are protected routes actually protected? |
| **UI Coherence** | Consistent styling, spacing, colors across pages? |
| **Security** | XSS risks, exposed secrets, missing input validation? |
| **Performance** | N+1 queries, unnecessary re-renders, large bundles? |
| **Accessibility** | Keyboard navigation, screen reader support, color contrast? |

### Step 3: Use Browser Tools (if available)

If browser/puppeteer tools are available:
- Navigate through the app
- Check visual consistency
- Look for console errors
- Verify responsive behavior

### Step 4: Update SUGGESTIONS.md

Add observations with priority markers:

| Priority | Meaning | Example |
|----------|---------|---------|
| **[P1]** | Needs human review for PRD promotion | "Missing logout button - should be a new story" |
| **[P2]** | Should fix soon, but doesn't need PRD | "Toast notifications not dismissible" |
| **[P3]** | Nice to have / future improvement | "Could add dark mode toggle" |

Format for new items:
```markdown
- [P2] **Area**: Description of the issue or improvement
```

### Step 5: Flag P1 Items

If any [P1] items were added, ensure there's a note at the top of SUGGESTIONS.md:
```markdown
## ACTION NEEDED: Review P1 items for PRD promotion
```

---

## What NOT to Do

- Do NOT implement fixes (this is observation only)
- Do NOT add items already in SUGGESTIONS.md
- Do NOT add story-specific issues (those go in the story's notes)
- Do NOT create new files or modify code

---

## Example Output

After running this skill, SUGGESTIONS.md might have new entries like:

```markdown
## ACTION NEEDED: Review P1 items for PRD promotion

### UI/UX
- [P1] **Navigation**: No way to return to dashboard from settings page
- [P2] **Loading states**: Settings page shows no loading indicator during save

### Security
- [P2] **Auth**: Login page doesn't redirect already-authenticated users

### Performance
- [P3] **Bundle**: Consider lazy-loading the charts library
```

---

## Usage

Run manually or as part of `afk-ralph.sh` integration review:
```
/exploratory-qa
```
