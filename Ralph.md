# How I Use Ralph to Build a Full SaaS with Claude Code

> **Ralph is a technique for running AI coding agents in a loop.** You run the same prompt repeatedly. The AI picks its own tasks from a PRD. It commits after each feature. You come back later to working code.
>
> — [AI Hero](https://www.aihero.dev/getting-started-with-ralph)

**[Visual flowchart of how Ralph works](https://snarktank.github.io/ralph/)**

Make AI work like a software engineer: tight feedback loops, automated verification, human oversight where it matters.

---

## Quick Start

```bash
# 1. Write your PRD with user stories
vim PRD.md

# 2. Convert to machine-readable format
/ralph-init

# 3. Run one iteration (human-in-the-loop)
task ralph:once

# 4. Or run autonomously overnight
task ralph:run -- 10
```

**Key files:**
- `PRD.md` → Human-readable user stories with `[ ]` checkboxes
- `prd.json` → Machine-readable version Ralph executes against
- `CLAUDE.md` → Project context and accumulated learnings
- `progress.txt` → Log of completed work

---

## The Problem: Context Windows

LLMs have a fundamental limitation: **context windows**. Long conversations drift, accumulate errors, and eventually break.

**The Ralph solution: Start fresh every time.**

Each iteration:
- Picks ONE small story from prd.json
- Completes it with TDD in a single context window
- Commits and exits

No drift. No accumulated confusion. Progress lives in files (prd.json, CLAUDE.md), not in the AI's "memory."

Ralph = **many small, independent sessions** instead of one long broken one.

## The Other Half: Feedback Loops

LLMs can't "know" if their code works just by writing it. They need **automated verification** at every step.

Ralph's verification stack:
- **Unit tests** - pytest, vitest (must pass before commit)
- **Type checking** - mypy, TypeScript strict mode
- **Docker** - actually run the app, not just tests
- **Browser tools** - Puppeteer screenshots for UI changes
- **Logs** - check for runtime errors

No "I think this works." Only "tests pass, Docker runs, browser shows expected result."

Without feedback loops, AI just generates plausible-looking code. With them, it generates **working** code.

## The Foundation: A Well-Structured PRD

Ralph is only as good as the PRD you give it. Two rules:

**1. Right-sized stories** - Each story must complete in ONE context window.

Too big? Split it:
- Data layer first (models, migrations)
- Backend logic (services, APIs)
- Frontend UI (pages, components)
- Integration (connecting pieces)

**2. Verifiable acceptance criteria** - Not "works correctly" but specific, testable outcomes.

| Bad | Good |
|-----|------|
| "Handles errors properly" | "Returns 401 when token is missing" |
| "Good UX" | "Shows loading spinner while fetching" |
| "Is secure" | "Passwords hashed with bcrypt" |

Every story must include: "Typecheck passes" + "Unit tests pass"

Bad PRD = AI spinning in circles. Good PRD = overnight productivity.

---

## The Daily Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   EVENING              NIGHT                MORNING       DAY   │
│   ────────             ─────                ───────       ───   │
│                                                                 │
│   Start Ralph    →    AI executes    →    Human reviews  →  ↵  │
│   task ralph:run      autonomously        /morning-routine      │
│                       (10+ stories)                             │
│                                                                 │
│   ←─────────────────── repeat daily ────────────────────────────│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| Responsibility | Human | AI (Ralph) |
|---------------|-------|------------|
| Write PRD with acceptance criteria | ✓ | |
| Execute stories with TDD | | ✓ |
| Run automated quality checks | | ✓ |
| Commit code | | ✓ |
| Review completed work | ✓ | |
| Triage suggestions & prioritize bugs | ✓ | |
| Manual browser testing | ✓ | |
| Learn patterns for CLAUDE.md | | ✓ |

**Key insight:** Humans decide *what* and *why*. AI handles *how*.

---

## Morning Routine

After Ralph runs overnight, follow these 6 steps to stay in control. You can run `/morning-routine` to be guided through this process, or follow manually:

```
/prd-sync → Review → /prd-archive → /review-suggestions → Manual QA → /ralph-init
```

### Step 1: `/prd-sync`

Sync completed stories from `prd.json` back to `PRD.md` checkboxes.

*Skip if: No stories completed overnight*

### Step 2: Review What Was Done

```bash
tail -50 progress.txt      # What Ralph completed
git log --oneline -20      # Scan commits for surprises
```

Look for: unusually large commits, odd messages, changes to unexpected files.

### Step 3: `/prd-archive`

Move fully completed epics to `ARCHIVED_PRD.md`.

*Skip if: No fully completed epics*

### Step 4: `/review-suggestions`

Triage each item in `SUGGESTIONS.md`:
- **Remove** - Not needed or already done
- **Promote to PRD** - Real issue, needs a user story
- **Skip** - Valid but save for later

### Step 5: Manual QA / Handle Promoted Items

Actually use the app. Click around. Try edge cases. No automated test replaces human eyes on the product.

For promoted items: `/prd` creates proper user stories.

### Step 6: `/ralph-init`

Generate fresh `prd.json` with only incomplete stories.

*Skip if: Not running Ralph today*

### After Routine

```bash
git add PRD.md prd.json SUGGESTIONS.md progress.txt
git commit -m "chore: morning routine sync and cleanup"
```

---

## What Ralph Does at Night

Once you run `task ralph:run -- N`, Claude autonomously executes this loop:

1. **Picks the next story** where `passes: false` in prd.json
2. **Implements with TDD** - writes failing test first, then code
3. **Runs quality checks** - pytest, mypy, npm test, npm run check
4. **Verifies in Docker** - unit tests alone aren't enough
5. **Verifies in Browser** - using browser tools for UI changes
6. **Updates prd.json** - sets `passes: true`
7. **Commits** with a clear message
8. **Logs learnings** to progress.txt and CLAUDE.md
9. **Loops** until N iterations complete or all stories done

**Periodic QA:** Every 3-5 iterations, Ralph runs `/exploratory-qa` to check for cross-cutting concerns (navigation consistency, error handling, security issues) and logs observations to `SUGGESTIONS.md`.

---

## Why This Works

- **No regressions** - Every change must pass existing tests. AI can't break what already works.
- **Autonomous but bounded** - Clear acceptance criteria prevent tangents.
- **Learning accumulates** - CLAUDE.md grows smarter with each session.
- **Human judgment where needed** - PRD creation, bug triage, and priorities stay human.

---

## Files Reference

| File | Purpose |
|------|---------|
| `PRD.md` | Human-readable user stories with `[ ]` checkboxes |
| `prd.json` | Machine-readable version Ralph executes against |
| `progress.txt` | Log of completed tasks |
| `CLAUDE.md` | Project context and accumulated learnings |
| `SUGGESTIONS.md` | QA observations with [P1]/[P2]/[P3] priorities |
| `prompt.md` | The execution prompt Ralph follows |

---

## Appendix: Skills Reference

### Planning Skills (before Ralph runs)

**`/prd`** - Create well-structured PRDs

Guides you through writing PRDs with right-sized stories and verifiable acceptance criteria. See [The Foundation](#the-foundation-a-well-structured-prd) for sizing rules.

**`/ralph-init`** - PRD to JSON

Converts `PRD.md` to `prd.json`. Validates story sizing and assigns priorities so dependencies run first.

---

### Review Skills (after Ralph runs)

**`/morning-routine`** - Guided morning review

Walks you through all 6 steps of the [Morning Routine](#morning-routine): sync, review, archive, triage, QA, and re-init.

**`/review-suggestions`** - Triage workflow

Interactively review each item in SUGGESTIONS.md:
```
Item 1/8 [P2] Add rate limiting to auth endpoints
> Vulnerable to brute force attacks

What should we do? [Remove / Promote to PRD / Skip]
```

**`/exploratory-qa`** - Periodic QA

Every 3-5 iterations, reviews the app for:
- Navigation consistency
- Error handling patterns
- Auth guards on protected routes
- UI coherence
- Security issues

Updates `SUGGESTIONS.md` with priority markers:
- **[P1]** - Needs human review. Should become PRD story.
- **[P2]** - Should fix soon.
- **[P3]** - Nice to have.

---

### Maintenance Skills (as needed)

**`/prd-sync`** - Keep PRD.md in sync

After Ralph completes stories, syncs `passes: true` back to PRD.md checkboxes.

**`/prd-archive`** - Clean up completed work

Archives completed epics to `ARCHIVED_PRD.md`. Keeps active PRD focused.

---

## About

This is my adaptation of [Ralph](https://www.aihero.dev/getting-started-with-ralph) by AI Hero.

I'm using it with Claude Code to build [Media Janitor](https://mediajanitor.com), a SaaS for Plex/Jellyfin media server owners. So far: 18+ user stories completed autonomously.

It's not perfect, but it's productive. The AI works like an engineer, not a chatbot.
