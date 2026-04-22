# research_digest/server.py
import os
import sys
from contextlib import asynccontextmanager

import anthropic as _anthropic
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Form
from fastapi.responses import JSONResponse

load_dotenv()

from research_digest.session import run_session
from research_digest.state import GDriveStateStore

_store = None
_active_sessions = {}   # user_id → session_id


@asynccontextmanager
async def lifespan(app):
    global _store
    _store = GDriveStateStore(
        credentials_path=os.environ["GDRIVE_CREDENTIALS_PATH"],
        root_folder_id=os.environ["GDRIVE_ROOT_FOLDER_ID"],
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/slack/digest")
async def slack_digest(
    background_tasks: BackgroundTasks,
    user_id: str = Form(...),
    text: str = Form(default=""),
    response_url: str = Form(default=""),
):
    message = text.strip() if text.strip() else "Run the research digest."
    background_tasks.add_task(
        _run_and_register,
        user_id=user_id,
        message=message,
    )
    return JSONResponse({"response_type": "ephemeral", "text": "\U0001f4e1 Running your digest..."})


def _run_and_register(user_id, message):
    def _register(session_id):
        _active_sessions[user_id] = session_id

    try:
        run_session(user_id=user_id, message=message, store=_store, on_session_created=_register)
    except Exception as exc:
        print("Session error for {}: {}".format(user_id, exc), file=sys.stderr)
    finally:
        # Session is complete (run_session returned) — clean up stale entry
        _active_sessions.pop(user_id, None)


_anthropic_client = _anthropic.Anthropic()


def _send_to_session(session_id, text):
    _anthropic_client.beta.sessions.events.send(
        session_id,
        {"events": [{
            "type": "user.message",
            "content": [{"type": "text", "text": text}],
        }]},
    )


@app.post("/slack/events")
async def slack_events(payload: dict):
    event = payload.get("event", {})
    user_id = event.get("user")
    text    = event.get("text", "")

    if user_id and user_id in _active_sessions:
        _send_to_session(_active_sessions[user_id], text)

    return JSONResponse({"ok": True})
