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

  result=$(docker sandbox run claude --permission-mode acceptEdits -p "@prompt.md
If all tasks in PRD.md are complete, output <promise>COMPLETE</promise>.")

  echo "$result"

  # Integration review every 3 iterations
  if (( i % 3 == 0 )); then
    echo ""
    echo "--- Integration Review (iteration $i) ---"
    echo ""

    docker sandbox run claude --permission-mode acceptEdits -p "@PRD.md @SUGGESTIONS.md @CLAUDE.md \
    Perform an integration review of the application: \
    1. Review all implemented features for consistency \
    2. Check for missing cross-cutting concerns (navigation, error handling, auth guards) \
    3. Verify UI coherence across pages using browser tools \
    4. Look for security gaps, performance issues, accessibility problems \
    5. Update SUGGESTIONS.md with any new observations (mark priority [P1]/[P2]/[P3]) \
    6. If there are [P1] items, add a note at the top of SUGGESTIONS.md: '## ACTION NEEDED: Review P1 items for PRD promotion' \
    Do NOT implement anything. Only observe, document, and commit SUGGESTIONS.md updates."
  fi

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
