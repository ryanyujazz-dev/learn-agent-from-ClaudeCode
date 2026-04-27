"""
Lesson 8: 权限与安全
新概念: 正则检测危险命令, os.path.realpath 路径检测, JSON 持久化规则
"""
import os
import re
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI

# ── 危险命令模式 ──────────────────────────────────────────────
_DANGEROUS = [
    (r"rm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r", "递归强制删除"),
    (r":\(\)\s*\{.*\|.*&", "fork bomb"),
    (r"dd\s+if=", "原始磁盘写入"),
    (r"mkfs\b", "格式化文件系统"),
    (r"curl\s+.*\|\s*(ba)?sh", "远程代码执行"),
]

RULES_FILE = os.path.join(os.path.dirname(__file__), "rules.json")


def _load_rules() -> dict:
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE) as f:
            return json.load(f)
    return {}


def _save_rules(rules: dict) -> None:
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)


def check_permissions(tool_name: str, command: str) -> bool:
    # 1. 危险模式
    for pattern, reason in _DANGEROUS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"\n[拦截] 危险命令: {reason}")
            return False

    # 2. 持久化规则
    rules = _load_rules()
    key = f"{tool_name}:{command}"
    if key in rules:
        if rules[key] == "allow":
            return True
        print(f"\n[拒绝] 已有规则拒绝此命令")
        return False

    # 3. 询问用户
    answer = input(f"\n允许执行 [{command}]? [y/N/a(永久允许)/d(永久拒绝)] ").strip().lower()
    if answer == "a":
        rules[key] = "allow"
        _save_rules(rules)
        return True
    if answer == "d":
        rules[key] = "deny"
        _save_rules(rules)
        return False
    return answer == "y"


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
        command = args["command"]
        if not check_permissions(self.name, command):
            return ToolResult(data="权限被拒绝", error=True)
        proc = await asyncio.create_subprocess_shell(
            command, cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return ToolResult(data=(stdout.decode() + stderr.decode()).strip())


class FileReadTool(Tool):
    name = "file_read"
    description_text = "读取文件内容"
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    async def call(self, args: dict, cwd: str) -> ToolResult:
        path = args["path"]
        real = os.path.realpath(path)
        if not real.startswith(os.path.realpath(cwd)):
            return ToolResult(data="路径越界，拒绝访问", error=True)
        try:
            with open(real, "r", encoding="utf-8") as f:
                return ToolResult(data=f.read())
        except Exception as e:
            return ToolResult(data=str(e), error=True)


# ── Agentic Loop ──────────────────────────────────────────────
client = AsyncOpenAI(
    api_key=os.environ["ZHIPUAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
TOOLS = [BashTool(), FileReadTool()]


async def query(messages: list, cwd: str, max_turns: int = 10):
    turn = 0
    while turn < max_turns:
        stream = await client.chat.completions.create(
            model="glm-5.1", messages=messages,
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
        if not tool_calls_raw:
            return
        turn += 1
        for tc in tool_calls_raw.values():
            args = json.loads(tc["arguments"] or "{}")
            tool = next((t for t in TOOLS if t.name == tc["name"]), None)
            result = await tool.call(args, cwd) if tool else ToolResult(data="未知工具", error=True)
            yield f"\n[{tc['name']}]: {result.data[:300]}\n"
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result.data})

    yield f"\n[已达到最大轮数 {max_turns}]\n"


async def main():
    cwd = os.getcwd()
    messages = []
    print(f"权限演示（工作目录: {cwd}）")
    print("试试：「执行 rm -rf /」或「列出当前目录」\n")
    while True:
        user_input = input("你: ").strip()
        if user_input == "/quit":
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        print("AI: ", end="")
        async for text in query(messages, cwd):
            print(text, end="", flush=True)
        print()


asyncio.run(main())
