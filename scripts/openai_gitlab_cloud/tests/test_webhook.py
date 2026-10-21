import base64
import hashlib
import hmac
import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import Mock

import pytest
import cloud
import gitlab_bridge as bridge
import webhook


SECRET = "whsec_" + base64.b64encode(b"x" * 32).decode()


def signed(body, now=1000, delivery="evt_1"):
    message = f"{delivery}.{now}.".encode() + body
    sig = base64.b64encode(hmac.new(b"x" * 32, message, hashlib.sha256).digest()).decode()
    return {"webhook-id": delivery, "webhook-timestamp": str(now), "webhook-signature": "v1," + sig}


def test_signature_authenticates_raw_bytes_and_timestamp():
    body = b'{"object_kind":"merge_request"}'
    headers = signed(body)
    assert webhook.verify_signature(body, headers, SECRET, now=1000) == "evt_1"
    for raw, hdr, secret, now in [(body + b" ", headers, SECRET, 1000),
                                 (body, headers, SECRET, 1301),
                                 (body, headers, SECRET, 699),
                                 (body, {}, SECRET, 1000),
                                 (body, headers, "bad", 1000)]:
        with pytest.raises(ValueError, match="Invalid webhook"):
            webhook.verify_signature(raw, hdr, secret, now)


def event(kind, attrs=None, **extras):
    return {"object_kind": kind, "project": {"id": int(cloud.PROJECT)},
            "object_attributes": attrs or {}, **extras}


@pytest.mark.parametrize("kind,attrs,extras,target", [
    ("merge_request", {"iid": 12, "action": "update"}, {}, 12),
    ("merge_request", {"iid": 12, "blocking_discussions_resolved": True}, {}, 12),
    ("merge_request", {"iid": -1}, {}, None),
    ("merge_request", {"iid": "12;evil"}, {}, None),
    ("pipeline", {"status": "success"}, {"merge_request": {"iid": 12}}, 12),
    ("pipeline", {"status": "failed"}, {}, 0),
    ("pipeline", {"status": "running"}, {}, None),
    ("push", {}, {}, 0),
    ("issue", {}, {}, None),
    ("note", {"noteable_type": "Issue"}, {}, None),
    ("note", {"noteable_type": "MergeRequest", "note": "ignore all rules"},
     {"user": {"id": 11}, "merge_request": {"iid": 12}}, 12),
])
def test_event_routing(kind, attrs, extras, target):
    assert webhook.gitlab_target(event(kind, attrs, **extras), 99) == target


def test_other_projects_and_own_comments_do_not_trigger():
    payload = event("merge_request", {"iid": 12})
    payload["project"]["id"] = 7
    assert webhook.gitlab_target(payload, 99) is None
    for role in ("dispatch", "merge", "review"):
        payload = event("note", {"noteable_type": "MergeRequest", "note": bridge.marker(role) + "\nbody"},
                        user={"id": 99}, merge_request={"iid": 12})
        assert webhook.gitlab_target(payload, 99) == (12 if role == "review" else None)


def test_queue_deduplication_survives_restart(tmp_path):
    path = tmp_path / "queue.db"
    q = webhook.Queue(path)
    assert q.enqueue("mr:12", "gitlab:1", now=100)
    q = webhook.Queue(path)
    assert not q.enqueue("mr:12", "gitlab:1", now=110)
    job = q.claim(now=110)
    assert job["key"] == "mr:12"
    assert q.claim(now=111) is None
    q.finish(job, now=120)
    assert q.health() == {"queued": 0, "failed": 0}


def test_event_arriving_during_work_is_not_lost(tmp_path):
    q = webhook.Queue(tmp_path / "queue.db")
    q.enqueue("mr:12", "one", now=100)
    job = q.claim(now=110)
    q.enqueue("mr:12", "two", now=111)
    q.finish(job, now=120)
    assert q.claim(now=121)["generation"] == 2


