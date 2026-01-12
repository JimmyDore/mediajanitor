# Ralph Task Prompt

@prd.json @progress.txt @CLAUDE.md @SUGGESTIONS.md

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
   - Wait 10s, test via curl
   - Check logs: `docker-compose logs backend`
   - If errors, fix and repeat from step 3
6. If UI changed with API calls, write frontend unit tests (vitest)
7. Run frontend quality checks:
   - Unit tests: `cd frontend && npm run test`
   - Typecheck: `cd frontend && npm run check`
8. If UI changed, write minimal E2E tests (Playwright)
9. Run E2E tests: `cd frontend && npm run test:e2e`
10. If UI changed and browser tools available, visually verify
11. Update prd.json: set `passes: true` for completed story
12. Commit: `feat(scope): [US-X.X] description`
13. Append to progress.txt (date, story ID, files changed, learnings)
14. Update CLAUDE.md with discovered patterns
15. Review broader context and add observations to SUGGESTIONS.md:
    - Missing UI elements (navigation, headers, footers)?
    - Patterns to extract (components, utilities, hooks)?
    - Security or performance concerns?
    - Database schema improvements?
    Mark items [P1]/[P2]/[P3]. P1 needs human review for PRD promotion.

If all stories have `passes: true`, output <promise>COMPLETE</promise>.

ONLY DO ONE STORY AT A TIME.
