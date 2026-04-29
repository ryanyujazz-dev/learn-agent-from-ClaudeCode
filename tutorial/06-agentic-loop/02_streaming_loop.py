"""
Lesson 6 — 第 2 步：流式 Agentic Loop
新概念: 流式输出（stream=True）、async generator（yield）、tool_calls 分块拼接

第 1 步的 loop 逻辑：while 循环 → 调 LLM → 执行工具 → 结果回喂 → 继续。
这是对的，但用户体验不好——每轮都要等 LLM 完整回复才能看到任何输出。

流式输出（stream=True）解决 this：
  - LLM 的文字逐字输出（用户立刻看到，不用等）
  - 工具调用一到达就执行
  - 用 yield 实时发送给调用方

代价：tool_calls 的参数是分多个 chunk 到达的，需要手动拼接。

本课在第 1 步的基础上，加上流式输出。
工具系统和 loop 逻辑完全一样，只改了"怎么从 LLM 拿数据"这部分。
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI


# ── 工具系统（和第 1 步完全一样）──────────────────────────────


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


class RecommendActivityTool(Tool):
    """根据天气情况推荐活动。需要先查天气，再推荐——这会触发多轮循环。"""

    name = "recommend_activity"
    description_text = "根据天气描述推荐适合的活动"
    input_schema = {
        "type": "object",
        "properties": {
            "weather": {"type": "string", "description": "天气情况，如'晴天，25°C'"},
        },
        "required": ["weather"],
    }

    async def call(self, args: dict) -> ToolResult:
        weather = args.get("weather", "")
        if "雨" in weather:
            return ToolResult(data="下雨天建议室内活动：看电影、逛博物馆、泡咖啡馆")
        elif "晴" in weather:
            return ToolResult(data="晴天建议户外活动：爬山、逛公园、骑行")
        elif "阴" in weather:
            return ToolResult(data="阴天可以：逛商场、看展览、约朋友吃饭")
        else:
            return ToolResult(data="建议：散步、看书、喝杯咖啡")


# ── 流式 Agentic Loop ─────────────────────────────────────────
#
# 和第 1 步的区别只有一个：stream=True
# 但这个改动让数据接收方式完全不同：
#   第 1 步：response = await ... → 一次性拿到完整回复
#   第 2 步：stream = await ... → 用 async for 逐个拿 chunk

client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)
TOOLS: list[Tool] = [WeatherTool(), EchoTool(), RecommendActivityTool()]


async def query(messages: list[dict], max_turns: int = 5):
    """
    流式 Agentic Loop — 用 yield 实时输出文字片段。

    async generator 的好处：
      - yield 的文字立刻发给调用方（用户看到逐字输出）
      - 工具调用一到达就执行（不用等 LLM 完整回复）
    """
    turn = 0

    while turn < max_turns:
        # stream=True：LLM 逐 chunk 返回，不用等完整回复
        stream = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "glm-5.1"),
            messages=messages,
            tools=[t.to_api_schema() for t in TOOLS],
            stream=True,  # ← 唯一改动
        )

        full_text = ""
        tool_calls_raw: dict[int, dict] = {}  # index → {id, name, arguments}

        # ── 从流中逐 chunk 读取 ────────────────────────────
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # 文字：直接 yield 给调用方
            if delta.content:
                full_text += delta.content
                yield delta.content  # 用户立刻看到文字

            # 工具调用：分块到达，需要拼接
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_raw:
                        tool_calls_raw[idx] = {"id": "", "name": "", "arguments": ""}

                    if tc.id:
                        tool_calls_raw[idx]["id"] = tc.id

                    if tc.function:
                        # name 只在第一个 chunk 出现 → 用 =
                        if tc.function.name:
                            tool_calls_raw[idx]["name"] = tc.function.name
                        # arguments 分多个 chunk 到达 → 用 += 拼接
                        if tc.function.arguments:
                            tool_calls_raw[idx]["arguments"] += tc.function.arguments

        # ── 把 assistant 消息加入历史 ───────────────────────
        assistant_msg: dict = {"role": "assistant", "content": full_text or None}
        if tool_calls_raw:
            assistant_msg["tool_calls"] = [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                for tc in tool_calls_raw.values()
            ]
        messages.append(assistant_msg)

        # ── 没有工具调用 → 结束循环 ─────────────────────────
        if not tool_calls_raw:
            return

        turn += 1

        # ── 执行工具 + 结果回喂（和第 1 步完全一样）────────
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
    print("流式 Agentic Loop（输入 /quit 退出）")
    print("试试：「北京今天适合做什么？」（需要先查天气再推荐活动，会触发多轮循环）\n")

    messages = []
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
        print("\n")


asyncio.run(main())
