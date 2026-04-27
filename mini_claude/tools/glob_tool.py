from ..tool import Tool, ToolResult, ToolUseContext
import glob
import os

MAX_RESULTS = 200


class GlobTool(Tool):
    name = "glob"
    description_text = "Find files matching a glob pattern."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern, e.g. **/*.py"},
        },
        "required": ["pattern"],
    }

    def is_read_only(self, args: dict) -> bool:
        return True

    async def call(self, args: dict, context: ToolUseContext) -> ToolResult:
        base = context.cwd or os.getcwd()
        pattern = os.path.join(base, args["pattern"])
        matches = sorted(glob.glob(pattern, recursive=True))
        if not matches:
            return ToolResult(data="No files found.")
        truncated = matches[:MAX_RESULTS]
        suffix = f"\n[truncated at {MAX_RESULTS} results]" if len(matches) > MAX_RESULTS else ""
        return ToolResult(data="\n".join(truncated) + suffix)
