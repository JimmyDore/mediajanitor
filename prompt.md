# Ralph Task Prompt

@prd.json @progress.txt @CLAUDE.md

## Execution Loop

1. Read prd.json and find the next story where `passes: false`
2. Read CLAUDE.md and progress.txt for context and patterns
3. Implement the story following TDD:
   - Write failing test first
   - Implement to make it pass
4. Run backend quality checks:
   - Tests: `cd backend && uv run pytest`
   - Typecheck: `cd backend && uv run mypy app/`
5. If backend changed, verify in Docker:
   - `docker-compose up --build -d`
   - Wait 10s for startup
   - Run integration tests: `cd backend && uv run pytest tests/test_integration.py -v`
   - If new feature, add relevant integration test to `tests/test_integration.py`
   - Quick curl QA (optional): Read credentials from .env.example, login, test endpoint
   - Check logs: `docker-compose logs backend`
   - If errors, fix and repeat from step 3
6. If UI changed with API calls, write frontend unit tests (vitest)
7. Run frontend quality checks:
   - Unit tests: `cd frontend && npm run test`
   - Typecheck: `cd frontend && npm run check`
8. E2E tests: ONLY write for NEW routes/pages (smoke test that page loads)
   - Do NOT write E2E for: form validation, API responses, loading states, toasts
   - These belong in unit tests (vitest), not E2E
9. Run E2E tests: `cd frontend && npm run test:e2e` (should be < 30 tests)
10. If UI changed and browser tools available, visually verify
11. Update prd.json: set `passes: true` for completed story
12. Commit: `feat(scope): [US-X.X] description`
13. Append to progress.txt (date, story ID, files changed, learnings)
14. Use /improve-claude-md skill to capture any new learnings for CLAUDE.md

If all stories have `passes: true`, output <promise>COMPLETE</promise>.

ONLY DO ONE STORY AT A TIME.
