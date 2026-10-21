# Project instructions

Support ticket app: React frontend, FastAPI backend, and GitLab CI/CD. Make small, reviewable changes; preserve the architecture and existing user work.

## Load guidance by scope

Read the matching file when work enters that folder; its instructions extend this file. For cross-stack work, read both application guides. Read the docs guide when updating bug evidence or assessing release readiness.

- [Frontend](frontend/AGENTS.md): UI behavior, status rendering, tests, and frontend subagents.
- [Backend](backend/AGENTS.md): API contracts, validation, tests, and backend subagents.
- [Docs](docs/AGENTS.md): bug history, verification evidence, and human release review.
- For an explicitly requested issue goal, use [run-issue-goal](.agents/skills/run-issue-goal/SKILL.md): apply [goal.md](goal.md) to user-supplied tickets, then load scoped guidance as needed.

## Shared quality rules

- Every bug fix needs a nearby regression test that fails before the fix and passes after it. Cover both layers for cross-stack bugs when practical; explain any limitation and add the closest useful guard.
- Run checks for each changed layer, matching `.gitlab-ci.yml`. After checks pass, update `docs/bug-log.md` in the same change; an undocumented fix is incomplete.
- Canonical wire statuses are `open`, `pending`, `in_progress`, and `resolved`. Keep frontend/backend contracts consistent.
- Preserve GitLab CI, the merge request template, and `bug_fix_evidence`. For gate changes, run `BASE_REF=HEAD CHECK_WORKTREE=1 sh scripts/ci/check_bug_fix_evidence.sh` from the root.
- Report changes, regression coverage, checks actually run, remaining risk, human decisions, and relevant SDLC follow-up. A human decides whether to merge and release.

## Delegation

- Delegate matching work to the roles in the scoped guides unless the user requests no subagents. Routine docs/config edits do not trigger product reviews.
- Use `api_contract_reviewer` for API schema/status changes or cross-stack integration bugs; use `gitlab_ci_reviewer` for pipeline failures or CI configuration/helper changes.
- After bug-fix tests and the bug-log update, use `quality_evidence_reviewer` for the evidence audit. Its detailed scope is in the docs guide.
- Spawn named roles with their exact `agent_type`; `.codex/agents/*.toml` owns model and reasoning settings. Announce those settings and report unavailable roles/models honestly.
- Give each role bounded scope; run independent work within concurrency limits, reuse findings, and wait for results. All specialists are read-only and must not delegate again; the parent owns edits and verification.
- For remote GitLab work, identify the project and MR/pipeline revision. Distinguish observed remote results from local checks and proposed checks.
