# Frontend instructions

Applies to `frontend/` in addition to the root instructions. This is the React/TypeScript UI, built with Vite and tested with Vitest and Testing Library. Paths below are relative to this folder.

## Implementation and contracts

- Keep API access in `src/api.ts`, shared ticket types in `src/types.ts`, and status formatting/validation in `src/status.ts`.
- Render the wire value `in_progress` as `In progress`, never `Unknown`. Keep status mappings centralized instead of duplicating them across components.
- Unknown response statuses must degrade gracefully. Test all canonical statuses plus an unknown value; do not require the wire alias `in-progress`.
- Check loading, empty, success, and error states, ticket-edit interactions, and accessible names and keyboard behavior when affected.
- For API boundary changes, inspect the backend contract and read `../backend/AGENTS.md` before working there.

## Subagents

Delegate matching work without requiring the user to say “use subagents”:

- `frontend_issue_spotter`: frontend reviews and UI bug investigations.
- `frontend_test_scout`: test planning, coverage reviews, and regression planning for frontend bugs.
- For a frontend bug fix, use the spotter for diagnosis and the scout for the regression plan. Share existing findings to avoid duplicate analysis.
- Include `api_contract_reviewer` when the issue crosses the API boundary. The root delegation rules apply; model/effort settings live in the role TOML files.

## Verification

- Add regression tests beside the affected code, using `src/App.test.tsx` and `src/status.test.ts` as existing patterns.
- Prefer observable output and accessible interaction assertions over component internals or broad snapshots. Keep async tests and mocks deterministic.
- From `frontend/`, run `npm test` and `npm run build` to match GitLab's frontend jobs.
- For cross-stack changes, run backend checks too. After relevant checks pass, follow `../docs/AGENTS.md` to record bug-fix evidence.

## Goal iterations

For an active goal, follow [the issue loop](../docs/goal-loop.md). Give the spotter/scout the current issue, baseline, acceptance criteria, and latest failure. First add a focused observable-behavior test and observe the intended failure, then implement and rerun it. Run frontend tests and build after the fix; include backend checks for contract changes. Never weaken assertions or label a build failure as a pass to advance the queue. Return issue-specific evidence and the next unresolved criterion.
