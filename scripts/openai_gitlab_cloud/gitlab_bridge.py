"""Uploaded into OpenAI-hosted sessions; uses only Python's standard library."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

REQUIRED_JOBS = ("backend_tests", "frontend_tests", "frontend_build",
                 "bug_fix_evidence", "openai_gitlab_cloud_tests")


class APIError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward an authentication header to a redirect.


def request(base, token, path, method="GET", data=None, beta=False):
    headers = {"Authorization": f"Bearer {token}"} if beta else {"PRIVATE-TOKEN": token}
    if beta:
        headers["OpenAI-Beta"] = "agents=v1"
    headers["Content-Type"] = "application/json"
    req = Request(base + path, headers=headers, method=method,
                  data=None if data is None else json.dumps(data).encode())
    try:
        with build_opener(NoRedirect).open(req, timeout=60) as response:
            body = response.read()
            return (json.loads(body) if body else None), response.headers
    except HTTPError as exc:
        # Error bodies can echo request credentials. Do not print them.
        raise APIError(f"{method} {path.split('?')[0]} returned HTTP {exc.code}") from None
    except (URLError, TimeoutError):
        raise APIError(f"{method} {path.split('?')[0]} failed; outcome may be unknown") from None


class GitLab:
    def __init__(self, token, project="81922742"):
        self.token = token
        self.project = str(project)
        self.root = f"/projects/{quote(self.project, safe='')}"

    def api(self, path, method="GET", data=None):
        return request("https://gitlab.com/api/v4", self.token, path, method, data)[0]

    def pages(self, path, **params):
        result, page = [], 1
        while True:
            values, headers = request("https://gitlab.com/api/v4", self.token,
                path + "?" + urlencode({**params, "per_page": 100, "page": page}))
            if not isinstance(values, list):
                raise APIError("Expected a GitLab list response")
            result.extend(values)
            next_page = headers.get("X-Next-Page")
            if next_page:
                page = int(next_page)
            elif len(values) == 100 and next_page is None:
                page += 1
            else:
                return result

    def mr_path(self, iid):
        return f"{self.root}/merge_requests/{int(iid)}"

    def mr(self, iid):
        return self.api(self.mr_path(iid) + "?with_merge_status_recheck=true")

    def target_sha(self, mr):
        branch = quote(mr["target_branch"], safe="")
        return self.api(f"{self.root}/repository/branches/{branch}")["commit"]["id"]

    def note(self, iid, marker, body, bot_id):
        notes = self.pages(self.mr_path(iid) + "/notes")
        for note in notes:
            if note.get("author", {}).get("id") == bot_id and note["body"].startswith(marker + "\n"):
                if note["body"] != body:
                    self.api(self.mr_path(iid) + f"/notes/{note['id']}", "PUT", {"body": body})
                return note["id"]
        return self.api(self.mr_path(iid) + "/notes", "POST", {"body": body})["id"]


def stamp(task):
    return {key: task[key] for key in ("project", "iid", "sha", "target_sha", "run_id")}


def marker(role):
    return f"<!-- openai-isolated-cloud-{role}:v1 -->"


def encode_record(role, record, text):
    # JSON cannot terminate the HTML comment, even with hostile review text.
    payload = json.dumps(record, sort_keys=True).replace("<", "\\u003c").replace(">", "\\u003e")
    return marker(role) + "\n" + text + "\n\n<!-- record:" + payload + " -->"


def decode_record(note, role, bot_id):
    if note.get("author", {}).get("id") != bot_id or not note.get("body", "").startswith(marker(role) + "\n"):
        return None
    match = re.search(r"\n<!-- record:(.*?) -->$", note["body"], re.S)
    try:
        value = json.loads(match.group(1)) if match else None
        return value if isinstance(value, dict) else None
    except ValueError:
        return None


def validate_review(review):
    if (set(review) != {"summary", "complete", "blockers"}
        or not isinstance(review["summary"], str)
        or type(review["complete"]) is not bool
        or not isinstance(review["blockers"], list)
        or any(not isinstance(b, str) or not b.strip() for b in review["blockers"])):
        raise ValueError("Review must contain summary:string, complete:boolean, blockers:string[]")


def find_review(notes, task):
    for note in notes:
        record = decode_record(note, "review", task["bot_id"])
        if record and all(record.get(k) == v for k, v in stamp(task).items()):
            review = record.get("review")
            if isinstance(review, dict):
                try:
                    validate_review(review)
                    return review
                except ValueError:
                    pass
    return None


def blockers(task, mr, target_sha, review, pipeline, jobs, approvals, discussions):
    missing = []
    if mr.get("state") != "opened":
        missing.append("MR is not open.")
    if mr.get("sha") != task["sha"] or target_sha != task["target_sha"]:
        missing.append("Source or target changed; a new review is required.")
    if mr.get("draft", True) or mr.get("work_in_progress", False):
        missing.append("Mark the MR ready for review.")
    if mr.get("detailed_merge_status") != "mergeable":
        missing.append("GitLab merge status: " + str(mr.get("detailed_merge_status", "unknown")))
    if mr.get("has_conflicts") is not False:
        missing.append("Resolve conflicts or wait for GitLab to determine conflict status.")
    if not review:
        missing.append("Waiting for the paired cloud review at this revision.")
    else:
        if review["complete"] is not True:
            missing.append("Review is incomplete.")
        missing.extend(review["blockers"])
    if pipeline.get("sha") != task["sha"] or pipeline.get("status") != "success":
        missing.append("A successful pipeline for the source SHA is required.")
    for name in REQUIRED_JOBS:
        matches = [job for job in jobs if job.get("name") == name]
        if not matches or any(job.get("status") != "success" for job in matches):
            missing.append(f"Required CI job must pass: {name}.")
    if approvals.get("approvals_left") != 0:
        missing.append("GitLab required approvals are missing or unavailable.")
    if any(n.get("resolvable") and n.get("resolved") is not True
           for d in discussions for n in d.get("notes", [])):
        missing.append("Resolve outstanding GitLab review discussions.")
    return missing


def snapshot(gl, task):
    mr = gl.mr(task["iid"])
    if mr["sha"] != task["sha"] or gl.target_sha(mr) != task["target_sha"]:
        raise APIError("Revision changed; stop and wait for a fresh dispatch")
    diffs = gl.pages(gl.mr_path(task["iid"]) + "/diffs")
    refreshed = gl.mr(task["iid"])
    if refreshed["sha"] != task["sha"] or gl.target_sha(refreshed) != task["target_sha"]:
        raise APIError("Revision changed while fetching the diff; a fresh dispatch is required")
    count = str(mr.get("changes_count", ""))
    complete = count.isdigit() and int(count) == len(diffs) and bool(diffs)
    complete = complete and all(d.get("diff") and not d.get("too_large") and not d.get("collapsed") for d in diffs)
    return {"mr": mr, "diffs": diffs, "diff_complete": bool(complete)}


def post_review(gl, task, review):
    validate_review(review)
    evidence = snapshot(gl, task)
    if not evidence["diff_complete"]:
        review = {**review, "complete": False,
                  "blockers": review["blockers"] + ["GitLab diff is incomplete, empty or truncated."]}
    record = {**stamp(task), "review": review}
    text = (f"### OpenAI cloud review\nRevision `{task['sha']}`\n\n{review['summary']}\n\n"
            + ("\n".join("- " + b for b in review["blockers"]) or "No blocking findings.")
            + f"\n\nReview complete: {review['complete']}")
    gl.note(task["iid"], marker("review"), encode_record("review", record, text), task["bot_id"])
    return record


def check(gl, task):
    mr = gl.mr(task["iid"])
    path = gl.mr_path(task["iid"])
    pipeline = mr.get("head_pipeline") or {}
    jobs = gl.pages(f"{gl.root}/pipelines/{int(pipeline['id'])}/jobs", include_retried="false") if pipeline.get("id") else []
    review = find_review(gl.pages(path + "/notes"), task)
    return mr, blockers(task, mr, gl.target_sha(mr), review, pipeline, jobs,
                        gl.api(path + "/approvals"), gl.pages(path + "/discussions"))


def coordinate(gl, task, attempts=31, delay=30):
    for attempt in range(attempts):
        try:
            mr, missing = check(gl, task)
        except APIError as exc:
            text = f"### OpenAI merge coordinator\nCannot verify merge requirements: {exc}. No merge attempted."
            gl.note(task["iid"], marker("merge"), encode_record("merge", stamp(task), text), task["bot_id"])
            raise
        if mr.get("state") == "merged":
            return {"state": "merged", "url": mr["web_url"]}
        if not missing:
            # Refresh all gates after the model has finished; the API also guards source SHA.
            mr, missing = check(gl, task)
        if not missing:
            result = gl.api(gl.mr_path(task["iid"]) + "/merge", "PUT", {"sha": task["sha"]})
            if result.get("state") != "merged":
                raise APIError("GitLab did not confirm a merge; inspect MR before retrying")
            text = f"### OpenAI merge coordinator\nMerged reviewed revision `{task['sha']}`."
            gl.note(task["iid"], marker("merge"), encode_record("merge", stamp(task), text), task["bot_id"])
            return {"state": "merged", "url": result["web_url"]}
        text = f"### OpenAI merge coordinator\nRevision `{task['sha']}` cannot merge yet:\n\n" + "\n".join("- " + b for b in missing)
        gl.note(task["iid"], marker("merge"), encode_record("merge", stamp(task), text), task["bot_id"])
        if mr.get("state") != "opened" or mr.get("sha") != task["sha"] or any("Source or target changed" in b for b in missing):
            break
        if attempt + 1 < attempts:
            time.sleep(delay)
    return {"state": "blocked", "blockers": missing, "url": mr["web_url"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["snapshot", "file", "post-review", "coordinate"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()
    task = json.loads(Path("/workspace/task.json").read_text())
    gl = GitLab(os.environ["GITLAB_TOKEN"], task["project"])
    if args.command == "snapshot":
        result = snapshot(gl, task)
    elif args.command == "file":
        path, ref = args.args
        if ref not in (task["sha"], task["target_sha"]):
            raise ValueError("Only pinned source/target refs are allowed")
        result = gl.api(f"{gl.root}/repository/files/{quote(path, safe='')}?ref={ref}")
        import base64
        print(base64.b64decode(result["content"]).decode())
        return
    elif args.command == "post-review":
        result = post_review(gl, task, json.loads(Path(args.args[0]).read_text()))
    else:
        result = coordinate(gl, task)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (APIError, ValueError, KeyError) as exc:
        raise SystemExit(str(exc)) from None