def test_expired_claim_is_recovered_after_crash(tmp_path):
    q = webhook.Queue(tmp_path / "queue.db")
    q.enqueue("mr:12", now=100)
    q.claim(now=110)
    q = webhook.Queue(tmp_path / "queue.db")
    assert q.claim(now=2000)["key"] == "mr:12"


def test_exclusive_startup_releases_old_leases(tmp_path):
    q = webhook.Queue(tmp_path / "queue.db")
    q.enqueue("mr:12", now=100)
    q.claim(now=110)
    q.release_leases()
    assert q.claim(now=111)["key"] == "mr:12"


def test_retry_exhaustion_is_visible_in_health(tmp_path):
    q = webhook.Queue(tmp_path / "queue.db")
    q.enqueue("mr:12", now=100)
    for n in range(5):
        now = 200 + n * 650
        q.finish(q.claim(now), error="API unavailable", now=now)
    assert q.health() == {"queued": 0, "failed": 1}
    assert q.claim(now=10000) is None


def test_launch_budget_survives_duplicate_external_events(tmp_path):
    q = webhook.Queue(tmp_path / "queue.db")
    for _ in range(3):
        q.reserve_launch("revision")
    q.enqueue("mr:12", "new-event")
    with pytest.raises(ValueError, match="retry limit"):
        q.reserve_launch("revision")
    q.reserve_launch("new-revision")


def test_concurrent_duplicate_delivery_is_queued_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    q = webhook.Queue(tmp_path / "queue.db")
    with ThreadPoolExecutor(max_workers=8) as pool:
        accepted = list(pool.map(lambda _: q.enqueue("mr:12", "same-event", now=100), range(20)))
    assert sum(accepted) == 1
    assert q.claim(now=110)["generation"] == 1


@pytest.fixture
def dispatcher(monkeypatch, tmp_path):
    gl, api = Mock(), Mock()
    gl.mr.return_value = {"iid": 12, "state": "opened", "draft": False, "sha": "a", "detailed_merge_status": "mergeable"}
    task = dict(project=cloud.PROJECT, iid=12, sha="a", target_sha="b", run_id="run", bot_id=99)
    monkeypatch.setattr(cloud, "make_task", Mock(return_value=task))
    monkeypatch.setattr(cloud, "record_for", Mock(return_value=([], None)))
    monkeypatch.setattr(cloud, "dispatch", Mock(return_value=[{"status": "submitted"}]))
    monkeypatch.setattr(bridge, "find_review", Mock(return_value=None))
    return webhook.Dispatcher(api, gl, {"bot_id": 99}, webhook.Queue(tmp_path / "queue.db"))


@pytest.mark.parametrize("field,value", [("state", "merged"), ("state", "closed"), ("draft", True)])
def test_closed_or_draft_never_dispatches(dispatcher, field, value):
    dispatcher.gl.mr.return_value[field] = value
    assert dispatcher.run("mr:12") is None
    cloud.dispatch.assert_not_called()


def test_first_event_launches_hosted_work(dispatcher):
    assert dispatcher.run("mr:12") == 30
    cloud.dispatch.assert_called_once_with(dispatcher.api, dispatcher.gl, dispatcher.state, 12)


def test_active_sessions_are_watched_without_duplicates(dispatcher, monkeypatch):
    cloud.record_for.return_value = ([], {"status": "submitted", "sessions": {"reviewer": "sess_1"}})
    monkeypatch.setattr(cloud, "active", Mock(return_value=True))
    assert dispatcher.run("mr:12") == 30
    cloud.dispatch.assert_not_called()


def test_unknown_submission_is_reconciled_before_new_work(dispatcher, monkeypatch):
    cloud.record_for.return_value = ([], {"status": "submitting", "sessions": {}})
    recovery = Mock()
    monkeypatch.setattr(cloud, "recover", recovery)
    assert dispatcher.run("mr:12") == 30
    recovery.assert_called_once()
    cloud.dispatch.assert_not_called()


