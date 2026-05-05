# Agent Instructions

## Project Goal

This repo is a full-stack support ticket app with a frontend, backend, tests, and GitLab CI/CD.

Automation agents should make small, reviewable changes and preserve the existing architecture unless explicitly asked otherwise.

## Quality Loop Contract

Use this repo to practice a tight SDLC quality loop:

1. Detect the bug while the relevant code, tests, and product behavior are still in context.
2. Add or update the closest regression test before or alongside the fix.
3. Make the smallest implementation change that satisfies the test and preserves the existing architecture.
4. Run local checks that match GitLab CI as closely as practical.
5. Keep GitLab visible as the remote review and enforcement layer by preserving `.gitlab-ci.yml`, the merge request template, and the `bug_fix_evidence` quality gate.
6. Update durable evidence artifacts, especially `docs/bug-log.md`, in the same change.
7. Surface remaining risk, release readiness, and any human decision needed instead of making release decisions automatically.
8. Note any follow-up opportunity that could improve the broader SDLC, such as CI gates, review templates, ownership rules, or monitoring.

## Bug Fix Policy

Every bug fix must include a regression test.

A regression test should:

- fail before the fix
- pass after the fix
- cover the behavior reported by the bug
- live as close as possible to the layer where the bug occurred

If a bug crosses the frontend/backend boundary, add coverage on both sides when practical:

- backend contract or API test
- frontend rendering or behavior test

If a regression test is not practical, explain why in the final summary and add the closest useful guard test.

Every bug fix must also update the dated bug history in `docs/bug-log.md` after the regression test has been implemented and the relevant checks have passed.

Bug history entries should include:

- date fixed
- symptom
- root cause
- fix summary
- regression test added
- checks run
- detection point
- evidence
- human decision needed
- follow-up SDLC opportunity

If the fix is not documented, the bug fix is not complete.

## Status Contract

Ticket statuses must be handled consistently across backend and frontend.

Canonical API statuses are:

- `open`
- `pending`
- `in_progress`
- `resolved`

The frontend may display `in_progress` as `In progress`, but it must not require a different wire value such as `in-progress`.

When fixing status-related bugs:

- centralize normalization or formatting logic
- avoid duplicating status mappings across components
- add tests for known status values
- add a test for unknown statuses so the UI degrades gracefully

Example regression case:

A backend ticket with:

```json
{ "status": "in_progress" }
```

must not render as `Unknown` in the frontend.

## Verification

Before finishing, run the relevant local checks.

For backend changes, run backend tests.

For frontend changes, run frontend tests.

For cross-stack changes, run both.

If GitLab CI has equivalent commands in `.gitlab-ci.yml`, prefer matching those commands locally.

For bug-fix evidence gate changes, preview the GitLab gate locally with:

```bash
BASE_REF=HEAD CHECK_WORKTREE=1 sh scripts/ci/check_bug_fix_evidence.sh
```

## Final Response

Summarize:

- what changed
- which regression test was added
- which checks were run
- any remaining risk
- any human release decision or SDLC follow-up that remains
