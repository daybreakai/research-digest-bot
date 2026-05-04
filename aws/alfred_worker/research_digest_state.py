import io
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
_SEEN_FILE = "seen-papers.json"
_PREFS_FILE = "prefs.json"
_ROLLING_DAYS = 90

DEFAULT_TOPICS = [
    {"keyword": "retail demand forecasting", "weight": 1.0},
    {"keyword": "tabular ML", "weight": 1.0},
    {"keyword": "deep learning time series", "weight": 1.0},
    {"keyword": "time series statistical analysis", "weight": 1.0},
]


class GDriveStateStore:
    def __init__(self, credentials_path: str, root_folder_id: str) -> None:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
        self._drive = build("drive", "v3", credentials=creds)
        self._root = root_folder_id
        self._folder_cache: Dict[str, str] = {}

    def _get_or_create_folder(self, name: str, parent_id: str) -> str:
        key = f"{parent_id}/{name}"
        if key in self._folder_cache:
            return self._folder_cache[key]
        results = self._drive.files().list(
            q=(f"name='{name}' and '{parent_id}' in parents "
               "and mimeType='application/vnd.google-apps.folder' and trashed=false"),
            fields="files(id)",
        ).execute()
        files = results.get("files", [])
        if files:
            folder_id = files[0]["id"]
        else:
            folder_id = self._drive.files().create(
                body={"name": name,
                      "mimeType": "application/vnd.google-apps.folder",
                      "parents": [parent_id]},
                fields="id",
            ).execute()["id"]
        self._folder_cache[key] = folder_id
        return folder_id

    def _get_file_id(self, filename: str, parent_id: str) -> Optional[str]:
        results = self._drive.files().list(
            q=f"name='{filename}' and '{parent_id}' in parents and trashed=false",
            fields="files(id)",
        ).execute()
        files = results.get("files", [])
        return files[0]["id"] if files else None

    def _read_json(self, filename: str, folder_id: str) -> Optional[dict]:
        file_id = self._get_file_id(filename, folder_id)
        if not file_id:
            return None
        raw = self._drive.files().get_media(fileId=file_id).execute()
        return json.loads(raw)

    def _write_json(self, filename: str, folder_id: str, data: dict) -> None:
        content = json.dumps(data, indent=2).encode()
        buf = io.BytesIO(content)
        media = MediaIoBaseUpload(buf, mimetype="application/json", chunksize=-1)
        buf.seek(0)
        file_id = self._get_file_id(filename, folder_id)
        if file_id:
            self._drive.files().update(fileId=file_id, media_body=media).execute()
        else:
            self._drive.files().create(
                body={"name": filename, "parents": [folder_id]},
                media_body=media,
                fields="id",
            ).execute()

    def _user_folder(self, user_id: str) -> str:
        users = self._get_or_create_folder("users", self._root)
        return self._get_or_create_folder(user_id, users)

    def list_users(self) -> List[str]:
        """Return all user IDs that have stored state."""
        try:
            users_folder = self._get_or_create_folder("users", self._root)
            results = self._drive.files().list(
                q=(f"'{users_folder}' in parents "
                   "and mimeType='application/vnd.google-apps.folder' and trashed=false"),
                fields="files(name)",
            ).execute()
            return [f["name"] for f in results.get("files", [])]
        except Exception:
            return []

    def get_seen_papers(self, user_id: str) -> List[str]:
        folder = self._user_folder(user_id)
        data = self._read_json(_SEEN_FILE, folder)
        if not data:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=_ROLLING_DAYS)
        return [
            e["id"] for e in data.get("seen", [])
            if datetime.fromisoformat(e["seen_at"]) > cutoff
        ]

    def save_seen_papers(self, user_id: str, ids: List[str]) -> None:
        folder = self._user_folder(user_id)
        existing = self._read_json(_SEEN_FILE, folder) or {"seen": []}
        existing_ids = {e["id"] for e in existing["seen"]}
        now = datetime.now(timezone.utc).isoformat()
        for paper_id in ids:
            if paper_id not in existing_ids:
                existing["seen"].append({"id": paper_id, "seen_at": now})
        self._write_json(_SEEN_FILE, folder, existing)

    def get_user_prefs(self, user_id: str) -> dict:
        """Return topics plus is_new_user flag when no prefs file exists."""
        folder = self._user_folder(user_id)
        data = self._read_json(_PREFS_FILE, folder)
        if not data:
            return {"topics": [t.copy() for t in DEFAULT_TOPICS], "is_new_user": True}
        return {"topics": data.get("topics", [t.copy() for t in DEFAULT_TOPICS]), "is_new_user": False}

    def save_user_prefs(self, user_id: str, topics: List[dict]) -> None:
        folder = self._user_folder(user_id)
        existing = self._read_json(_PREFS_FILE, folder) or {"topics": [], "history": []}
        existing["topics"] = topics
        self._write_json(_PREFS_FILE, folder, existing)
