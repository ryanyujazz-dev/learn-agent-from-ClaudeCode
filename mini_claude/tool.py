from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from .security.command_check import check_command
from .security.rules import check_rule


@dataclass
class ToolUseContext:
    """Dependency injection container — mirrors src/Tool.ts ToolUseContext."""
    tools: list["Tool"]
    permission_mode: str = "default"  # default | auto | bypass
    cwd: str = ""
    preapproved_permissions: set[str] = field(default_factory=set)
    session_allowed_tools: set[str] = field(default_factory=set)
    waiting_for_permission: bool = False
    keyboard_monitor_restore: Any = None


@dataclass
class ToolResult:
    """Mirrors src/Tool.ts ToolResult<T>."""
    data: Any
    error: bool = False


class Tool(ABC):
    """Abstract base — mirrors src/Tool.ts Tool interface."""
    name: str = ""
    description_text: str = ""
    input_schema: dict = field(default_factory=dict)

    @abstractmethod
    async def call(self, args: dict, context: ToolUseContext) -> ToolResult:
        ...

    def check_permissions(self, args: dict, context: "Optional[ToolUseContext]" = None) -> bool:
        """
        Three-step permission check — mirrors bashPermissions.ts:
        1. Static dangerous pattern check (always blocks)
        2. Persistent allow/deny rules
        3. Interactive prompt with session-level bypass
        """
        command = args.get("command", args.get("path", str(args)))

        if self.is_read_only(args):
            return True

        # 1. Dangerous command check
        check = check_command(command)
        if not check.safe:
            print(f"[BLOCKED] {check.reason}")
            return False

        permission_key = f"{self.name}:{command}"
        if context and permission_key in context.preapproved_permissions:
            context.preapproved_permissions.remove(permission_key)
            return True

        # 2. Persistent deny/allow rules
        rule = check_rule(self.name, command)
        if rule == "deny":
            print(f"[DENIED by rule] {command}")
            return False
        if context and self.name in context.session_allowed_tools:
            return True
        if rule == "allow":
            return True

        # 3. Session bypass
        if context and context.permission_mode == "bypass":
            return True

        # 4. Interactive prompt — show intent for clarity
        intent = check.intent
        if context:
            context.waiting_for_permission = True
            if context.keyboard_monitor_restore:
                context.keyboard_monitor_restore()
        try:
            answer = input(f"Allow {self.name} ({intent})? [y] once/[a] session/[N] no ").strip().lower()
        finally:
            if context:
                context.waiting_for_permission = False
        if answer == "a":
            if context:
                context.session_allowed_tools.add(self.name)
            return True
        if answer == "y":
            return True
        return False

    def is_read_only(self, args: dict) -> bool:
        return False

    def to_api_schema(self) -> dict:
        """Convert to OpenAI function calling format (used by ZhipuAI compatible API)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description_text,
                "parameters": self.input_schema,
            },
        }
