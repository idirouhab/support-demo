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

## Enhancements

## 2026-10-21 - Increase workspace typography for readability

- Requested enhancement: The user found the redesigned fonts too small. Raise
  body/Description to 17px, controls/values/buttons to 16px, queue titles to 18px,
  and all secondary text/labels to at least 14px. Title is 32px desktop/28px mobile.
  Widen the queue and wrap narrow metadata without shrinking text at breakpoints.
- Scope: CSS only; behavior, API contracts, branding removal and intentional
  demo bugs remain unchanged. No new unit assertion duplicates CSS declarations.
- Checks run: `npm run build` passed; `npm test` reports 27 passed / 19 failed,
  with the identical exercise failure set and all 16 workspace cases passing.
  Browser checks at 100% zoom confirm no horizontal overflow at 1440px, 390px
  and 320px; larger queue metadata wraps without collisions. Mobile Save remains
  adjacent to Description and is fully reachable with a short scroll.
- Evidence: Both design agents reviewed paired before/after and narrow-screen
  captures in `output/design/typography/`. `design-qa.md` records the current
  scale and measurements. `git diff --check` passed. Backend and remote CI were
  not run for this CSS enhancement.
- Human decision: Review the larger type in the local preview. Merge/release
  remains a separate human decision; the intentional demo baseline is still red.

## 2026-10-21 - Iterate the workspace design and preserve drafts across navigation

- Enhancement: Two design agents critiqued the rendered workspace, discussed
  tradeoffs and implemented two substantial rounds plus a focus repair. Compact
  the queue/header, bound the form width, clarify editable versus read-only
  fields, raise small labels, and place actions directly below Description.
  Keep graphite/paper/citrine art direction and the removed branding.
- Symptoms: Ticket switching silently discarded unsaved fields. On mobile the
  queue consumed much of the editing screen and Save began around y1111 at
  390×844. The first redesign also exposed a skip link targeting a hidden pane
  and resize/navigation focus problems.
- Root causes: Draft state belonged to a keyed editor; mobile stacked two
  scrolling panes; action layout pushed Save to the bottom. A static skip target
  and replayed focus request did not account for hidden/visible controls.
- Fix: Store drafts per ticket in App, clearing only the saved/cancelled ticket.
  Show Unsaved changes, use one visible mobile pane with Back/Return navigation,
  select the visible skip destination, and issue focus requests only for explicit
  navigation or controls becoming hidden. Keep focus in Description when it
  remains visible. This supersedes the previous entry's draft-discard-on-switch
  behavior; the earlier entry remains historical.
- Regression tests: Add nine nearby cases to
  `frontend/src/TicketWorkspace.test.tsx` for draft isolation/retention, mobile
  pane reopening, pending-save Back locking, save/cancel focus, visible skip
  target, navigation focus, both resize directions, retained Description focus,
  and unsaved feedback. The reverse-resize guard already passed through the
  existing queue-focus effect and required no additional production fix.
- Before/after evidence: Original seven workspace tests passed. First new
  behavior cases yielded 7 passes/3 failures, then 10 passes. Next focus cases
  yielded 10 passes/3 failures; adding unsaved feedback yielded 10/4 before its
  implementation. Later the stale-focus regression yielded 14 passes/1 failure,
  then 15 passes. The final full suite includes all 16 workspace cases passing.
- Checks run: Frontend `npm test` reports 27 passed / 19 failed. The failed test
  names exactly match the starting 18-pass/19-failure exercise baseline. The
  deliberate status/error/count bugs and their correct assertions are preserved;
  the full suite is not release-green. `npm run build` and `git diff --check`
  pass. Backend checks and remote CI were not run; no backend/API files changed
  in this iteration.
- Browser evidence: Desktop 1440×960, mobile 390×844 and 320×844, plus native
  619×615. Verify draft switching/cancel, keyboard queue activation and focus,
  no horizontal overflow, and a long title expanding vertically at 320px. Save
  is now y681–725 for T-101 at 390×844. Browser error/warning log query is empty.
  Test drafts were cancelled without persisting data. Clear final captures at
  approved 100% zoom are in `output/design/iterations/04-final-*`; `design-qa.md`
  records comparisons, rejected captures, normalization and verification limits.
- Detection point: User-requested iterative design review, direct discussion
  between critic and implementer, targeted red/green tests and browser checks.
- Human decision needed: Review the local demo; decide whether to merge/release.
  Physical-device keyboard behavior and assistive technology remain unverified.
  Nothing was committed, pushed or deployed. Local evidence gate checks file
  presence across the already dirty tracked tree, not behavior or remote CI.
