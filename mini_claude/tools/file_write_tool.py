from ..tool import Tool, ToolResult, ToolUseContext
from ..security.path_check import check_path
import os


class FileWriteTool(Tool):
    name = "file_write"
    description_text = "Write content to a file, creating it if it doesn't exist."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    }

    def is_read_only(self, args: dict) -> bool:
        return False

    async def call(self, args: dict, context: ToolUseContext) -> ToolResult:
        if not self.check_permissions(args, context):
            return ToolResult(data="Permission denied.", error=True)
        path = os.path.join(context.cwd, args["path"]) if not os.path.isabs(args["path"]) else args["path"]
        safe, reason = check_path(path, context.cwd)
        if not safe:
            return ToolResult(data=f"Path not allowed: {reason}", error=True)
        try:
            dirpath = os.path.dirname(path)
            if dirpath:
                os.makedirs(dirpath, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(args["content"])
            return ToolResult(data=f"Written to {path}")
        except Exception as e:
            return ToolResult(data=str(e), error=True)
