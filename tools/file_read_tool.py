from tool import Tool, ToolResult, ToolUseContext
from security.path_check import check_path
import os


class FileReadTool(Tool):
    name = "file_read"
    description_text = "Read the contents of a file."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path"},
        },
        "required": ["path"],
    }

    def is_read_only(self, args: dict) -> bool:
        return True

    async def call(self, args: dict, context: ToolUseContext) -> ToolResult:
        path = os.path.join(context.cwd, args["path"]) if not os.path.isabs(args["path"]) else args["path"]
        safe, reason = check_path(path, context.cwd)
        if not safe:
            return ToolResult(data=f"Path not allowed: {reason}", error=True)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return ToolResult(data=f.read())
        except Exception as e:
            return ToolResult(data=str(e), error=True)
