import re
from dataclasses import dataclass


@dataclass
class CommandCheckResult:
    safe: bool
    reason: str = ""
    intent: str = ""  # human-readable description of what the command does


# Patterns that are always dangerous — mirrors bashSecurity.ts BASH_SECURITY_CHECK_IDS
_DANGEROUS = [
    (r"rm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r", "recursive force delete"),
    (r":\(\)\s*\{.*\|.*&", "fork bomb"),
    (r"dd\s+if=", "raw disk write (dd)"),
    (r"mkfs\b", "filesystem format"),
    (r">\s*/dev/sd[a-z]", "direct disk overwrite"),
    (r"chmod\s+-R\s+777\s+/", "world-writable root"),
    (r"curl\s+.*\|\s*(ba)?sh", "remote code execution via curl|sh"),
    (r"wget\s+.*\|\s*(ba)?sh", "remote code execution via wget|sh"),
    (r"/etc/passwd|/etc/shadow", "sensitive system file access"),
    (r"\$\(.*\$\(", "nested command substitution (injection risk)"),
]

# Intent classification — maps command prefix to readable description
_INTENT_MAP = [
    (r"^rm\b", "delete files"),
    (r"^mv\b", "move/rename files"),
    (r"^cp\b", "copy files"),
    (r"^chmod\b", "change file permissions"),
    (r"^chown\b", "change file ownership"),
    (r"^curl\b|^wget\b", "network request"),
    (r"^git\b", "git operation"),
    (r"^pip3?\b", "install Python packages"),
    (r"^npm\b|^yarn\b", "install Node packages"),
    (r"^python\b|^python3\b", "run Python script"),
    (r"^ls\b|^find\b", "list/find files"),
    (r"^cat\b|^head\b|^tail\b", "read file"),
    (r"^echo\b|^printf\b", "print output"),
    (r"^mkdir\b", "create directory"),
    (r"^touch\b", "create/update file"),
]


def check_command(command: str) -> CommandCheckResult:
    """
    Check a shell command for dangerous patterns and classify its intent.
    Mirrors the spirit of bashSecurity.ts validateDangerousPatterns.
    """
    for pattern, reason in _DANGEROUS:
        if re.search(pattern, command, re.IGNORECASE):
            return CommandCheckResult(safe=False, reason=reason, intent=_classify_intent(command))

    return CommandCheckResult(safe=True, intent=_classify_intent(command))


def _classify_intent(command: str) -> str:
    cmd = command.strip()
    for pattern, description in _INTENT_MAP:
        if re.match(pattern, cmd):
            return description
    return "shell command"
