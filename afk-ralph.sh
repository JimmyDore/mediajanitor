#!/bin/bash

# AFK Ralph - Autonomous loop mode
# Usage: ./afk-ralph.sh [-q|--qa-first] [--qa=skill1,skill2] <iterations>

RETRY_WAIT_SECONDS=60  # 1 minute
QA_FIRST=false
LOGFILE="ralph-output.log"

# All available QA skills (in recommended order)
ALL_QA_SKILLS=(
  "qa-security"
  "qa-api-contracts"
  "qa-test-coverage"
  "qa-performance"
  "qa-architecture"
  "qa-ux"
  "qa-accessibility"
  "qa-documentation"
)

# Default: run all QA skills
QA_SKILLS=("${ALL_QA_SKILLS[@]}")

# Prompts
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
  echo "Retrying..."
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
        wait_and_retry "Credit/rate limit detected."
      else
        wait_and_retry "Claude command failed with exit code $exit_code"
      fi
      continue
    fi

    break
  done
}

run_qa_skill() {
  local skill="$1"
  section_header "QA: $skill"
  run_claude_with_retry "Use /$skill skill to review the application" false
}

run_all_qa_skills() {
  local label="${1:-Final QA Review}"
  section_header "$label"
  echo "Running ${#QA_SKILLS[@]} QA skills: ${QA_SKILLS[*]}"
  echo ""

  for skill in "${QA_SKILLS[@]}"; do
    run_qa_skill "$skill"
  done
}

run_ralph() {
  run_claude_with_retry "$RALPH_PROMPT" true
}

show_help() {
  echo "AFK Ralph - Autonomous development loop"
  echo ""
  echo "Usage: $0 [options] <iterations>"
  echo ""
  echo "Options:"
  echo "  -q, --qa-first           Run QA skills before starting iterations"
  echo "  --qa=skill1,skill2,...   Run only specified QA skills (comma-separated)"
  echo "  --qa=none                Skip QA entirely"
  echo "  --list-qa                List available QA skills and exit"
  echo "  -h, --help               Show this help message"
  echo ""
  echo "Available QA skills:"
  for skill in "${ALL_QA_SKILLS[@]}"; do
    echo "  - $skill"
  done
  echo ""
  echo "Examples:"
  echo "  $0 20                           # Run 20 iterations, all QA skills at end"
  echo "  $0 -q 10                        # Run QA first, then 10 iterations, QA at end"
  echo "  $0 --qa=qa-security,qa-ux 5     # Run 5 iterations, only security and UX QA"
  echo "  $0 --qa=none 5                  # Run 5 iterations, skip QA entirely"
}

# --- Parse options ---

while [[ "$1" == -* ]]; do
  case "$1" in
    -q|--qa-first)
      QA_FIRST=true
      shift
      ;;
    --qa=*)
      QA_ARG="${1#--qa=}"
      if [ "$QA_ARG" = "none" ]; then
        QA_SKILLS=()
      else
        IFS=',' read -ra QA_SKILLS <<< "$QA_ARG"
        # Validate skill names
        for skill in "${QA_SKILLS[@]}"; do
          valid=false
          for available in "${ALL_QA_SKILLS[@]}"; do
            if [ "$skill" = "$available" ]; then
              valid=true
              break
            fi
          done
          if [ "$valid" = false ]; then
            echo "Error: Unknown QA skill '$skill'"
            echo "Run '$0 --list-qa' to see available skills"
            exit 1
          fi
        done
      fi
      shift
      ;;
    --list-qa)
      echo "Available QA skills:"
      for skill in "${ALL_QA_SKILLS[@]}"; do
        echo "  - $skill"
      done
      exit 0
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run '$0 --help' for usage"
      exit 1
      ;;
  esac
done

if [ -z "$1" ]; then
  show_help
  exit 1
fi

ITERATIONS="$1"

# --- Main ---

echo "Starting AFK Ralph with $ITERATIONS iterations..."
[ "$QA_FIRST" = true ] && echo "  (with initial QA review)"
if [ ${#QA_SKILLS[@]} -eq 0 ]; then
  echo "  (QA skills disabled)"
elif [ ${#QA_SKILLS[@]} -lt ${#ALL_QA_SKILLS[@]} ]; then
  echo "  (QA skills: ${QA_SKILLS[*]})"
fi
echo "=========================================="

# Initial QA if requested
if [ "$QA_FIRST" = true ] && [ ${#QA_SKILLS[@]} -gt 0 ]; then
  run_all_qa_skills "Initial QA Review"
fi

# Main development loop
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
    echo "$REMAINING stories remaining..."
  fi
done

# Final QA review
if [ ${#QA_SKILLS[@]} -gt 0 ]; then
  run_all_qa_skills "Final QA Review"
fi

echo ""
echo "=========================================="
echo "Completed $ITERATIONS iterations. Check progress.txt for status."
echo "=========================================="
