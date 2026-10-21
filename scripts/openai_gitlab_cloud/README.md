# OpenAI-hosted GitLab agents

This separate integration creates two reusable Agents API agents for
[`idirouhab/support-demo`](https://gitlab.com/idirouhab/support-demo):

- `support-demo-isolated-reviewer` reads an MR and its source, tests and evidence,
  then posts a review comment with actionable blockers.
- `support-demo-isolated-merger` updates a blocker comment and merges the reviewed
  source SHA when all checks pass. It waits up to 15 minutes per session.

Both run in OpenAI-hosted sandboxes. `cloud.py` submits sessions and exits; it does
not run inference, execute repository code, or keep a local polling worker alive.
The event receiver in [webhook.py](webhook.py) can supply future triggers from
GitLab webhooks. The original GitLab schedule was disabled at the user's request.
The receiver must be deployed and registered before event-driven watching works;
the Agents API does not automatically subscribe a saved agent to GitLab events.

See [webhook deployment](webhook-deployment.md) for the receiver, durable queue,
hosting requirements, and activation checks. Agent execution stays in OpenAI's
cloud; the receiver only authenticates events and coordinates sessions.

This directory has separate saved agents, vault, `.state.json`, comment markers,
CI switch and resource group from `../gitlab_agents/`. Do not enable both merge
implementations on the same MRs. Neither implementation is an approval source for
the other.

## Configure and launch

Use Python 3.12. From the repository root:

```bash
python3 -m venv scripts/openai_gitlab_cloud/.venv
scripts/openai_gitlab_cloud/.venv/bin/pip install -r scripts/openai_gitlab_cloud/requirements.txt
```

Add missing entries from [.env.example](.env.example) to the root `.env`; preserve
existing values. Both `OPENAI_API` and `OPENAI_API_KEY` are accepted; `OPENAI_API`
takes precedence when nonempty. Existing process environment values take precedence
over `.env`. The OpenAI application key needs Agents read/write, Responses write,
and Vaults read/write access. `GITLAB_TOKEN` needs GitLab API access, permission to
comment on this project, and permission to merge into the protected target branch.
Use a dedicated project-scoped bot identity.

```bash
scripts/openai_gitlab_cloud/.venv/bin/python scripts/openai_gitlab_cloud/cloud.py provision
scripts/openai_gitlab_cloud/.venv/bin/python scripts/openai_gitlab_cloud/cloud.py dispatch --mr 12
```

Omitting `--mr` considers every open, non-draft MR in this project. Provisioning
saves IDs to ignored `.state.json`. The OpenAI key never enters the sandbox.
The GitLab token is stored in an OpenAI vault: the sandbox receives a placeholder
that the network proxy substitutes only for HTTPS calls to `gitlab.com`.
Model selection is configurable through `OPENAI_AGENT_MODEL`.

## Original scheduled trigger (currently disabled)

[ci.yml](ci.yml) is a separate include for this implementation. Activation uses
only this directory and the include in the remote default branch; unrelated local
work is preserved. To configure or recreate activation:

1. Commit this directory and include `scripts/openai_gitlab_cloud/ci.yml` from the
   root `.gitlab-ci.yml`. Preserve any existing includes. This include also makes
   application checks run in MR pipelines.
2. Merge the integration onto the protected default branch.
3. Add masked, protected GitLab CI variables `OPENAI_API`, `GITLAB_TOKEN`, and
   `OPENAI_GITLAB_CLOUD_CONFIG` containing the compact JSON from `.state.json`.
   Scope these variables to the environment `openai-isolated-dispatch` so only
   the dispatch job receives them. Do not upload `.env`.
4. Create a GitLab pipeline schedule for the protected default branch, for example
   every five minutes, with `RUN_ISOLATED_CLOUD_AGENTS=1`. Keep the other integration's
   `RUN_CLOUD_AGENTS` switch unset on this schedule.

The scheduled job only dispatches sessions. A failed submission fails the job;
already active sessions are skipped. Only one dispatcher should be enabled for
this integration. The CI resource group serializes scheduled jobs; do not run a
manual dispatch concurrently with a scheduled dispatch.

Do not reactivate the schedule alongside the event receiver. The receiver has its
own single-worker lock and durable state; it does not share GitLab CI's resource
group. Manual dispatch must also be stopped while the receiver is running.

The schedule and CI include are not activated by provisioning. A newly required
`openai_gitlab_cloud_tests` job must exist and pass in the MR pipeline before this
merger can merge. Existing MRs without that job remain blocked until their branch
includes the integration and CI has rerun.

## Merge requirements

The helper requires an open, non-draft, conflict-free MR with GitLab status
`mergeable`, a complete review without blockers by the configured bot identity,
and unchanged source and target SHAs. It also requires:

- A successful MR head pipeline whose SHA equals the source SHA.
- Successful `backend_tests`, `frontend_tests`, `frontend_build`,
  `bug_fix_evidence`, and `openai_gitlab_cloud_tests` jobs in that pipeline.
- Zero remaining GitLab-required approvals and no unresolved review discussions.

Missing or unknown evidence blocks merging. Truncated, collapsed, binary/empty
diffs are conservatively treated as incomplete. Synthetic merged-results pipeline
SHAs are not accepted by this implementation. It does not add an extra human
approval requirement or bypass project approval rules. GitLab receives the
reviewed source SHA on the merge request.

These helper checks prevent accidental unsafe transitions; the helper runs in a
writable agent sandbox and is not a security boundary against a compromised agent
with the same token. GitLab protected branches and token permissions remain the
enforcement boundary. GitLab's merge endpoint guards the source SHA, not the target
SHA; there remains a small target-update race after the final target check.

## Monitor and recover

The dispatch comment contains session IDs. Inspect a session with:

```bash
scripts/openai_gitlab_cloud/.venv/bin/python scripts/openai_gitlab_cloud/cloud.py status --session SESSION_ID
```

Check the saved turn status. `idle` alone does not prove success: setup may still
be provisioning. Review and merge comments state observed outcomes, and GitLab MR
state confirms whether a merge occurred. API failures block the merge and are
reported in the merge comment when GitLab comments remain available.

If the reviewer finishes after the merger's wait expires, the next dispatch reuses
the complete review for the same source, target and helper/prompt version, and
launches only a new merger. Source, target or policy changes invalidate the review.

A timeout during session creation has an unknown outcome. Dispatch leaves a
`submitting` record and fails rather than blindly creating duplicates. Reconcile:

```bash
scripts/openai_gitlab_cloud/.venv/bin/python scripts/openai_gitlab_cloud/cloud.py recover --mr 12
```

Recovery looks up session metadata and restores known IDs. If no session can be
found, inspect the project's OpenAI sessions and cancel any unknown active work
before deleting only the isolated dispatch comment and retrying. Recovery does
not assume that an interrupted request failed to create a session.

Saved sessions retain history and may retain a sandbox. After retrieving any
needed artifacts, delete finished sessions through the Agents API
`DELETE /v1/agents/sessions/{session_id}` with `OpenAI-Beta: agents=v1`.
Disable the GitLab schedule before retiring the integration. To rotate the GitLab
token, update `.env`, rerun `provision`, and finish/cancel old sessions; existing
sandboxes do not receive a rotated credential automatically.

## Verification

```bash
scripts/openai_gitlab_cloud/.venv/bin/python -m pytest scripts/openai_gitlab_cloud/tests -q
```

Tests use API doubles and make no network calls. They cover merge gates, stale and
spoofed reviews, incomplete diffs, comment deduplication, source-SHA merging, late
reviews, session completion checks and partial-submission recovery. Live evidence
is recorded separately in [verification.md](verification.md).

API references: [Agents API quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart),
[hosted sandboxes](https://developers.openai.com/api/docs/guides/agents-api/environments/openai-hosted),
[vaults](https://developers.openai.com/api/docs/guides/agents-api/tools/vaults),
[GitLab merge requests](https://docs.gitlab.com/api/merge_requests/).
