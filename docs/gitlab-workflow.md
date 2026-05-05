# GitLab Workflow

GitLab is the handoff point between local implementation work and the human release decision. Local changes can trace, fix, test, and document the issue; GitLab makes that work visible and enforceable in a merge request.

## What GitLab Does

1. Runs the independent CI checks in `.gitlab-ci.yml`.
2. Runs `bug_fix_evidence`, a quality gate that checks bug-fix evidence.
3. Stores `gitlab-quality-evidence.txt` as a CI artifact for reviewers.
4. Presents `.gitlab/merge_request_templates/bug-fix.md` as the human review surface.
5. Leaves merge and release approval with a person.

## Pipeline Stages

- `test`: runs backend tests and frontend tests.
- `quality`: runs the GitLab evidence gate.
- `build`: builds the frontend after tests and quality checks pass.

## Evidence Gate

The `bug_fix_evidence` job runs in merge request and branch pipelines. In merge request pipelines it compares against the MR target branch; in branch pipelines it compares against the default branch. When backend or frontend implementation/test files change, it requires:

- `docs/bug-log.md` to be updated
- backend app changes to include nearby backend tests
- frontend source changes to include nearby frontend tests

This gives GitLab a concrete quality role: it can fail a merge request that contains a code fix without regression coverage or bug-log evidence.

## Local Gate Preview

To preview the evidence gate against uncommitted local changes:

```bash
BASE_REF=HEAD CHECK_WORKTREE=1 sh scripts/ci/check_bug_fix_evidence.sh
```
