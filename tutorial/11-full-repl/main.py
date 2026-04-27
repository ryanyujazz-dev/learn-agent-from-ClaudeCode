"""
Lesson 11: 完整 REPL
新概念: ToolUseContext 依赖注入, is_error 信号, readline
"""
import os
import sys
import re
import json
import asyncio

try:
    import readline  # 启用上下键历史、左右键移动光标
except ImportError:
    pass  # Windows 上不可用，忽略

from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI

# ── 配置 ──────────────────────────────────────────────────────
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest.json")

_DANGEROUS = [
    (r"rm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r", "递归强制删除"),
    (r":\(\)\s*\{.*\|.*&", "fork bomb"),
    (r"dd\s+if=", "原始磁盘写入"),
    (r"mkfs\b", "格式化文件系统"),
    (r"curl\s+.*\|\s*(ba)?sh", "远程代码执行"),
]

RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")


# ── 记忆系统 ──────────────────────────────────────────────────
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
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def load_session() -> list:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


# ── 权限系统 ──────────────────────────────────────────────────
def _load_rules() -> dict:
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE) as f:
            return json.load(f)
    return {}


def _save_rules(rules: dict) -> None:
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)


def check_permissions(tool_name: str, command: str, auto: bool) -> bool:
    for pattern, reason in _DANGEROUS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"\n[拦截] 危险命令: {reason}")
            return False
    if auto:
        return True
    rules = _load_rules()
    key = f"{tool_name}:{command}"
    if key in rules:
        if rules[key] == "allow":
            return True
        print(f"\n[拒绝] 已有规则拒绝此命令")
        return False
    answer = input(f"\n允许执行 [{command}]? [y/N/a/d] ").strip().lower()
    if answer == "a":
        rules[key] = "allow"; _save_rules(rules); return True
    if answer == "d":
        rules[key] = "deny"; _save_rules(rules); return False
    return answer == "y"


# ── 工具系统 ──────────────────────────────────────────────────
@dataclass
class ToolResult:
    data: str
    error: bool = False


@dataclass
class ToolUseContext:
    """依赖注入容器：把工具调用所需的上下文打包传递，而不是散落在各函数签名里。"""
    tools: list
    cwd: str = ""
    permission_mode: str = "default"  # default | auto


class Tool(ABC):
    name: str = ""
    description_text: str = ""
    input_schema: dict = {}

    @abstractmethod
    async def call(self, args: dict, context: "ToolUseContext") -> ToolResult: ...

    def to_api_schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description_text,
            "parameters": self.input_schema,
        }}


class BashTool(Tool):
    name = "bash"
    description_text = "执行 shell 命令"
    input_schema = {"type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"]}

    async def call(self, args: dict, context: "ToolUseContext") -> ToolResult:
        cmd = args["command"]
        auto = context.permission_mode == "auto"
        if not check_permissions(self.name, cmd, auto):
            return ToolResult(data="权限被拒绝", error=True)
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=context.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return ToolResult(data=(stdout.decode() + stderr.decode()).strip())


class FileReadTool(Tool):
    name = "file_read"
    description_text = "读取文件内容"
    input_schema = {"type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]}

    async def call(self, args: dict, context: "ToolUseContext") -> ToolResult:
        real = os.path.realpath(args["path"])
        if not real.startswith(os.path.realpath(context.cwd)):
            return ToolResult(data="路径越界", error=True)
        try:
            return ToolResult(data=open(real, encoding="utf-8").read())
        except Exception as e:
            return ToolResult(data=str(e), error=True)


class FileWriteTool(Tool):
    name = "file_write"
    description_text = "写入文件内容"
    input_schema = {"type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"]}

    async def call(self, args: dict, context: "ToolUseContext") -> ToolResult:
        real = os.path.realpath(args["path"])
        if not real.startswith(os.path.realpath(context.cwd)):
            return ToolResult(data="路径越界", error=True)
        auto = context.permission_mode == "auto"
        if not check_permissions(self.name, args["path"], auto):
            return ToolResult(data="权限被拒绝", error=True)
        try:
            os.makedirs(os.path.dirname(real), exist_ok=True)
            with open(real, "w", encoding="utf-8") as f:
                f.write(args["content"])
            return ToolResult(data=f"已写入 {real}")
        except Exception as e:
            return ToolResult(data=str(e), error=True)


# ── Agentic Loop ──────────────────────────────────────────────
client = AsyncOpenAI(
    api_key=os.environ["ZHIPUAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
TOOLS = [BashTool(), FileReadTool(), FileWriteTool()]


async def query(messages: list, system_prompt: str, context: "ToolUseContext", max_turns: int = 20):
    api_messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + messages
    turn = 0
    while turn < max_turns:
        stream = await client.chat.completions.create(
            model="glm-5.1", messages=api_messages,
            tools=[t.to_api_schema() for t in context.tools], stream=True,
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
            tool = next((t for t in context.tools if t.name == tc["name"]), None)
            result = await tool.call(args, context) if tool else ToolResult(data="未知工具", error=True)
            yield f"\n[{tc['name']}]: {result.data[:500]}\n"
            tool_msg = {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result.data,
                **({"is_error": True} if result.error else {}),
            }
            messages.append(tool_msg)
            api_messages.append(tool_msg)

    yield f"\n[已达到最大轮数 {max_turns}]\n"


# ── REPL ──────────────────────────────────────────────────────
async def main():
    cwd = os.getcwd()
    resume = "--resume" in sys.argv
    auto = "--auto" in sys.argv

    messages = load_session() if resume else []
    if resume:
        print(f"[已恢复会话，共 {len(messages)} 条消息]")

    claude_md = load_claude_md(cwd)
    if claude_md:
        print("[已加载 CLAUDE.md]")

    context = ToolUseContext(
        tools=[BashTool(), FileReadTool(), FileWriteTool()],
        cwd=cwd,
        permission_mode="auto" if auto else "default",
    )

    mode = "自动" if auto else "交互"
    print(f"mini-claude（工作目录: {cwd}，权限模式: {mode}）")
    print("输入 /quit 退出，/clear 清空对话\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (KeyboardInterrupt, EOFError):
            save_session(messages)
            print("\n[会话已保存，再见]")
            break

        if user_input == "/quit":
            save_session(messages)
            print("[会话已保存]")
            break
        if user_input == "/clear":
            messages.clear()
            print("[对话已清空]")
            continue
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        print("AI: ", end="")
        async for text in query(messages, claude_md, context):
            print(text, end="", flush=True)
        print()
        save_session(messages)


asyncio.run(main())
