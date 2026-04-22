import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import MagicMock
import pytest

from tests.conftest import _make_file_list, _make_media


def _wire_folder_traversal(mock_drive, folder_ids: list, file_id: Optional[str] = None):
    """
    Simulate folder resolution: users_folder → user_folder → optional file lookup.
    folder_ids: [users_folder_id, user_folder_id]
    file_id: the file found (or None = not found)
    """
    list_side_effects = [
        _make_file_list([folder_ids[0]]),   # 'users' folder
        _make_file_list([folder_ids[1]]),   # user_id folder
    ]
    if file_id is not None:
        list_side_effects.append(_make_file_list([file_id]))
    else:
        list_side_effects.append(_make_file_list([]))
    mock_drive.files.return_value.list.return_value.execute.side_effect = list_side_effects


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
