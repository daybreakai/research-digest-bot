import json
import pytest
from unittest.mock import MagicMock
from research_digest.tools import handle_custom_tool


@pytest.fixture
def store():
    s = MagicMock()
    s.get_seen_papers.return_value = ["paper-1", "paper-2"]
    s.get_user_prefs.return_value = {
        "topics": [{"keyword": "retail demand forecasting", "weight": 1.2}]
    }
    return s


def test_get_seen_papers(store):
    result = handle_custom_tool("get_seen_papers", {"user_id": "U123"}, store)
    assert json.loads(result) == ["paper-1", "paper-2"]
    store.get_seen_papers.assert_called_once_with("U123")


def test_get_user_prefs(store):
    result = handle_custom_tool("get_user_prefs", {"user_id": "U123"}, store)
    parsed = json.loads(result)
    assert "topics" in parsed
    assert parsed["topics"][0]["keyword"] == "retail demand forecasting"


def test_save_seen_papers(store):
    result = handle_custom_tool(
        "save_seen_papers", {"user_id": "U123", "ids": ["p-3", "p-4"]}, store
    )
    store.save_seen_papers.assert_called_once_with("U123", ["p-3", "p-4"])
    assert "Saved" in result


def test_save_user_prefs(store):
    topics = [{"keyword": "conformal prediction", "weight": 1.0}]
    result = handle_custom_tool(
        "save_user_prefs", {"user_id": "U123", "topics": topics}, store
    )
    store.save_user_prefs.assert_called_once_with("U123", topics)
    assert "Saved" in result


def test_unknown_tool_returns_error_string(store):
    result = handle_custom_tool("nonexistent", {"user_id": "U123"}, store)
    assert "Unknown tool" in result


def test_store_exception_returns_error_string(store):
    store.get_seen_papers.side_effect = Exception("Drive unavailable")
    result = handle_custom_tool("get_seen_papers", {"user_id": "U123"}, store)
    assert "Error" in result
