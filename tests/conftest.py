import json
import pytest
from unittest.mock import MagicMock, patch


def _make_file_list(file_ids: list[str]) -> dict:
    return {"files": [{"id": fid} for fid in file_ids]}


def _make_media(content: dict) -> bytes:
    return json.dumps(content).encode()


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
    return store
