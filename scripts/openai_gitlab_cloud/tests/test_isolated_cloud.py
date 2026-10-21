import base64
import json
from unittest.mock import Mock

import pytest
import cloud
import gitlab_bridge as bridge


def gitlab_mock():
    gl = Mock()
    gl.root = "/projects/81922742"
    gl.mr_path.side_effect = lambda iid: f"{gl.root}/merge_requests/{iid}"
    return gl


@pytest.fixture
def ready():
    task = dict(project="81922742", iid=12, sha="a" * 40, target_sha="b" * 40,
                run_id="key", bot_id=99)
    return dict(task=task,
        mr=dict(iid=12, state="opened", draft=False, sha=task["sha"], has_conflicts=False,
                detailed_merge_status="mergeable", web_url="https://gitlab.com/mr/12"),
        target_sha=task["target_sha"], review=dict(summary="Reviewed", complete=True, blockers=[]),
        pipeline=dict(id=1, sha=task["sha"], status="success"),
        jobs=[dict(name=n, status="success") for n in bridge.REQUIRED_JOBS],
        approvals=dict(approvals_left=0), discussions=[])


def test_ready_does_not_require_extra_human_approval(ready):
    assert bridge.blockers(**ready) == []


@pytest.mark.parametrize("field,value", [("draft", True), ("state", "closed"),
    ("sha", "old"), ("has_conflicts", True), ("detailed_merge_status", "checking")])
def test_mr_gate_failures(ready, field, value):
    ready["mr"][field] = value
    assert bridge.blockers(**ready)


@pytest.mark.parametrize("name", bridge.REQUIRED_JOBS)
@pytest.mark.parametrize("status", ["failed", "skipped", "running", "manual"])
def test_each_required_job_must_pass(ready, name, status):
    for job in ready["jobs"]:
        if job["name"] == name:
            job["status"] = status
    assert bridge.blockers(**ready)


@pytest.mark.parametrize("field,value", [
    ("target_sha", "new"), ("review", None), ("approvals", {}),
    ("approvals", {"approvals_left": 1}), ("jobs", []),
    ("pipeline", {"sha": "old", "status": "success"}),
    ("review", {"summary": "Missing", "complete": False, "blockers": []}),
    ("review", {"summary": "Bug", "complete": True, "blockers": ["Fix app.py:9"]}),
    ("discussions", [{"notes": [{"resolvable": True, "resolved": False}]}])])
def test_unknown_or_failing_evidence_blocks(ready, field, value):
    ready[field] = value
    assert bridge.blockers(**ready)


def note(role, record, bot=99):
    return dict(author={"id": bot}, body=bridge.encode_record(role, record, "Status"))


def test_review_bound_to_author_revision_and_run(ready):
    task = ready["task"]
    record = {**bridge.stamp(task), "review": ready["review"]}
    assert bridge.find_review([note("review", record)], task)
    assert bridge.find_review([note("review", record, 10)], task) is None
    for key in ("sha", "target_sha", "run_id", "iid", "project"):
        assert bridge.find_review([note("review", {**record, key: "stale"})], task) is None
    assert bridge.find_review([note("review", {**record, "review": {"complete": "true"}})], task) is None


def test_comment_update_is_owned_and_idempotent():
    gl = bridge.GitLab("token")
    gl.pages = Mock(return_value=[dict(id=1, author=dict(id=99), body="marker\nbody")])
    gl.api = Mock(return_value={"id": 2})
    gl.note(12, "marker", "marker\nbody", 99)
    gl.api.assert_not_called()
    gl.note(12, "marker", "marker\nchanged", 99)
    assert gl.api.call_args.args[1] == "PUT"
    gl.note(12, "marker", "marker\nchanged", 10)
    assert gl.api.call_args.args[1] == "POST"


def test_pagination_includes_late_discussions(monkeypatch):
    req = Mock(side_effect=[([1], {"X-Next-Page": "2"}), ([2], {"X-Next-Page": ""})])
    monkeypatch.setattr(bridge, "request", req)
    assert bridge.GitLab("token").pages("/discussions") == [1, 2]


@pytest.mark.parametrize("diff", [{"diff": ""}, {"diff": "+x", "too_large": True},
                                  {"diff": "+x", "collapsed": True}])
def test_truncated_review_cannot_clear_gate(ready, diff):
    gl = gitlab_mock()
    gl.mr.return_value = {**ready["mr"], "changes_count": "1"}
    gl.target_sha.return_value = ready["target_sha"]
    gl.pages.return_value = [diff]
    result = bridge.post_review(gl, ready["task"], ready["review"])
    assert not result["review"]["complete"] and result["review"]["blockers"]


def test_merge_refreshes_and_uses_sha_guard(monkeypatch, ready):
    gl = gitlab_mock()
    gl.api.return_value = dict(state="merged", web_url="url")
    check = Mock(return_value=(ready["mr"], []))
    monkeypatch.setattr(bridge, "check", check)
    assert bridge.coordinate(gl, ready["task"], attempts=1)["state"] == "merged"
    assert check.call_count == 2
    assert gl.api.call_args.args[1:] == ("PUT", {"sha": ready["task"]["sha"]})


