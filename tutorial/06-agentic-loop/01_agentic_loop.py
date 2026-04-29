"""
Lesson 6 — 第 1 步：Agentic Loop（非流式版）
新概念: while 循环、tool result 回喂、max_turns

第 5 课学了：
  - 工具长什么样（Tool ABC）
  - 怎么告诉 LLM（JSON Schema / to_api_schema()）
  - LLM 怎么决定调工具（tool_calls）

但第 5 课少了关键一步：工具执行完，结果要**回喂给 LLM**，
让 LLM 看到结果后继续生成回复。

本课加上这一步，并用 while 循环包起来——这就是 Agentic Loop：
  LLM 调工具 → 结果回喂 → LLM 继续 → 可能再调工具 → 直到不需要工具为止
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI


# ── 工具系统（和第 5 课完全一样，直接搬过来）──────────────────


@dataclass
class ToolResult:
    data: str
    error: bool = False


class Tool(ABC):
    name: str = ""
    description_text: str = ""
    input_schema: dict = {}

    @abstractmethod
    async def call(self, args: dict) -> ToolResult:
        ...

    def to_api_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description_text,
                "parameters": self.input_schema,
            },
        }


class WeatherTool(Tool):
    name = "get_weather"
    description_text = "查询指定城市的天气"
    input_schema = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"},
        },
        "required": ["city"],
    }

    WEATHER_DATA = {
        "北京": "晴天，25°C",
        "上海": "多云，28°C，有阵雨",
        "深圳": "阴天，30°C",
        "成都": "小雨，22°C",
    }

    async def call(self, args: dict) -> ToolResult:
        city = args.get("city", "")
        if city in self.WEATHER_DATA:
            return ToolResult(data=f"{city}：{self.WEATHER_DATA[city]}")
        return ToolResult(data=f"未找到「{city}」的天气", error=True)


class EchoTool(Tool):
    name = "echo"
    description_text = "原样返回输入的消息"
    input_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "要回显的内容"},
        },
        "required": ["message"],
    }

    async def call(self, args: dict) -> ToolResult:
        return ToolResult(data=args["message"])


# ── Agentic Loop ──────────────────────────────────────────────
#
# 和第5课 File 3 的区别：
# 第5课：LLM 调工具 → 我们执行 → 打印结果 → 结束
# 本课： LLM 调工具 → 我们执行 → 结果回喂给 LLM → LLM 继续回复
#
# 多了"回喂"这一步，LLM 就能基于工具结果生成自然的回复。
# 用 while 循环包起来，LLM 可以连续调用多个工具。


client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)
TOOLS: list[Tool] = [WeatherTool(), EchoTool()]


async def chat(messages: list[dict], max_turns: int = 5):
    """
    Agentic Loop 核心。

    每一轮：
      1. 调 LLM，传入 messages + tools
      2. LLM 回复：
         - 没有 tool_calls → 打印文字，结束循环
         - 有 tool_calls → 执行工具，把结果加入 messages，继续下一轮
    """
    turn = 0

    while turn < max_turns:
        # ── 第 1 步：调用 LLM ─────────────────────────────
        response = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "glm-5.1"),
            messages=messages,
            tools=[t.to_api_schema() for t in TOOLS],
        )

        message = response.choices[0].message

        # ── 第 2 步：LLM 回复里有文字吗？先加入 messages ──
        # LLM 可能在调工具前说一句话（比如"让我查一下"）
        # 这句话也要加入 messages，保持对话完整
        #
        # 注意：即使 message.content 为空（LLM 直接调工具，没说话），
        # 也必须 append！因为 API 要求 messages 的顺序是严格的：
        #   assistant（带 tool_calls）→ tool（带 tool_call_id）
        # 如果跳过这条 assistant 消息，后面的 tool 消息就接不上，
        # API 会报错："messages with role 'tool' must be a response
        # to a preceding message with 'tool_calls'"
        messages.append({
            "role": "assistant",
            "content": message.content,
        })
        if message.content:
            print(f"AI: {message.content}")

        # ── 第 3 步：LLM 要调工具吗？ ─────────────────────
        if not message.tool_calls:
            return  # 没有工具调用，循环结束

        turn += 1

        # ── 第 4 步：执行每个工具，结果回喂给 LLM ──────────
        # 这是和第 5 课最大的区别：
        #   第 5 课：打印结果 → 结束
        #   本课：  把结果以 role="tool" 消息加入 messages → LLM 下一轮能看到
        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"  正在调用工具: {tc.function.name}({args})")

            # 在 TOOLS 列表里按名字找到对应的工具实例
            tool = None
            for t in TOOLS:
                if t.name == tc.function.name:
                    tool = t
                    break
            # 等价的惯用写法（更紧凑但不够直观）：
            # tool = next((t for t in TOOLS if t.name == tc.function.name), None)
            if tool:
                result: ToolResult = await tool.call(args)
            else:
                result = ToolResult(data="未知工具", error=True)  # error 字段目前未使用，第 11 课会用 is_error 通知 LLM

            print(f"  [结果: {result.data}]")

            # 关键！把结果加入 messages（role: "tool"）
            # tool_call_id 用来匹配"哪个结果对应哪次调用"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result.data,
            })

        # 回到 while 开头，LLM 看到工具结果后会继续回复

    print(f"\n[已达到最大轮数 {max_turns}，停止]")


async def main():
    print("Agentic Loop 演示（输入 /quit 退出）")
    print("试试：「北京天气怎么样」或「帮我 echo hello」\n")

    messages = []
    while True:
        user_input = input("你: ").strip()
        if user_input == "/quit":
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        await chat(messages)
        print()


asyncio.run(main())
