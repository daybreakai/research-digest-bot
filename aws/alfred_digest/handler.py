"""
Weekly digest scheduler — runs Alfred digest sessions for all known users.
Triggered by EventBridge every Monday 13:00 UTC (8am CT).
"""
import base64
import json
import os
import sys
import tempfile

import anthropic

ALFRED_AGENT_ID        = os.environ["ALFRED_AGENT_ID"]
ENV_ID                 = os.environ["ENV_ID"]
GDRIVE_ROOT_FOLDER_ID  = os.environ.get("GDRIVE_ROOT_FOLDER_ID", "")
GDRIVE_CREDENTIALS_B64 = os.environ.get("GDRIVE_CREDENTIALS_B64", "")

_client = anthropic.Anthropic()


def _get_store():
    if not GDRIVE_CREDENTIALS_B64 or not GDRIVE_ROOT_FOLDER_ID:
        return None
    try:
        from research_digest_state import GDriveStateStore
        creds_json = base64.b64decode(GDRIVE_CREDENTIALS_B64)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(creds_json)
            creds_path = f.name
        return GDriveStateStore(credentials_path=creds_path, root_folder_id=GDRIVE_ROOT_FOLDER_ID)
    except Exception as exc:
        print("GDrive init error: {}".format(exc), file=sys.stderr)
        return None


def _handle_custom_tool(store, tool_name, tool_input):
    try:
        user_id = tool_input.get("user_id", "default")
        if tool_name == "get_seen_papers":
            return json.dumps(store.get_seen_papers(user_id))
        elif tool_name == "save_seen_papers":
            store.save_seen_papers(user_id, tool_input["ids"])
            return "Saved."
        elif tool_name == "get_user_prefs":
            return json.dumps(store.get_user_prefs(user_id))
        elif tool_name == "save_user_prefs":
            store.save_user_prefs(user_id, tool_input["topics"])
            return "Saved."
        return json.dumps({"error": "unknown tool"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _run_digest_for_user(user_id, store):
    session = _client.beta.sessions.create(
        agent=ALFRED_AGENT_ID,
        environment_id=ENV_ID,
        title="Weekly digest — {}".format(user_id),
    )
    msg = "[user_id: {}]\n\nPlease run the weekly research digest for this user.".format(user_id)
    pending_tools = []

    with _client.beta.sessions.events.stream(session.id) as stream:
        _client.beta.sessions.events.send(
            session.id,
            events=[{"type": "user.message",
                     "content": [{"type": "text", "text": msg}]}],
        )
        for event in stream:
            if event.type == "agent.custom_tool_use":
                pending_tools.append(event)
            elif event.type == "session.status_idle":
                if pending_tools:
                    results = [
                        {"type": "user.custom_tool_result",
                         "custom_tool_use_id": t.id,
                         "content": [{"type": "text",
                                      "text": _handle_custom_tool(store, t.name, t.input)}]}
                        for t in pending_tools
                    ]
                    _client.beta.sessions.events.send(session.id, events=results)
                    pending_tools.clear()
                else:
                    break
            elif event.type in ("session.status_terminated", "session.error"):
                break

    print("Digest complete for user {}".format(user_id))


def lambda_handler(event, context):
    store = _get_store()
    if store is None:
        print("ERROR: GDrive store unavailable", file=sys.stderr)
        return

    users = store.list_users()
    if not users:
        print("No users found — skipping digest run")
        return

    print("Running weekly digest for {} user(s): {}".format(len(users), users))
    for user_id in users:
        try:
            _run_digest_for_user(user_id, store)
        except Exception as exc:
            print("Digest error for {}: {}".format(user_id, exc), file=sys.stderr)
