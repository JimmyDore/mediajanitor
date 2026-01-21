---
name: qa-ux
description: UX-focused QA review using Puppeteer for visual inspection. Adds findings to SUGGESTIONS.md. Does NOT implement changes.
---

# UX QA Skill

Review the application's user experience using browser tools and add findings to SUGGESTIONS.md.

**Note:** This skill is for **observation only**. Use `/ux-expert` when you want to actually redesign and implement changes.

## Scope

This skill focuses on **user experience concerns only**:
- Navigation flow
- Visual consistency
- Loading & error states
- Feedback mechanisms
- Information architecture

## Workflow

### Step 1: Start the Application

Ensure Docker is running:
```bash
docker-compose ps
```

If not running, start it:
```bash
docker-compose up -d
```

### Step 2: Navigate Through the App

Use Puppeteer to visit each page systematically:

1. **Public pages**: `/login`, `/register`
2. **Authenticated pages**: `/dashboard`, `/issues`, `/unavailable`, `/recently-available`, `/whitelist`, `/settings`

For each page, take a screenshot and check:

| Area | What to Check |
|------|---------------|
| **Navigation** | Can users reach all pages? Is current page indicated? |
| **Visual Consistency** | Same colors, spacing, typography across pages? |
| **Loading States** | Skeleton loaders or spinners during data fetch? |
| **Error States** | Clear error messages when things fail? |
| **Empty States** | Helpful message when no data? |
| **Feedback** | Toast notifications for actions? Button loading states? |

### Step 3: Check Interactive Elements

For forms and actions:
- Submit with invalid data - are errors clear?
- Submit with valid data - is success feedback shown?
- Check button states (disabled while loading?)
- Check modal/dialog behavior (escape to close? click outside?)

### Step 4: Check Responsive Behavior

Resize viewport to check:
- Mobile (375px width)
- Tablet (768px width)
- Desktop (1280px width)

Look for:
- Overlapping elements
- Truncated text
- Unusable buttons/inputs
- Hidden navigation

### Step 5: Check Console for Errors

Look for:
- JavaScript errors
- Failed network requests
- React/Svelte warnings

### Step 6: Update SUGGESTIONS.md

Add findings to the **UI/UX** section with priority markers:

```markdown
## UI/UX

- [P2] Settings page shows no loading indicator during save
- [P2] Issues table doesn't indicate current sort column
- [P3] Dashboard cards could use hover effect for clickability
```

Priority guide:
- **[P1]** - Broken flow, users can't complete task
- **[P2]** - Confusing or inconsistent, should fix
- **[P3]** - Polish improvement

## What NOT to Do

- Do NOT implement fixes (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md
- Do NOT check non-UX concerns (security, performance, etc.)
- Do NOT modify any code
- Do NOT use this skill to redesign - use `/ux-expert` for that

## Example Findings

```markdown
## UI/UX

### Navigation
- [P2] No breadcrumbs on detail pages - users lose context

### Consistency
- [P2] Inconsistent save patterns: Connections need explicit Save, Theme auto-saves on click
- [P3] Dark mode contrast issues: Edit buttons blend into background

### Feedback
- [P2] No confirmation dialog before deleting whitelist items
- [P3] Toast notifications not dismissible by clicking

### Responsive
- [P2] Issues table horizontal scroll needed on mobile - consider card layout
```
