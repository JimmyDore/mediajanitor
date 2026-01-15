# Ralph Task Prompt

@prd.json @progress.txt @CLAUDE.md

## Execution Loop

1. Read prd.json and find the next story where `passes: false` (pick the one with **lowest priority number**)
2. Read CLAUDE.md and progress.txt for context and patterns
3. Implement the story following TDD:
   - Write failing test first
   - Implement to make it pass
4. **If you modified `app/database.py` (added/removed columns, tables):**
   - Create migration IMMEDIATELY: `cd backend && uv run alembic revision --autogenerate -m "describe_change"`
   - Review the generated migration file in `alembic/versions/`
   - Apply locally: `cd backend && uv run alembic upgrade head`
   - **MUST do this BEFORE running Docker**
5. Run backend quality checks:
   - Tests: `cd backend && uv run pytest`
   - Typecheck: `cd backend && uv run mypy app/`
6. If backend changed, verify in Docker:
   - `docker-compose up --build -d`
   - Wait 10s for startup
   - Run integration tests: `cd backend && uv run pytest tests/test_integration.py -v`
   - If new feature, add relevant integration test to `tests/test_integration.py`
   - Quick curl QA (optional): Read credentials from .env.example, login, test endpoint
   - Check logs: `docker-compose logs backend`
   - If errors, fix and repeat from step 3
7. If UI changed with API calls, write frontend unit tests (vitest)
8. Run frontend quality checks:
   - Unit tests: `cd frontend && npm run test`
   - Typecheck: `cd frontend && npm run check`
9. E2E tests: ONLY write for NEW routes/pages (smoke test that page loads)
   - Do NOT write E2E for: form validation, API responses, loading states, toasts
   - These belong in unit tests (vitest), not E2E
10. Run E2E tests: `cd frontend && npm run test:e2e` (should be < 30 tests)
11. If UI changed and browser tools available, visually verify
12. Update prd.json: set `passes: true` for completed story
13. Commit: `feat(scope): [US-X.X] description`
    - **Include migration files in the same commit as model changes**
14. Append to progress.txt (date, story ID, files changed, learnings)
15. Use /improve-claude-md skill to capture any new learnings for CLAUDE.md

If all stories have `passes: true`, output <promise>COMPLETE</promise>.

**CRITICAL: STOP AFTER ONE STORY.**
After completing steps 1-15 for ONE story, you MUST stop immediately. Do NOT look for the next story. Do NOT continue working. The script will start a fresh session for the next story. This is essential for memory management.
