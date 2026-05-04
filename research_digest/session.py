import os
import sys
import anthropic
from research_digest.state import GDriveStateStore
from research_digest.tools import handle_custom_tool

client = anthropic.Anthropic()


def _require_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        print("WARNING: {} not set — run setup.py first".format(name), file=sys.stderr)
    return val


AGENT_ID        = _require_env("AGENT_ID")
ALFRED_AGENT_ID = _require_env("ALFRED_AGENT_ID")
ENV_ID          = _require_env("ENV_ID")

AGENT_TOOLS = [
    {"type": "agent_toolset_20260401"},
    {
        "type": "custom",
        "name": "get_seen_papers",
        "description": (
            "Return paper IDs already delivered to this user (last 90 days). "
            "Pass the user_id from the [user_id: ...] tag at conversation start."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
    {
        "type": "custom",
        "name": "save_seen_papers",
        "description": "Record the paper IDs delivered in this run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["user_id", "ids"],
        },
    },
    {
        "type": "custom",
        "name": "get_user_prefs",
        "description": (
            "Return this user's topic keywords and weights as "
            '{"topics": [{"keyword": "...", "weight": 1.0}]}.'
        ),
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
    {
        "type": "custom",
        "name": "save_user_prefs",
        "description": (
            "Replace this user's topic keywords and weights. "
            "Call after collecting in-session feedback or when the user adds/removes topics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "topics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"},
                            "weight": {"type": "number"},
                        },
                        "required": ["keyword", "weight"],
                    },
                },
            },
            "required": ["user_id", "topics"],
        },
    },
]


def run_session(user_id: str, message: str, store: GDriveStateStore, on_session_created=None) -> str:
    """
    Create a Managed Agent session for one user invocation, stream it to completion,
    and return the session ID for thread tracking.
    """
    session = client.beta.sessions.create(
        agent=AGENT_ID,
        environment_id=ENV_ID,
        title="Research digest — {}".format(user_id),
    )

    # Call the callback immediately after session creation, before blocking on stream
    # This lets callers register the session_id while the session is still active
    if on_session_created is not None:
        on_session_created(session.id)

    first_message = (
        "[user_id: {}]\n\n"
        "{}\n\n"
        "After posting the digest to Slack, summarize the papers here and ask "
        "if I have any feedback on topics to adjust. "
        "Use my user_id in all tool calls."
    ).format(user_id, message)

    pending_tools = []

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            {"events": [{
                "type": "user.message",
                "content": [{"type": "text", "text": first_message}],
            }]},
        )

        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(block.text, end="", flush=True)
            elif event.type == "agent.tool_use":
                print("\n  [{}]".format(event.name), flush=True)
            elif event.type == "agent.custom_tool_use":
                pending_tools.append(event)
            elif event.type == "session.status_idle":
                if pending_tools:
                    try:
                        _service_tools(session.id, pending_tools, store)
                    finally:
                        pending_tools.clear()
                    # Stay in stream — agent will resume
                else:
                    print("\n")
                    break
            elif event.type == "session.status_terminated":
                break
            elif event.type == "session.error":
                print("\n Session error: {}".format(event))
                break

    return session.id


def run_alfred_session(thread_ts: str, paper_url: str, question: str) -> str:
    """
    Create a one-shot Alfred managed agent session for a single @alfred question.
    Returns the agent's reply text.
    """
    session = client.beta.sessions.create(
        agent=ALFRED_AGENT_ID,
        environment_id=ENV_ID,
        title="Alfred — {}".format(thread_ts),
    )

    message = (
        "[thread_ts: {}]\n"
        "[paper_url: {}]\n\n"
        "{}"
    ).format(thread_ts, paper_url, question)

    reply_parts = []

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            {"events": [{
                "type": "user.message",
                "content": [{"type": "text", "text": message}],
            }]},
        )

        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        reply_parts.append(block.text)
            elif event.type in ("session.status_terminated", "session.error"):
                break
            elif event.type == "session.status_idle":
                break

    return "".join(reply_parts).strip()


def _service_tools(session_id: str, pending: list, store: GDriveStateStore) -> None:
    results = [
        {
            "type": "user.custom_tool_result",
            "custom_tool_use_id": t.id,
            "content": [{
                "type": "text",
                "text": handle_custom_tool(t.tool_name, t.input, store),
            }],
        }
        for t in pending
    ]
    client.beta.sessions.events.send(session_id, {"events": results})
