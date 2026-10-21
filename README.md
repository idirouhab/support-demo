# Support Ticket App

This repository contains a small full-stack support ticket application with a React dashboard, a FastAPI backend, automated tests, and GitLab CI/CD. It also includes a quality workflow for fixing issues with regression coverage, durable evidence, and human release review.

## Application

The backend exposes support ticket data through a FastAPI API. The frontend renders the ticket queue, status badges, priority indicators, and summary counts with React and Vite.

Core areas:

- `backend/`: FastAPI application, ticket models, fixtures, and backend tests
- `frontend/`: React application, API client, status formatting, and frontend tests
- `docs/`: engineering notes, issue history, quality process, and release review guidance
- `.gitlab-ci.yml`: GitLab pipeline for tests, quality evidence, and build verification
- `.gitlab/merge_request_templates/`: merge request templates for consistent review evidence
- `.github/workflows/`: GitHub CI, issue implementation, and read-only Codex PR review
- `scripts/ci/`: CI helper scripts used locally and in GitLab

## Status Contract

The backend returns support tickets with canonical API statuses:

- `open`
- `pending`
- `in_progress`
- `resolved`

The frontend may display `in_progress` as `In progress`, but the API wire value should remain `in_progress`. Status-related fixes should preserve that contract and include regression coverage for known and unknown statuses.

## Quality Workflow

Issue fixes should move through the same loop locally and in GitLab:

1. Reproduce or identify the issue while implementation context is fresh.
2. Add the closest regression test.
3. Make the smallest safe fix.
4. Run the same checks represented in GitLab CI.
5. Update `docs/bug-log.md` with the symptom, root cause, fix, regression test, checks run, evidence, and any human decision needed.
6. Open a GitLab merge request with the bug-fix template.
7. Use GitLab CI results and release-review guidance to decide whether to merge.

The quality workflow is described in [docs/quality-loop.md](docs/quality-loop.md). GitLab's role is described in [docs/gitlab-workflow.md](docs/gitlab-workflow.md).

## GitLab Workflow

GitLab is the review and enforcement layer after local changes are ready. The pipeline runs:

- `backend_tests`: backend API and contract tests
- `frontend_tests`: frontend rendering and helper tests
- `bug_fix_evidence`: evidence gate for regression tests and bug-log updates
- `frontend_build`: production frontend build

The `bug_fix_evidence` job publishes `gitlab-quality-evidence.txt` so reviewers can see what GitLab checked before deciding whether to merge and release.

## GitHub and Codex

The GitHub repository is [idirouhab/support-demo](https://github.com/idirouhab/support-demo).
Opening an issue as a repository writer starts Codex implementation, runs the quality
checks, and creates a `codex/issue-<number>` branch and pull request. A separate
read-only Codex review posts feedback on the PR. Nothing is merged or deployed
automatically. Public issues from people without write access do not start Codex.

See [the GitHub workflow guide](docs/github-workflow.md) for setup, manual retries,
security boundaries, usage costs, and the relationship to the existing GitLab CI.

## Local Setup

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend at `http://localhost:5173`. The backend runs at `http://localhost:8000`.

## Verification

Run the checks represented in GitLab CI:

```bash
cd backend
pytest
```

```bash
cd frontend
npm test
npm run build
```

Preview the GitLab evidence gate locally:

```bash
BASE_REF=HEAD CHECK_WORKTREE=1 sh scripts/ci/check_bug_fix_evidence.sh
```

## Issue History

Fixed bugs are recorded in [docs/bug-log.md](docs/bug-log.md). Each entry should include the date fixed, symptom, root cause, fix summary, regression test, checks run, evidence, human decision needed, and any follow-up SDLC opportunity.
