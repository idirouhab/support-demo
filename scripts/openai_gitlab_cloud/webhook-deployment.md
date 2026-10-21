# Deploy event-driven GitLab agents

Deploy one persistent webhook receiver so GitLab changes start the existing
OpenAI-hosted agents automatically. This replaces the five-minute GitLab timer.
The receiver authenticates notifications, records work in SQLite, and calls the
Agents API. It does not run the agent model or execute repository code.

## Current status

The receiver is implemented and locally tested, but **not deployed**. GitLab
schedule `4477979` remains disabled. No project webhook has been registered.
The configured `Staging-Server` was unreachable over SSH during preparation;
the local Google Cloud login also requires reauthentication. Select an accessible
host and a public HTTPS hostname before activation.

## How events become work

- MR creation, updates, approvals, and resolution of all review threads wake the
  corresponding MR. Draft and closed MRs are ignored after checking GitLab.
- Completed/blocked pipeline events and branch pushes refresh affected work.
  Events without an MR IID refresh all open non-draft MRs, including when the
  target branch changed.
- Human MR comments wake a fresh state check. Comment text is never executed or
  forwarded as agent instructions. The bot's dispatch and coordinator comments
  are ignored; its structured review comment is accepted.
- Optional OpenAI `agent.session.idle` and `agent.session.failed` webhooks wake a
  state check. The receiver retrieves session metadata before selecting an MR;
  it never interprets `idle` as successful completion.
- While a submitted session is active, the queue checks it every 30 seconds for
  at most 90 minutes. This follows existing work, rather than periodically
  scanning GitLab for new work. Once blocked work settles, it waits for an event.

The existing review, source/target SHA, CI-job, approval, conflict and discussion
gates remain unchanged. Only the hosted merge coordinator invokes the merge API.
The receiver can refresh the same blocker comment without starting another model
session. Source, target or helper/prompt changes require a fresh review.

## Hosting and credentials

Use one Linux host with Docker Compose, a persistent disk, outbound HTTPS to
GitLab/OpenAI, and a public HTTPS reverse proxy. A stateless function without
persistent storage and a background worker is unsuitable for this package.

1. Copy this directory to the host, excluding `.env`, `.state.json`, caches and
   `.webhook-data`. The Docker build uses an explicit allowlist and never copies
   credentials into its image.
2. Create a mode-600 `.webhook.env` on the host with `OPENAI_API` (or
   `OPENAI_API_KEY`), `GITLAB_TOKEN`, and `OPENAI_GITLAB_CLOUD_CONFIG` containing the
   provisioned agent/vault/bot IDs from `.state.json`. Use the existing bot token
   and cloud configuration; do not provision a second pair of agents.
3. Generate `GITLAB_WEBHOOK_SECRET` as `whsec_` followed by base64 of 32 random
   bytes, and add it to `.webhook.env`. Keep it out of commits and logs. This is
   the GitLab HMAC signing key, not the GitLab API token.
4. Confirm schedule `4477979` is disabled and no manual dispatcher is running.
   Then run from this directory:

   ```bash
   docker compose up -d --build
   curl --fail http://127.0.0.1:8080/healthz
   ```

   Startup checks the bot identity and queues one reconciliation of open MRs.
   Starting the service therefore authorizes processing existing ready MRs.
5. Configure your existing reverse proxy to route the chosen HTTPS hostname to
   `127.0.0.1:8080`. Preserve the request body and `webhook-*` headers. A minimal
   Caddy site block is:

   ```caddyfile
   agents.example.com {
       request_body {
           max_size 2MB
       }
       reverse_proxy 127.0.0.1:8080
   }
   ```

   Replace the example hostname with a real DNS name pointed at this host. Use a
   trusted TLS certificate; GitLab certificate verification stays enabled.
6. With the same private `.webhook.env` available to the configuration script,
   run from the repository root:

   ```bash
   backend/.venv/bin/python scripts/openai_gitlab_cloud/configure_webhook.py \
     --url https://agents.example.com
   ```

   The script checks HTTPS health and the disabled schedule, then creates or
   updates only the hook named **OpenAI isolated cloud agents (events)**. It
   configures MR, pipeline, note and push events. Other project hooks are preserved.
7. Send a test delivery from GitLab's webhook settings, then exercise a real
   harmless MR with an unresolved inline discussion. Confirm review and blocker
   comments, passing required CI, and automatic merge after resolving the thread.

OpenAI lifecycle webhooks are optional because the durable queue follows active
sessions itself. To enable them, register `/webhooks/openai` through the OpenAI
project's webhook settings for `agent.session.idle` and `agent.session.failed`;
store that endpoint's signing key as `OPENAI_WEBHOOK_SECRET` in `.webhook.env`
and recreate the container. The route is disabled when that key is absent.

## Reliability and recovery

Both webhook routes verify Standard Webhooks HMAC signatures against the raw
body and reject timestamps more than five minutes away. Keep the host clock
synchronized. Requests are acknowledged only after SQLite commits the work.
Duplicate delivery IDs are retained for 30 days. Events arriving during a job
increment its generation so the worker cannot accidentally discard a newer event.

Run one replica with one persistent `webhook-data` volume. A file lock prevents
two workers sharing that volume. Restarting releases stale queue leases and
refreshes open MRs. Do not run separate replicas with separate databases.

API failures retry up to five times with backoff. A revision can launch at most
three sets of sessions; this survives repeated webhook notifications and service
restarts. Unknown session-creation outcomes use the existing recovery command
instead of blindly resubmitting. Exhausted jobs make `/healthz` return HTTP 503
and attempt to post an attention comment. Monitor this endpoint and container
logs; Docker does not restart a container merely because its health is degraded.

If a revision exhausts its launch budget, stop the receiver and inspect GitLab
comments and OpenAI session outcomes. Reconcile uncertain submissions using
`cloud.py recover --mr IID`. After confirming there is no unknown active work,
an operator can reset only that revision's `launches` row in SQLite and restart
the receiver. Do not delete the database to reset one MR.

The SQLite database and signing key must persist through deployments. Missed
deliveries during downtime can be redelivered from GitLab; service startup also
refreshes current open MRs. There is no periodic catch-up scan for events GitLab
never delivers while the receiver stays up. Use webhook-delivery monitoring and
redelivery for that case.

To stop new dispatches, run `docker compose stop webhook` and disable/delete this
specific project webhook. Already submitted cloud sessions can still finish and
merge; stopping the receiver does not cancel them. The GitLab schedule stays off.

## Verification

```bash
backend/.venv/bin/python -m pytest scripts/openai_gitlab_cloud/tests -q
```

The tests cover HMAC tampering/replay, event filtering, duplicate/concurrent
deliveries, durable retries and leases, new events during work, session limits,
late review completion, failure comments, and authenticated HTTP ingress. They
also retain the existing merge-gate tests. Container startup, public HTTPS,
provider delivery and a full automatic merge must be verified after deployment.

References: [GitLab webhook events](https://docs.gitlab.com/user/project/integrations/webhook_events/),
[GitLab signing tokens](https://docs.gitlab.com/user/project/integrations/webhooks/#signing-tokens),
[OpenAI session webhooks](https://developers.openai.com/api/docs/guides/agents-api/sessions/webhooks).
