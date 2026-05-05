#!/bin/sh
set -eu

EVIDENCE_FILE="${EVIDENCE_FILE:-gitlab-quality-evidence.txt}"
TARGET_BRANCH="${CI_MERGE_REQUEST_TARGET_BRANCH_NAME:-}"
DEFAULT_BRANCH="${CI_DEFAULT_BRANCH:-}"
BASE_REF="${BASE_REF:-}"
CHECK_WORKTREE="${CHECK_WORKTREE:-0}"

: > "$EVIDENCE_FILE"

log() {
  printf '%s\n' "$*" | tee -a "$EVIDENCE_FILE"
}

changed_files_matching() {
  printf '%s\n' "$CHANGED_FILES" | grep -E "$1" || true
}

has_changed_file_matching() {
  [ -n "$(changed_files_matching "$1")" ]
}

if [ "${QUALITY_EVIDENCE_ALLOW_SKIP:-false}" = "true" ]; then
  log "Quality evidence gate skipped by QUALITY_EVIDENCE_ALLOW_SKIP=true."
  exit 0
fi

if [ -n "$BASE_REF" ]; then
  DIFF_BASE="$BASE_REF"
elif [ -n "$TARGET_BRANCH" ]; then
  git fetch origin "$TARGET_BRANCH"
  DIFF_BASE="origin/$TARGET_BRANCH"
elif [ -n "$DEFAULT_BRANCH" ]; then
  git fetch origin "$DEFAULT_BRANCH"
  DIFF_BASE="origin/$DEFAULT_BRANCH"
else
  log "No GitLab merge request target branch or BASE_REF was provided."
  log "No CI_DEFAULT_BRANCH was provided for branch pipeline comparison."
  log "Skipping evidence gate because no diff base could be determined."
  exit 0
fi

if [ "$CHECK_WORKTREE" = "1" ]; then
  CHANGED_FILES="$(git diff --name-only "$DIFF_BASE")"
else
  CHANGED_FILES="$(git diff --name-only "$DIFF_BASE"...HEAD)"
fi

log "GitLab bug-fix evidence gate"
log "Diff base: $DIFF_BASE"
log ""
log "Changed files:"
if [ -n "$CHANGED_FILES" ]; then
  printf '%s\n' "$CHANGED_FILES" | tee -a "$EVIDENCE_FILE"
else
  log "No changed files detected."
  exit 0
fi
log ""

IMPLEMENTATION_OR_TEST_CHANGES="$(changed_files_matching '^(backend/app/|backend/tests/|frontend/src/)')"

if [ -z "$IMPLEMENTATION_OR_TEST_CHANGES" ]; then
  log "No backend/frontend implementation or test changes detected."
  log "Evidence gate passed."
  exit 0
fi

FAILURES=0

if ! has_changed_file_matching '^docs/bug-log\.md$'; then
  log "FAIL: backend/frontend changes must include a docs/bug-log.md evidence update."
  FAILURES=1
fi

if has_changed_file_matching '^backend/app/' && ! has_changed_file_matching '^backend/tests/'; then
  log "FAIL: backend app changes must include nearby backend regression test coverage."
  FAILURES=1
fi

FRONTEND_SOURCE_CHANGES="$(changed_files_matching '^frontend/src/.*\.(ts|tsx|css)$' | grep -Ev '(^frontend/src/test/|\.test\.)' || true)"

if [ -n "$FRONTEND_SOURCE_CHANGES" ] && ! has_changed_file_matching '^frontend/src/.*\.test\.(ts|tsx)$'; then
  log "FAIL: frontend source changes must include nearby frontend regression test coverage."
  FAILURES=1
fi

if [ "$FAILURES" -ne 0 ]; then
  log ""
  log "Evidence gate failed. Add the missing regression test or bug-log evidence, then rerun the pipeline."
  exit 1
fi

log "Evidence gate passed."
