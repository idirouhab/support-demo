# Quality Loop

This repository uses a repeatable software delivery pattern: catch the issue while the implementation context is fresh, turn the fix into a regression test, keep durable evidence with the change, and leave release judgment with a human reviewer.

## Loop

1. Detect the issue in context.
2. Add the closest regression test.
3. Make the smallest safe fix.
4. Run local checks that match GitLab CI.
5. Update evidence artifacts.
6. Ask a human to review quality, risk, and release readiness.
7. Capture any SDLC improvement the issue exposed.

## How The Repo Covers The Loop

- Earlier detection: issues start from visible product behavior and are traced while the frontend/backend contract is loaded.
- Regression-first fix: `AGENTS.md` requires every bug fix to include a regression test that would fail before the fix and pass after it.
- GitLab enforcement: `.gitlab-ci.yml` runs tests, build, and the `bug_fix_evidence` job so missing regression coverage or bug-log evidence can block a merge request.
- Evidence with the change: `docs/bug-log.md` records the symptom, root cause, fix, regression test, checks run, evidence, human decision, and follow-up opportunity.
- Human control: `docs/release-review-checklist.md` and the GitLab merge request template ask reviewers to decide whether the fix is understandable, sufficiently tested, and safe to release.
- SDLC redesign entry point: each issue can reveal a process improvement, such as a stronger API contract test, a CI gate, an ownership rule, a monitoring check, or a release policy update.

## Evidence Artifacts

Use these artifacts together when presenting or reviewing a fix:

- regression test diff
- implementation diff
- local check output matching `.gitlab-ci.yml`
- GitLab pipeline result
- `gitlab-quality-evidence.txt` from the `bug_fix_evidence` job
- `docs/bug-log.md` entry
- merge request checklist answers
- final human release decision

## Broader SDLC Opportunities

A single fixed bug should not automatically redesign the delivery process. It should create a clear entry point for humans to decide whether the same failure mode needs a broader guardrail.

Examples:

- Promote repeated bug-log themes into CI checks.
- Add merge request template questions for recurring risk areas.
- Add ownership rules for API contracts that cross frontend/backend boundaries.
- Add release gates for high-risk changes.
- Add monitoring or alerting when production behavior can reveal the same class of issue.
