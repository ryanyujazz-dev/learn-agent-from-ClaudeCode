import json
import os
from datetime import datetime


SESSIONS_DIR = os.path.expanduser("~/.mini-claude/sessions")
LATEST = os.path.join(SESSIONS_DIR, "latest.json")


def save_session(messages: list) -> None:
    """Write latest.json and archive a timestamped copy."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    data = json.dumps(messages, ensure_ascii=False, indent=2)
    with open(LATEST, "w", encoding="utf-8") as f:
        f.write(data)
    archive = os.path.join(SESSIONS_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(archive, "w", encoding="utf-8") as f:
        f.write(data)


def _is_complete(messages: list) -> bool:
    """
    Check that every assistant tool_call has a matching tool result.
    Prevents resuming with a broken message sequence that causes API errors.
    """
    pending = set()
    for msg in messages:
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls", []):
                pending.add(tc["id"])
        elif msg.get("role") == "tool":
            pending.discard(msg.get("tool_call_id", ""))
    return len(pending) == 0


def load_latest_session() -> list:
    """Load latest.json for --resume. Drops incomplete sessions."""
    if not os.path.isfile(LATEST):
        return []
    with open(LATEST, "r", encoding="utf-8") as f:
        messages = json.load(f)
    if not _is_complete(messages):
        print("[Warning] Last session was incomplete (interrupted mid-tool-call). Starting fresh.")
        return []
    return messages
