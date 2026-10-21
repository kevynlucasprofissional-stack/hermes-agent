#!/bin/bash
# SessionStart hook: warn if not on the expected collaboration branch.
# Fail-open: if git or branch detection fails, do not block session start.
EXPECTED_BRANCH="feat/hermes-workstation-mvp-20261013"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0

if [ -z "$CURRENT_BRANCH" ]; then
  exit 0
fi

if [ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]; then
  echo "WARNING: Current branch is '$CURRENT_BRANCH', but the collaboration protocol expects '$EXPECTED_BRANCH'. Run 'git switch $EXPECTED_BRANCH' before editing shared files." >&2
  # Exit 0 (fail-open) — warning only, do not block session start
fi
exit 0