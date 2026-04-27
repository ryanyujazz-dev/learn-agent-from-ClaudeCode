"""
Lesson 9: 记忆系统
新概念: CLAUDE.md 注入, 向上遍历目录, messages JSON 持久化, --resume
"""
import os
import sys
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI

SESSION_FILE = os.path.join(os.path.dirname(__file__), "latest.json")


def load_claude_md(start_dir: str) -> str:
    """向上遍历目录，收集所有 CLAUDE.md 内容。"""
    parts = []
    path = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(path, "CLAUDE.md")
        if os.path.exists(candidate):
            parts.append(open(candidate, encoding="utf-8").read().strip())
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return "\n\n".join(parts)


def save_session(messages: list) -> None:
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def load_session() -> list:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


# ── 工具基类（复用自 Lesson 8）────────────────────────────────
@dataclass
class ToolResult:
    data: str
    error: bool = False


class Tool(ABC):
    name: str = ""
    description_text: str = ""
    input_schema: dict = {}

    @abstractmethod
    async def call(self, args: dict, cwd: str) -> ToolResult: ...

    def to_api_schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description_text,
            "parameters": self.input_schema,
        }}


class BashTool(Tool):
    name = "bash"
    description_text = "执行 shell 命令"
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    async def call(self, args: dict, cwd: str) -> ToolResult:
        proc = await asyncio.create_subprocess_shell(
            args["command"], cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return ToolResult(data=(stdout.decode() + stderr.decode()).strip())


# ── Agentic Loop ──────────────────────────────────────────────
client = AsyncOpenAI(
    api_key=os.environ["ZHIPUAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
TOOLS = [BashTool()]


async def query(messages: list, system_prompt: str, cwd: str, max_turns: int = 10):
    api_messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + messages
    turn = 0
    while turn < max_turns:
        stream = await client.chat.completions.create(
            model="glm-5.1", messages=api_messages,
            tools=[t.to_api_schema() for t in TOOLS], stream=True,
        )
        full_text = ""
        tool_calls_raw: dict[int, dict] = {}
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue
            if delta.content:
                full_text += delta.content
                yield delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_raw:
                        tool_calls_raw[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_raw[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_raw[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_raw[idx]["arguments"] += tc.function.arguments

        assistant_msg = {"role": "assistant", "content": full_text or None}
        if tool_calls_raw:
            assistant_msg["tool_calls"] = [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                for tc in tool_calls_raw.values()
            ]
        messages.append(assistant_msg)
        api_messages.append(assistant_msg)
        if not tool_calls_raw:
            return
        turn += 1
        for tc in tool_calls_raw.values():
            args = json.loads(tc["arguments"] or "{}")
            tool = next((t for t in TOOLS if t.name == tc["name"]), None)
            result = await tool.call(args, cwd) if tool else ToolResult(data="未知工具", error=True)
            yield f"\n[{tc['name']}]: {result.data[:300]}\n"
            tool_msg = {"role": "tool", "tool_call_id": tc["id"], "content": result.data}
            messages.append(tool_msg)
            api_messages.append(tool_msg)

    yield f"\n[已达到最大轮数 {max_turns}]\n"


async def main():
    cwd = os.getcwd()
    resume = "--resume" in sys.argv

    messages = load_session() if resume else []
    if resume:
        print(f"[已恢复会话，共 {len(messages)} 条消息]")

    claude_md = load_claude_md(cwd)
    system_prompt = claude_md if claude_md else ""
    if claude_md:
        print(f"[已加载 CLAUDE.md]\n")

    print("记忆系统演示（输入 /quit 退出）\n")
    while True:
        user_input = input("你: ").strip()
        if user_input == "/quit":
            save_session(messages)
            print("[会话已保存]")
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        print("AI: ", end="")
        async for text in query(messages, system_prompt, cwd):
            print(text, end="", flush=True)
        print()
        save_session(messages)  # 每轮自动保存，Ctrl+C 也不丢数据


asyncio.run(main())
