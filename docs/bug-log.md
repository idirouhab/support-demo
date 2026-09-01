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
