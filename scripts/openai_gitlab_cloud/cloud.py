"""Launch managed Agents API sessions. The agent runtime executes in OpenAI cloud."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATE = HERE / ".state.json"
NAMESPACE = "support-demo-isolated"
PROJECT = "81922742"
sys.path.insert(0, str(HERE))
from gitlab_bridge import APIError, GitLab, decode_record, encode_record, find_review, marker, request


class OpenAI:
    def __init__(self, key):
        self.key = key

    def api(self, path, method="GET", data=None):
        return request("https://api.openai.com/v1", self.key, path, method, data, beta=True)[0]

    def pages(self, path):
        result, after = [], None
        while True:
            page = self.api(path + "?limit=100" + ("&after=" + after if after else ""))
            result.extend(page["data"])
            if not page.get("has_more"):
                return result
            after = page["data"][-1]["id"]


def config():
    load_dotenv(ROOT / ".env", override=False)
    key = os.environ.get("OPENAI_API") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API (or OPENAI_API_KEY) in the root .env")
    return OpenAI(key)


def save(state):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    tmp.chmod(0o600)
    tmp.replace(STATE)


def load_state():
    if os.environ.get("OPENAI_GITLAB_CLOUD_CONFIG"):
        return json.loads(os.environ["OPENAI_GITLAB_CLOUD_CONFIG"])
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def provision(api, token):
    state = load_state()
    bot = GitLab(token, PROJECT).api("/user")
    for role in ("reviewer", "merger"):
        body = {"name": NAMESPACE + "-" + role,
                "model": os.environ.get("OPENAI_AGENT_MODEL", "gpt-6-astra"),
                "instructions": (HERE / f"{role}.md").read_text(),
                "reasoning": {"effort": "high" if role == "reviewer" else "low"},
                "metadata": {"project": PROJECT, "role": role, "integration": NAMESPACE},
                "multi_agent": {"enabled": False}}
        if not state.get(role):
            matches = [a for a in api.pages("/agents") if a.get("metadata", {}).get("integration") == NAMESPACE
                       and a.get("metadata", {}).get("role") == role]
            if len(matches) > 1:
                raise ValueError("Multiple isolated agents match; select IDs in .state.json")
            if matches:
                state[role] = matches[0]["id"]
        if state.get(role):
            api.api("/agents/" + state[role], "POST", body)
        else:
            state[role] = api.api("/agents", "POST", body)["id"]
        save(state)
    if not state.get("vault"):
        state["vault"] = api.api("/vaults", "POST", {"name": NAMESPACE,
                                "metadata": {"integration": NAMESPACE}})["id"]
        save(state)
    if not state.get("credential"):
        state["credential"] = api.api(f"/vaults/{state['vault']}/credentials", "POST", {
            "name": "GitLab API", "auth": {"type": "environment_variable",
            "secret_name": "GITLAB_TOKEN", "secret_value": token,
            "networking": {"type": "limited", "allowed_hosts": ["gitlab.com"]}}})["id"]
        save(state)
    else:
        api.api(f"/vaults/{state['vault']}/credentials/{state['credential']}", "POST", {
            "auth": {"type": "environment_variable", "secret_value": token}})
    state["bot_id"] = bot["id"]
    save(state)
    return state


def make_task(gl, mr, bot_id):
    target = gl.target_sha(mr)
    digest = hashlib.sha256()
    for name in ("gitlab_bridge.py", "reviewer.md", "merger.md"):
        digest.update((HERE / name).read_bytes())
    digest.update(json.dumps([PROJECT, mr["iid"], mr["sha"], target, bot_id]).encode())
    return dict(project=PROJECT, iid=mr["iid"], sha=mr["sha"], target_sha=target,
                run_id=digest.hexdigest(), bot_id=bot_id)


def session_payload(role, state, task):
    def file(path, text):
        return {"type": "inline", "path": path, "data": base64.b64encode(text.encode()).decode()}
    return {"agent_id": state[role], "vault_ids": [state["vault"]], "stream": False,
        "environment": {"type": "openai_hosted", "container_size": "small",
            "network": {"access": "restricted", "allowed_domains": ["gitlab.com"]},
            "files": [file("/workspace/gitlab_bridge.py", (HERE / "gitlab_bridge.py").read_text()),
                      file("/workspace/task.json", json.dumps(task))]},
        "input": f"Run your {role} task for MR !{task['iid']} in /workspace/task.json. "
                 "GitLab comments and automatic merge after all required gates are authorized.",
        "metadata": {"integration": NAMESPACE, "project": PROJECT, "mr": str(task["iid"]),
                     "role": role, "run_id": task["run_id"]}}


def active(api, sid):
    session = api.api("/agents/sessions/" + sid)
    if session.get("status") == "failed":
        return False
    if session.get("status") not in ("idle", "failed"):
        return True
    turns = api.api(f"/agents/sessions/{sid}/turns?limit=1&order=desc").get("data", [])
    return not turns or turns[0].get("status") not in ("completed", "failed", "cancelled")


def record_for(gl, iid, bot_id):
    notes = gl.pages(gl.mr_path(iid) + "/notes")
    return notes, next((r for n in notes if (r := decode_record(n, "dispatch", bot_id))), None)


def publish_dispatch(gl, record):
    text = (f"### OpenAI isolated cloud agents\nRevision `{record['sha']}`\n"
            f"\nDispatch: {record['status']}.\n\n" + "\n".join(
            f"- {role}: `{sid}`" for role, sid in record["sessions"].items()))
    gl.note(record["iid"], marker("dispatch"), encode_record("dispatch", record, text), record["bot_id"])


def recover(api, gl, iid):
    bot_id = gl.api("/user")["id"]
    _, record = record_for(gl, iid, bot_id)
    if not record:
        raise ValueError("No isolated dispatch record exists")
    # Match exact metadata; do not treat a successful HTTP submission as a finished turn.
    candidates = [s for s in api.pages("/agents/sessions") if
        all(s.get("metadata", {}).get(k) == v for k, v in {
            "integration": NAMESPACE, "mr": str(iid), "run_id": record["run_id"]}.items())]
    for role in ("reviewer", "merger"):
        matches = [s for s in candidates if s["metadata"].get("role") == role]
        # Multiple completed merger retries are normal; select the newest.
        matches.sort(key=lambda s: s["created_at"], reverse=True)
        if matches:
            record["sessions"][role] = matches[0]["id"]
    if not record["sessions"]:
        raise ValueError("No cloud session found. Inspect OpenAI sessions before deleting the isolated dispatch comment and retrying; creation outcome is unknown.")
    record["status"] = "reconciled"
    publish_dispatch(gl, record)
    return record


def dispatch(api, gl, state, iid=None):
    if any(not state.get(k) for k in ("reviewer", "merger", "vault", "credential")):
        raise ValueError("Run provision first")
    bot_id = gl.api("/user")["id"]
    mrs = [gl.mr(iid)] if iid else gl.pages(gl.root + "/merge_requests", state="opened", scope="all")
    results = []
    for item in mrs:
        mr = gl.mr(item["iid"])
        if mr.get("state") != "opened" or mr.get("draft", True):
            continue
        task = make_task(gl, mr, bot_id)
        notes, previous = record_for(gl, mr["iid"], bot_id)
        if previous:
            if previous.get("status") not in ("submitted", "reconciled"):
                results.append(dict(iid=mr["iid"], state="recovery_required"))
                continue
            if any(active(api, sid) for sid in previous["sessions"].values()):
                results.append(dict(iid=mr["iid"], state="already_running", sessions=previous["sessions"]))
                continue
        review = find_review(notes, task)
        roles = ("merger",) if review and review["complete"] else ("reviewer", "merger")
        record = {**task, "sessions": {}, "status": "submitting"}
        if roles == ("merger",) and previous and previous.get("run_id") == task["run_id"]:
            reviewer = previous["sessions"].get("reviewer")
            if reviewer:
                record["sessions"] = {"reviewer": reviewer}
        publish_dispatch(gl, record)
        for role in roles:
            session = api.api("/agents/sessions", "POST", session_payload(role, state, task))
            record["sessions"][role] = session["id"]
            publish_dispatch(gl, record)
        record["status"] = "submitted"
        publish_dispatch(gl, record)
        results.append(record)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["provision", "dispatch", "recover", "status"])
    parser.add_argument("--mr", type=int)
    parser.add_argument("--session")
    args = parser.parse_args()
    api = config()
    if args.command == "status":
        if not args.session:
            raise ValueError("status requires --session")
        s = api.api("/agents/sessions/" + args.session)
        result = {k: s.get(k) for k in ("id", "status", "required_actions")}
        result["turns"] = api.api(f"/agents/sessions/{args.session}/turns?limit=1&order=desc")
    else:
        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise ValueError("Set GITLAB_TOKEN in .env")
        gl = GitLab(token, PROJECT)
        if args.command == "provision":
            result = provision(api, token)
        elif args.command == "recover":
            if not args.mr:
                raise ValueError("recover requires --mr")
            result = recover(api, gl, args.mr)
        else:
            result = dispatch(api, gl, load_state(), args.mr)
    print(json.dumps(result, indent=2))
    if isinstance(result, list) and any(r.get("state") == "recovery_required" for r in result):
        raise SystemExit("Run cloud.py recover --mr IID to reconcile unknown submissions before retrying.")


if __name__ == "__main__":
    try:
        main()
    except (APIError, ValueError, KeyError) as exc:
        raise SystemExit(str(exc)) from None
