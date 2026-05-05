# Release Review Checklist

Use this checklist when reviewing a bug-fix merge request. The goal is not to slow down small fixes; it is to keep quality, risk, and release timing as explicit human decisions.

## Bug Understanding

- The reported symptom is clear.
- The root cause is explained in plain language.
- The fix is small enough to review confidently.
- The implementation preserves the existing architecture unless a larger change is justified.

## Regression Coverage

- A regression test covers the reported behavior.
- The test would have failed before the fix.
- Cross-stack bugs have backend and frontend coverage when practical.
- Unknown or edge-case behavior degrades gracefully where relevant.

## Evidence

- Local checks matching GitLab CI were run.
- GitLab CI passed in the merge request.
- The `bug_fix_evidence` job passed or any failure is understood.
- The `gitlab-quality-evidence.txt` artifact was reviewed when available.
- Any skipped check is explained.
- `docs/bug-log.md` was updated after tests passed.
- The merge request includes enough evidence for another reviewer to verify the change.

## Human Decision

- The remaining risk is acceptable.
- Any release timing concern is documented.
- Any required follow-up is tracked outside the release decision.
- A human reviewer, not automation alone, decides whether to merge and release.
