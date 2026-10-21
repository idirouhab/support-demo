# Documentation and evidence instructions

Applies to `docs/` in addition to the root instructions. Read this guide when recording a bug fix or reviewing release evidence. Paths below are relative to this folder.

## Writing

- Ground commands and behavior in the current code and CI configuration. Use concise Markdown and relative links; verify referenced files exist.
- Keep detailed process guidance in `quality-loop.md`, GitLab specifics in `gitlab-workflow.md`, and release criteria in `release-review-checklist.md`.
- Preserve existing history and user changes. Routine documentation or agent-configuration edits need no fictional bug-log entry or product review.

## Bug history

After implementing the regression test and passing relevant checks, add a dated entry to `bug-log.md` in the same change as every bug fix. Include:

- Date fixed and short bug title.
- Symptom, root cause, and fix summary.
- Regression test added and why it fails before the fix and passes afterward.
- Checks actually run, detection point, and supporting evidence.
- Remaining human decision and a relevant follow-up SDLC opportunity.

Distinguish reproduced failures from inferred behavior, and proposed tests from implemented tests. Explain impractical regression coverage and the closest useful guard. Do not claim a passing test, pipeline, or reproduction without observed evidence.

## Evidence review

- Use `quality_evidence_reviewer` after bug-fix verification and the bug-log update, or for requested merge-request evidence/release-readiness reviews. Follow the root delegation rules and the role's configured model/effort.
- Supply the scoped implementation/test diff, local check outputs, bug-log entry, and relevant GitLab pipeline/commit evidence. Reuse existing outputs rather than repeating product reviews.
- Check against `release-review-checklist.md` and `../.gitlab/merge_request_templates/bug-fix.md`. Identify missing, stale, skipped, or failing checks.
- A passing `bug_fix_evidence` gate checks file presence; it does not prove behavioral correctness or authorize release. Keep local results separate from remote CI results.
- Summarize readiness for human review, remaining risk, the human merge/release decision, and any justified SDLC follow-up. Never fabricate approval.

## Verification

For documentation-only changes, check links, commands against source, and `git diff --check`; no application tests are needed unless behavior changed. For bug-fix evidence, use actual results from the changed layers' checks before writing the entry.

## Goal evidence

Follow [the issue loop](goal-loop.md) for active goals. Keep a per-issue record of acceptance criteria, observed failing and passing checks, remaining gaps, and the next action. Preserve the distinction between a completed local implementation, passing remote CI, and a closed GitLab issue. The evidence reviewer returns missing criteria to the parent for another iteration; it never changes the goal status itself. Document enhancements as enhancements rather than inventing prior bugs, while satisfying the repository evidence gate.
