from tool import Tool, ToolResult, ToolUseContext
import asyncio


class BashTool(Tool):
    name = "bash"
    description_text = "Execute a shell command and return stdout/stderr."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
        },
        "required": ["command"],
    }

    def is_read_only(self, args: dict) -> bool:
        return False

    async def call(self, args: dict, context: ToolUseContext) -> ToolResult:
        if not self.check_permissions(args, context):
            return ToolResult(data="Permission denied.", error=True)
        try:
            full_cmd = args["command"] + "\npwd"
            proc = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=context.cwd or None,
            )
            timeout = args.get("timeout", 30)
            try:
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(data="Command timed out.", error=True)

            stdout_lines = stdout_b.decode(errors="replace").splitlines()
            if stdout_lines:
                new_cwd = stdout_lines[-1].strip()
                if new_cwd and new_cwd != context.cwd:
                    context.cwd = new_cwd
                output = "\n".join(stdout_lines[:-1])
            else:
                output = ""
            stderr = stderr_b.decode(errors="replace")
            if stderr:
                output += f"\n[stderr]\n{stderr}"
            return ToolResult(data=output or "(no output)", error=proc.returncode != 0)
        except Exception as e:
            return ToolResult(data=str(e), error=True)
