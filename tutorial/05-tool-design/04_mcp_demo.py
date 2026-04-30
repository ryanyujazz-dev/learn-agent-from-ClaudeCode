"""
Lesson 5 File 4：MCP（Model Context Protocol）实战
新概念: MCP 服务器, 动态工具发现, MCP Schema → OpenAI Schema 转换

前面三个文件的工具都是硬编码在 agent 代码里的：
  class EchoTool(Tool): ...
  class WeatherTool(Tool): ...
  TOOLS = [EchoTool(), WeatherTool()]

要加一个工具？改 agent 代码，重启程序。

MCP 的核心思想：工具不由 agent 代码定义，而是由外部服务器提供。
agent 启动时连接服务器，自动发现可用工具。
要加一个工具？只改服务器，agent 代码不用动。

本文件用一种巧妙的方式演示这个流程：
  - 加 --server 参数运行 → 作为 MCP 服务器（提供 echo、add、get_weather 三个工具）
  - 不加参数运行       → 作为 agent，启动服务器子进程，发现工具，接入 LLM

运行方式：
  pip install "mcp[cli]"       # 需要先安装 MCP SDK
  python3 04_mcp_demo.py       # 启动 agent（自动启动 MCP 服务器）
"""
import os
import sys
import json
import asyncio

# ── 模式判断 ──────────────────────────────────────────────────
# 同一个文件，两种运行模式

if "--server" in sys.argv:
    # ============================================================
    # MCP 服务器模式
    # ============================================================
    # 用 FastMCP 定义工具，和 File 1-3 的 Tool 类做的事一样：
    #   定义名字、描述、参数 → 等待调用 → 返回结果
    # 区别是这些工具通过 MCP 协议暴露给外部，而不是写在 agent 代码里。

    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("demo-tools")

    @mcp.tool()
    def echo(message: str) -> str:
        """原样返回输入的消息"""
        return message

    @mcp.tool()
    def add(a: float, b: float) -> str:
        """计算两个数的和"""
        return str(a + b)

    @mcp.tool()
    def get_weather(city: str) -> str:
        """查询指定城市的天气"""
        # 简化版，和第 6 课的 WeatherTool 一样的数据
        weather_data = {
            "北京": "晴天，25°C",
            "上海": "多云，28°C，有阵雨",
            "深圳": "阴天，30°C",
            "成都": "小雨，22°C",
        }
        return weather_data.get(city, f"未找到「{city}」的天气")

    # 启动服务器，通过 stdin/stdout 通信
    mcp.run(transport="stdio")

else:
    # ============================================================
    # Agent 客户端模式
    # ============================================================

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        print("请先安装 MCP SDK：pip install 'mcp[cli]'")
        sys.exit(1)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
    )

    # ── 第 1 步：连接 MCP 服务器，发现工具 ───────────────────
    # 和 File 1-3 最大的区别：工具列表不是硬编码的，而是运行时从服务器获取。
    # 服务器可以随时加新工具，这里代码不用改。

    async def discover_tools(session: ClientSession) -> tuple[list, list[dict]]:
        """
        从 MCP 服务器获取工具列表，转成 OpenAI 的 tools 格式。

        返回：
          - mcp_tools: MCP 工具列表（用于后续调用）
          - openai_tools: OpenAI 格式的工具列表（用于传给 LLM）
        """
        result = await session.list_tools()
        mcp_tools = result.tools

        # MCP Schema → OpenAI Schema 转换
        # 两者的 JSON Schema 格式几乎一样，只是外层包装不同：
        #
        # MCP:    {name, description, inputSchema: {...}}
        # OpenAI: {type: "function", function: {name, description, parameters: {...}}}
        openai_tools = []
        for tool in mcp_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            })

        return mcp_tools, openai_tools

    # ── 第 2 步：Agentic Loop（用 MCP 工具）──────────────────
    # 和第 6 课的 agentic loop 几乎一样，
    # 唯一区别：工具调用走 MCP 协议，而不是本地 call()。

    async def chat(messages: list, openai_tools: list[dict],
                   session: ClientSession, max_turns: int = 5):
        turn = 0
        while turn < max_turns:
            response = await client.chat.completions.create(
                model=os.environ.get("LLM_MODEL", "glm-5.1"),
                messages=messages,
                tools=openai_tools,
            )

            message = response.choices[0].message

            # assistant 回复加入 messages（和第 6 课一样）
            messages.append({
                "role": "assistant",
                "content": message.content,
            })
            if message.content:
                print(f"AI: {message.content}")

            # 没有工具调用 → 结束
            if not message.tool_calls:
                return

            turn += 1

            # 执行每个工具调用
            for tc in message.tool_calls:
                args = json.loads(tc.function.arguments)
                print(f"  [MCP 调用: {tc.function.name}({args})]")

                # 关键区别！不是本地 tool.call()，而是通过 MCP 协议调用远程工具
                result = await session.call_tool(tc.function.name, args)
                tool_output = result.content[0].text if result.content else "（无结果）"

                print(f"  [结果: {tool_output}]")

                # 结果回喂给 LLM（和第 6 课一样）
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_output,
                })

        print(f"\n[已达到最大轮数 {max_turns}，停止]")

    # ── 主程序 ──────────────────────────────────────────────
    async def main():
        # 启动 MCP 服务器子进程（就是本文件自身，加 --server 参数）
        server_params = StdioServerParameters(
            command="python3",
            args=[__file__, "--server"],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 发现工具
                mcp_tools, openai_tools = await discover_tools(session)

                print("=== MCP 工具发现 ===")
                print(f"从 MCP 服务器发现 {len(mcp_tools)} 个工具：")
                for tool in mcp_tools:
                    print(f"  - {tool.name}: {tool.description}")
                print()
                print("对比 File 1-3：工具是硬编码的（TOOLS = [EchoTool(), ...]）")
                print("MCP 方式：工具从服务器动态获取，agent 代码不用改")
                print()

                # 进入多轮对话
                print("MCP Agent 演示（输入 /quit 退出）")
                print("试试：「帮我 echo hello」或「3加5等于多少」或「北京天气怎么样」\n")

                messages = []
                while True:
                    user_input = input("你: ").strip()
                    if user_input == "/quit":
                        break
                    if not user_input:
                        continue
                    messages.append({"role": "user", "content": user_input})
                    await chat(messages, openai_tools, session)
                    print()

    asyncio.run(main())
