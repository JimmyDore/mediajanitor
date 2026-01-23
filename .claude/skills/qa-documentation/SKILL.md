---
name: qa-documentation
description: Documentation review for CLAUDE.md accuracy and code comments. Adds findings to SUGGESTIONS.md.
---

# Documentation QA Skill

Review documentation accuracy and add findings to SUGGESTIONS.md.

## Scope

This skill focuses on **documentation concerns only**:
- CLAUDE.md accuracy
- Stale code comments
- Missing docstrings
- README accuracy
- Inline documentation

## Workflow

### Step 0: Review Existing Findings

**Before starting any review, read `SUGGESTIONS.md`** to understand what has already been discovered:

```bash
# Read the Documentation section of SUGGESTIONS.md
```

Focus on:
- **Active items** - Don't duplicate these
- **Struck-through items (`~~item~~`)** - Already fixed, don't re-report
- **Gaps** - What documentation concerns HAVEN'T been checked yet?

This prevents wasting time re-discovering known issues and helps you focus on finding NEW problems.

### Step 1: Review CLAUDE.md Patterns

Read `CLAUDE.md` and verify each documented pattern:

For each pattern, check:
- Does the code actually follow this pattern?
- Is the example code still accurate?
- Are file paths still correct?
- Are the commands still working?

```bash
# Test documented commands
cd backend && uv run pytest  # Does this work?
cd frontend && npm run test  # Does this work?
```

### Step 2: Check for Stale Patterns

Look for patterns in CLAUDE.md that are:
- No longer used in the codebase
- Superseded by newer approaches
- Referencing deleted files
- Using outdated syntax

### Step 3: Identify Missing Patterns

Look for patterns in the code that should be in CLAUDE.md:
- Repeated code patterns
- Non-obvious conventions
- Workarounds for known issues
- Integration patterns

### Step 4: Review Code Comments

Check for stale comments:

```bash
# Find TODO/FIXME comments
grep -rn "TODO\|FIXME\|HACK\|XXX" backend/ frontend/src/

# Find comments referencing old code
grep -rn "// old\|# old\|// deprecated\|# deprecated" backend/ frontend/src/
```

Look for:
- Comments that don't match the code
- Commented-out code that should be deleted
- TODOs that are already done
- References to removed features

### Step 5: Check Docstrings

**Python functions should have docstrings:**
```python
async def get_content_issues(db: AsyncSession, user_id: int) -> list[ContentIssueItem]:
    """
    Get all content items with issues for a user.

    Args:
        db: Database session
        user_id: User ID to get issues for

    Returns:
        List of content items with at least one issue
    """
```

Check:
- Public functions have docstrings
- Docstrings match actual behavior
- Parameters documented correctly
- Return values documented

### Step 6: Check README Accuracy

If `README.md` exists:
- Are setup instructions current?
- Do environment variable examples match `.env.example`?
- Are all commands working?
- Is the tech stack description accurate?

### Step 7: Check Inline Documentation

For complex logic, verify:
- Non-obvious code has explaining comments
- Magic numbers have comments
- Workarounds reference issue/ticket numbers
- Complex regex has explanation

### Step 8: Update SUGGESTIONS.md

Add findings to a **Documentation** section:

```markdown
## Documentation

- [P2] CLAUDE.md references `app/services/auth.py` but file is `app/services/user.py`
- [P2] Comment on line 45 of sync.py says "temporary fix" from 6 months ago
- [P3] Add docstring to `calculate_issue_types()` - complex logic
```

Priority guide:
- **[P1]** - Misleading docs causing errors
- **[P2]** - Outdated or inaccurate docs
- **[P3]** - Missing docs that would help

## What NOT to Do

- Do NOT write documentation (observation only)
- Do NOT duplicate items already in SUGGESTIONS.md (check both active AND struck-through `~~items~~`)
- Do NOT check non-documentation concerns
- Do NOT modify any code
- Do NOT add positive observations (e.g., "good implementation", "works correctly", "no issues found") - SUGGESTIONS.md tracks only items that need improvement

## Example Findings

```markdown
## Documentation

### CLAUDE.md
- [P2] "Testing Strategy" section says E2E tests are in `frontend/e2e/` but they're in `frontend/tests/e2e/`
- [P2] Docker command example uses `docker-compose` but we use `docker compose` (v2)
- [P3] Add pattern for "how to add a new API endpoint"

### Code Comments
- [P2] `content.py:234` comment says "TODO: add caching" but caching was added in commit abc123
- [P3] Remove commented-out code in `sync.py:89-102`

### Docstrings
- [P3] `services/content.py::get_old_content()` missing docstring - complex business logic
- [P3] `routers/whitelist.py` - none of the endpoints have docstrings

### Stale References
- [P2] README mentions "Slack notifications" feature that doesn't exist yet
- [P3] `.env.example` has `REDIS_URL` but we don't use Redis
```
