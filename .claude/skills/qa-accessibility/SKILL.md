---
name: qa-accessibility
description: Accessibility-focused QA review using Puppeteer for testing. Adds findings to SUGGESTIONS.md.
---

# Accessibility QA Skill

Review the application's accessibility using browser tools and code inspection. Add findings to SUGGESTIONS.md.

## Scope

This skill focuses on **accessibility concerns only**:
- Keyboard navigation
- Screen reader support (ARIA)
- Color contrast
- Focus management
- Semantic HTML

## Workflow

### Step 1: Start the Application

Ensure Docker is running:
```bash
docker-compose ps
```

### Step 2: Keyboard Navigation Test

Use Puppeteer to test keyboard-only navigation:

1. Navigate to each page
2. Press Tab repeatedly - check:
   - Can you reach all interactive elements?
   - Is focus order logical (top-to-bottom, left-to-right)?
   - Is focus visible (outline or highlight)?
   - Can you skip to main content?

3. Test specific interactions:
   - Enter/Space to activate buttons
   - Escape to close modals
   - Arrow keys in dropdowns/menus

### Step 3: Screen Reader Audit (Code Review)

Check the codebase for ARIA issues:

| Element | Required |
|---------|----------|
| **Images** | `alt` attribute (empty for decorative) |
| **Buttons** | Text content or `aria-label` |
| **Icons** | `aria-hidden="true"` if decorative, `aria-label` if meaningful |
| **Forms** | `<label>` associated with inputs, or `aria-label` |
| **Modals** | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` |
| **Live regions** | `aria-live` for dynamic content (toasts, errors) |
| **Landmarks** | `<main>`, `<nav>`, `<header>`, `<footer>` |

Files to check:
- `frontend/src/routes/**/*.svelte` - All pages
- `frontend/src/lib/components/**/*.svelte` - Reusable components

### Step 4: Color Contrast Check

Use Puppeteer to screenshot and visually inspect:

| Element | Minimum Contrast |
|---------|------------------|
| **Normal text** | 4.5:1 |
| **Large text (18px+)** | 3:1 |
| **UI components** | 3:1 |

Common issues:
- Light gray text on white background
- Placeholder text too light
- Disabled state indistinguishable
- Links not distinguishable from text (color alone)

### Step 5: Focus Management

Check these scenarios:
- After modal opens, focus moves to modal
- After modal closes, focus returns to trigger
- After form submit, focus moves to result/error
- After page navigation, focus moves to main content

### Step 6: Semantic HTML Check

Look for:
- Heading hierarchy (`h1` → `h2` → `h3`, no skipping)
- Lists using `<ul>/<ol>/<li>` not divs
- Tables using `<table>/<th>/<td>` with headers
- Buttons vs links (action = button, navigation = link)

### Step 7: Update SUGGESTIONS.md

Add findings to the **Accessibility** section:

```markdown
## Accessibility

- [P1] Modal doesn't trap focus - Tab escapes to background
- [P2] Icon buttons missing aria-label
- [P3] Skip to main content link would help keyboard users
```

Priority guide:
- **[P1]** - Blocks users with disabilities
- **[P2]** - Degrades experience significantly
- **[P3]** - Best practice improvement

## What NOT to Do

- Do NOT implement fixes (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md (check both active AND struck-through `~~items~~`)
- Do NOT check non-accessibility concerns
- Do NOT modify any code
- Do NOT add positive observations (e.g., "good implementation", "works correctly", "no issues found") - SUGGESTIONS.md tracks only items that need improvement

## Example Findings

```markdown
## Accessibility

### Keyboard Navigation
- [P1] Duration picker modal: Tab key escapes modal, should trap focus
- [P2] Dropdown menus not navigable with arrow keys

### Screen Reader
- [P2] Delete buttons only have trash icon - need aria-label="Delete {item name}"
- [P2] Loading spinners missing aria-live announcement
- [P3] Page titles don't update on navigation

### Color Contrast
- [P2] Muted text (#6b7280) on light gray background fails 4.5:1
- [P3] Focus ring too subtle in dark mode

### Semantic HTML
- [P2] Stats cards use divs - should be `<article>` with headings
- [P3] Footer links should be in `<nav>` landmark
```
