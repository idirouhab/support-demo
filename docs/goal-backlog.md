# Example issue backlog

Prepared on 2026-10-06. [GitLab tracker #13](https://gitlab.com/idirouhab/support-demo/-/work_items/13) groups eight work items with acceptance criteria and regression plans. The issues are open; this preparation has not started a goal or implemented their fixes.

## Work items

| GitLab issue | Work | Classification |
| --- | --- | --- |
| [5](https://gitlab.com/idirouhab/support-demo/-/work_items/5) | Show an explicit successful empty-queue state | UX defect |
| [6](https://gitlab.com/idirouhab/support-demo/-/work_items/6) | Keep malformed ticket dates from crashing the dashboard | Confirmed robustness bug |
| [7](https://gitlab.com/idirouhab/support-demo/-/work_items/7) | Announce load failures and retry from the dashboard | Accessibility defect and recovery enhancement |
| [8](https://gitlab.com/idirouhab/support-demo/-/work_items/8) | Isolate ticket-store objects and validate status assignments | Confirmed data-layer contract bug |
| [9](https://gitlab.com/idirouhab/support-demo/-/work_items/9) | Filter the ticket queue by canonical status | Product enhancement |
| [10](https://gitlab.com/idirouhab/support-demo/-/work_items/10) | Add an optional validated status filter to GET tickets | API enhancement |
| [11](https://gitlab.com/idirouhab/support-demo/-/work_items/11) | Include untracked application files in the local evidence gate | Confirmed CI-helper bug |
| [12](https://gitlab.com/idirouhab/support-demo/-/work_items/12) | Reject deleted tests and bug logs as regression evidence | Confirmed CI-helper bug |

This is an optional example batch, not the default scope of goal.md. When explicitly selecting this batch, use the listed order. Empty-state work supports retry/filter UI work; the first CI issue establishes the test harness used by the second. A smaller goal can explicitly select only the first three issues. Choose the subset before starting so completion is measurable.

## Baseline matters

Use this prepared local workspace, with HEAD `dd78d76938834732bff9b2566b214d08fa6477f5` plus existing uncommitted application and agent changes. GitLab `main` was `ff38610acb030c509b5cc6a6eebb1e3e54dca6cb` at inspection and does not include that preparation. No preparation changes have been committed or pushed by this task. A fresh remote clone needs the prepared baseline before it can reproduce the same starting state.

Existing GitLab issues #1–#4 describe earlier defects already addressed in this working tree. They remain unchanged and are outside this example batch; a user may select any of them for a separate goal. Check actual behavior before editing; never undo a fix to manufacture a test failure.

## Start a goal

Supply the desired tickets with **Start goal.md for** followed by their IDs or URLs. To select this entire example batch, explicitly request the work items in tracker #13. The root [goal file](../goal.md) defines reusable working boundaries and completion criteria; the user request supplies the ticket scope. Nothing in this backlog is selected automatically.

The root [AGENTS.md](../AGENTS.md) routes that request to the [run-issue-goal skill](../.agents/skills/run-issue-goal/SKILL.md). The skill reads the goal, loads only the relevant folder guidance, and delegates focused work to the configured subagents. Detailed iteration and evidence rules live in [the issue loop](goal-loop.md).

No token budget is implied. Specify one only if desired. Reading or editing the goal file does not start execution or expand permissions.

## What was verified during preparation

- Existing GitLab backlog inspected; all eight new issue bodies and the tracker read back and matched the intended payloads.
- Frontend baseline: `npm test -- --no-cache` passed 28 tests. Isolated React/jsdom checks reproduced invalid-date failure, missing empty feedback, and missing retry/alert behavior; real-browser and screen-reader behavior was not tested.
- Backend: isolated data-layer/API probes reproduced shared-object mutation and noncanonical response status. No full backend suite was run for this documentation/configuration task.
- CI: disposable Git repositories reproduced successful gate exits for untracked implementation and deleted regression tests, without changing the application checkout.
- All seven agent TOML files parsed, all four AGENTS.md files route to the loop, and documentation links/whitespace were checked.

Suggested regression tests in GitLab are future implementation work, not passing tests claimed by this preparation. Follow [the issue loop](goal-loop.md) for actual run evidence and completion decisions.
