import json
import pytest
from unittest.mock import MagicMock, patch


def _make_file_list(file_ids: list[str]) -> dict:
    return {"files": [{"id": fid} for fid in file_ids]}


def _make_media(content: dict) -> bytes:
    return json.dumps(content).encode()


def _wire_folder_traversal(mock_drive, folder_ids: list, file_id=None):
    """
    Simulate folder resolution: users_folder → user_folder → optional file lookup.
    folder_ids: [users_folder_id, user_folder_id]
    file_id: the file found (or None = not found)
    """
    list_side_effects = [
        _make_file_list([folder_ids[0]]),
        _make_file_list([folder_ids[1]]),
    ]
    if file_id is not None:
        list_side_effects.append(_make_file_list([file_id]))
    else:
        list_side_effects.append(_make_file_list([]))
    mock_drive.files.return_value.list.return_value.execute.side_effect = list_side_effects


@pytest.fixture
def mock_drive():
    return MagicMock()


@pytest.fixture
def mock_store(mock_drive):
    from research_digest.state import GDriveStateStore
    with patch("research_digest.state.build", return_value=mock_drive), \
         patch("research_digest.state.service_account") as mock_sa:
        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        store = GDriveStateStore(
            credentials_path="fake/path.json",
            root_folder_id="root_id",
        )
        yield store   # yield, not return
