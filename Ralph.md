# How to Use Ralph

Ralph is an iterative AI development technique where Claude works through your PRD one task at a time.

## Files Required

| File | Purpose |
|------|---------|
| `PRD.md` | User stories with `[ ]` checkboxes |
| `progress.txt` | Log of completed tasks |
| `CLAUDE.md` | Project context for Claude |
| `ralph-once.sh` | Human-in-the-loop mode |
| `afk-ralph.sh` | Autonomous loop mode |

## Option 1: Human-in-the-Loop (Recommended)

Watch Claude work on one task at a time:

```bash
# First time only
chmod +x ralph-once.sh

# Run one iteration
./ralph-once.sh
```

**What happens:**
1. Claude reads PRD.md and finds the next `[ ]` task
2. Writes a failing test (TDD)
3. Implements the feature
4. Runs unit tests to verify
5. If UI changed, runs E2E tests (`npm run test:e2e`)
6. If UI changed, uses browser to visually verify
7. Marks task as `[x]` in PRD.md
8. Updates progress.txt
9. Updates CLAUDE.md with learnings
10. Commits changes

**When done:** Run again for the next task.

## Option 2: Autonomous Loop (AFK Mode)

Let Claude work unattended for N iterations:

```bash
chmod +x afk-ralph.sh

# Run 5 tasks unattended
./afk-ralph.sh 5
```

**Note:** Requires `docker sandbox run` setup.

## Option 3: Manual (In Current Session)

Just say:

> "Do the next task from PRD.md"

## Tips

- **Start with Option 1** to understand the flow
- **Review each commit** before running the next iteration
- **Edit PRD.md** if you want to change priorities or add tasks
- **Check progress.txt** for a history of what was done

## Current Status

- **Completed:** US-0.1 (Hello World), US-0.2 (Docker), US-0.3 (Deploy)
- **Next task:** US-1.1 (User Registration)

## Testing

### Unit Tests
```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm run test
```

### E2E Tests (Playwright)
```bash
cd frontend
npm run test:e2e      # Headless
npm run test:e2e:ui   # With Playwright UI
```

### Browser Verification (MCP)
Claude can use the Puppeteer MCP server (`.mcp.json`) to:
- Open the app in Chrome
- Take screenshots
- Click buttons and fill forms
- Verify visual appearance

## Reference

Based on: https://www.aihero.dev/getting-started-with-ralph
