# Demo Seeded Bugs

These defects are intentionally present on the `codex/seed-demo-bugs` branch for SDLC planning, triage, regression-test, and review demos. They are not fixed-bug-log entries. Add entries to `docs/bug-log.md` only when each bug is repaired.

## Seeded Defects

### Resolved Tickets Are Hidden

- Symptom: The API no longer returns resolved ticket `T-104`, so the dashboard shows fewer tickets than the fixture data contains.
- Location: `backend/app/tickets.py`
- Likely detection: Backend contract test or manual API check of `GET /api/tickets`.
- Fix direction: Return the full ticket list unless a real filter parameter is added.

### API Failures Look Like Empty Queues

- Symptom: When `GET /api/tickets` returns a non-2xx status, the frontend renders an empty queue instead of the error state.
- Location: `frontend/src/api.ts`
- Likely detection: Frontend error-state test or browser test with the backend down.
- Fix direction: Throw on non-OK responses so `App` can render the existing error message.

### Summary Counts Are Inflated

- Symptom: The dashboard counts every ticket as active and counts medium-priority tickets as high priority.
- Location: `frontend/src/App.tsx`
- Likely detection: Frontend rendering test that asserts summary metrics against known ticket fixtures.
- Fix direction: Count active tickets by excluding `resolved`, and count high priority only when `priority === "high"`.

### `in_progress` Status Renders As Unknown

- Symptom: Backend status `in_progress` renders as `Unknown` even though it is a canonical API value.
- Location: `frontend/src/status.ts` and `frontend/src/types.ts`
- Likely detection: Frontend status-helper test using the backend wire value `in_progress`.
- Fix direction: Use `in_progress` as the typed wire value and format it as `In progress`.

### High Priority Badge Looks Low Priority

- Symptom: High-priority tickets use the same green treatment as low-priority tickets, reducing visual urgency.
- Location: `frontend/src/styles.css`
- Likely detection: Visual review, screenshot comparison, or style assertion.
- Fix direction: Restore a distinct high-priority danger treatment.
