"""
Lesson 6: Agentic Loop（核心）
新概念: tool_calls 解析, tool_result 回喂, async generator, max_turns
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

    def to_api_schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description_text,
            "parameters": self.input_schema,
        }}


class EchoTool(Tool):
    name = "echo"
    description_text = "原样返回输入的消息"
    input_schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }

    async def call(self, args: dict) -> ToolResult:
        return ToolResult(data=args["message"])


client = AsyncOpenAI(
    api_key=os.environ["ZHIPUAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
TOOLS = [EchoTool()]


async def query(messages: list, max_turns: int = 5):
    """Agentic loop — 边执行边 yield 文字片段。"""
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

        # 把 assistant 消息加入历史
        assistant_msg = {"role": "assistant", "content": full_text or None}
        if tool_calls_raw:
            assistant_msg["tool_calls"] = [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                for tc in tool_calls_raw.values()
            ]
        messages.append(assistant_msg)

        if not tool_calls_raw:
            return  # 没有工具调用，结束

        turn += 1

        # 执行工具
        for tc in tool_calls_raw.values():
            args = json.loads(tc["arguments"] or "{}")
            yield f"\n[调用工具: {tc['name']}({args})]\n"

            tool = next((t for t in TOOLS if t.name == tc["name"]), None)
            result = await tool.call(args) if tool else ToolResult(data="未知工具", error=True)
            yield f"[结果: {result.data}]\n"

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result.data,
            })

    yield f"\n[已达到最大轮数 {max_turns}，停止]\n"


async def main():
    messages = []
    print("Agentic Loop 演示（输入 /quit 退出）")
    print("提示：试着说「帮我 echo 一下 hello world」\n")
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
