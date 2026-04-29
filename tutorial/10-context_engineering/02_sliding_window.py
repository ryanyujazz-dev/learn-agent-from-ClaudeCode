"""
Lesson 10 进阶：滑动窗口记忆
新概念: 滑动窗口, messages 裁剪, context window 保护

在 01_memory_agent.py 基础上，加入滑动窗口：
当 messages 过长时，只保留 system prompt + 最近 K 轮对话，
丢弃更早的消息，防止超过模型的 context window。
"""
import os
import sys
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI

# ── 会话文件路径 ──────────────────────────────────────────────
# 用绝对路径定位文件，避免"从不同目录运行脚本"时路径跑偏。
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
SESSION_FILE = os.path.join(DATA_DIR, "latest_window.json")

# ── 滑动窗口配置 ──────────────────────────────────────────────
MAX_MESSAGES = 20  # 保留最近 20 条对话（约 10 轮）


def apply_sliding_window(api_messages: list) -> list:
    """滑动窗口：超过阈值时，保留 system prompt + 最近 MAX_MESSAGES 条。"""
    if len(api_messages) <= MAX_MESSAGES + 1:  # +1 给 system prompt
        return api_messages
    system = [api_messages[0]] if api_messages[0]["role"] == "system" else []
    return system + api_messages[-MAX_MESSAGES:]


def load_claude_md(start_dir: str) -> str:
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
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def load_session() -> list:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


# ── 工具基类 ──────────────────────────────────────────────────
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


# ── Agentic Loop（与 01 的唯一区别：apply_sliding_window）─────
client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)
TOOLS = [BashTool()]


async def query(messages: list, system_prompt: str, cwd: str, max_turns: int = 10):
    api_messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + messages
    turn = 0
    while turn < max_turns:
        # 滑动窗口：裁剪过长的消息
        api_messages = apply_sliding_window(api_messages)

        stream = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "glm-5.1"), messages=api_messages,
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
        print("[已加载 CLAUDE.md]")

    print(f"滑动窗口记忆（窗口大小: {MAX_MESSAGES} 条）")
    print("试试连续对话 10 轮以上，观察消息数量变化\n")

    while True:
        user_input = input("你: ").strip()
        if user_input == "/quit":
            save_session(messages)
            print("[会话已保存]")
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})

        # 显示当前消息数（观察窗口效果）
        api_count = 1 + len(messages)  # system + messages
        if api_count > MAX_MESSAGES + 1:
            api_count = 1 + MAX_MESSAGES  # 裁剪后
        print(f"  [messages: {len(messages)} → 发送: {api_count}]")

        print("AI: ", end="")
        async for text in query(messages, system_prompt, cwd):
            print(text, end="", flush=True)
        print()
        save_session(messages)


asyncio.run(main())
