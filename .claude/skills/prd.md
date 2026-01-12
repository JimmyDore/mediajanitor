# PRD Creation Skill

Generate well-structured Product Requirements Documents with right-sized user stories.

## Workflow

### Step 1: Clarify Requirements

Ask 3-5 essential questions to understand the feature:

1. **Problem/Goal**: What problem does this solve? What's the success criteria?
2. **Core Functionality**: What are the must-have features vs nice-to-haves?
3. **Scope Boundaries**: What's explicitly OUT of scope?
4. **Technical Constraints**: Any existing patterns, APIs, or dependencies to use?
5. **User Types**: Who will use this feature?

Present options as lettered choices (A/B/C/D) when applicable.

### Step 2: Generate PRD

Create a markdown PRD with these sections:

```markdown
## [Feature Name]

### Overview
Brief description of the feature and problem it solves.

### Goals
- Specific, measurable objective 1
- Specific, measurable objective 2

### User Stories

#### US-X.1: [Story Title]
**As a** [user type]
**I want** [capability]
**So that** [benefit]

**Acceptance Criteria:**
- [ ] [Specific, verifiable criterion]
- [ ] [Another criterion]
- [ ] Typecheck passes
- [ ] Unit tests pass

### Non-Goals
- What this feature will NOT do
- Explicit scope boundaries

### Technical Considerations
- Dependencies on existing code
- Database changes needed
- API contracts
```

### Step 3: Save the PRD

Save as `PRD.md` or append to existing PRD file.

---

## Story Sizing Guidelines (CRITICAL)

Each story must be completable in ONE context window (~1 session).

### Right-Sized Stories (Good)
- Add a database column/table
- Create a single API endpoint
- Build one UI component/page
- Add a form with validation
- Implement one service function

### Over-Scoped Stories (Must Split)
- "Build the authentication system" → Split into: User model, Register endpoint, Login endpoint, JWT middleware, Auth UI
- "Create the dashboard" → Split into: Layout, Navigation, Individual widgets
- "Add settings management" → Split into: Settings model, API endpoints, Settings page

### Splitting Strategy

When a story is too big, split by:
1. **Data layer first** (models, migrations)
2. **Backend logic** (services, APIs)
3. **Frontend UI** (pages, components)
4. **Integration** (connecting pieces)

---

## Acceptance Criteria Rules

Every criterion must be **verifiable** - not vague.

### Good Criteria
- "Form displays validation error when email is invalid"
- "API returns 401 when token is missing"
- "Settings page shows 'Connected' badge when Jellyfin is configured"
- "Typecheck passes"
- "Unit tests pass"

### Bad Criteria (Avoid)
- "Works correctly"
- "Good UX"
- "Handles errors properly"
- "Is secure"

### Mandatory Criteria

**Every story must include:**
- "Typecheck passes"
- "Unit tests pass"

**UI stories must also include:**
- "Verify in browser using browser tools"

---

## Example Output

```markdown
## Epic 3: Old Content Detection

### Overview
Allow users to identify content in their Jellyfin library that hasn't been watched in a configurable period.

### Goals
- Surface unwatched content older than threshold
- Help users reclaim storage by identifying candidates for removal
- Respect user's protected content whitelist

### User Stories

#### US-3.1: View Old Unwatched Content
**As a** media server owner
**I want** to see a list of content not watched in X months
**So that** I can decide what to delete

**Acceptance Criteria:**
- [ ] Page displays movies/shows not watched in 4+ months
- [ ] Each item shows: title, last watched date, size
- [ ] Items in whitelist are excluded
- [ ] Typecheck passes
- [ ] Unit tests pass
- [ ] Verify in browser using browser tools

#### US-3.2: Configure Old Content Threshold
**As a** user
**I want** to set my own "old content" threshold
**So that** the detection matches my preferences

**Acceptance Criteria:**
- [ ] Settings page has "Old content months" input
- [ ] Default value is 4 months
- [ ] Value persists in user settings
- [ ] Typecheck passes
- [ ] Unit tests pass

### Non-Goals
- Automatic deletion (user must manually delete)
- Jellyfin API calls for deletion (out of scope for v1)

### Technical Considerations
- Requires Jellyfin API: /Users/{userId}/Items with filters
- Need to cache results (API is slow)
- Whitelist stored in UserSettings model
```

---

## Do NOT Implement

This skill only creates the PRD document. Do NOT:
- Write any code
- Create files other than PRD
- Start implementation

After PRD is created, user should run `/ralph-init` to convert to prd.json.
