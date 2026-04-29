"""
Lesson 10 File 4：Skills（技能 / 操作手册）
新概念: skill 加载, skill 列表, 指令注入

前面三个文件讲了：
  File 1: CLAUDE.md — 静态项目知识注入
  File 2: 滑动窗口 — 上下文裁剪
  File 3: RAG — 动态检索知识注入

本文件演示 Skills：把"任务级行为指令"注入到 system prompt。

Skills 和 Tools 的区别：
  - Tools 告诉模型"你能做什么"（比如执行 bash 命令）
  - Skills 告诉模型"怎么做某个任务"（比如按什么步骤做 code review）

Skills 本质上是一份 md 文件（操作手册），加载后注入 system prompt。
模型读了这份手册，就知道按什么步骤、用什么工具、遵循什么标准来完成任务。

运行方式：
  python3 04_skills.py
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI


# ── Skills 系统 ──────────────────────────────────────────────

# skills 目录：存放 .md 文件，每个文件是一个 skill（操作手册）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")


def list_skills() -> dict[str, str]:
    """
    扫描 skills 目录，返回 {skill 名字: 文件路径}。

    和 Tools 的注册方式不同：
      Tools：用 API 参数 tools=[{name, schema}] 注册
      Skills：用系统提示列出可用名字，用户选择后加载全文注入
    """
    skills = {}
    if not os.path.exists(SKILLS_DIR):
        return skills
    for filename in os.listdir(SKILLS_DIR):
        if filename.endswith(".md"):
            # 文件名去掉 .md 后缀就是 skill 名字
            # code_review.md → code_review
            name = filename[:-3]
            skills[name] = os.path.join(SKILLS_DIR, filename)
    return skills


def load_skill(name: str, skills: dict[str, str]) -> str:
    """加载 skill 文件的完整内容。这就是要注入 system prompt 的操作手册。"""
    path = skills.get(name)
    if not path or not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


# ── 工具基类（复用自 01）───────────────────────────────────

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
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)
TOOLS = [BashTool()]


async def query(messages: list, system_prompt: str, cwd: str, max_turns: int = 10):
    api_messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + messages
    turn = 0
    while turn < max_turns:
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
    messages: list[dict] = []
    active_skill: str = ""

    # ── 启动时扫描 skills 目录 ──────────────────────────────
    skills = list_skills()
    if not skills:
        print(f"未找到 skills 目录或目录为空：{SKILLS_DIR}")
        print("请确认 skills/ 目录下有 .md 文件")
        return

    print("Skills 演示（操作手册注入）")
    print(f"已发现 {len(skills)} 个 skills：")
    for name in skills:
        print(f"  /{name}")
    print()
    print("命令：")
    print("  /skill <名字>  — 加载一个 skill（注入操作手册）")
    print("  /skills        — 列出所有可用 skills")
    print("  /clear         — 清除当前 skill，回到普通对话")
    print("  /quit          — 退出")
    print()

    while True:
        user_input = input("你: ").strip()
        if not user_input:
            continue

        # ── 命令处理 ────────────────────────────────────────
        if user_input == "/quit":
            break

        if user_input == "/skills":
            print(f"可用 skills：{', '.join(f'/{n}' for n in skills)}")
            if active_skill:
                print(f"当前激活：{active_skill}")
            print()
            continue

        if user_input == "/clear":
            active_skill = ""
            messages.clear()
            print("[已清除 skill 和对话历史]\n")
            continue

        if user_input.startswith("/skill "):
            skill_name = user_input[7:].strip()
            if skill_name not in skills:
                print(f"未找到 skill：{skill_name}")
                print(f"可用：{', '.join(skills.keys())}\n")
                continue
            active_skill = skill_name
            messages.clear()
            print(f"[已加载 skill: {active_skill}]")
            print(f"[模型现在会按照「{active_skill}」操作手册的步骤来工作]\n")
            continue

        # ── 构造 system prompt ──────────────────────────────
        # 核心：如果用户选择了 skill，把完整的操作手册注入 system prompt
        # 这就是 Skills 的本质——按需加载的 system prompt 增量
        if active_skill:
            skill_content = load_skill(active_skill, skills)
            system_prompt = (
                f"你现在正在使用「{active_skill}」技能。\n\n"
                f"请严格按照以下操作手册执行任务：\n\n"
                f"{skill_content}"
            )
        else:
            system_prompt = ""

        # ── 正常对话 ────────────────────────────────────────
        messages.append({"role": "user", "content": user_input})
        print("AI: ", end="")
        async for text in query(messages, system_prompt, cwd):
            print(text, end="", flush=True)
        print("\n")


asyncio.run(main())
