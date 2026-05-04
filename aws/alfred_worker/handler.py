import base64
import json
import os
import re
import sys
import tempfile
import time
import urllib.request

import anthropic

SLACK_BOT_TOKEN        = os.environ["SLACK_BOT_TOKEN"]
ALFRED_AGENT_ID        = os.environ["ALFRED_AGENT_ID"]
ENV_ID                 = os.environ["ENV_ID"]
ALFRED_CHANNEL_ID      = os.environ.get("ALFRED_CHANNEL_ID", "C0AT9D2UYUX")
GDRIVE_ROOT_FOLDER_ID  = os.environ.get("GDRIVE_ROOT_FOLDER_ID", "")
GDRIVE_CREDENTIALS_B64 = os.environ.get("GDRIVE_CREDENTIALS_B64", "")

SLACK_MAX_CHARS   = 3800   # Slack limit is 4000; leave headroom
TOOL_TIMEOUT_SECS = 20     # Max time to spend on a single GDrive tool call
STREAM_CUTOFF_MS  = 30_000 # Stop streaming when Lambda has <30s remaining

_client = anthropic.Anthropic()
_store  = None

_DIGEST_SIGNALS = {"find", "search", "papers", "digest", "weekly", "new in", "what's new",
                   "status", "preferences", "my topics", "what do you know"}

# Phrases that indicate a Mode 4 (paper discovery) request — handler pre-fetches
# GDrive state so the session never needs to call get_seen_papers / get_user_prefs.
_MODE4_SIGNALS = {"search arxiv", "run a digest", "run digest",
                  "what's new in", "give me the latest", "latest papers"}


def _get_store():
    global _store
    if _store is not None:
        return _store
    if not GDRIVE_CREDENTIALS_B64 or not GDRIVE_ROOT_FOLDER_ID:
        return None
    try:
        from research_digest_state import GDriveStateStore
        creds_json = base64.b64decode(GDRIVE_CREDENTIALS_B64)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(creds_json)
            creds_path = f.name
        _store = GDriveStateStore(credentials_path=creds_path, root_folder_id=GDRIVE_ROOT_FOLDER_ID)
    except Exception as exc:
        print("GDrive init error: {}".format(exc), file=sys.stderr)
    return _store


def _handle_custom_tool(tool_name, tool_input):
    """Service a custom tool call with a hard timeout."""
    store = _get_store()
    if store is None:
        return json.dumps({"error": "state store unavailable"})
    deadline = time.time() + TOOL_TIMEOUT_SECS
    try:
        user_id = tool_input.get("user_id", "default")
        if tool_name == "get_seen_papers":
            result = store.get_seen_papers(user_id)
        elif tool_name == "save_seen_papers":
            store.save_seen_papers(user_id, tool_input["ids"])
            result = "Saved."
        elif tool_name == "get_user_prefs":
            result = store.get_user_prefs(user_id)
        elif tool_name == "save_user_prefs":
            store.save_user_prefs(user_id, tool_input["topics"])
            result = "Saved."
        else:
            return json.dumps({"error": "unknown tool: {}".format(tool_name)})

        if time.time() > deadline:
            return json.dumps({"error": "tool timed out"})
        return json.dumps(result) if not isinstance(result, str) else result
    except Exception as exc:
        print("Tool error {}: {}".format(tool_name, exc), file=sys.stderr)
        return json.dumps({"error": str(exc)})


# ── Slack helpers ──────────────────────────────────────────────────────────────

