"""
Lesson 7: 真实工具
新概念: asyncio.create_subprocess_shell, 文件读写, is_read_only()
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI


@dataclass
class ToolResult:
    data: str
    error: bool = False


class Tool(ABC):
    name: str = ""
    description_text: str = ""
    input_schema: dict = {}

    @abstractmethod
    async def call(self, args: dict) -> ToolResult: ...

    def is_read_only(self, args: dict) -> bool:
        return False

    def to_api_schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description_text,
            "parameters": self.input_schema,
        }}


class BashTool(Tool):
    name = "bash"
    description_text = "执行 shell 命令，返回输出"
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string", "description": "要执行的命令"}},
        "required": ["command"],
    }

    async def call(self, args: dict) -> ToolResult:
        proc = await asyncio.create_subprocess_shell(
            args["command"],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode() + stderr.decode()
        return ToolResult(data=output.strip() or "(无输出)", error=proc.returncode != 0)


class FileReadTool(Tool):
    name = "file_read"
    description_text = "读取文件内容"
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "文件路径"}},
        "required": ["path"],
    }

    def is_read_only(self, args: dict) -> bool:
        return True

    async def call(self, args: dict) -> ToolResult:
        try:
            with open(args["path"], "r", encoding="utf-8") as f:
                return ToolResult(data=f.read())
        except Exception as e:
            return ToolResult(data=str(e), error=True)


client = AsyncOpenAI(
    api_key=os.environ["ZHIPUAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
TOOLS = [BashTool(), FileReadTool()]


async def query(messages: list, max_turns: int = 10):
    turn = 0
    while turn < max_turns:
        stream = await client.chat.completions.create(
            model="glm-5.1",
            messages=messages,
            tools=[t.to_api_schema() for t in TOOLS],
            stream=True,
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
            yield f"\n[工具: {tc['name']}]\n"
            tool = next((t for t in TOOLS if t.name == tc["name"]), None)
            result = await tool.call(args) if tool else ToolResult(data="未知工具", error=True)
            yield f"[结果]: {result.data[:300]}\n"
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result.data})

    yield f"\n[已达到最大轮数 {max_turns}]\n"


async def main():
    messages = []
    print("真实工具演示（输入 /quit 退出）")
    print("提示：试着说「列出当前目录的文件」\n")
    while True:
        user_input = input("你: ").strip()
        if user_input == "/quit":
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        print("AI: ", end="")
        async for text in query(messages):
            print(text, end="", flush=True)
        print()


asyncio.run(main())
