# Bug Log

This file is the dated record of bugs that have occurred in the support ticket application. Add a new entry whenever a bug is fixed.

## Entry Format

```text
## YYYY-MM-DD - Short Bug Title

- Symptom:
- Root cause:
- Fix:
- Regression test:
- Checks run:
- Detection point:
- Evidence:
- Human decision needed:
- Follow-up SDLC opportunity:
```

## Fixed Bugs

## 2026-09-01 - Restore resolved tickets in the ticket-list API

- Symptom: `GET /api/tickets` returned three seeded tickets instead of four;
  resolved ticket `T-104` was missing and `test_list_tickets_contract` failed.
- Root cause: `list_tickets()` unconditionally filtered out the `resolved` status,
  although the list endpoint's contract includes every ticket.
- Fix: Return a fresh list of all seeded tickets, preserving canonical statuses
  and the existing list-copy behavior.
- Regression test: Added `test_list_tickets_includes_resolved_tickets` in
  `backend/tests/test_tickets_api.py`, asserting that the endpoint includes `T-104`
  with the canonical `resolved` status. The existing four-ticket assertion remains.
- Checks run: From `backend`, `.venv/bin/python -m pytest` passed all five tests.
  Integrated frontend tests (seven), the frontend production build, and the
  existing bug-fix evidence gate also passed.
- Detection point: The initial [GitHub CI run](https://github.com/idir-oai/support-demo/actions/runs/33495130717)
  failed, followed by a local regression-first reproduction.
- Evidence: Before the fix, the new test failed because `T-104` was absent from
  the response. After the fix, both that test and the original contract test pass.
- Human decision needed: Review and merge the fix before relying on the default
  branch's CI. Merge and release remain separate human decisions.
- Follow-up SDLC opportunity: Keep lifecycle-status coverage in API contracts;
  introduce any future status filtering as an explicit, tested API option.

## 2026-09-01 - Surface unsuccessful ticket API responses in the dashboard

- Symptom: HTTP failures appeared as an empty successful ticket queue. The existing
  dashboard test could not find the `Could not load tickets` error message.
- Root cause: `fetchTickets()` resolved to an empty array on non-OK responses,
  preventing the component's existing error handler from running.
- Fix: Reject unsuccessful responses with an error containing the HTTP status,
  without parsing the error body. Successful responses still return their JSON.
- Regression test: Extended `frontend/src/App.test.tsx` with HTTP 400 and 500
  rejection cases using invalid-JSON error bodies, plus a successful empty-list
  case. Retained the existing dashboard error-rendering test unchanged.
- Checks run: From `frontend`, `npm test` passed all seven tests and
  `npm run build` passed. All five backend tests, 73 automation tests, and the
  existing bug-fix evidence gate also passed.
- Detection point: The initial GitHub CI run and local reproduction, with the
  HTTP-error regression tests added before changing the implementation.
- Evidence: Before the fix, both new HTTP cases incorrectly resolved `[]` and the
  existing error UI test failed (three failed, four passed). After the fix, all
  seven pass; unsuccessful response bodies are not parsed and HTTP success with
  an empty list still resolves normally.
- Human decision needed: Review the PR and decide whether to merge and release.
  Unrelated seeded status/priority defects are outside this fix's scope.
- Follow-up SDLC opportunity: Preserve distinct tests for transport/HTTP failures
  and valid empty API responses so error handling cannot silently become success.

## 2026-09-01 - Suppress stale Codex review comments after a PR base changes

- Symptom: During development of the GitHub automation, a review could be posted
  after its PR was retargeted or its base moved, even though the reviewed head had
  not changed. The comment would describe an outdated diff.
- Root cause: The initial feedback helper compared only the head SHA before
  publishing and did not validate the reviewed base SHA.
- Fix: Require and validate both reviewed SHAs, compare both to the live PR, and
  skip outdated feedback. Include both SHAs in the advisory review comment.
- Regression test: `scripts/github/automation.test.cjs` covers a moved/retargeted
  base, changed head, missing/malformed reviewed SHAs, and closed/fork PRs. The
  moved-base test observed an unwanted comment before the fix and passes afterward.
- Checks run: `node --test scripts/github/automation.test.cjs` (58 passed),
  `python3 -m unittest discover -s scripts/github/tests -v` (15 passed), and
  actionlint 1.7.12 on all three new workflows (passed; optional shellcheck/pyflakes
  integrations unavailable). The frontend production build also passed.
- Detection point: Regression-first development and independent review of the new
  workflow, before deployment; this was not a production incident.
- Evidence: The changed-base test expects zero comment writes; the valid-review
  test verifies the pinned base and head are included. Adjacent patch-guard tests
  also prove that validation does not alter the real checkout/index.
- Human decision needed: Review the automation before relying on it for releases.
  Existing application tests still fail independently: backend
  `test_list_tickets_contract` expects four tickets but receives three; frontend
  `shows an error when the API fails` cannot find the error message. Those seeded
  application bugs were not changed by this setup.
- Follow-up SDLC opportunity: Decide required-check/branch-protection policy,
  pin reviewed action versions, configure API usage budgets, and use a real issue
  to verify the complete development/review flow before unattended use.