- Follow-up SDLC opportunity: Add responsive queue/editor navigation and draft
  preservation to browser smoke coverage if this view becomes permanent. Keep
  demo bug restoration separate from production release checks.

## 2026-10-21 - Implement the selected ticket workspace and restore exercise bugs

- Enhancement: Implement `output/design/support-workspace-v3.png` in the existing
  React app: empty top-left header, charcoal queue, warm editor, quiet metadata,
  and citrine actions. No new application scaffold or routes were introduced.
- Requested baseline restoration: The user explicitly asked to revert fixes to
  bugs deliberately created for this demo. Restored the original list filter
  that omits resolved tickets, GET-client HTTP failures returning an empty list,
  the hyphenated status-label lookup and raw status classes, and summary
  predicates counting every ticket as active and medium priority as high.
  Canonical wire values, edit validation/endpoints, seed content and unrelated
  repository work remain. Earlier fix entries below are historical and no longer
  describe the current exercise baseline. No existing correctness assertion was
  removed, skipped or changed to expect incorrect results.
- Change: Select the first ticket by default; move editing into a persistent
  adjacent pane; add bounded Previous/Next controls; reset unsaved fields on
  Cancel and ticket switching; retain the selected ticket after saving. Keep
  draft preservation, exact update payloads, disabled controls and focus return.
  Self-host Geist fonts and use Phosphor icons. Stack the panes on narrow screens.
- Review symptoms: ID-only queue button labels omitted useful assistive-technology
  context, and a previous success message could remain after a later failed save.
  These were new workspace issues, separate from the requested seeded bugs.
- Root causes and fixes: Associate each queue button with its visible title,
  requester, status and priority using `aria-describedby`. Clear saved feedback
  when a new save starts, preserving the later error and unsaved draft.
- Acceptance/regression coverage: Add seven nearby cases in
  `frontend/src/TicketWorkspace.test.tsx` for initial selection/navigation, Cancel,
  persistent save, duplicate prevention/navigation locking, transport errors,
  accessible queue context and success-then-failure feedback. Adapt existing
  table-specific assertions to queue/editor semantics while retaining correct
  status, error and summary expectations.
- Before/after evidence: Original fixed baseline passed 30 frontend and 56 backend
  tests. After the requested reversions, frontend passed 10 and failed 20; backend
  passed 52 and failed 4. All five initial workspace acceptance tests failed
  before implementation. The two later review regressions produced 5 passes and
  2 failures before their fixes; all seven workspace checks pass afterward.
- Checks run: Final frontend `npm test` reports 18 passed / 19 failed; all remaining
  failures are the retained status/error/count assertions for restored bugs.
  The adapted unknown-status save guard now passes instead of failing on an
  ambiguous text query. Backend `.venv/bin/python -m pytest -q --tb=no` reports
  52 passed / 4 failed for resolved-ticket list expectations. These suites are
  intentionally red, not passing release checks. `npm run build` passes.
- Local evidence gate: Passed with `BASE_REF=HEAD CHECK_WORKTREE=1` and
  `EVIDENCE_FILE=/private/tmp/support-workspace-quality-evidence.txt`;
  `git diff --check` passed. The unchanged gate checks tracked-path file presence
  across the already dirty workspace, excludes new untracked source files, and
  does not establish behavioral correctness or a passing remote pipeline.
- Browser evidence: Compiled preview verified at 1485px, 390px and 320px; no
  horizontal overflow at either mobile width, including a 200-character title.
  Verified keyboard queue selection and focus, navigation, draft cancellation,
  and saving/reloading all three editable fields; restored original demo values.
  The fresh compiled-preview tab had no console messages/errors. Desktop/mobile
  screenshots, paired visual comparisons and test counts are in `output/design/`;
  the detailed visual report is `design-qa.md`. Remote CI was not run.
- Detection point: User-selected mock implementation, specialist source review,
  targeted red/green tests, and direct in-app browser verification.
- Human decision needed: Review the local demo UI. Merging/releasing remains a
  human decision; the restored exercise baseline intentionally fails correctness
  checks. Nothing was committed, pushed or deployed by this change.
- Follow-up SDLC opportunity: Keep exercise restoration separate from production
  fixes, and add a browser navigation/save/reload smoke flow to CI if this UI
  becomes the long-term view.

## 2026-10-20 - Show the ticket queue in a responsive table

- Enhancement: Replace the card list with a basic table so ticket fields can be
  compared across rows. This is a requested layout enhancement, not a previously
  reported application defect.
