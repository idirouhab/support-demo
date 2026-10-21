# Verification — October 6, 2026

This is a new isolated integration, not a support-ticket product bug fix.
Existing application changes and the separate `scripts/gitlab_agents` launcher
are outside this verification scope.

## Local evidence

- `backend/.venv/bin/python -m pytest scripts/openai_gitlab_cloud/tests -q`:
  **55 passed**. The existing backend environment supplied the test dependencies;
  installation into a new environment was unavailable through the local package
  mirror. The documented clean install command is not claimed as verified here.
- Python compilation and `git diff --check`: passed.
- Both CI YAML files parsed locally. GitLab's project CI lint endpoint validated
  a merged representation of the current root CI and this optional include:
  `valid: true`, no errors, no warnings. This is configuration validation, not a
  passing pipeline for the uncommitted integration.
- `gitlab_ci_reviewer` independently checked the isolated CI configuration and
  reproduced the fixed session-retry cases with API doubles; no further findings
  in its bounded review.

## Cloud resources

Provisioned and saved locally in ignored `.state.json`:

- Reviewer: `agent_7f3e28096c3a4f53bc84f313aeb2b627dadd25893168476bae`
- Merge coordinator: `agent_fd9eb8fd5d8c4190aa216bc84452c5be42bfadce54a24850ab`
- Vault: `vault_fbb3ab3e78fe4494a28f1735263e05ecf393795672194af6bd`

Both saved agents use `gpt-6-astra`. A read-only hosted smoke session
`sess_05a3b2a220df74ac006ac51feec66881958fd9970854ea5ed3` completed and reported
GitLab user `43094426` and project `idirouhab/support-demo` (`81922742`). This
verified vault-backed GitLab access from an OpenAI-hosted sandbox.
The smoke session was deleted after retrieving its result to release its sandbox.

## Live merge request

Dispatched both agents for [MR !12](https://gitlab.com/idirouhab/support-demo/-/merge_requests/12):

- Source SHA: `077f2b6265ea87f6d57a4eac62772ab93da18afc`
- Target SHA: `ff38610acb030c509b5cc6a6eebb1e3e54dca6cb`
- Reviewer session: `sess_01dc1c8bd3d3e96f006ac52052abac819588b61cafdf3109f1`
- Merger session: `sess_0a34a8ab8915e669006ac52063812081938a2e847b869cd233`

Observed [pipeline 2619933813](https://gitlab.com/idirouhab/support-demo/-/pipelines/2619933813)
at that source SHA reported success, but its job list contained only
`bug_fix_evidence`. It does not satisfy this integration's required job policy.
The [dispatch record](https://gitlab.com/idirouhab/support-demo/-/merge_requests/12#note_3964453062)
was posted successfully. The reviewer completed and posted a
[review with no blocking code findings](https://gitlab.com/idirouhab/support-demo/-/merge_requests/12#note_3964464411)
for the template-only change. The coordinator posted a
[merge-blocker comment](https://gitlab.com/idirouhab/support-demo/-/merge_requests/12#note_3964458009)
listing the missing backend tests, frontend tests, frontend build, and isolated
cloud-agent tests. The coordinator session continues its bounded wait; no
successful merge is claimed. A passing pipeline containing only the evidence gate
was correctly insufficient to authorize a merge.

## Initial activation state and remaining limits

At the initial verification above, the CI include and schedule were not activated.
No integration commit or pipeline deployment was claimed. Activation requires this isolated
integration, configure protected CI variables, and enable only the chosen
implementation's schedule. Automatic MR merging after checks is authorized; this
integration does not automate releases.

Unit tests prove helper behavior with doubles, not resilience against an agent
bypassing its writable helper. GitLab permissions remain the enforcement boundary.
Review the token's project scope and protected-branch settings before unattended
use, and retain the SHA checks and named CI-job checks when extending the workflow.

## Deployment — October 6, 2026

The user subsequently authorized activation. Only this directory and a minimal
CI include were published in [MR !14](https://gitlab.com/idirouhab/support-demo/-/merge_requests/14).
[Pipeline 2918756434](https://gitlab.com/idirouhab/support-demo/-/pipelines/2918756434)
passed all five required jobs at source commit
`bdf8517ea78eddb177c9f222478976306c87f40b`. Required GitLab approvals were satisfied
and there were no unresolved discussions. The MR was merged to protected `main`
as `1751f3352bc31506da79cdf7decac8124210526a`.

The OpenAI key, GitLab token, and saved-agent configuration were configured as
masked, protected, non-expanding CI variables scoped to `openai-isolated-dispatch`.
No other local application changes were published. The other integration's
dispatch switch is not configured in these variables or this schedule.

Schedule `4477979`, **OpenAI cloud agents (isolated)**, is active on
`refs/heads/main`, configured every five minutes in `America/New_York` with
`RUN_ISOLATED_CLOUD_AGENTS=1`. An immediate scheduled run created
[pipeline 2918771823](https://gitlab.com/idirouhab/support-demo/-/pipelines/2918771823)
at the deployed merge commit. Its
[OpenAI dispatch job 16976082747](https://gitlab.com/idirouhab/support-demo/-/jobs/16976082747)
completed successfully. This confirms the GitLab runner can load the scoped
credentials and execute the cloud dispatcher without a local process.

Existing MR !12 still requires its source branch to incorporate the integration
and rerun the complete CI pipeline. The watcher does not bypass missing jobs or
update source branches automatically. Disabling this GitLab schedule stops future
dispatches; already-running OpenAI sessions have their own bounded lifecycle.

## Event-driven replacement — October 6, 2026

The user stopped schedule `4477979`; a subsequent GitLab API read confirmed
`active: false` and no project webhooks. Remote `main` was still
`1751f3352bc31506da79cdf7decac8124210526a` at that check.

Added an authenticated webhook receiver, persistent SQLite event queue, bounded
session recovery, a private Docker Compose deployment, and an idempotent GitLab
hook registration command. This is an integration enhancement, not a product
bug fix. Existing merge gates and agent instructions are unchanged.

Local verification: `backend/.venv/bin/python -m pytest
scripts/openai_gitlab_cloud/tests -q` reported **92 passed**, including a local
HTTP delivery test and concurrent duplicate-delivery coverage. No provider
webhook delivery or new automatic merge has been claimed.

Live deployment remains pending: SSH to the configured `Staging-Server` timed
out; Google Cloud could not refresh authentication without interactive login.
The local Docker daemon was unavailable, so a container build/start is also
unverified. The schedule remains disabled while a public HTTPS host is selected.
