#!/bin/bash
# PreToolUse hook: block Bash commands that write to files claimed by another agent.
# Fail-open: if parsing or the coordination script fails, allow the command.
INPUT=$(cat)
COMMAND=$(python -c "import sys,json; print(json.loads(sys.stdin.read()).get('tool_input',{}).get('command',''))" <<< "$INPUT" 2>/dev/null)
if [ -z "$COMMAND" ]; then
  exit 0
fi

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
if [ -z "$REPO_ROOT" ]; then
  exit 0
fi

# Extract potential write targets from common shell patterns
TARGETS=""
TARGETS="$TARGETS $(echo "$COMMAND" | grep -oE '>{1,2}\s*[^ ;|&]+' | sed 's/>{1,2}\s*//')"
TARGETS="$TARGETS $(echo "$COMMAND" | grep -oE 'tee\s+(-a\s+)?[^ ;|&]+' | sed 's/tee\s\+\(-a\s\+\)\?//')"
TARGETS="$TARGETS $(echo "$COMMAND" | grep -oE 'sed\s+-i\S*\s+\S+\s+[^ ;|&]+' | awk '{print $NF}')"
TARGETS="$TARGETS $(echo "$COMMAND" | grep -oE '(mv|cp)\s+\S+\s+[^ ;|&]+' | awk '{print $NF}')"

for TARGET in $TARGETS; do
  case "$TARGET" in
    ""|"$"*|"("*|")"*|"|"*|"&"*|";;"*) continue ;;
  esac

  if [[ "$TARGET" = /* ]]; then
    REL_PATH="${TARGET#"$REPO_ROOT"/}"
  else
    REL_PATH="$TARGET"
  fi

  if [ "$REL_PATH" = "$TARGET" ] && [[ "$TARGET" = /* ]]; then
    continue
  fi
  [ -z "$REL_PATH" ] && continue

  RESULT=$(python "$REPO_ROOT/workstation/scripts/multi_agent_coordination.py" check-path "$REL_PATH" 2>/dev/null) || continue
  ALLOWED=$(python -c "import sys,json; print(str(json.loads(sys.stdin.read()).get('allowed',True)).lower())" <<< "$RESULT" 2>/dev/null)

  if [ "$ALLOWED" = "false" ]; then
    OWNER=$(python -c "import sys,json; print(json.loads(sys.stdin.read()).get('owner','unknown'))" <<< "$RESULT" 2>/dev/null)
    LANE=$(python -c "import sys,json; print(json.loads(sys.stdin.read()).get('lane','unknown'))" <<< "$RESULT" 2>/dev/null)
    echo "BLOCKED: Bash write target '$REL_PATH' is claimed by agent '$OWNER' (lane: $LANE). Request a release or choose another file." >&2
    exit 2
  fi
done

exit 0