- Previous behavior: `App.tsx` rendered cards alongside shared fetch, summary,
  selection, and save state. The empty queue had no explanatory message.
- Change: Extract presentation into `frontend/src/TicketQueue.tsx`, with Ticket,
  Requester, Status, Priority, Created, and Actions columns. Keep the current
  theme, API contract, summary semantics, and existing editor. Details expand in
  the next table row; the table scrolls horizontally on narrow screens while the
  editor fits the visible area. Empty queues show `No tickets to display.`
  No packages or backend behavior changed.
- Acceptance coverage: `frontend/src/App.test.tsx` checks table semantics and
  matching row data for every canonical status plus an unknown status. It also
  covers the empty message, editor association and placement, focus on opening,
  single-editor switching, cancellation, and focus return after saving. Existing
  save-payload, retry, disabled-control, status, and summary tests remain.
- Checks run: From `frontend/`, `npm test` passed all 30 tests and
  `npm run build` passed. Chromium checks at 1280px, 390px, and 320px verified no
  page-level horizontal overflow, keyboard scrolling with visible focus, a
  viewport-sized editor, draft cancellation/reset with a long description, and
  focus restoration. No uncaught page errors were observed. `git diff --check`
  passed. The local evidence gate passed with `BASE_REF=HEAD CHECK_WORKTREE=1`
  and `EVIDENCE_FILE=/private/tmp/support-table-quality-evidence.txt`; this
  checks tracked-path file presence across the existing dirty working tree, not
  behavior, and excludes the new untracked `TicketQueue.tsx`. Backend tests and
  remote GitLab CI were not run for this frontend-only change.
- Evidence: The baseline suite passed 28 tests. Before implementation, both new
  acceptance cases failed because the named table and empty message were absent;
  afterward, the full 30-test suite passed. Initial static review identified an
  oversized mobile editor; the narrow-screen width rule and subsequent Chromium
  measurements confirmed 208px and 278px input widths at 320px and 390px.
- Human decision needed: Review the table layout and decide whether to merge and
  release. Verification used Chromium at the listed widths; other browser engines
  and screen-reader behavior were not exercised. No deployment was performed.
- Follow-up SDLC opportunity: Add the narrow-screen scrolling and editor-focus
  smoke checks to CI if the table becomes the established queue view.

## Coverage Improvements

## 2026-09-07 - Expand backend contract and validation coverage

- Symptom: The five backend tests passed but did not cover model validation,
  health responses, CORS, unique seeded ticket IDs, or timestamp validity.
- Root cause: Existing tests focused on response field names, ticket count,
  selected statuses, and the OpenAPI title.
- Fix: Add model and API guard tests and strengthen the ticket-list contract.
  This is a test-only coverage improvement; no backend runtime defect was
  reproduced or repaired, and application behavior is unchanged.
- Regression test: `backend/tests/test_ticket_models.py` checks canonical status
  definition consistency, preservation of all valid statuses and priorities,
  and rejection of aliases, unknown values, empty values, and invalid types.
  `backend/tests/test_health_and_cors.py` covers health, responses and preflight
  requests from both configured frontend origins, and an unrelated origin.
  `backend/tests/test_tickets_api.py` now checks unique and expected seeded IDs,
  the complete ID-to-status mapping, and parseable timestamps with timezones.
- Checks run: From `backend`, `.venv/bin/python -m pytest` passed all 33 tests
  (28 added cases); the baseline passed all five existing tests. From the repo
  root, `BASE_REF=HEAD CHECK_WORKTREE=1 sh scripts/ci/check_bug_fix_evidence.sh`
  and `git diff --check` also passed.
- Detection point: Read-only backend test scouting and local implementation of
  the identified coverage gaps.
- Evidence: All new guards pass against the existing backend implementation.
  These are preventive tests, not evidence of a newly fixed runtime bug.
- Human decision needed: Review and merge the test changes; no release action
  was taken or release readiness assessed.
- Follow-up SDLC opportunity: Add frontend regression coverage using canonical
  API statuses and assert dashboard summary counts against known ticket data.

## Fixed Bugs

## 2026-09-11 - Verify GitHub issue #1 baseline fixes

- Symptom: Resolved ticket T-104 was omitted from the list, and failed HTTP
  requests appeared as successful empty queues.
- Root cause: The original list implementation filtered resolved tickets, and
  the frontend API client returned an empty array for unsuccessful responses.
- Fix: Verified the existing fixes from commit `dd78d76`, already on GitHub
  main. No additional backend or API-client implementation change was needed.
