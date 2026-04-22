import pytest
from unittest.mock import MagicMock, patch
from research_digest.session import run_session


def _event(type_: str, **kwargs):
    e = MagicMock()
    e.type = type_
    for k, v in kwargs.items():
        setattr(e, k, v)
    return e


def _text_block(text: str):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


@pytest.fixture
def mock_client():
    c = MagicMock()
    session = MagicMock()
    session.id = "sesn_test"
    c.beta.sessions.create.return_value = session
    return c


def _attach_stream(mock_client, events: list):
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=iter(events))
    ctx.__exit__ = MagicMock(return_value=False)
    mock_client.beta.sessions.events.stream.return_value = ctx


def test_first_message_contains_user_id(mock_client, mock_store):
    _attach_stream(mock_client, [_event("session.status_idle")])

    with patch("research_digest.session.client", mock_client):
        run_session("U123", "Run the digest.", mock_store)

    send_call = mock_client.beta.sessions.events.send.call_args
    text = send_call.args[1]["events"][0]["content"][0]["text"]
    assert "[user_id: U123]" in text


def test_terminates_on_status_terminated(mock_client, mock_store):
    _attach_stream(mock_client, [_event("session.status_terminated")])

    with patch("research_digest.session.client", mock_client):
        run_session("U123", "Run the digest.", mock_store)  # must not raise


def test_services_custom_tool_then_continues(mock_client, mock_store):
    """On idle with pending custom tool, services it then re-enters the stream."""
    tool_evt = _event("agent.custom_tool_use")
    tool_evt.tool_name = "get_seen_papers"
    tool_evt.input = {"user_id": "U123"}
    tool_evt.id = "sevt_1"

    _attach_stream(mock_client, [
        tool_evt,
        _event("session.status_idle"),            # idle with pending tool → service + continue
        _event("agent.message", content=[_text_block("Here are papers.")]),
        _event("session.status_idle"),             # idle with no pending → break
    ])

    with patch("research_digest.session.client", mock_client):
        run_session("U123", "Run the digest.", mock_store)

    # send called twice: initial message + tool result
    assert mock_client.beta.sessions.events.send.call_count == 2
    result_events = mock_client.beta.sessions.events.send.call_args_list[1].args[1]["events"]
    assert result_events[0]["type"] == "user.custom_tool_result"
    assert result_events[0]["custom_tool_use_id"] == "sevt_1"


def test_returns_session_id(mock_client, mock_store):
    _attach_stream(mock_client, [_event("session.status_terminated")])

    with patch("research_digest.session.client", mock_client):
        result = run_session("U123", "Run the digest.", mock_store)

    assert result == "sesn_test"
