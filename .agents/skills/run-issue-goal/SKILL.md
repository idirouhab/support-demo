---
name: run-issue-goal
description: Start or continue a goal for user-supplied GitLab ticket IDs, URLs, or ticket text using goal.md, scoped AGENTS.md guidance, specialist subagents, and verification iterations. Use for an explicit request to run a ticket goal; creating or editing the goal or skill does not start it.
---

# Run the issue goal

Apply the reusable [goal.md contract](../../../goal.md) to the tickets selected by the user. Ticket scope comes from the request or a matching active goal, never a default backlog.

## Resolve the request before creating a goal

1. Read goal.md, or the alternative goal file explicitly selected by the user. A request to prepare, inspect, or edit instructions does not authorize execution.
2. Resolve ticket IDs/URLs from the start request or its explicit conversation reference. Bind bare GitLab IDs to this checkout's GitLab remote; keep the project identity of explicit URLs. Read the selected issues using the existing authenticated CLI/connector. For pasted tickets, retain the supplied content and mark remote state unverified. Confirm repository relevance before implementation; clarify ambiguous project/scope rather than guessing.
3. Ask for ticket IDs/URLs or ticket text if none are supplied and there is no matching active goal. Do not select example issues or all open tickets. Expand a tracker into child issues only when the user requests it; otherwise do not silently add linked work or dependencies.
4. Record the resolved project/ticket identities, requested outcome, measurable acceptance criteria, dependencies, and constraints. If criteria are incomplete, derive testable checks from the stated intent and repository contract; ask only when a material product decision is missing.
5. On an explicit start/run request, inspect the active goal. If none exists, create a concrete objective from the resolved ticket scope plus goal.md's boundaries and completion criteria, not a vague instruction to read a file later. Set a token budget only if the user supplied one. Continue a matching active goal; do not overwrite a different unfinished goal or silently merge scopes.
6. For resume requests, recover the selected tickets from the matching active goal and checkpoint and follow current goal-tool/UI resume rules. Do not create a replacement goal to emulate resume. If goal tools are unavailable, state the limitation instead of claiming Goal mode is active.

## Load only what the iteration needs

- [Root AGENTS.md](../../../AGENTS.md) supplies shared rules and specialist routing. Read child guidance only for the current scope; read docs guidance when recording or reviewing evidence.
- Read [docs/goal-loop.md](../../../docs/goal-loop.md) for iteration, checkpoint, verification, and stopping rules. Reuse it throughout the run.
- The [example backlog](../../../docs/goal-backlog.md) is optional historical context, not default input. Read it only when the user explicitly selects that batch or needs its history.
- Reconcile docs/goal-progress.md with the active goal's project/ticket scope and actual worktree before resuming. Preserve previous run history; do not reuse its verified status for a new ticket set.

## Delegate, implement, verify, continue

Choose the applicable subagents and configured model/effort values from repository guidance. Supply the current ticket, scope/revision, acceptance checklist, and existing evidence. Keep independent analysis parallel within available slots and implementation with the parent; reuse relevant results.

Classify the work and follow the issue loop with appropriate verification. Bug fixes require meaningful red/green regression evidence; enhancements require acceptance coverage. Documentation, configuration, and investigation tickets use validation suited to their actual behavior and criteria. Do not fabricate a runtime defect or run unrelated suites just to resemble a code-fix loop.

Record per-ticket results and the next action in docs/goal-progress.md. For one ticket, complete when its criteria and required verification are satisfied. For multiple tickets, continue through the selected set; one completed issue is insufficient. Do not ask whether to continue already-authorized work.

Use goal-status tools under their current rules. Respect explicit pause/stop requests, budgets, and genuine blockers. This skill grants no additional permission to post comments, close issues, push, merge, or deploy.
