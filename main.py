import asyncio
import os
import sys
import readline  # enables arrow keys / history in input()

from tool import ToolUseContext
from tools import ALL_TOOLS
from query import query
from memory.claudemd import load_claudemd
from memory.session import save_session, load_latest_session


async def repl(resume: bool = False, auto: bool = False):
    cwd = os.getcwd()
    system_prompt = load_claudemd(cwd)
    messages = load_latest_session() if resume else []

    permission_mode = "bypass" if auto else "default"
    context = ToolUseContext(tools=ALL_TOOLS, cwd=cwd, permission_mode=permission_mode)

    if resume and messages:
        print(f"[Resumed session with {len(messages)} messages]")

    print("mini-claude (glm-5.1) — type 'exit' to quit\n")

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
        async for chunk in query(messages, system_prompt, context):
            # Decode literal \n/\t that some APIs return as escaped strings
            print(chunk.replace("\\n", "\n").replace("\\t", "\t"), end="", flush=True)
        print("\n")

        save_session(messages)


if __name__ == "__main__":
    resume = "--resume" in sys.argv
    auto = "--auto" in sys.argv
    asyncio.run(repl(resume=resume, auto=auto))
