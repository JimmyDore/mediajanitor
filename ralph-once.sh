#!/bin/bash

# Ralph Once - Human-in-the-loop mode
# Run this script, watch what Claude does, then run again

claude --permission-mode acceptEdits "@PRD.md @progress.txt @CLAUDE.md \
1. Read the PRD, progress file, and CLAUDE.md for context. \
2. Find the next incomplete task (unchecked [ ] item) and implement it. \
3. Follow TDD: write a failing test first, then implement to pass. \
4. Run unit tests to verify the implementation passes. \
5. If backend was changed, build and test in Docker: \
   - Run: docker-compose up --build -d \
   - Wait 10s for containers to start \
   - Test the feature via curl (e.g., curl -X POST http://localhost:8080/api/...) \
   - Check logs: docker-compose logs backend \
   - If errors, fix and repeat from step 3. \
6. If UI was changed, write minimal E2E tests (just a safety net, not exhaustive). \
7. If UI was changed, run E2E tests (npm run test:e2e in frontend). \
8. If UI was changed, use browser tools to visually verify the changes look correct. \
9. Update PRD.md to mark the task as complete [x]. \
10. Append what you did to progress.txt. \
11. Update CLAUDE.md with any learnings, patterns, or context useful for future iterations. \
12. Commit your changes with a descriptive message. \
ONLY DO ONE TASK AT A TIME."