def test_change_before_merge_blocks(monkeypatch, ready):
    gl = gitlab_mock()
    monkeypatch.setattr(bridge, "check", Mock(side_effect=[(ready["mr"], []), (ready["mr"], ["CI restarted"])]))
    assert bridge.coordinate(gl, ready["task"], attempts=1)["state"] == "blocked"
    gl.api.assert_not_called()


def test_merge_failure_is_not_success(monkeypatch, ready):
    gl = gitlab_mock()
    gl.api.side_effect = bridge.APIError("HTTP 409")
    monkeypatch.setattr(bridge, "check", Mock(return_value=(ready["mr"], [])))
    with pytest.raises(bridge.APIError):
        bridge.coordinate(gl, ready["task"], attempts=1)
    gl.note.assert_not_called()


def test_vault_keeps_secret_out_of_payload(ready, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "secret-token")
    state = dict(reviewer="agent_r", vault="vault_g")
    payload = cloud.session_payload("reviewer", state, ready["task"])
    assert "secret-token" not in json.dumps(payload)
    assert payload["environment"]["type"] == "openai_hosted"
    assert payload["vault_ids"] == ["vault_g"]
    assert json.loads(base64.b64decode(payload["environment"]["files"][1]["data"])) == ready["task"]


@pytest.mark.parametrize("turns,expected", [([], True), ([{"status": "queued"}], True),
    ([{"status": "waiting"}], True), ([{"status": "completed"}], False)])
def test_idle_is_not_assumed_completed(turns, expected):
    api = Mock()
    api.api.side_effect = [{"status": "idle"}, {"data": turns}]
    assert cloud.active(api, "session") is expected


def test_failed_session_without_turn_is_terminal():
    api = Mock()
    api.api.return_value = {"status": "failed"}
    assert cloud.active(api, "failed") is False
    assert api.api.call_count == 1


@pytest.mark.parametrize("keep_reviewer", [True, False])
def test_late_review_is_reused_after_merger_timeout(ready, keep_reviewer):
    gl = gitlab_mock()
    gl.api.return_value = {"id": 99}
    gl.mr.return_value = ready["mr"]
    gl.target_sha.return_value = ready["target_sha"]
    task = cloud.make_task(gl, ready["mr"], 99)
    previous = {**task, "sessions": {"reviewer": "review", "merger": "oldmerge"}, "status": "submitted"}
    if not keep_reviewer:
        del previous["sessions"]["reviewer"]
    gl.pages.return_value = [note("dispatch", previous),
        note("review", {**bridge.stamp(task), "review": ready["review"]})]
    api = Mock()
    api.api.side_effect = ([{"status": "idle"}, {"data": [{"status": "completed"}]}]
                          * len(previous["sessions"]) + [{"id": "newmerge"}])
    state = dict(reviewer="r", merger="m", vault="v", credential="c")
    result = cloud.dispatch(api, gl, state, 12)[0]
    assert result["run_id"] == task["run_id"]
    assert result["sessions"] == ({"reviewer": "review", "merger": "newmerge"}
                                  if keep_reviewer else {"merger": "newmerge"})
    writes = [c for c in api.api.call_args_list if len(c.args) > 1 and c.args[1] == "POST"]
    assert len(writes) == 1 and writes[0].args[2]["agent_id"] == "m"


def test_unknown_submission_blocks_until_reconciled(ready):
    gl = gitlab_mock()
    gl.api.return_value = {"id": 99}
    gl.mr.return_value = ready["mr"]
    gl.target_sha.return_value = ready["target_sha"]
    record = {**ready["task"], "status": "submitting", "sessions": {}}
    gl.pages.return_value = [note("dispatch", record)]
    api = Mock()
    state = dict(reviewer="r", merger="m", vault="v", credential="c")
    assert cloud.dispatch(api, gl, state, 12)[0]["state"] == "recovery_required"
    api.api.assert_not_called()
    api.pages.return_value = [{"id": "known", "created_at": 1, "metadata": {
        "integration": cloud.NAMESPACE, "mr": "12", "run_id": record["run_id"], "role": "reviewer"}}]
    assert cloud.recover(api, gl, 12)["sessions"] == {"reviewer": "known"}


def test_separate_namespace_and_state():
    assert cloud.STATE.parent.name == "openai_gitlab_cloud"
    assert cloud.NAMESPACE == "support-demo-isolated"
    assert "isolated" in bridge.marker("review")


def test_environment_alias_and_precedence(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("OPENAI_API=file-value\n")
    monkeypatch.setattr(cloud, "ROOT", tmp_path)
    monkeypatch.setenv("OPENAI_API", "process-value")
    assert cloud.config().key == "process-value"
