"""GitLab operations used inside OpenAI-hosted sandboxes (standard library only)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

PROJECT = "81922742"
REQUIRED_JOBS = {"backend_tests", "frontend_tests", "bug_fix_evidence", "frontend_build"}
MARKER = "<!-- support-demo-cloud-review-v1 "
STATUS_MARKER = "<!-- support-demo-cloud-merge-v1 -->"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, headers, method="GET", data=None):
    body = None if data is None else json.dumps(data).encode()
    req = Request(url, data=body, method=method,
                  headers={**headers, "Content-Type": "application/json"})
    try:
        with build_opener(NoRedirect).open(req, timeout=60) as response:
            return json.load(response), response.headers
    except HTTPError as exc:
        # Never echo response bodies, request bodies, or credentials.
        raise RuntimeError(f"{method} request failed: HTTP {exc.code}") from None


class GitLab:
    def __init__(self):
        self.headers = {"PRIVATE-TOKEN": os.environ["GITLAB_TOKEN"]}
        self.bot_id = self.api("/user")["id"]

    def api(self, path, method="GET", data=None):
        return request("https://gitlab.com/api/v4" + path, self.headers, method, data)[0]

    def pages(self, path):
        items, page = [], 1
        while True:
            data, headers = request("https://gitlab.com/api/v4" + path +
                                    ("&" if "?" in path else "?") +
                                    urlencode({"per_page": 100, "page": page}), self.headers)
            items.extend(data)
            if not headers.get("X-Next-Page"):
                return items
            page = int(headers["X-Next-Page"])

    def mr_path(self, iid):
        return f"/projects/{PROJECT}/merge_requests/{int(iid)}"

    def snapshot(self, iid):
        path = self.mr_path(iid)
        mr = self.api(path)
        target = self.api(f"/projects/{PROJECT}/repository/branches/" + quote(mr["target_branch"], safe=""))
        diffs = self.pages(path + "/diffs")
        complete = bool(diffs) and str(mr.get("changes_count", "")).isdigit()
        complete = complete and len(diffs) == int(mr["changes_count"])
        complete = complete and all(not d.get("too_large") and not d.get("collapsed") and d.get("diff") for d in diffs)
        identity = {"sha": mr.get("sha"), "diff_refs": mr.get("diff_refs"),
                    "policy": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "target_sha": target["commit"]["id"], "target_branch": mr["target_branch"]}
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        return {"mr": mr, "identity": identity, "key": key, "diffs": diffs,
                "complete": bool(complete), "discussions": self.pages(path + "/discussions")}

    def notes(self, iid):
        return self.pages(self.mr_path(iid) + "/notes?sort=desc&order_by=created_at")

    def review(self, iid, key):
        for note in self.notes(iid):
            body = note.get("body", "")
            if note.get("author", {}).get("id") != self.bot_id or not body.startswith(MARKER):
                continue
            try:
                report = json.loads(body[len(MARKER):body.index(" -->")])
                if report.get("key") == key:
                    return report
            except (ValueError, TypeError):
                continue
        return None

    def post_status(self, iid, body):
        body = STATUS_MARKER + "\n" + body
        for note in self.notes(iid):
            if note.get("author", {}).get("id") == self.bot_id and note.get("body", "").startswith(STATUS_MARKER):
                if note["body"] != body:
                    self.api(self.mr_path(iid) + f"/notes/{note['id']}", "PUT", {"body": body})
                return
        self.api(self.mr_path(iid) + "/notes", "POST", {"body": body})

    def publish_review(self, iid, expected_key, report):
        snap = self.snapshot(iid)
        if snap["key"] != expected_key or snap["mr"]["state"] != "opened":
            raise RuntimeError("MR changed during review; rerun on its current revision")
        if report.get("verdict") not in {"pass", "blocked"} or not isinstance(report.get("findings"), list):
            raise ValueError("Review needs verdict pass/blocked and findings list")
        if not isinstance(report.get("summary"), str) or not report["summary"].strip():
            raise ValueError("Review needs an evidence-based summary")
        if report["findings"] or not snap["complete"]:
            report["verdict"] = "blocked"
        record = {"key": expected_key, "sha": snap["identity"]["sha"],
                  "verdict": report["verdict"], "summary": report["summary"],
                  "findings": report["findings"]}
        # Do not allow a generated report to override the pinned identity.
        record["key"], record["sha"] = expected_key, snap["identity"]["sha"]
        if self.review(iid, expected_key) == record:
            return record
        metadata = json.dumps(record, ensure_ascii=True).replace("-->", "--\\u003e")
        body = MARKER + metadata + " -->\n## OpenAI review\n"
        body += f"Commit: `{record['sha']}`\n\n**{record['verdict']}** — {record['summary']}\n"
        body += "\n".join("- " + str(f) for f in record["findings"])
        if not snap["complete"]:
            body += "\n- GitLab did not supply a complete diff; manual review is required."
        self.api(self.mr_path(iid) + "/notes", "POST", {"body": body})
        return record

    def gates(self, iid, key):
        snap = self.snapshot(iid)
        mr, path = snap["mr"], self.mr_path(iid)
        pipeline = mr.get("head_pipeline") or {}
        jobs = self.pages(f"/projects/{PROJECT}/pipelines/{pipeline['id']}/jobs") if pipeline.get("id") else []
        approvals = self.api(path + "/approvals")
        review = self.review(iid, key)
        return snap, blockers(snap, key, review, pipeline, jobs, approvals)

    def merge(self, iid, key):
        snap, missing = self.gates(iid, key)
        if missing:
            self.post_status(iid, "## Merge blocked\n" + "\n".join("- " + x for x in missing))
            return {"merged": False, "blockers": missing}
        # Re-read all gates immediately before the conditional merge request.
        snap, missing = self.gates(iid, key)
        if missing:
            self.post_status(iid, "## Merge blocked\n" + "\n".join("- " + x for x in missing))
            return {"merged": False, "blockers": missing}
        result = self.api(self.mr_path(iid) + "/merge", "PUT", {"sha": snap["identity"]["sha"]})
        if result.get("state") != "merged":
            raise RuntimeError("GitLab did not confirm a completed merge")
        self.post_status(iid, f"## Merged\nReviewed commit `{snap['identity']['sha']}` passed all merge gates.")
        return {"merged": True, "sha": snap["identity"]["sha"]}


def blockers(snap, expected_key, review, pipeline, jobs, approvals):
    mr = snap["mr"]
    result = []
    if snap["key"] != expected_key:
        result.append("Source or target changed; a fresh review is required.")
    if mr.get("state") != "opened" or mr.get("draft") or mr.get("work_in_progress"):
        result.append("MR must be open and ready for review.")
    if not snap["complete"]:
        result.append("Complete diff unavailable.")
    if not review or review.get("verdict") != "pass" or review.get("findings") != []:
        result.append("A passing bot review for this revision is required.")
    if mr.get("detailed_merge_status") != "mergeable" or mr.get("has_conflicts"):
        result.append("GitLab merge status: " + str(mr.get("detailed_merge_status", "unknown")))
    if pipeline.get("status") != "success" or pipeline.get("sha") != mr.get("sha"):
        result.append("A successful pipeline on the reviewed source SHA is required.")
    for name in sorted(REQUIRED_JOBS):
        matching = [job for job in jobs if job.get("name") == name]
        if not matching or any(j.get("status") != "success" for j in matching):
            result.append(f"Required CI job missing or unsuccessful: {name}")
    if approvals.get("approvals_left") != 0:
        result.append("GitLab approval requirements are unsatisfied or unknown.")
    if any(n.get("resolvable") and n.get("resolved") is not True
           for d in snap["discussions"] for n in d.get("notes", [])):
        result.append("Resolve all review discussions.")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["snapshot", "file", "publish-review", "merge"])
    parser.add_argument("--iid", type=int, required=True)
    parser.add_argument("--key")
    parser.add_argument("--path")
    args = parser.parse_args()
    client = GitLab()
    if args.action == "snapshot":
        result = client.snapshot(args.iid)
    elif args.action == "file":
        snap = client.snapshot(args.iid)
        if snap["key"] != args.key:
            raise RuntimeError("Revision changed")
        result = client.api(f"/projects/{PROJECT}/repository/files/" + quote(args.path, safe="") +
                            "?ref=" + quote(snap["identity"]["sha"], safe=""))
    elif args.action == "publish-review":
        result = client.publish_review(args.iid, args.key, json.loads(Path(args.path).read_text()))
    else:
        result = client.merge(args.iid, args.key)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
