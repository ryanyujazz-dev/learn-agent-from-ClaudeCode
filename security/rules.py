import json
import os
import fnmatch


RULES_FILE = os.path.expanduser("~/.mini-claude/permissions.json")


def _load() -> dict:
    if not os.path.isfile(RULES_FILE):
        return {"allow": [], "deny": []}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(rules: dict) -> None:
    os.makedirs(os.path.dirname(RULES_FILE), exist_ok=True)
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)


def _matches(pattern: str, value: str) -> bool:
    return fnmatch.fnmatch(value, pattern)


def check_rule(tool_name: str, command: str) -> str:
    """
    Returns 'allow', 'deny', or 'ask'.
    Mirrors bashPermissions.ts allow/deny rule matching.
    """
    rules = _load()
    key = f"{tool_name}:{command}"
    for pattern in rules.get("deny", []):
        if _matches(pattern, key) or _matches(pattern, command):
            return "deny"
    for pattern in rules.get("allow", []):
        if _matches(pattern, key) or _matches(pattern, command):
            return "allow"
    return "ask"


def add_rule(decision: str, tool_name: str, command: str) -> None:
    """Persist an allow or deny rule."""
    rules = _load()
    pattern = f"{tool_name}:{command}"
    key = "allow" if decision == "allow" else "deny"
    if pattern not in rules[key]:
        rules[key].append(pattern)
    _save(rules)
