from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from security.command_check import check_command
from security.rules import check_rule, add_rule


@dataclass
class ToolUseContext:
    """Dependency injection container — mirrors src/Tool.ts ToolUseContext."""
    tools: list["Tool"]
    permission_mode: str = "default"  # default | auto | bypass
    cwd: str = ""


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

    def check_permissions(self, args: dict, context: "ToolUseContext | None" = None) -> bool:
        """
        Three-step permission check — mirrors bashPermissions.ts:
        1. Static dangerous pattern check (always blocks)
        2. Persistent allow/deny rules
        3. Interactive prompt with session-level bypass
        """
        if self.is_read_only(args):
            return True

        # 1. Dangerous command check
        command = args.get("command", args.get("path", str(args)))
        check = check_command(command)
        if not check.safe:
            print(f"[BLOCKED] {check.reason}")
            return False

        # 2. Persistent rules
        rule = check_rule(self.name, command)
        if rule == "allow":
            return True
        if rule == "deny":
            print(f"[DENIED by rule] {command}")
            return False

        # 3. Session bypass
        if context and context.permission_mode == "bypass":
            return True

        # 4. Interactive prompt — show intent for clarity
        intent = check.intent
        answer = input(f"Allow {self.name} ({intent})? [y/N/a(lways)/d(eny always)] ").strip().lower()
        if answer == "a":
            # Store as persistent allow rule (mirrors original "always allow this pattern")
            add_rule("allow", self.name, command)
            return True
        if answer == "d":
            add_rule("deny", self.name, command)
            return False
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
