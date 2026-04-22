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