def _slack_get(path, params=""):
    url = "https://slack.com/api/{}?{}".format(path, params)
    req = urllib.request.Request(
        url, headers={"Authorization": "Bearer {}".format(SLACK_BOT_TOKEN)}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _slack_post(thread_ts, text, channel=None):
    text = _truncate(text)
    data = json.dumps({
        "channel": channel or ALFRED_CHANNEL_ID,
        "thread_ts": thread_ts,
        "text": text,
    }).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage", data=data,
        headers={"Authorization": "Bearer {}".format(SLACK_BOT_TOKEN),
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _slack_update(channel, ts, text):
    text = _truncate(text)
    data = json.dumps({"channel": channel, "ts": ts, "text": text}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.update", data=data,
        headers={"Authorization": "Bearer {}".format(SLACK_BOT_TOKEN),
                 "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)


def _truncate(text):
    """Trim to Slack's message limit, appending a note if cut."""
    if len(text) <= SLACK_MAX_CHARS:
        return text
    cutoff = text.rfind("\n", 0, SLACK_MAX_CHARS) or SLACK_MAX_CHARS
    return text[:cutoff] + "\n\n_...response truncated. Ask me to continue if needed._"


def _clean_slack_text(text):
    text = re.sub(r"<@[A-Z0-9]+>", "@alfred", text)
    text = re.sub(r"<https?://[^|>]+\|([^>]+)>", r"\1", text)
    text = re.sub(r"<(https?://[^>]+)>", r"\1", text)
    return text.strip()


def _get_thread_data(thread_ts, channel, max_msgs=5):
    """
    Single Slack API call that returns both the paper URL (from the thread root)
    and the thread history (from subsequent messages).  Replaces two separate
    conversations.replies calls.
    """
    data = _slack_get(
        "conversations.replies",
        "channel={}&ts={}&limit={}".format(
            channel or ALFRED_CHANNEL_ID, thread_ts, max_msgs + 2
        ),
    )
    msgs = data.get("messages", [])

    # Paper URL lives in the thread root (first message).
    # Normalize to the abstract page (/abs/) — never pass a PDF URL to Alfred.
    paper_url = ""
    if msgs:
        match = re.search(r"https?://arxiv\.org/\S+", msgs[0].get("text", ""))
        if match:
            url = match.group().rstrip(">")
            url = re.sub(r"/pdf/", "/abs/", url)
            url = re.sub(r"\.pdf$", "", url)
            paper_url = url

    # Thread history is everything between root and the current (last) message
    thread_ctx = ""
    if len(msgs) > 2:
        lines = []
        for msg in msgs[1:-1][-max_msgs:]:
            user = "Alfred" if msg.get("bot_id") else msg.get("user", "user")
            text = _clean_slack_text(msg.get("text", ""))[:250]
            if text:
                lines.append("{}: {}".format(user, text))
        thread_ctx = "\n".join(lines)

    return paper_url, thread_ctx


def _needs_paper_context(question):
    q = question.lower()
    return not any(sig in q for sig in _DIGEST_SIGNALS)


def _is_mode4_request(question):
    """True when the message is a fresh paper-discovery request (Mode 4)."""
    q = question.lower()
    return any(sig in q for sig in _MODE4_SIGNALS)


def _prefetch_digest_context(user_id):
    """
    Pre-fetch GDrive state before creating the session so Alfred never needs
    to call get_seen_papers or get_user_prefs as session tool calls.
    Returns a dict with 'seen_papers' and 'user_prefs', or None on failure.
    """
    store = _get_store()
    if store is None:
        return None
    try:
        seen  = store.get_seen_papers(user_id)
        prefs = store.get_user_prefs(user_id)
        return {"seen_papers": seen, "user_prefs": prefs}
    except Exception as exc:
        print("Pre-fetch GDrive failed: {}".format(exc), file=sys.stderr)
        return None


# ── Alfred session ─────────────────────────────────────────────────────────────

def _run_alfred_session(context_msg, lambda_context=None):
    session = _client.beta.sessions.create(
        agent=ALFRED_AGENT_ID,
        environment_id=ENV_ID,
        title="Alfred session",
    )
    reply_parts   = []
    pending_tools = []
    timed_out     = False

    with _client.beta.sessions.events.stream(session.id) as stream:
        _client.beta.sessions.events.send(
            session.id,
            events=[{"type": "user.message",
                     "content": [{"type": "text", "text": context_msg}]}],
        )
        for event in stream:
            # Check Lambda time budget — bail out gracefully before hard kill
            if (lambda_context and
                    lambda_context.get_remaining_time_in_millis() < STREAM_CUTOFF_MS):
                timed_out = True
                print("Stream cut: budget low, reply_len={}".format(
                    sum(len(p) for p in reply_parts)), file=sys.stderr)
                break

            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        reply_parts.append(block.text)
            elif event.type == "agent.custom_tool_use":
                pending_tools.append(event)
                print("custom_tool: {}".format(event.name), file=sys.stderr)
            elif event.type == "agent.tool_use":
                print("builtin_tool: {}".format(getattr(event, "name", "?")), file=sys.stderr)
            elif event.type == "session.status_idle":
                if pending_tools:
                    results = [
                        {"type": "user.custom_tool_result",
                         "custom_tool_use_id": t.id,
                         "content": [{"type": "text",
                                      "text": _handle_custom_tool(t.name, t.input)}]}
                        for t in pending_tools
                    ]
                    _client.beta.sessions.events.send(session.id, events=results)
                    pending_tools.clear()
                else:
                    print("session_idle: reply_len={}".format(
                        sum(len(p) for p in reply_parts)), file=sys.stderr)
                    break
            elif event.type in ("session.status_terminated", "session.error"):
                print("session_{}: reply_len={}".format(
                    event.type, sum(len(p) for p in reply_parts)), file=sys.stderr)
                if event.type == "session.error":
                    print("error detail: {}".format(event), file=sys.stderr)
                break

    if timed_out:
        partial = "".join(reply_parts).strip()
        if partial:
            return partial + "\n\n_I ran short on time — ask me to continue._"
        return None  # signal timeout with no partial result

    return "".join(reply_parts).strip()


# ── Event handlers ─────────────────────────────────────────────────────────────

def _handle_mention(event, lambda_context):
    thread_ts = event.get("thread_ts") or event.get("ts")
    channel   = event.get("channel", ALFRED_CHANNEL_ID)
    user_id   = event.get("user", "unknown")
    question  = re.sub(r"<@[A-Z0-9]+>", "", event.get("text", "")).strip()

    if not question:
        _slack_post(thread_ts, "*Alfred* 🤖\nHow may I be of service?", channel)
        return

    thinking    = _slack_post(thread_ts, "_Alfred is attending to your request..._", channel)
    thinking_ts = thinking.get("ts") if thinking else None

    parts = [
        "[user_id: {}]".format(user_id),
        "[thread_ts: {}]".format(thread_ts),
    ]

    # Only a threaded reply has useful parent context to fetch.
    # Top-level mentions have no prior thread — skip the Slack round-trip entirely.
    is_reply = event.get("thread_ts") not in (None, event.get("ts"))

    if _is_mode4_request(question):
        # Pre-fetch GDrive state so the session skips get_seen_papers / get_user_prefs.
        digest_ctx = _prefetch_digest_context(user_id)
        if digest_ctx is not None:
            parts.append("[seen_papers: {}]".format(json.dumps(digest_ctx["seen_papers"])))
            parts.append("[user_prefs: {}]".format(json.dumps(digest_ctx["user_prefs"])))
            parts.append("[prefetched: true]")
    elif is_reply:
        # One Slack API call for both the paper URL and thread history.
        needs_paper = _needs_paper_context(question)
        paper_url, thread_ctx = _get_thread_data(thread_ts, channel)
        if needs_paper and paper_url:
            parts.append("[paper_url: {}]".format(paper_url))
        if thread_ctx:
            parts.append("[thread_history:\n{}\n]".format(thread_ctx))

    parts.append("\n{}".format(question))

    try:
        reply = _run_alfred_session("\n".join(parts), lambda_context)
        if reply is None:
            # Timed out with no partial result
            reply = (
                "*Alfred* 🤖\n"
                "My apologies — this request is taking longer than anticipated. "
                "Please try a more specific question, or break it into smaller parts."
            )
        elif not reply:
            reply = "*Alfred* 🤖\nI'm afraid I couldn't formulate a response. Do try again."
    except Exception as exc:
        print("Alfred session error: {}".format(exc), file=sys.stderr)
        reply = (
            "*Alfred* 🤖\n"
            "I encountered an unexpected difficulty. "
            "Could you rephrase, or perhaps provide a bit more context?"
        )

    if thinking_ts:
        _slack_update(channel, thinking_ts, reply)
    else:
        _slack_post(thread_ts, reply, channel)


def _handle_reaction(event):
    reaction = event.get("reaction", "")
    user_id  = event.get("user", "unknown")
    item     = event.get("item", {})
    channel  = item.get("channel", ALFRED_CHANNEL_ID)
    msg_ts   = item.get("ts", "")

    if reaction not in ("thumbsup", "thumbsdown", "+1", "-1"):
        return

    data  = _slack_get(
        "conversations.replies",
        "channel={}&ts={}&limit=1&oldest={}&inclusive=true".format(channel, msg_ts, msg_ts),
    )
    msgs  = data.get("messages", [])
    text  = msgs[0].get("text", "") if msgs else ""
    match = re.search(r"https?://arxiv\.org/\S+", text)
    if not match:
        return

    paper_url = match.group().rstrip(">")
    direction = "positive" if reaction in ("thumbsup", "+1") else "negative"

    context_msg = (
        "[user_id: {user_id}]\n"
        "[event: reaction]\n"
        "[reaction: {direction}]\n"
        "[paper_url: {paper_url}]\n\n"
        "The user reacted {direction}ly to this paper. "
        "Call get_user_prefs, identify the closest topic tag, "
        "adjust its weight ({mult}), clamp to [0.1, 3.0], "
        "call save_user_prefs, then confirm in one brief line."
    ).format(
        user_id=user_id,
        direction=direction,
        paper_url=paper_url,
        mult="× 1.2" if direction == "positive" else "× 0.8",
    )
    try:
        _run_alfred_session(context_msg)
    except Exception as exc:
        print("Reaction handler error: {}".format(exc), file=sys.stderr)


# ── Lambda entrypoint ──────────────────────────────────────────────────────────

def lambda_handler(event, context):
    if event.get("type") == "reaction_added":
        _handle_reaction(event)
    else:
        _handle_mention(event, context)
