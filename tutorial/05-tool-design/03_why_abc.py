"""
Lesson 5 — 第 3 步：工具多了怎么办？为什么需要 ABC？

第 1 步：工具 = 名字 + 函数，直接用就行，不需要装饰器。
第 2 步：用 JSON Schema 告诉 LLM 工具的存在，LLM 能决定调用工具。

但你可能注意到了一个问题：

  File 1 定义了 EchoTool，name = "echo"
  File 2 手写了 echo_schema，name = "echo"

  同一个工具，信息写了两遍！如果有 10 个工具，就要手写 10 份 JSON。

File 3 解决这个问题：工具自己生成 JSON Schema，并且我们用真实 LLM 调用来演示。
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI


# ════════════════════════════════════════════════════════════════
# 第一部分：ToolResult — 工具的返回值
# ════════════════════════════════════════════════════════════════
#
# 第 1 步的工具，call() 直接返回字符串。
# 但如果工具出错了呢？光返回字符串，loop 分不清成功还是失败。
#
# ToolResult 同时包含"结果"和"是否出错"：
#   成功: ToolResult(data="晴天，25度")
#   失败: ToolResult(data="城市不存在", error=True)
#
# @dataclass 帮你自动生成 __init__，省掉手写构造函数。


@dataclass
class ToolResult:
    data: str           # 结果内容
    error: bool = False  # 是否出错


# ════════════════════════════════════════════════════════════════
# 第二部分：Tool 基类 — 所有工具的"模板"
# ════════════════════════════════════════════════════════════════
#
# 没有统一接口会怎样？有人写 call()，有人写 execute()，loop 没法统一处理。
# ABC 强制所有子类实现相同的方法：都必须有 name 和 call()。
# @abstractmethod：忘了实现 call() → Python 启动就报错。


class Tool(ABC):
    name: str = ""              # 工具名，LLM 用这个名字调用
    description_text: str = ""  # 工具描述，告诉 LLM 这个工具干嘛的
    input_schema: dict = {}     # 参数格式，告诉 LLM 要传什么参数

    @abstractmethod
    async def call(self, args: dict) -> ToolResult:
        ...

    def to_api_schema(self) -> dict:
        """自动生成 JSON Schema——就是 File 2 手写的那个！"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description_text,
                "parameters": self.input_schema,
            },
        }


# ════════════════════════════════════════════════════════════════
# 第三部分：实现真实工具
# ════════════════════════════════════════════════════════════════


class WeatherTool(Tool):
    """查询天气——LLM 自己没有实时数据，需要工具帮忙。"""

    name = "get_weather"
    description_text = "查询指定城市的天气"
    input_schema = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名，如 北京、上海"},
        },
        "required": ["city"],
    }

    # 模拟天气数据（真实项目里会调天气 API）
    WEATHER_DATA = {
        "北京": "晴天，25°C，空气质量良好",
        "上海": "多云，28°C，有阵雨",
        "深圳": "阴天，30°C，湿度较高",
        "成都": "小雨，22°C，记得带伞",
    }

    async def call(self, args: dict) -> ToolResult:
        city = args.get("city", "")
        if city in self.WEATHER_DATA:
            return ToolResult(data=f"{city}：{self.WEATHER_DATA[city]}")
        return ToolResult(data=f"未找到城市「{city}」的天气数据", error=True)


class EchoTool(Tool):
    """回显消息——第 1 步就见过的工具，现在套上了 Tool 基类。"""

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


# ════════════════════════════════════════════════════════════════
# 第四部分：真实 LLM 调用——看看 ABC 的威力
# ════════════════════════════════════════════════════════════════

client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)

TOOLS: list[Tool] = [WeatherTool(), EchoTool()]


async def main():
    user_input = input("你: ").strip() or "北京和上海今天天气怎么样？"
    print()

    # ── Step 1: 调用 LLM，把工具列表传进去 ─────────────────────
    # to_api_schema() 自动生成每个工具的 JSON Schema
    # 不用像 File 2 那样手写了！
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=[{"role": "user", "content": user_input}],
        tools=[t.to_api_schema() for t in TOOLS],  # ← 自动生成！
    )

    message = response.choices[0].message

    # ── Step 2: LLM 没有调用工具 → 直接打印文字回复 ───────────
    if not message.tool_calls:
        print(f"LLM: {message.content}")
        return

    # ── Step 3: LLM 调用了工具 → 统一查找 + 统一执行 ───────────
    # 这就是 ABC 的威力：不管有几个工具、调了哪个工具，
    # 都用同一套代码处理。新增工具时，这里不用改。
    for tc in message.tool_calls:
        print(f"LLM 决定调用: {tc.function.name}({tc.function.arguments})")

        # 找工具
        tool = next((t for t in TOOLS if t.name == tc.function.name), None)
        if not tool:
            print(f"  → 未知工具")
            continue

        # 执行工具（所有工具都实现了 call()，统一调用）
        args = json.loads(tc.function.arguments)
        result: ToolResult = await tool.call(args)

        if result.error:
            print(f"  → 执行失败: {result.data}")
        else:
            print(f"  → {result.data}")

    # ── 第 6 课要做的 ─────────────────────────────────────────
    # 把工具结果（role: "tool"）回喂给 LLM，让 LLM 生成最终回复。
    # 比如 LLM 会说："北京晴天25度，上海多云28度有阵雨。"


asyncio.run(main())
