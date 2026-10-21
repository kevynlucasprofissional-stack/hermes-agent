#!/bin/bash
# PreToolUse hook: block Edit/Write on files claimed by another agent.
# Fail-open: if the coordination script fails, allow the edit (solo work must not break).
INPUT=$(cat)
FILE_PATH=$(python -c "import sys,json; print(json.loads(sys.stdin.read()).get('tool_input',{}).get('file_path',''))" <<< "$INPUT" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Convert absolute path to repo-relative for check-path
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
if [ -z "$REPO_ROOT" ]; then
  exit 0
fi

REL_PATH="${FILE_PATH#"$REPO_ROOT"/}"
if [ "$REL_PATH" = "$FILE_PATH" ]; then
  # Path is already relative or outside repo
  exit 0
fi

RESULT=$(python "$REPO_ROOT/workstation/scripts/multi_agent_coordination.py" check-path "$REL_PATH" 2>/dev/null) || exit 0

ALLOWED=$(python -c "import sys,json; print(str(json.loads(sys.stdin.read()).get('allowed',True)).lower())" <<< "$RESULT" 2>/dev/null)
if [ "$ALLOWED" = "false" ]; then
  OWNER=$(python -c "import sys,json; print(json.loads(sys.stdin.read()).get('owner','unknown'))" <<< "$RESULT" 2>/dev/null)
  LANE=$(python -c "import sys,json; print(json.loads(sys.stdin.read()).get('lane','unknown'))" <<< "$RESULT" 2>/dev/null)
  echo "BLOCKED: '$REL_PATH' is claimed by agent '$OWNER' (lane: $LANE). Request a release or choose another file." >&2
  exit 2
fi

exit 0