# Backend instructions

Applies to `backend/` in addition to the root instructions. This is the FastAPI/Pydantic API, tested with pytest. Paths below are relative to this folder.

## Implementation and contracts

- Keep routes and HTTP behavior in `app/main.py`, schemas/validation in `app/models.py`, and ticket data operations in `app/tickets.py`.
- Preserve canonical statuses `open`, `pending`, `in_progress`, and `resolved`. Centralize validation and keep schema definitions consistent; UI labels are not wire values.
- Check request validation, response shapes and HTTP codes, unknown ticket IDs, and state isolation when affected. Derive accepted inputs from the API schema.
- For schema or ticket-update changes, inspect `../frontend/src/api.ts` and `../frontend/src/types.ts`; read `../frontend/AGENTS.md` before working in that folder.

## Subagents

Delegate matching work without requiring the user to say “use subagents”:

- `backend_bug_spotter`: backend reviews and API bug investigations.
- `backend_test_scout`: test planning, coverage reviews, and regression planning for backend bugs.
- For a backend bug fix, use the spotter for diagnosis and the scout for the regression plan. Share existing findings to avoid duplicate analysis.
- Include `api_contract_reviewer` for API schema/status changes or frontend/backend mismatches. The root delegation rules apply; model/effort settings live in the role TOML files.

## Verification

- Put regression tests in `tests/`, close to the affected API or model tests. Assert concrete inputs, response bodies, and HTTP codes; isolate mutable ticket state.
- From `backend/`, run `pytest` using the project environment, matching the GitLab backend job. Dependencies are in `requirements.txt`; pytest configuration is in `pyproject.toml`.
- For cross-stack changes, run frontend checks too. After relevant checks pass, follow `../docs/AGENTS.md` to record bug-fix evidence.

## Goal iterations

For an active goal, follow [the issue loop](../docs/goal-loop.md). Give the spotter/scout the current issue, baseline, acceptance criteria, and latest failure. First add a focused API/model test and observe the intended failure, then make the smallest change and rerun it. Run the backend suite after the fix; include frontend checks for contract changes. Return issue-specific evidence and the next unresolved criterion, not a claim that the entire goal is finished.
