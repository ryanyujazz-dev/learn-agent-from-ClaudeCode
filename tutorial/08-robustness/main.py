"""
Lesson 8: 健壮性工程
新概念: asyncio.wait_for 超时, 指数退避重试, cd cwd 追踪
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI, APIError


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
    description_text = "执行 shell 命令，支持 cd 切换目录"
    input_schema = {"type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"]}

    def __init__(self):
        self.current_cwd: str = ""

    async def call(self, args: dict, cwd: str) -> ToolResult:
        if not self.current_cwd:
            self.current_cwd = cwd

        # 追加 pwd 以追踪 cd 后的新目录
        full_cmd = args["command"] + "\npwd"
        proc = await asyncio.create_subprocess_shell(
            full_cmd, cwd=self.current_cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            # 超时保护：30秒
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(data="命令超时（30秒）", error=True)

        output = stdout.decode()
        err = stderr.decode()

        # 从最后一行读取新 cwd
        lines = output.strip().splitlines()
        if lines and lines[-1].startswith("/"):
            self.current_cwd = lines[-1]
            output = "\n".join(lines[:-1])  # 去掉 pwd 输出

        result = (output + err).strip() or "(无输出)"
        return ToolResult(data=result, error=proc.returncode != 0)


# ── API 重试 ──────────────────────────────────────────────────
client = AsyncOpenAI(
    api_key=os.environ["ZHIPUAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)


async def _create_stream_with_retry(client, **kwargs):
    for attempt in range(3):
        try:
            return await client.chat.completions.create(**kwargs)
        except APIError as e:
            if attempt == 2 or e.status_code in (400, 401, 403):
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


TOOLS = [BashTool()]


async def query(messages: list, cwd: str, max_turns: int = 10):
    turn = 0
    while turn < max_turns:
        stream = await _create_stream_with_retry(
            client, model="glm-5.1", messages=messages,
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
    print("健壮性演示（超时+重试+cwd追踪）")
    print("试试：「cd /tmp 然后列出文件」或「执行 sleep 60」\n")
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
