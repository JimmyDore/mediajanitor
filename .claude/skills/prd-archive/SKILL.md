---
name: prd-archive
description: Move completed epics from PRD.md to ARCHIVED_PRD.md
---

# PRD Archive Skill

Move completed epics from PRD.md to ARCHIVED_PRD.md for historical reference.

## Purpose

Keep PRD.md focused on pending work by archiving completed epics. This makes the PRD easier to navigate and reduces context size for Ralph execution.

## When to Use

- After completing a significant number of stories (e.g., all stories in one or more epics)
- When PRD.md becomes unwieldy with completed content
- Before starting a new phase of development

## Workflow

### Step 1: Analyze PRD.md

1. Read `PRD.md` and identify all epics
2. For each epic, check if **ALL** user stories are complete:
   - A story is complete when **ALL** its acceptance criteria have `[x]` checkboxes
   - If ANY checkbox is `[ ]`, the story (and thus the epic) is incomplete
3. Build a list of completed epics with their line ranges

### Step 2: Read/Create ARCHIVED_PRD.md

1. If `ARCHIVED_PRD.md` doesn't exist, create it with header:
   ```markdown
   # Media Janitor - Archived PRD

   Completed epics moved from PRD.md for historical reference.

   ## Summary
   - **X completed user stories** across Y epics
   - **Archived**: YYYY-MM-DD
   - **Active PRD**: See `PRD.md` for pending stories

   ---
   ```
2. If it exists, read current content

### Step 3: Move Completed Epics

For each completed epic:

1. **Extract** the epic section from PRD.md:
   - Start: `## Epic X:` heading
   - End: Next `## Epic` heading (or end of epic content area)
   - Include: Overview, Goals, User Stories, Non-Goals, Technical Considerations

2. **Append** to ARCHIVED_PRD.md before the checklist section

3. **Remove** from PRD.md

### Step 4: Update Checklists

1. **ARCHIVED_PRD.md**: Add moved stories to the archived checklist
2. **PRD.md**: Update the "Completed" section to reference archive:
   ```markdown
   ### Completed ✅ (X stories)
   See [ARCHIVED_PRD.md](./ARCHIVED_PRD.md) for completed epics and stories.
   ```

### Step 5: Show Summary

Report what was moved:
```
Archived 3 epics to ARCHIVED_PRD.md:
- Epic 5: Language Issues (3 stories)
- Epic 6: Jellyseerr Requests (2 stories)
- Epic V: Validation (4 stories)

Total: 9 stories moved
PRD.md now has X pending stories
```

---

## What to Preserve in PRD.md

**NEVER archive these sections** (always keep at top of PRD.md):
- Vision
- Tech Stack
- Architecture Decisions
- Dashboard & Issues Architecture diagram

These provide essential context for understanding pending work.

---

## Epic Completion Detection

An epic is complete when:

```
epic.complete = all(story.complete for story in epic.stories)
story.complete = all(criterion.checked for criterion in story.acceptance_criteria)
criterion.checked = criterion.startswith("[x]") or criterion.startswith("- [x]")
```

**Partial completion does NOT count** - if even one checkbox is unchecked, the epic stays in PRD.md.

---

## Example

### Before

**PRD.md**:
```markdown
## Epic 5: Language Issues (COMPLETE)
### US-5.1: Language Backend ✅
- [x] Criterion 1
- [x] Criterion 2

### US-5.2: Mark French-Only ✅
- [x] All criteria checked

## Epic 17: Bug Fixes (INCOMPLETE)
### US-17.1: Multi-User Watch Data
- [ ] Not done yet
- [ ] Also pending
```

### After `/prd-archive`

**PRD.md** (Epic 5 removed):
```markdown
## Epic 17: Bug Fixes
### US-17.1: Multi-User Watch Data
- [ ] Not done yet
- [ ] Also pending
```

**ARCHIVED_PRD.md** (Epic 5 added):
```markdown
## Epic 5: Language Issues
### US-5.1: Language Backend ✅
- [x] Criterion 1
- [x] Criterion 2

### US-5.2: Mark French-Only ✅
- [x] All criteria checked
```

---

## Edge Cases

1. **No completed epics**: Report "No completed epics found to archive" and exit
2. **All epics completed**: Move all, leave PRD.md with only header sections
3. **Epic with `✅` in title but unchecked items**: Trust checkboxes, not emoji - skip the epic
4. **Stories without acceptance criteria**: Treat as incomplete (conservative approach)

---

## Do NOT

- Do NOT archive partial epics (all stories must be complete)
- Do NOT modify story content (only move as-is)
- Do NOT reorder epics within files
- Do NOT create commits automatically (let user review first)
- Do NOT archive the Vision/Tech Stack/Architecture sections

---

## Usage

After completing multiple epics:

```bash
# Check which epics might be complete
grep -E "^## Epic.*✅" PRD.md

# Or check for unchecked items
grep -c "\[ \]" PRD.md

# Run this skill to archive completed epics
/prd-archive
```

Then review and commit:
```bash
# Review changes
git diff PRD.md ARCHIVED_PRD.md

# Commit the archive
git add PRD.md ARCHIVED_PRD.md && git commit -m "docs: archive completed epics"
```
