import asyncio
import os
import sys
import readline  # enables arrow keys / history in input()

from rich.console import Console
from rich.status import Status

from tool import ToolUseContext
from tools import ALL_TOOLS
from query import query, get_model
from memory.claudemd import load_claudemd
from memory.session import save_session, load_latest_session

console = Console()


async def repl(resume: bool = False, auto: bool = False):
    cwd = os.getcwd()
    system_prompt = load_claudemd(cwd)
    messages = load_latest_session() if resume else []

    permission_mode = "bypass" if auto else "default"
    context = ToolUseContext(tools=ALL_TOOLS, cwd=cwd, permission_mode=permission_mode)

    if resume and messages:
        console.print(f"[dim][Resumed session with {len(messages)} messages][/]")

    console.print(f"mini-claude ({get_model()}) — type 'exit' to quit\n")

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        messages.append({"role": "user", "content": user_input})
        print()

        status = Status("", console=console)
        spinner_running = False
        async for chunk in query(messages, system_prompt, context):
            if chunk.startswith("\x00TOOL:"):
                parts = chunk[1:].split(":", 2)
                name = parts[1] if len(parts) > 1 else "?"
                args_preview = parts[2][:50] if len(parts) > 2 else ""
                status.update(f"[cyan]{name}[/] {args_preview}")
                if not spinner_running:
                    status.start()
                    spinner_running = True
            elif chunk.startswith("\x00DONE:"):
                if spinner_running:
                    status.stop()
                    spinner_running = False
                parts = chunk[1:].split(":", 2)
                flag = parts[1] if len(parts) > 1 else "OK"
                summary = parts[2] if len(parts) > 2 else ""
                if flag == "OK":
                    console.print(f"[green]✓[/] {summary}")
                else:
                    console.print(f"[red]✗[/] {summary}")
            else:
                if spinner_running:
                    status.stop()
                    spinner_running = False
                console.print(chunk.replace("\\n", "\n").replace("\\t", "\t"), end="")

        if spinner_running:
            status.stop()
        print("\n")

        save_session(messages)


if __name__ == "__main__":
    resume = "--resume" in sys.argv
    auto = "--auto" in sys.argv
    asyncio.run(repl(resume=resume, auto=auto))

