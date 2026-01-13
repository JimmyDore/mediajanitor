#!/bin/bash

# AFK Ralph - Autonomous loop mode
# Usage: ./afk-ralph.sh <iterations>

RETRY_WAIT_SECONDS=600  # 10 minutes

# Run claude command with unlimited retries on credit/rate limit errors
run_claude_with_retry() {
  local prompt="$1"
  local iteration_log="$2"

  while true; do
    # Run claude and capture exit code
    # Using a temp file to capture full output for error detection
    local temp_output=$(mktemp)

    claude --permission-mode acceptEdits --output-format stream-json --verbose -p "$prompt" 2>&1 | tee -a "$iteration_log" | tee "$temp_output" | jq -r --unbuffered '
      select(.type == "assistant" and .message.content != null) |
      .message.content[] |
      select(.type == "text") |
      .text // empty
    ' 2>/dev/null

    local exit_code=${PIPESTATUS[0]}
    local output=$(cat "$temp_output")
    rm -f "$temp_output"

    # Check for credit/rate limit errors
    if [ $exit_code -ne 0 ]; then
      if echo "$output" | grep -qi -E "(credit|rate.?limit|quota|limit.*reached|too.?many.?requests)"; then
        echo ""
        echo "⏳ Credit/rate limit detected. Waiting 10 minutes before retry..."
        echo "   Time: $(date)"
        echo ""
        sleep $RETRY_WAIT_SECONDS
        echo "🔄 Retrying..."
        continue
      else
        echo ""
        echo "⚠️  Claude command failed with exit code $exit_code"
        echo "   Waiting 10 minutes before retry..."
        sleep $RETRY_WAIT_SECONDS
        echo "🔄 Retrying..."
        continue
      fi
    fi

    # Success - exit the retry loop
    break
  done
}

if [ -z "$1" ]; then
  echo "Usage: $0 <iterations>"
  echo "Example: $0 20"
  exit 1
fi

echo "Starting AFK Ralph with $1 iterations..."
echo "=========================================="

logfile="ralph-output.log"

for ((i=1; i<=$1; i++)); do
  echo ""
  echo "--- Iteration $i of $1 ---"
  echo ""

  run_claude_with_retry "@prompt.md
If all tasks in PRD.md are complete, output <promise>COMPLETE</promise>." "$logfile"

  result=$(tail -100 "$logfile")

  # Integration review every 3 iterations
  if (( i % 3 == 0 )); then
    echo ""
    echo "--- Integration Review (iteration $i) ---"
    echo ""

    run_claude_with_retry "Use /exploratory-qa skill to review the application for cross-cutting concerns" "$logfile"
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
