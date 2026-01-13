---
name: improve-claude-md
description: Extract learnings from current session and update CLAUDE.md patterns
---

# Improve CLAUDE.md Skill

Extract learnings from the current session and update CLAUDE.md.

## Purpose

After completing a story or making significant code changes, capture any NEW patterns and learnings that will benefit future development. CLAUDE.md is the institutional memory of this project.

## Workflow

### Step 1: Review What Was Done

Look at what you just implemented in this session:
- What code did you write or modify?
- What problems did you encounter and solve?
- What patterns did you follow or discover?

### Step 2: Check Existing Learnings

Read the "Learnings & Patterns" section of CLAUDE.md to avoid duplicating existing content.

### Step 3: Identify NEW Learnings

Only capture genuinely new information in these categories:

| Category | Examples |
|----------|----------|
| **API patterns** | New endpoint conventions, auth patterns, error handling |
| **Testing strategies** | What worked, what didn't, mocking approaches |
| **Database/Model patterns** | Schema patterns, migration gotchas, query patterns |
| **Frontend patterns** | Component patterns, state management, styling |
| **Environment/Config** | Environment variables, Docker settings, build config |
| **Third-party gotchas** | Library quirks, version issues, workarounds |
| **Docker/Deployment** | Container issues, networking, production concerns |

### Step 4: Update CLAUDE.md

If you found new learnings:
1. Add them to the appropriate section in "Learnings & Patterns"
2. Use the same format as existing entries
3. Be concise but complete

If nothing new was learned:
- Say "No new learnings to capture" and do nothing
- This is perfectly acceptable - not every story produces new patterns

---

## What NOT to Add

- Information already in CLAUDE.md
- Obvious or trivial things
- Story-specific details (those go in progress.txt)
- TODO items or future work (those go in SUGGESTIONS.md)

---

## Example Update

If you discovered that bcrypt requires special handling in Python 3.12+:

```markdown
### Backend (FastAPI + SQLAlchemy)

**Password Hashing**: Use `bcrypt` directly (not passlib) for Python 3.12+ compatibility
\`\`\`python
import bcrypt
hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
\`\`\`
```

---

## Usage

Run this skill after completing implementation work:
```
/improve-claude-md
```

Or call it as step 14 in the Ralph workflow (prompt.md).
