#!/bin/bash

# AFK Ralph - Autonomous loop mode
# Usage: ./afk-ralph.sh [-q|--qa-first] <iterations>

RETRY_WAIT_SECONDS=60  # 1 minute
QA_FIRST=false
LOGFILE="ralph-output.log"

# Prompts
QA_PROMPT="Use /exploratory-qa skill to review the application for cross-cutting concerns"
RALPH_PROMPT="@prompt.md"

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
  echo "   Waiting 1 minute before retry... ($(date))"
  sleep $RETRY_WAIT_SECONDS
  echo "🔄 Retrying..."
}

run_claude_with_retry() {
  local prompt="$1"
  local use_streaming="${2:-false}"

  while true; do
    local temp_output=$(mktemp)

    if [ "$use_streaming" = true ]; then
      # Stream JSON with jq parsing for clean output
      claude --permission-mode acceptEdits --output-format stream-json --verbose -p "$prompt" 2>&1 | tee -a "$LOGFILE" | tee "$temp_output" | jq -r --unbuffered '
        select(.type == "assistant" and .message.content != null) |
        .message.content[] |
        select(.type == "text") |
        .text // empty
      ' 2>/dev/null
    else
      # Text output for QA (supports MCP tools like Puppeteer)
      claude --permission-mode acceptEdits --output-format text --verbose -p "$prompt" 2>&1 | tee -a "$LOGFILE" | tee "$temp_output"
    fi

    local exit_code=${PIPESTATUS[0]}
    local output=$(cat "$temp_output")
    rm -f "$temp_output"

    if [ $exit_code -ne 0 ]; then
      if echo "$output" | grep -qi -E "(credit|rate.?limit|quota|limit.*reached|too.?many.?requests|overloaded)"; then
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
  run_claude_with_retry "$QA_PROMPT" false
}

run_ralph() {
  run_claude_with_retry "$RALPH_PROMPT" true
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

  # Check for completion by verifying prd.json directly (don't trust Claude's output)
  REMAINING=$(jq '[.userStories[] | select(.passes == false)] | length' prd.json 2>/dev/null || echo "999")
  if [ "$REMAINING" -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "PRD complete after $i iterations! (0 stories remaining)"
    echo "=========================================="
    break
  else
    echo ""
    echo "📋 $REMAINING stories remaining..."
  fi
done

# Final QA review after all iterations
run_qa "Final Integration Review"

echo ""
echo "=========================================="
echo "Completed $ITERATIONS iterations. Check progress.txt for status."
echo "=========================================="
