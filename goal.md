# Resolve the supplied tickets

Implement and verify the ticket or tickets selected in the user's start request. Continue until every selected acceptance criterion and applicable verification step is satisfied. This file defines the reusable goal contract; it contains no default ticket list.

## Start with scope

Say **Start goal.md for** followed by a ticket ID, ticket URL, or list of tickets. Ticket text supplied directly in the conversation is also valid input. No file editing or long prompt is needed.

The root [AGENTS.md](AGENTS.md) routes the request to [run-issue-goal](.agents/skills/run-issue-goal/SKILL.md). Creating, reading, or editing these instructions alone does not start execution.

## Resolve the selected work

- Take scope from the user's request, not a historical backlog, example, previous run, or hardcoded issue range.
- Resolve bare GitLab issue IDs against this checkout's GitLab remote; preserve the project identity of explicit URLs. Confirm that the selected ticket applies to this repository before changing code. Ask only if project identity or intended scope is ambiguous.
- Read each selected ticket's current description, acceptance criteria, and dependencies. For pasted tickets, use the supplied content and record that its remote state is unverified.
- If a start request supplies no ticket and no matching active goal exists, ask for the ticket IDs/URLs or ticket text. Never silently select the example backlog.
- Expand a tracker into child issues only when the user requests that scope. Dependencies outside the selected set are context or blockers, not permission to implement more tickets.
- Record the resolved scope and measurable criteria in the active goal and `docs/goal-progress.md`. On resume, recover that scope from the matching active goal/checkpoint; do not import completed work from a different run.

## Execute the appropriate loop

- Inspect this checkout's actual branch, HEAD, and worktree. Preserve existing changes and do not reset to a remote branch to manufacture a clean baseline.
- Classify each ticket: bug fix, enhancement, tests, documentation, configuration, or investigation. Choose checks that prove its acceptance criteria. Bugs need meaningful failing-then-passing regression tests; enhancements need observable acceptance coverage. Documentation and investigation tasks need appropriate evidence, not artificial application failures.
- Follow [the issue loop](docs/goal-loop.md) and load only the relevant nested `AGENTS.md` guidance. Use the matching specialist subagents; the parent owns implementation and verification. Report unavailable capabilities honestly.
- Work in dependency order within the selected scope. Verify one issue, record evidence, then continue. If an issue is already satisfied, prove it; if blocked, record the cause and continue independent selected work.
- Maintain `docs/goal-progress.md` with scope, criteria, observed commands/results, source state, evidence links, remaining gaps, and the next action. Revalidate stale evidence on resume.
- Keep changes local unless the user separately authorizes external writes. Do not post comments, close issues, push, merge, or deploy by default. A human retains merge/release decisions.

## Completion criteria

- Every selected ticket satisfies its agreed acceptance criteria, supported by observed checks or documented proof it was already satisfied at baseline.
- The final combined changes pass all applicable tests, builds, CI-helper checks, evidence gates, and diff/documentation checks for their actual scope. Unrelated application suites are not required for documentation-only work.
- Each verified bug fix has dated evidence in `docs/bug-log.md` after its checks pass. Label enhancements honestly where the repository gate requires an evidence entry; do not invent bug history for routine docs/configuration changes.
- `docs/goal-progress.md` accounts for every selected ticket and any remaining risk. Evidence review finds no unresolved selected criteria; proposed checks are not presented as executed and local results are not presented as remote CI results.
- The final handoff links ticket outcomes and evidence, reports limitations, and identifies any human decision still needed.

Continue while selected, authorized work remains. For a single-ticket goal, finish when that ticket and all required checks are complete. For multiple tickets, one finished issue is not enough. Respect user pause/stop requests and current goal-tool budget/status rules. No token budget is implied.