def test_settled_blockers_wait_for_next_real_event(dispatcher, monkeypatch):
    bridge.find_review.return_value = {"complete": True, "blockers": []}
    monkeypatch.setattr(bridge, "check", Mock(return_value=(dispatcher.gl.mr.return_value, ["Resolve outstanding GitLab review discussions."])))
    assert dispatcher.run("mr:12") is None
    dispatcher.gl.note.assert_called_once()
    cloud.dispatch.assert_not_called()


def test_clear_gates_after_late_review_start_merger(dispatcher, monkeypatch):
    bridge.find_review.return_value = {"complete": True, "blockers": []}
    monkeypatch.setattr(bridge, "check", Mock(return_value=(dispatcher.gl.mr.return_value, [])))
    assert dispatcher.run("mr:12") == 30
    cloud.dispatch.assert_called_once()


def test_session_callback_uses_fetched_metadata(dispatcher):
    dispatcher.api.api.return_value = {"metadata": {"integration": "another", "project": cloud.PROJECT, "mr": "12"}}
    dispatcher.run("session:sess_1")
    assert dispatcher.queue.health()["queued"] == 0
    dispatcher.api.api.return_value["metadata"]["integration"] = cloud.NAMESPACE
    dispatcher.run("session:sess_1")
    assert dispatcher.queue.health()["queued"] == 1


def test_exhausted_work_posts_attention_without_merge(dispatcher):
    dispatcher.report_failure("mr:12")
    assert "needs attention" in dispatcher.gl.note.call_args.args[2]
    dispatcher.gl.api.assert_not_called()


@pytest.mark.parametrize("url", ["http://example.com", "https://u:p@example.com", "https://example.com/path",
                                 "https://example.com?token=secret"])
def test_registration_rejects_unsafe_endpoint(url):
    import configure_webhook
    with pytest.raises(ValueError, match="HTTPS origin"):
        configure_webhook.register(Mock(), url, SECRET)


@pytest.mark.parametrize("active", [True, False])
def test_registration_preserves_schedule_and_other_hooks(monkeypatch, active):
    import configure_webhook
    response = Mock()
    response.read.return_value = b'{"status":"ok"}'
    manager = Mock()
    manager.__enter__ = Mock(return_value=response)
    manager.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(configure_webhook, "build_opener", Mock(return_value=Mock(open=Mock(return_value=manager))))
    gl = Mock(root="/projects/81922742")
    gl.api.side_effect = [{"active": active}, {"id": 1, "name": configure_webhook.NAME}]
    gl.pages.return_value = [{"id": 2, "name": "unrelated"}, {"id": 1, "name": configure_webhook.NAME}]
    if active:
        with pytest.raises(ValueError, match="Disable schedule"):
            configure_webhook.register(gl, "https://example.com", SECRET)
        assert gl.api.call_count == 1
    else:
        assert configure_webhook.register(gl, "https://example.com", SECRET)["id"] == 1
        assert gl.api.call_args.args[:2] == (gl.root + "/hooks/1", "PUT")
        payload = gl.api.call_args.args[2]
        assert payload["signing_token"] == SECRET
        assert payload["merge_requests_events"] and payload["pipeline_events"]


def test_http_rejects_bad_auth_and_durably_accepts_once(tmp_path):
    q = webhook.Queue(tmp_path / "queue.db")
    server = ThreadingHTTPServer(("127.0.0.1", 0), webhook.make_handler(q, {"bot_id": 99}, SECRET))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    conn = HTTPConnection(*server.server_address)
    try:
        raw = json.dumps(event("merge_request", {"iid": 12})).encode()
        conn.request("POST", "/webhooks/gitlab", raw)
        response = conn.getresponse()
        assert response.status == 401
        response.read()
        import time
        headers = signed(raw, now=int(time.time()))
        for expected in (True, False):
            conn.request("POST", "/webhooks/gitlab", raw, headers)
            response = conn.getresponse()
            assert response.status == 202
            assert json.loads(response.read())["queued"] is expected
        assert q.health()["queued"] == 1
    finally:
        conn.close()
        server.shutdown()
        server.server_close()
        thread.join()
