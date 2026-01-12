#!/bin/bash

# Ralph Once - Human-in-the-loop mode
# Run this script, watch what Claude does, then run again

claude --permission-mode acceptEdits "@PRD.md @progress.txt @CLAUDE.md \
1. Read the PRD, progress file, and CLAUDE.md for context. \
2. Find the next incomplete task (unchecked [ ] item) and implement it. \
3. Follow TDD: write a failing test first, then implement to pass. \
4. Run unit tests to verify the implementation passes. \
5. If UI was changed, run E2E tests (npm run test:e2e in frontend). \
6. If UI was changed, use browser tools to visually verify the changes look correct. \
7. Update PRD.md to mark the task as complete [x]. \
8. Append what you did to progress.txt. \
9. Update CLAUDE.md with any learnings, patterns, or context useful for future iterations. \
10. Commit your changes with a descriptive message. \
ONLY DO ONE TASK AT A TIME."
