# tests/test_server.py
import importlib
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def test_app(mock_store):
    env_overrides = {
        "SLACK_SIGNING_SECRET": "test_secret",
        "GDRIVE_CREDENTIALS_PATH": "fake/creds.json",
        "GDRIVE_ROOT_FOLDER_ID": "fake_root",
        "AGENT_ID": "agent_test",
        "ENV_ID": "env_test",
    }
    with patch("research_digest.server.GDriveStateStore", return_value=mock_store), \
         patch.dict("os.environ", env_overrides):
        import research_digest.server as srv
        importlib.reload(srv)
        yield srv.app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_health_ok(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


def test_slash_command_acks_immediately(client):
    with patch("research_digest.server.run_session", return_value="sesn_1"):
        resp = client.post("/slack/digest", data={
            "user_id": "U123",
            "text": "",
            "response_url": "https://hooks.slack.com/test",
        })
    assert resp.status_code == 200
    assert "\U0001f4e1" in resp.json().get("text", "")


def test_slash_command_uses_text_as_message(client):
    with patch("research_digest.server.run_session", return_value="sesn_1") as mock_run:
        client.post("/slack/digest", data={
            "user_id": "U456",
            "text": "add topic: conformal prediction",
            "response_url": "https://hooks.slack.com/test",
        })
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["user_id"] == "U456"
    assert "conformal prediction" in call_kwargs["message"]


def test_slash_command_default_message_when_text_empty(client):
    with patch("research_digest.server.run_session", return_value="sesn_1") as mock_run:
        client.post("/slack/digest", data={
            "user_id": "U789",
            "text": "  ",
            "response_url": "https://hooks.slack.com/test",
        })
    assert "digest" in mock_run.call_args.kwargs["message"].lower()


def test_slack_events_routes_reply_to_active_session(client):
    """Message from a user with an active session is forwarded to that session."""
    import research_digest.server as srv
    srv._active_sessions["U123"] = "sesn_active"

    with patch("research_digest.server._send_to_session") as mock_send:
        resp = client.post("/slack/events", json={
            "event": {
                "type": "message",
                "user": "U123",
                "text": "boost tabular ML weight",
                "thread_ts": "ts_irrelevant",
            }
        })
    assert resp.status_code == 200
    mock_send.assert_called_once_with("sesn_active", "boost tabular ML weight")


def test_slack_events_ignores_user_with_no_active_session(client):
    import research_digest.server as srv
    srv._active_sessions.clear()

    with patch("research_digest.server._send_to_session") as mock_send:
        resp = client.post("/slack/events", json={
            "event": {"type": "message", "user": "U_UNKNOWN", "text": "hello"}
        })
    assert resp.status_code == 200
    mock_send.assert_not_called()
