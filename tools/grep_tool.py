from tool import Tool, ToolResult, ToolUseContext
import glob as glob_mod
import os
import re

MAX_RESULTS = 200


class GrepTool(Tool):
    name = "grep"
    description_text = "Search for a regex pattern in files."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search"},
            "path": {"type": "string", "description": "File or directory to search", "default": "."},
            "glob": {"type": "string", "description": "File glob filter, e.g. *.py"},
        },
        "required": ["pattern"],
    }

    def is_read_only(self, args: dict) -> bool:
        return True

    async def call(self, args: dict, context: ToolUseContext) -> ToolResult:
        base = context.cwd or os.getcwd()
        search_path = os.path.join(base, args.get("path", "."))
        glob_filter = args.get("glob", "*")
        try:
            regex = re.compile(args["pattern"])
        except re.error as e:
            return ToolResult(data=f"Invalid regex: {e}", error=True)

        results = []
        files = glob_mod.glob(os.path.join(search_path, "**", glob_filter), recursive=True)
        for filepath in sorted(files):
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"{filepath}:{i}: {line.rstrip()}")
                            if len(results) >= MAX_RESULTS:
                                results.append(f"[truncated at {MAX_RESULTS} results]")
                                return ToolResult(data="\n".join(results))
            except Exception:
                continue

        if not results:
            return ToolResult(data="No matches found.")
        return ToolResult(data="\n".join(results))
