"""Register only this integration's GitLab webhook after HTTPS health succeeds."""
import argparse
import json
import os
import re
from urllib.parse import urlsplit
from urllib.request import build_opener

from dotenv import load_dotenv

import cloud
from gitlab_bridge import NoRedirect

NAME = "OpenAI isolated cloud agents (events)"


def register(gl, base_url, secret):
    url = urlsplit(base_url)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.path not in ("", "/")):
        raise ValueError("Use a public HTTPS origin without credentials, path or query")
    if not re.fullmatch(r"whsec_[A-Za-z0-9+/]{43}=", secret):
        raise ValueError("GITLAB_WEBHOOK_SECRET must encode a 32-byte signing key")
    base_url = base_url.rstrip("/")
    with build_opener(NoRedirect).open(base_url + "/healthz", timeout=15) as response:
        if json.loads(response.read()).get("status") != "ok":
            raise ValueError("Webhook receiver is not healthy")
    # The user explicitly stopped polling. Never enable or recreate a schedule.
    schedule = gl.api(gl.root + "/pipeline_schedules/4477979")
    if schedule.get("active"):
        raise ValueError("Disable schedule 4477979 before activating event dispatch")
    hooks = [h for h in gl.pages(gl.root + "/hooks") if h.get("name") == NAME]
    if len(hooks) > 1:
        raise ValueError("Multiple matching webhooks; inspect them before changing configuration")
    body = dict(name=NAME, description="Trigger OpenAI-hosted review and merge sessions from project events",
                url=base_url + "/webhooks/gitlab", signing_token=secret, enable_ssl_verification=True,
                merge_requests_events=True, pipeline_events=True, note_events=True, push_events=True,
                issues_events=False, job_events=False, tag_push_events=False, confidential_note_events=False)
    path = gl.root + "/hooks" + ("/" + str(hooks[0]["id"]) if hooks else "")
    result = gl.api(path, "PUT" if hooks else "POST", body)
    return {k: result.get(k) for k in ("id", "name", "url", "merge_requests_events", "pipeline_events", "note_events", "push_events")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    load_dotenv(cloud.HERE / ".webhook.env", override=False)
    cloud.config()
    print(json.dumps(register(cloud.GitLab(os.environ["GITLAB_TOKEN"]), args.url,
                              os.environ["GITLAB_WEBHOOK_SECRET"]), indent=2))
