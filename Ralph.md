# How I Use Ralph to Build a Full SaaS with Claude Code

This is my adaptation of [Ralph](https://www.aihero.dev/getting-started-with-ralph), an iterative AI development technique created by AI Hero. I'm using it with Claude Code to build [Media Janitor](https://mediajanitor.com), a SaaS for Plex/Jellyfin media server owners.

The core idea: **make AI work like a real software engineer**, not just a code generator.

## What Makes a Good Engineer?

Good engineers don't just write code. They work in tight feedback loops:

1. Write a test
2. Run it (it fails)
3. Write the code
4. Run it again (it passes)
5. Commit
6. Repeat

They make small, verifiable changes. They don't break existing functionality. They learn from their mistakes.

**AI without structure produces chaos.** Random code generation, context lost between sessions, no way to verify correctness.

**AI with structure produces predictable results.** Clear tasks, automated verification, accumulated knowledge.

The hardest part? **Writing a good PRD.** If you get that right, execution becomes mechanical.

## The Daily Rhythm

![Ralph Workflow](./ralph-workflow.png)
*Diagram from [snarktank/ralph](https://snarktank.github.io/ralph/)*

My workflow follows a daily cycle with clear human checkpoints:

```
Evening: Start Ralph (./afk-ralph.sh)
         ↓
Night:   Ralph runs autonomously (10+ stories)
         ↓
Morning: Human review ritual
         ↓
Day:     Build next PRD, fix easy bugs
         ↓
Evening: Start Ralph again
```

The key insight: **humans and AI have different strengths**. Let Ralph handle the mechanical execution overnight. Use your human judgment for review, prioritization, and planning.

## Phase 1: Planning (Human)

**1. Write a PRD** (using `/prd` skill)

Break your feature into user stories. Each story must:
- Fit in ONE Claude context window (this is critical)
- Have specific, verifiable acceptance criteria
- Include "Typecheck passes" and "Unit tests pass"
- Include "Verify in browser" for UI changes

**2. Convert to prd.json** (using `/ralph-init` skill)

Transform your human-readable PRD into a machine-readable format that Ralph can query:

```json
{
  "id": "US-001",
  "title": "Add priority field to database",
  "acceptanceCriteria": [
    "Add priority column to tasks table",
    "Generate and run migration",
    "Typecheck passes"
  ],
  "passes": false
}
```

## Phase 2: Execution (Ralph)

Once you run `./ralph-once.sh` (or `./afk-ralph.sh` for autonomous mode), Claude:

1. **Picks the next story** where `passes: false`
2. **Implements with TDD** - writes a failing test first, then the code, and iterate
3. **Runs quality checks** - pytest, mypy, npm test, npm run check
4. **Verifies in Docker** - because unit tests alone aren't enough
5. **Verifies in Browser** - using browser tools
6. **Updates prd.json** - sets `passes: true`
7. **Commits** with a clear message
8. **Logs learnings** to progress.txt
9. **Updates CLAUDE.md** with patterns discovered
10. **Runs /exploratory-qa** periodically for cross-cutting concerns
11. **Loops** until all stories are done

## Phase 3: Review (Human)

This is the critical human checkpoint that keeps you in control.

### The Morning Review Ritual

When Ralph finishes overnight, I follow this sequence:

**1. Check progress.txt**

See what Ralph completed. How many stories? Any failures logged?

```bash
tail -50 progress.txt
```

**2. Run /review-suggestions**

The `/exploratory-qa` skill populates `SUGGESTIONS.md` with observations during Ralph runs. Now I triage them:

- **Remove** - Not needed, already done, or false positive
- **Promote to PRD** - Real issue, needs a proper user story
- **Keep** - Valid but too big for now, save for later

This keeps the suggestions file from growing forever while ensuring nothing important is lost.

**3. Git log review**

Scan commits for anything unexpected:

```bash
git log --oneline -20
```

Look for: unusually large commits, odd commit messages, changes to files you didn't expect.

**4. Manual browser testing**

Actually use the app. Click around. Try edge cases. No amount of automated testing replaces human eyes on the product.

**5. Handle bugs found**

- **Easy bugs** - Use `/fix` skill. It investigates, fixes, and adds a regression test.
- **Hard bugs** - Note them down. They become user stories in the next PRD.

## The Skills

### Planning Skills (before Ralph runs)

**`/prd`** - The hardest part

Writing a good PRD is 80% of the work. Bad PRD = AI spinning in circles. Good PRD = smooth execution.

**Sizing is everything.** Each story must complete in one session. If it's too big, split it:
1. Data layer first (models, migrations)
2. Backend logic (services, APIs)
3. Frontend UI (pages, components)
4. Integration (connecting pieces)

**Acceptance criteria must be verifiable.** Not "works correctly" - but "returns 401 when token is invalid" or "displays error toast on API failure."

**`/ralph-init`** - PRD to JSON

Converts your PRD to machine format. Validates sizing before Ralph starts. Assigns priorities so dependencies run first (data before backend, backend before frontend).

### Review Skills (after Ralph runs)

**`/review-suggestions`** - The triage workflow

Interactively review each item in SUGGESTIONS.md:

```
Item 1/8 [P2] Add rate limiting to auth endpoints
> Vulnerable to brute force attacks

What should we do? [Remove / Promote to PRD / Skip]
```

This is where P1 items get promoted to real user stories. P2/P3 items either get removed (not worth it) or kept for future consideration.

**`/exploratory-qa`** - The human-in-the-loop QA

Every 3-5 Ralph iterations, this skill reviews the entire app for cross-cutting concerns:

- Navigation consistency
- Error handling patterns
- Auth guards on protected routes
- UI coherence (styling, spacing)
- Security issues

It updates `SUGGESTIONS.md` with priority markers:

- **[P1]** - Needs human review. Should become a new PRD story.
- **[P2]** - Should fix soon, doesn't need PRD.
- **[P3]** - Nice to have, future improvement.

**Key insight: QA can't be fully automated.** P1 items need human judgment to decide if they're worth doing and how to prioritize them.

### Maintenance Skills (as needed)

**`/fix`** - Systematic bug fixing

When you find a bug during manual QA, don't just patch it. The `/fix` skill:

1. Reproduces the bug
2. Searches for related code
3. Checks logs for clues
4. Identifies root cause
5. Implements the fix
6. **Adds a regression test** (mandatory!)
7. Verifies the fix works

The regression test is critical. Without it, the same bug will come back.

**`/prd-sync`** - Keep PRD.md in sync

After Ralph completes stories, this syncs the `passes: true` status back to PRD.md checkboxes. Keeps your human-readable doc accurate.

**`/prd-archive`** - Clean up completed work

When PRD.md gets long with completed epics, archive them to ARCHIVED_PRD.md. Keeps the active PRD focused on pending work.

## The Learning Loop

After each story, Claude captures what it learned in `CLAUDE.md`:

- "Always use async sessions in tests to match production"
- "Docker verification is critical - unit tests alone mask bugs"
- "Use bcrypt directly, not passlib, for Python 3.12+"

Future iterations benefit from past learnings. The project gets smarter over time.

## Why This Works

**Reduced feedback loop.** Tests run automatically. Failures are caught immediately. No waiting for human review to find bugs.

**No regressions.** Every change must pass existing tests. The AI can't break what already works.

**Autonomous but bounded.** Claude works within clear acceptance criteria. It can't go off on tangents because the task is clearly defined.

**Human judgment where needed.** PRD creation is human. Bug triage is human. Priority decisions are human. The AI handles execution, humans handle direction.

## How to Try It

### Human-in-the-Loop (Recommended for beginners)

Watch Claude work on one task at a time:

```bash
chmod +x ralph-once.sh
./ralph-once.sh
```

Review the commit, then run again for the next task.

### Autonomous Mode

Let Claude work unattended for N iterations:

```bash
chmod +x afk-ralph.sh
./afk-ralph.sh 5
```

### Files You Need

| File | Purpose |
|------|---------|
| `PRD.md` | Your user stories with `[ ]` checkboxes |
| `prd.json` | Machine-readable version for Ralph |
| `progress.txt` | Log of completed tasks |
| `CLAUDE.md` | Project context and accumulated learnings |
| `SUGGESTIONS.md` | QA observations with [P1]/[P2]/[P3] priorities |
| `ARCHIVED_PRD.md` | Completed epics for historical reference |
| `prompt.md` | The execution prompt Ralph follows |
| `.claude/skills/prd/` | Skill for creating well-structured PRDs |
| `.claude/skills/ralph-init/` | Skill for converting PRD.md to prd.json |
| `.claude/skills/prd-sync/` | Skill for syncing status back to PRD.md |
| `.claude/skills/prd-archive/` | Skill for archiving completed epics |
| `.claude/skills/exploratory-qa/` | Skill for periodic QA reviews |
| `.claude/skills/review-suggestions/` | Skill for triaging QA findings |
| `.claude/skills/fix/` | Skill for systematic bug fixing |

## Current Status

I'm building [Media Janitor](https://mediajanitor.com) using this workflow. So far:
- 18 user stories completed autonomously
- Patterns accumulated in CLAUDE.md
- QA observations tracked in SUGGESTIONS.md

It's not perfect, but it's productive. The AI works like an engineer, not a chatbot.

---

Based on: [AI Hero's Ralph](https://www.aihero.dev/getting-started-with-ralph) | Adapted for [Claude Code](https://claude.ai/claude-code)
