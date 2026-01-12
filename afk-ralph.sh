#!/bin/bash
set -e

# AFK Ralph - Autonomous loop mode
# Usage: ./afk-ralph.sh <iterations>

if [ -z "$1" ]; then
  echo "Usage: $0 <iterations>"
  echo "Example: $0 20"
  exit 1
fi

echo "Starting AFK Ralph with $1 iterations..."
echo "=========================================="

for ((i=1; i<=$1; i++)); do
  echo ""
  echo "--- Iteration $i of $1 ---"
  echo ""

  result=$(docker sandbox run claude --permission-mode acceptEdits -p "@PRD.md @progress.txt @CLAUDE.md \
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
  8. Update PRD.md to mark the task as complete [x]. \
  9. Append what you did to progress.txt with timestamp. \
  10. Update CLAUDE.md with any learnings, patterns, or context useful for future iterations. \
  11. Commit your changes with a descriptive message. \
  ONLY WORK ON A SINGLE TASK. \
  If all tasks in PRD.md are complete, output <promise>COMPLETE</promise>.")

  echo "$result"

  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo ""
    echo "=========================================="
    echo "PRD complete after $i iterations!"
    echo "=========================================="
    exit 0
  fi
done

echo ""
echo "=========================================="
echo "Completed $1 iterations. Check progress.txt for status."
echo "=========================================="
