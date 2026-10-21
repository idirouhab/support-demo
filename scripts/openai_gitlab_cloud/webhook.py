"""Durable, event-driven dispatcher. Agents still execute in OpenAI's cloud.

Run one service replica, behind an HTTPS reverse proxy, with a persistent data
directory. No repository code or webhook text is executed by this service.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cloud
import gitlab_bridge as bridge

LOG = logging.getLogger("cloud-webhook")
MAX_BODY = 2 * 1024 * 1024
MAX_LAUNCHES = 3


def verify_signature(body, headers, secret, now=None):
    """Standard Webhooks authentication used by both providers; no downgrade."""
    now = time.time() if now is None else now
    try:
        event_id = headers["webhook-id"]
        timestamp = headers["webhook-timestamp"]
        signatures = headers["webhook-signature"]
        if not event_id or len(event_id) > 200 or abs(now - int(timestamp)) > 300:
            raise ValueError("Invalid webhook")
        key = base64.b64decode(secret.removeprefix("whsec_"), validate=True)
        if len(key) < 32:
            raise ValueError("Invalid webhook")
        signed = event_id.encode() + b"." + timestamp.encode() + b"." + body
        expected = "v1," + base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
        if not any(hmac.compare_digest(expected, item) for item in signatures.split()):
            raise ValueError("Invalid webhook")
        return event_id
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError("Invalid webhook") from None


def gitlab_target(payload, bot_id):
    """Return MR IID, 0 for an open-MR refresh, or None for irrelevant events."""
    if str(payload.get("project", {}).get("id")) != cloud.PROJECT:
        return None
    kind = payload.get("object_kind")
    attrs = payload.get("object_attributes") or {}
    if kind == "merge_request":
        iid = attrs.get("iid")
    elif kind == "note":
        if attrs.get("noteable_type") != "MergeRequest":
            return None
        # Only a structured review from our bot is useful. Status comments must
        # never wake themselves. Human comments are data, never instructions.
        if payload.get("user", {}).get("id") == bot_id:
            if not attrs.get("note", "").startswith(bridge.marker("review") + "\n"):
                return None
        iid = (payload.get("merge_request") or {}).get("iid")
    elif kind == "pipeline":
        if attrs.get("status") not in ("success", "failed", "canceled", "skipped", "manual"):
            return None
        iid = (payload.get("merge_request") or {}).get("iid")
        return iid if type(iid) is int and iid > 0 else 0
    elif kind == "push":
        return 0  # Target-branch pushes invalidate existing reviews too.
    else:
        return None
    return iid if type(iid) is int and iid > 0 else None


class Queue:
    """SQLite transactions deduplicate deliveries and retain wakeups during work."""
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS deliveries (
                    id TEXT PRIMARY KEY, received REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    key TEXT PRIMARY KEY, generation INTEGER NOT NULL DEFAULT 1,
                    due REAL NOT NULL, lease REAL NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0, deadline REAL NOT NULL,
                    error TEXT);
                CREATE TABLE IF NOT EXISTS launches (
                    run_id TEXT PRIMARY KEY, count INTEGER NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def release_leases(self):
        # Call only after acquiring the process-wide exclusive file lock.
        with self.connect() as db:
            db.execute("UPDATE jobs SET lease=0")

    def enqueue(self, key, delivery=None, now=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if delivery:
                result = db.execute("INSERT OR IGNORE INTO deliveries VALUES (?, ?)", (delivery, now))
                if not result.rowcount:
                    return False
            db.execute("""INSERT INTO jobs(key,due,deadline) VALUES(?,?,?)
                ON CONFLICT(key) DO UPDATE SET generation=generation+1,
                due=min(due,excluded.due), attempts=0, deadline=excluded.deadline, error=NULL""",
                (key, now + 3, now + 5400))
            db.execute("DELETE FROM deliveries WHERE received < ?", (now - 30 * 86400,))
        return True

    def claim(self, now=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE due<=? AND lease<=? AND error IS NULL ORDER BY due LIMIT 1",
                             (now, now)).fetchone()
            if row:
                db.execute("UPDATE jobs SET lease=? WHERE key=?", (now + 1800, row["key"]))
                return dict(row)
        return None

    def finish(self, job, delay=None, error=None, now=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT generation FROM jobs WHERE key=?", (job["key"],)).fetchone()
            if not current:
                return
            if current[0] != job["generation"]:
                db.execute("UPDATE jobs SET lease=0 WHERE key=?", (job["key"],))
            elif delay is None and error is None:
                db.execute("DELETE FROM jobs WHERE key=?", (job["key"],))
            else:
                attempts = job["attempts"] + bool(error)
                dead = (error or "Session did not settle within 90 minutes") if attempts >= 5 or now >= job["deadline"] else None
                db.execute("UPDATE jobs SET lease=0,due=?,attempts=?,error=? WHERE key=?",
                           (now + (delay or min(30 * 2 ** attempts, 600)), attempts, dead, job["key"]))
                if dead:
                    LOG.error("Job %s needs attention: %s", job["key"], dead)
                return dead

    def reserve_launch(self, run_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT count FROM launches WHERE run_id=?", (run_id,)).fetchone()
            if count and count[0] >= MAX_LAUNCHES:
                raise ValueError("Cloud session retry limit reached for this revision; inspect session outcomes")
            db.execute("INSERT INTO launches VALUES (?,1) ON CONFLICT(run_id) DO UPDATE SET count=count+1", (run_id,))

    def health(self):
        with self.connect() as db:
            return dict(queued=db.execute("SELECT count(*) FROM jobs WHERE error IS NULL").fetchone()[0],
                        failed=db.execute("SELECT count(*) FROM jobs WHERE error IS NOT NULL").fetchone()[0])


class Dispatcher:
    def __init__(self, api, gl, state, queue):
        self.api, self.gl, self.state, self.queue = api, gl, state, queue

    def run(self, key):
        if key.startswith("session:"):
            sid = key.split(":", 1)[1]
            session = self.api.api("/agents/sessions/" + sid)
            meta = session.get("metadata") or {}
            if meta.get("integration") == cloud.NAMESPACE and meta.get("project") == cloud.PROJECT:
                iid = int(meta["mr"])
                if iid > 0:
                    self.queue.enqueue("mr:" + str(iid))
            return None
        iid = int(key.split(":", 1)[1])
        if iid == 0:
            for mr in self.gl.pages(self.gl.root + "/merge_requests", state="opened", scope="all"):
                if not mr.get("draft", True):
                    self.queue.enqueue("mr:" + str(mr["iid"]))
            return None
        mr = self.gl.mr(iid)
        if mr.get("state") != "opened" or mr.get("draft", True):
            return None
        bot_id = self.state["bot_id"]
        task = cloud.make_task(self.gl, mr, bot_id)
        notes, previous = cloud.record_for(self.gl, iid, bot_id)
        if previous:
            if previous.get("status") not in ("submitted", "reconciled"):
                cloud.recover(self.api, self.gl, iid)
                return 30
            if any(cloud.active(self.api, sid) for sid in previous["sessions"].values()):
                return 30
        review = bridge.find_review(notes, task)
        if review:
            current, missing = bridge.check(self.gl, task)
            if missing:
                text = f"### OpenAI merge coordinator\nRevision `{task['sha']}` cannot merge yet:\n\n" + "\n".join("- " + b for b in missing)
                self.gl.note(iid, bridge.marker("merge"), bridge.encode_record("merge", bridge.stamp(task), text), bot_id)
                # GitLab sometimes needs a moment after CI/approval events to
                # compute mergeability. Other blockers wait for a real event.
                if current.get("detailed_merge_status") in ("checking", "unchecked", "preparing", "approvals_syncing"):
                    return 30
                return None
        self.queue.reserve_launch(task["run_id"])
        result = cloud.dispatch(self.api, self.gl, self.state, iid)
        if any(r.get("state") == "recovery_required" for r in result):
            raise ValueError("Cloud submission needs recovery")
        # Track only work already started; this is not periodic repository
        # polling. It also covers unavailable OpenAI lifecycle webhooks.
        return 30 if result else None

    def report_failure(self, key):
        if not key.startswith("mr:") or key == "mr:0":
            return
        iid = int(key.split(":", 1)[1])
        mr = self.gl.mr(iid)
        if mr.get("state") != "opened":
            return
        text = ("### OpenAI merge coordinator\nAutomatic processing needs attention: "
                "the event worker exhausted its retry or session limit. "
                "Inspect the webhook service health and cloud session outcomes before retrying. "
                "No checks have been bypassed.")
        self.gl.note(iid, bridge.marker("merge"), bridge.marker("merge") + "\n" + text, self.state["bot_id"])


def make_handler(queue, state, gitlab_secret, openai_secret=None, worker_alive=lambda: True):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log request headers, bodies, or URL query parameters.

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def reply(self, status, value):
            data = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path != "/healthz":
                return self.reply(404, {"error": "Not found"})
            health = queue.health()
            healthy = not health["failed"] and worker_alive()
            return self.reply(200 if healthy else 503, {"status": "ok" if healthy else "attention", **health})

        def do_POST(self):
            secrets = {"/webhooks/gitlab": gitlab_secret, "/webhooks/openai": openai_secret}
            secret = secrets.get(self.path)
            if not secret:
                return self.reply(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY or self.headers.get("Transfer-Encoding"):
                    return self.reply(413, {"error": "Invalid body length"})
                body = self.rfile.read(length)
                headers = {k.lower(): v for k, v in self.headers.items()}
                delivery = verify_signature(body, headers, secret)
            except (ValueError, TimeoutError):
                return self.reply(401, {"error": "Invalid webhook"})
            try:
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    raise ValueError("Expected object")
                key = None
                if self.path.endswith("gitlab"):
                    iid = gitlab_target(payload, state["bot_id"])
                    if iid is not None:
                        key = "mr:" + str(iid)
                elif payload.get("type") in ("agent.session.idle", "agent.session.failed"):
                    sid = (payload.get("data") or {}).get("id", "")
                    if isinstance(sid, str) and sid.startswith("sess_") and sid.replace("_", "").isalnum() and len(sid) <= 100:
                        key = "session:" + sid
                accepted = queue.enqueue(key, self.path + ":" + delivery) if key else False
                return self.reply(202, {"queued": accepted})
            except (ValueError, TypeError, AttributeError):
                return self.reply(400, {"error": "Invalid event"})
            except sqlite3.Error:
                return self.reply(503, {"error": "Queue unavailable"})
    return Handler


def work(queue, dispatcher, stop):
    while not stop.is_set():
        job = queue.claim()
        if not job:
            stop.wait(1)
            continue
        try:
            delay = dispatcher.run(job["key"])
            dead = queue.finish(job, delay=delay)
            if dead:
                dispatcher.report_failure(job["key"])
            LOG.info("Processed %s (%s)", job["key"], "waiting" if delay else "settled")
        except Exception as exc:
            # Only our redacted exceptions may reach logs. Third-party strings
            # can echo secrets, response content, or the incoming request.
            message = str(exc) if isinstance(exc, (bridge.APIError, ValueError)) else type(exc).__name__
            LOG.warning("Retrying %s: %s", job["key"], message)
            dead = queue.finish(job, error=message)
            if dead:
                try:
                    dispatcher.report_failure(job["key"])
                except Exception:
                    LOG.error("Could not publish attention comment for %s", job["key"])


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cloud.load_dotenv(cloud.HERE / ".webhook.env", override=False)
    api = cloud.config()
    state = cloud.load_state()
    for name in ("reviewer", "merger", "vault", "credential", "bot_id"):
        if not state.get(name):
            raise ValueError("Missing provisioned cloud agent configuration")
    secret = os.environ["GITLAB_WEBHOOK_SECRET"]
    directory = Path(os.environ.get("WEBHOOK_DATA_DIR", str(cloud.HERE / ".webhook-data")))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    # An OS lock prevents two dispatchers from racing on the same durable state.
    import fcntl
    lock = (directory / "worker.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    queue = Queue(directory / "queue.sqlite3")
    queue.release_leases()
    gl = bridge.GitLab(os.environ["GITLAB_TOKEN"], cloud.PROJECT)
    if gl.api("/user")["id"] != state["bot_id"]:
        raise ValueError("GitLab token identity differs from provisioned bot")
    stop = threading.Event()
    dispatcher = Dispatcher(api, gl, state, queue)
    worker = threading.Thread(target=work, args=(queue, dispatcher, stop), daemon=True)
    worker.start()
    # Recover pending state after restarts, including events missed while down.
    queue.enqueue("mr:0")
    server = ThreadingHTTPServer((os.environ.get("WEBHOOK_HOST", "127.0.0.1"), int(os.environ.get("PORT", "8080"))),
                                make_handler(queue, state, secret, os.environ.get("OPENAI_WEBHOOK_SECRET"), worker.is_alive))
    def supervise():
        worker.join()
        if not stop.is_set():
            LOG.critical("Queue worker exited; stopping server for container restart")
            server.shutdown()
    threading.Thread(target=supervise, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()
        worker.join(timeout=65)
        lock.close()
    if not worker.is_alive():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
