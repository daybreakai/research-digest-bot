import json
from research_digest.state import GDriveStateStore


def handle_custom_tool(
    tool_name: str,
    tool_input: dict,
    store: GDriveStateStore,
) -> str:
    """Dispatch an agent.custom_tool_use event to the state store. Returns JSON or status string."""
    user_id: str = tool_input["user_id"]
    try:
        if tool_name == "get_seen_papers":
            return json.dumps(store.get_seen_papers(user_id))
        elif tool_name == "save_seen_papers":
            store.save_seen_papers(user_id, tool_input["ids"])
            return "Saved seen papers."
        elif tool_name == "get_user_prefs":
            return json.dumps(store.get_user_prefs(user_id))
        elif tool_name == "save_user_prefs":
            store.save_user_prefs(user_id, tool_input["topics"])
            return "Saved user prefs."
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as exc:
        return f"Error in {tool_name}: {exc}"