- Regression test: Retained `test_list_tickets_includes_resolved_tickets` and
  the four-ticket API contract, HTTP 400/500 rejection tests that avoid parsing
  error bodies, successful-empty-list coverage, and dashboard error rendering.
- Checks run: Backend `.venv/bin/python -m pytest` (56 passed), frontend
  `npm test` (28 passed), `npm run build` (passed), and the existing evidence
  gate with `BASE_REF=HEAD CHECK_WORKTREE=1` (passed).
- Detection point: Implementation audit of
  [issue #1](https://github.com/idir-oai/support-demo/issues/1).
- Evidence: Current tests verify all four seeded IDs, canonical resolved status,
  rejected HTTP errors, and visible error feedback. The September 1 entries
  retain the original failing-before/passing-after evidence; this is a fresh
  verification, not a newly reproduced baseline bug.
- Human decision needed: Review verification and decide whether to close #1.
  No issue was closed, and no merge or release was performed.
- Follow-up SDLC opportunity: Reconcile completed fixes with open issues so
  already-delivered work does not get implemented twice.

## 2026-09-11 - Complete GitHub issue #2 status regression coverage

- Symptom: GitHub main renders canonical `in_progress` as Unknown; arbitrary
  unknown values do not receive a consistent fallback class.
- Root cause: Main's frontend expects `in-progress`, interpolates arbitrary
  status values into CSS classes, and does not guard inherited object keys.
- Fix: Preserved the existing local canonical types, fixtures, guarded shared
  label/class helpers, and dedicated blue `.status-in_progress` CSS rule. Added
  missing regression coverage without changing backend statuses or styling.
- Regression test: `frontend/src/status.test.ts` now checks labels and classes
  for all four canonical statuses, plus blocked, hyphenated, empty, and inherited
  key inputs. `frontend/src/App.test.tsx` asserts the visible In progress badge
  class from an API fixture and the visible Unknown fallback badge class.
- Checks run: Backend `.venv/bin/python -m pytest` (56 passed), frontend
  `npm test` (28 passed), `npm run build` (passed), existing evidence gate with
  `BASE_REF=HEAD CHECK_WORKTREE=1` (passed), and `git diff --check` (passed).
- Detection point: Acceptance-criteria review of
  [issue #2](https://github.com/idir-oai/support-demo/issues/2).
- Evidence: In an isolated temporary frontend copy, restoring App.tsx,
  status.ts, types.ts, and styles.css from `dd78d76` made eight status-helper
  cases and both dashboard status cases fail. The same assertions pass with
  the current local implementation. The workspace's existing edits were not
  reverted. CSS inspection confirms the canonical selector has its own blue
  styling and is separate from the unknown selector.
- Human decision needed: Review the local changes before publishing or merging;
  no automation was dispatched, no PR was created, and #2 remains open.
- Follow-up SDLC opportunity: Keep API-shaped frontend fixtures and label/class
  assertions together so label-only repairs cannot hide badge regressions.

## 2026-09-11 - Correct GitHub issue #3 dashboard summary counts

- Symptom: Medium-priority tickets inflate the High priority count; unknown API
  statuses count as Active. Main also counts resolved tickets as Active.
- Root cause: High priority used `priority !== 'low'`; the local Active predicate
  excluded only resolved values, while main counted every ticket.
- Fix: Count only `priority === 'high'`. Reuse the shared canonical-status guard
  and exclude resolved tickets, counting only open, pending, and in_progress.
  Total remains the queue length. API, badges, priority colors, and workflows
  were not modified by this fix.
- Regression test: Five dashboard cases cover mixed statuses/priorities,
  all-resolved, empty, medium/low-only, and unknown-status queues. Assertions
  locate each count within its labeled summary block; the mixed fixture expects
  4 total, 3 active, and 1 high priority. Existing save-to-resolved coverage stays.
- Checks run: Frontend `npm test` (28 passed), `npm run build` (passed), backend
  `.venv/bin/python -m pytest` (56 passed), existing evidence gate with
  `BASE_REF=HEAD CHECK_WORKTREE=1` (passed), and `git diff --check` (passed).
- Detection point: Regression-first implementation of
  [issue #3](https://github.com/idir-oai/support-demo/issues/3).
- Evidence: Before the predicate fix, the new tests produced four failures and
  24 passes: mixed, all-resolved, medium/low-only, and unknown-status cases failed.
  Afterward all 28 tests pass. The isolated original-main reproduction also
  failed four summary cases, including resolved-ticket Active calculations.
- Human decision needed: Review and decide whether to publish, merge, and
  release. The workspace contains earlier unrelated changes that require
  separate selection during publication; #3 remains open.
- Follow-up SDLC opportunity: Retain summary edge-case tests in frontend CI and
  use explicit membership rules when adding future status or priority values.

## 2026-09-09 - Add ticket details editing and preserve canonical status behavior

- Symptom: Tickets had no details or edit action, description field, or save
  endpoint. The API's `in_progress` status rendered as `Unknown`, and the Active
  summary included resolved tickets, so resolving a ticket could not reduce it.
- Root cause: The dashboard and API only supported listing seeded tickets. The
  frontend used `in-progress` instead of the canonical API value and counted all
  tickets as active. Unknown status lookup also admitted inherited object keys.
- Fix: Add a View details button and an expandable editor for title, description,
  and status, with Save changes and Cancel. Add descriptions to the ticket model
  and seeds, `GET /api/tickets/{ticket_id}`, and validated
  `PUT /api/tickets/{ticket_id}` updates. Save only the three editable fields,
  retain drafts on failure, prevent duplicate submissions, return focus to the
  details button, and refresh the saved card and Active count. Centralize the
  canonical frontend status values and use a safe unknown-status fallback.
- Regression test: `backend/tests/test_ticket_updates.py` covers detail reads,
  saving all four statuses, reading saved values back, preserving other fields
  and tickets, empty descriptions, invalid/incomplete updates, and missing IDs.
  The existing list contract now requires description. `frontend/src/App.test.tsx`
  covers opening/switching editors, cancel and focus, all three saved fields,
  updated Active counts, HTTP failures and retry, blank titles, duplicate-save
  prevention, and unknown statuses. Status helpers are tested against canonical
  API values and unknown values, including inherited object property names.
- Checks run: Backend `.venv/bin/python -m pytest` (56 passed); frontend
  `npm test` (13 passed) and `npm run build` passed. Chrome verification saved
  title, a multiline description, and resolved status, reloaded the page, and
  confirmed all three persisted and Active decreased. The original demo ticket
  was restored afterward. The local GitLab evidence gate
  (`BASE_REF=HEAD CHECK_WORKTREE=1 sh scripts/ci/check_bug_fix_evidence.sh`) and
  `git diff --check` passed.
- Detection point: Regression-first implementation of the requested editor,
  inspection of the status contract, and integration checks against the local API.
- Evidence: Before implementation, the expanded backend tests had 19 failures
  because descriptions and routes were absent; frontend checks had nine failures
  because details controls were missing and canonical/unknown status formatting
  was incorrect. All relevant checks pass after implementation. The existing
  security-lab isolation test still receives 404 for its absent search route.
- Human decision needed: Review and release remain human decisions. Updates use
  the existing in-memory store: they survive a browser reload but reset on a
  backend restart, and are not shared across separate server processes. Decide
  durable storage requirements before treating this as a multi-user workflow.
- Follow-up SDLC opportunity: Add a browser save-and-reload scenario to CI and
  define persistence and concurrent-edit behavior before production deployment.

## 2026-09-07 - Use localhost consistently in launcher URLs

- Symptom: The launcher printed localhost links, but Vite and Uvicorn advertised
  `127.0.0.1` URLs. The user saw another application's Firebase warning when
  opening that browser origin.
- Root cause: Both server commands explicitly used `--host 127.0.0.1`, while
  the launcher's links and frontend API client used `localhost`.
- Fix: Pass `--host localhost` to both servers so their advertised URLs match
  the launcher's frontend, backend, and API documentation links.
- Regression test: `scripts/tests/test_run.py` runs an isolated launcher copy
  with lightweight command substitutes. It checks all five URLs emitted by the
  launcher and simulated servers, verifies launch from another folder, and
  checks the launcher's Ctrl+C exit status without using the real app's ports.
- Checks run: `python3 -m unittest discover -s scripts/tests -v` (one passed),
  `bash -n run.sh`, backend `.venv/bin/python -m pytest` (33 passed), and frontend
  `npm test` (seven passed).
- Detection point: User report while opening the locally running dashboard.
- Evidence: Before the fix, the new regression test failed on the two
  `http://127.0.0.1` server URLs; after the fix, all five URLs use localhost.
- Human decision needed: Restart the local launcher to use the updated commands.
  Merge and release remain human decisions; no deployment was performed.
- Follow-up SDLC opportunity: Add the launcher regression test to CI so local
  startup URLs remain consistent with the frontend API and CORS configuration.

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
