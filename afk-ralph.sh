#!/bin/bash

# AFK Ralph - Autonomous loop mode
# Usage: ./afk-ralph.sh [-q|--qa-first] <iterations>

RETRY_WAIT_SECONDS=600  # 10 minutes
QA_FIRST=false
LOGFILE="ralph-output.log"

# Prompts
QA_PROMPT="Use /exploratory-qa skill to review the application for cross-cutting concerns"
RALPH_PROMPT="@prompt.md
If all tasks in PRD.md are complete, output <promise>COMPLETE</promise>."

# --- Helper functions ---

section_header() {
  echo ""
  echo "--- $1 ---"
  echo ""
}

wait_and_retry() {
  local reason="$1"
  echo ""
  echo "$reason"
  echo "   Waiting 10 minutes before retry... ($(date))"
  sleep $RETRY_WAIT_SECONDS
  echo "🔄 Retrying..."
}

run_claude_with_retry() {
  local prompt="$1"

  while true; do
    local temp_output=$(mktemp)

    # Note: Using text output (not stream-json) to support MCP tools like Puppeteer
    claude --permission-mode acceptEdits --output-format text --verbose -p "$prompt" 2>&1 | tee -a "$LOGFILE" | tee "$temp_output"

    local exit_code=${PIPESTATUS[0]}
    local output=$(cat "$temp_output")
    rm -f "$temp_output"

    if [ $exit_code -ne 0 ]; then
      if echo "$output" | grep -qi -E "(credit|rate.?limit|quota|limit.*reached|too.?many.?requests)"; then
        wait_and_retry "⏳ Credit/rate limit detected."
      else
        wait_and_retry "⚠️  Claude command failed with exit code $exit_code"
      fi
      continue
    fi

    break
  done
}

run_qa() {
  local label="${1:-Exploratory QA}"
  section_header "$label"
  run_claude_with_retry "$QA_PROMPT"
}

run_ralph() {
  run_claude_with_retry "$RALPH_PROMPT"
}

# --- Parse options ---

while [[ "$1" == -* ]]; do
  case "$1" in
    -q|--qa-first)
      QA_FIRST=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [ -z "$1" ]; then
  echo "Usage: $0 [-q|--qa-first] <iterations>"
  echo "  -q, --qa-first  Run exploratory QA before starting iterations"
  echo "Example: $0 20"
  echo "Example: $0 -q 10"
  exit 1
fi

ITERATIONS="$1"

# --- Main ---

echo "Starting AFK Ralph with $ITERATIONS iterations..."
[ "$QA_FIRST" = true ] && echo "  (with initial exploratory QA)"
echo "=========================================="

[ "$QA_FIRST" = true ] && run_qa "Initial Exploratory QA"

for ((i=1; i<=$ITERATIONS; i++)); do
  section_header "Iteration $i of $ITERATIONS"
  run_ralph

  # Integration review every 3 iterations
  if (( i % 3 == 0 )); then
    run_qa "Integration Review (iteration $i)"
  fi

  # Check for completion
  if tail -100 "$LOGFILE" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "=========================================="
    echo "PRD complete after $i iterations!"
    echo "=========================================="
    exit 0
  fi
done

echo ""
echo "=========================================="
echo "Completed $ITERATIONS iterations. Check progress.txt for status."
echo "=========================================="
