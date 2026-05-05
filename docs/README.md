# Project Documentation

This directory holds the durable engineering notes for the support ticket application. Keep it short, factual, and close to the code so it can be updated as part of the same reviewable change.

## What This Repo Contains

The app is a full-stack support ticket dashboard:

- `backend/` exposes a FastAPI API that returns support ticket data.
- `frontend/` renders the ticket queue with React and Vite.
- `backend/tests/` covers backend API behavior.
- `frontend/src/*.test.ts*` covers frontend rendering and status formatting behavior.
- `.gitlab-ci.yml` runs backend tests, frontend tests, and the frontend build in GitLab CI.
- `docs/quality-loop.md` explains how issue fixes move through test, evidence, and review.
- `docs/gitlab-workflow.md` explains GitLab's role as CI verifier, evidence gate, and merge request review surface.
- `docs/release-review-checklist.md` gives human reviewers a lightweight release decision prompt.
- `.gitlab/merge_request_templates/bug-fix.md` brings the same quality loop into merge request review.
- `scripts/ci/check_bug_fix_evidence.sh` powers the GitLab evidence gate.

## Bug History

Use `docs/bug-log.md` as the dated record of bugs that have occurred and been fixed. Each bug fix should land with:

- the code change
- the regression test
- the passing verification command
- the evidence captured from local checks or CI
- the human release decision still needed
- the follow-up SDLC opportunity, if one is visible
- the bug-log entry

This keeps issue history easy to review: a reported bug is traced, fixed, tested, and documented in the same reviewable change.

## Documentation Rules

Update documentation when a change affects how someone should understand, run, verify, or debug the project. For bug fixes, always update `docs/bug-log.md` after the regression test has been added and the relevant local checks have passed.
