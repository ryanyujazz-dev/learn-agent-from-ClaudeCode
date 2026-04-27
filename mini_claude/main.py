import asyncio
import contextlib
import os
import select
import sys
import termios
import threading
import time
from typing import Optional, Sequence
import tty

try:
    import readline  # enables arrow keys / history in input()
except ImportError:
    pass

from rich.console import Console
from rich.status import Status

from .tool import ToolUseContext
from .tools import ALL_TOOLS
from .query import query, get_model
from .memory.claudemd import load_claudemd
from .memory.session import save_session, load_latest_session

console = Console()

HELP = """mini-claude

Usage:
  mini-claude [--resume] [--auto]

Options:
  --resume   Resume the latest saved session.
  --auto     Skip all permission prompts.
  -h, --help Show this help message.

Run this command from the project directory you want mini-claude to operate on.
During a response, press Esc to interrupt and return to the prompt.
"""


def _start_escape_monitor(
    context: ToolUseContext,
    loop: asyncio.AbstractEventLoop,
    interrupt_event: asyncio.Event,
) -> threading.Event:
    stop_event = threading.Event()

    if not sys.stdin.isatty():
        return stop_event

    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)
    mode_lock = threading.Lock()
    cbreak_enabled = False

    def enable_cbreak() -> None:
        nonlocal cbreak_enabled
        with mode_lock:
            if not cbreak_enabled:
                tty.setcbreak(fd)
                cbreak_enabled = True

    def disable_cbreak() -> None:
        nonlocal cbreak_enabled
        with mode_lock:
            if cbreak_enabled:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
                cbreak_enabled = False

    context.keyboard_monitor_restore = disable_cbreak

    def watch_escape() -> None:
        try:
            while not stop_event.is_set():
                if context.waiting_for_permission:
                    disable_cbreak()
                    time.sleep(0.05)
                    continue
                enable_cbreak()
                readable, _, _ = select.select([sys.stdin], [], [], 0.05)
                if not readable:
                    continue
                char = os.read(fd, 1)
                if char == b"\x1b":
                    loop.call_soon_threadsafe(interrupt_event.set)
                    return
        finally:
            disable_cbreak()

    thread = threading.Thread(target=watch_escape, daemon=True)
    thread.start()
    return stop_event


def _render_chunk(chunk: str, status: Status, spinner_state: dict) -> None:
    if chunk.startswith("\x00TOOL:"):
        parts = chunk[1:].split(":", 2)
        name = parts[1] if len(parts) > 1 else "?"
        args_preview = parts[2][:50] if len(parts) > 2 else ""
        status.update(f"[cyan]{name}[/] {args_preview}")
        if not spinner_state["running"]:
            status.start()
            spinner_state["running"] = True
    elif chunk.startswith("\x00DONE:"):
        if spinner_state["running"]:
            status.stop()
            spinner_state["running"] = False
        parts = chunk[1:].split(":", 2)
        flag = parts[1] if len(parts) > 1 else "OK"
        summary = parts[2] if len(parts) > 2 else ""
        if flag == "OK":
            console.print(f"[green]✓[/] {summary}")
        else:
            console.print(f"[red]✗[/] {summary}")
    else:
        if spinner_state["running"]:
            status.stop()
            spinner_state["running"] = False
        console.print(chunk.replace("\\n", "\n").replace("\\t", "\t"), end="")


async def _run_query_interruptible(messages: list[dict], system_prompt: str, context: ToolUseContext) -> bool:
    status = Status("", console=console)
    spinner_state = {"running": False}
    interrupt_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    stop_escape = _start_escape_monitor(context, loop, interrupt_event)
    stream = query(messages, system_prompt, context)
    interrupted = False

    try:
        while True:
            next_chunk = asyncio.create_task(stream.__anext__())
            interrupt_wait = asyncio.create_task(interrupt_event.wait())
            done, pending = await asyncio.wait(
                {next_chunk, interrupt_wait},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if interrupt_wait in done:
                interrupted = True
                next_chunk.cancel()
                with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
                    await next_chunk
                await stream.aclose()
                console.print("\n[yellow]Interrupted[/]")
                break

            interrupt_wait.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await interrupt_wait

            try:
                chunk = next_chunk.result()
            except StopAsyncIteration:
                break

            _render_chunk(chunk, status, spinner_state)
    finally:
        stop_escape.set()
        if context.keyboard_monitor_restore:
            context.keyboard_monitor_restore()
        context.keyboard_monitor_restore = None
        if spinner_state["running"]:
            status.stop()

    return interrupted


async def repl(resume: bool = False, auto: bool = False):
    cwd = os.getcwd()
    system_prompt = load_claudemd(cwd)
    messages = load_latest_session() if resume else []

    permission_mode = "bypass" if auto else "default"
    context = ToolUseContext(tools=ALL_TOOLS, cwd=cwd, permission_mode=permission_mode)

    if resume and messages:
        console.print(f"[dim][Resumed session with {len(messages)} messages][/]")

    console.print(f"mini-claude ({get_model()}) — type 'exit' to quit, Esc to interrupt\n")

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

        start_len = len(messages)
        messages.append({"role": "user", "content": user_input})
        print()

        interrupted = await _run_query_interruptible(messages, system_prompt, context)
        if interrupted:
            del messages[start_len:]
        print("\n")

        if not interrupted:
            save_session(messages)


def cli(argv: Optional[Sequence[str]] = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        print(HELP)
        return
    resume = "--resume" in args
    auto = "--auto" in args
    asyncio.run(repl(resume=resume, auto=auto))


if __name__ == "__main__":
    cli()
