import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest

from tests.conftest import _make_file_list, _make_media, _wire_folder_traversal


def test_get_seen_papers_filters_to_90_days(mock_drive, mock_store):
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=91)).isoformat()
    recent_ts = (now - timedelta(days=10)).isoformat()

    data = {"seen": [
        {"id": "old-paper", "seen_at": old_ts},
        {"id": "recent-paper", "seen_at": recent_ts},
    ]}
    _wire_folder_traversal(mock_drive, ["uf", "u123f"], "seen_file")
    mock_drive.files.return_value.get_media.return_value.execute.return_value = _make_media(data)

    result = mock_store.get_seen_papers("U123")

    assert result == ["recent-paper"]
    assert "old-paper" not in result


def test_get_seen_papers_empty_for_new_user(mock_drive, mock_store):
    _wire_folder_traversal(mock_drive, ["uf", "u_new_f"], file_id=None)

    result = mock_store.get_seen_papers("U_NEW")

    assert result == []


def test_save_seen_papers_appends_new_deduped(mock_drive, mock_store):
    """New IDs appended with timestamp; existing IDs not duplicated."""
    existing = {"seen": [{"id": "old-1", "seen_at": "2026-04-01T00:00:00+00:00"}]}

    # read call to get existing data
    _wire_folder_traversal(mock_drive, ["uf", "u123f"], "seen_file")
    mock_drive.files.return_value.get_media.return_value.execute.return_value = (
        _make_media(existing)
    )
    # write call uses update (file exists)
    mock_drive.files.return_value.update.return_value.execute.return_value = {}

    # Reset side_effect so the write path's _get_file_id also resolves
    mock_drive.files.return_value.list.return_value.execute.side_effect = None
    mock_drive.files.return_value.list.return_value.execute.return_value = (
        _make_file_list(["seen_file"])
    )

    mock_store.save_seen_papers("U123", ["old-1", "new-paper"])

    update_call = mock_drive.files.return_value.update.call_args
    written = json.loads(update_call.kwargs["media_body"]._fd.read())
    ids = [e["id"] for e in written["seen"]]
    assert "new-paper" in ids
    assert ids.count("old-1") == 1   # not duplicated


def test_save_seen_papers_creates_file_for_new_user(mock_drive, mock_store):
    """Creates seen-papers.json when user has no existing file."""
    mock_drive.files.return_value.list.return_value.execute.return_value = (
        _make_file_list([])
    )
    mock_drive.files.return_value.create.return_value.execute.return_value = {"id": "new_f"}

    mock_store.save_seen_papers("U_NEW", ["paper-1"])

    assert mock_drive.files.return_value.create.called


def test_get_user_prefs_returns_topics_only_not_history(mock_drive, mock_store):
    """History is stripped — agent never receives it."""
    prefs = {
        "topics": [
            {"keyword": "retail demand forecasting", "weight": 1.3},
            {"keyword": "tabular ML", "weight": 0.9},
        ],
        "history": [{"timestamp": "2026-01-01T00:00:00+00:00", "source": "init"}],
    }
    _wire_folder_traversal(mock_drive, ["uf", "u123f"], "prefs_file")
    mock_drive.files.return_value.get_media.return_value.execute.return_value = (
        _make_media(prefs)
    )

    result = mock_store.get_user_prefs("U123")

    assert "history" not in result
    assert "topics" in result
    assert len(result["topics"]) == 2
    assert result["topics"][0]["keyword"] == "retail demand forecasting"


def test_get_user_prefs_returns_defaults_for_new_user(mock_drive, mock_store):
    """New user with no prefs file gets four seeded default topics."""
    _wire_folder_traversal(mock_drive, ["uf", "u_new_f"], file_id=None)

    result = mock_store.get_user_prefs("U_NEW")

    assert "topics" in result
    assert "history" not in result
    keywords = [t["keyword"] for t in result["topics"]]
    assert "retail demand forecasting" in keywords
    assert len(result["topics"]) == 4


def test_save_user_prefs_replaces_topics_preserves_history(mock_drive, mock_store):
    """Topics array replaced; history array left untouched."""
    existing = {
        "topics": [{"keyword": "old topic", "weight": 1.0}],
        "history": [{"timestamp": "2026-01-01T00:00:00+00:00", "source": "init"}],
    }
    new_topics = [
        {"keyword": "retail demand forecasting", "weight": 1.2},
        {"keyword": "conformal prediction", "weight": 1.0},
    ]

    mock_drive.files.return_value.list.return_value.execute.return_value = (
        _make_file_list(["prefs_file"])
    )
    mock_drive.files.return_value.get_media.return_value.execute.return_value = (
        _make_media(existing)
    )
    mock_drive.files.return_value.update.return_value.execute.return_value = {}

    mock_store.save_user_prefs("U123", new_topics)

    update_call = mock_drive.files.return_value.update.call_args
    written = json.loads(update_call.kwargs["media_body"]._fd.read())
    assert written["topics"] == new_topics
    assert written["history"] == existing["history"]   # untouched


def test_save_user_prefs_creates_with_empty_history_for_new_user(mock_drive, mock_store):
    """New user: creates prefs.json with topics and empty history."""
    mock_drive.files.return_value.list.return_value.execute.return_value = (
        _make_file_list([])
    )
    mock_drive.files.return_value.create.return_value.execute.return_value = {"id": "nf"}

    mock_store.save_user_prefs("U_NEW", [{"keyword": "retail", "weight": 1.0}])

    create_call = mock_drive.files.return_value.create.call_args
    written = json.loads(create_call.kwargs["media_body"]._fd.read())
    assert written["topics"] == [{"keyword": "retail", "weight": 1.0}]
    assert written["history"] == []
