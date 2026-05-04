# research_digest/server.py
import hashlib
import hmac
import json
import os
import re
import sys
import time
from contextlib import asynccontextmanager

import anthropic as _anthropic
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import JSONResponse

load_dotenv()

from research_digest.session import run_alfred_session, run_session
from research_digest.state import GDriveStateStore

SLACK_BOT_TOKEN     = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
ALFRED_CHANNEL_ID   = "C0AT9D2UYUX"

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


def _verify_slack_signature(body: bytes, headers: dict) -> bool:
    timestamp = headers.get("x-slack-request-timestamp", "0")
    if abs(time.time() - int(timestamp)) > 300:
        return False
    sig_base = "v0:{}:{}".format(timestamp, body.decode()).encode()
    expected = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(), sig_base, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, headers.get("x-slack-signature", ""))


def _slack_post(thread_ts: str, text: str) -> None:
    import urllib.request
    data = json.dumps({
        "channel": ALFRED_CHANNEL_ID,
        "thread_ts": thread_ts,
        "text": text,
    }).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=data,
        headers={
            "Authorization": "Bearer {}".format(SLACK_BOT_TOKEN),
            "Content-Type": "application/json",
        },
    )
    urllib.request.urlopen(req, timeout=10)


def _get_thread_parent_text(thread_ts: str) -> str:
    import urllib.request
    url = (
        "https://slack.com/api/conversations.replies"
        "?channel={}&ts={}&limit=1&oldest={}&inclusive=true"
    ).format(ALFRED_CHANNEL_ID, thread_ts, thread_ts)
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer {}".format(SLACK_BOT_TOKEN)},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    msgs = data.get("messages", [])
    return msgs[0].get("text", "") if msgs else ""


def _handle_alfred_mention(thread_ts: str, question: str) -> None:
    parent_text = _get_thread_parent_text(thread_ts)
    match = re.search(r"https?://arxiv\.org/\S+", parent_text)
    paper_url = match.group().rstrip(">") if match else ""

    if not paper_url:
        _slack_post(thread_ts, "*Alfred* 🤖\nI couldn't find the paper link in this thread. Can you paste the URL?")
        return

    if not question:
        _slack_post(thread_ts, "*Alfred* 🤖\nWhat would you like to know about this paper?")
        return

    try:
        reply = run_alfred_session(thread_ts=thread_ts, paper_url=paper_url, question=question)
        if not reply:
            reply = "*Alfred* 🤖\nI had trouble generating a response. Try again or paste a direct arxiv link."
    except Exception as exc:
        print("Alfred session error: {}".format(exc), file=sys.stderr)
        reply = "*Alfred* 🤖\nI had trouble fetching this paper. Try again or paste a direct arxiv link."

    _slack_post(thread_ts, reply)


@app.post("/slack/alfred")
async def slack_alfred(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Skip Slack retries — first delivery handles it
    if headers.get("x-slack-retry-num"):
        return JSONResponse({"ok": True})

    if SLACK_SIGNING_SECRET and not _verify_slack_signature(body, headers):
        return JSONResponse({"error": "invalid signature"}, status_code=403)

    payload = json.loads(body)

    # URL verification handshake
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload["challenge"]})

    ev = payload.get("event", {})

    # Only handle app_mention in #research-digest, ignore bot messages
    if ev.get("type") != "app_mention" or ev.get("channel") != ALFRED_CHANNEL_ID or ev.get("bot_id"):
        return JSONResponse({"ok": True})

    thread_ts = ev.get("thread_ts") or ev.get("ts")
    question  = re.sub(r"<@[A-Z0-9]+>", "", ev.get("text", "")).strip()

    background_tasks.add_task(_handle_alfred_mention, thread_ts=thread_ts, question=question)
    return JSONResponse({"ok": True})
