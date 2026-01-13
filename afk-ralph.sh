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

  logfile="ralph-output.log"
  claude --permission-mode acceptEdits --output-format stream-json --verbose -p "@prompt.md
If all tasks in PRD.md are complete, output <promise>COMPLETE</promise>." 2>&1 | tee -a "$logfile" | jq -r --unbuffered '
    select(.type == "assistant" and .message.content != null) |
    .message.content[] |
    select(.type == "text") |
    .text // empty
  ' 2>/dev/null
  result=$(tail -100 "$logfile")

  # Integration review every 3 iterations
  if (( i % 3 == 0 )); then
    echo ""
    echo "--- Integration Review (iteration $i) ---"
    echo ""

    claude --permission-mode acceptEdits -p "Use /exploratory-qa skill to review the application for cross-cutting concerns"
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
