"""
Lesson 5 File 4 — MCP Agent（客户端）

这是 agent 程序，它连接到 MCP 服务器，动态发现可用工具，然后接入 LLM。

和 File 1-3 的最大区别：
  File 1-3：TOOLS = [EchoTool(), WeatherTool()]  ← 工具硬编码
  本文件：  tools = await session.list_tools()    ← 从服务器动态获取

要加一个新工具？只改 server.py，本文件代码不用动。
这就是 MCP 的价值：agent 和工具解耦。

运行方式：
  pip install "mcp[cli]"       # 先安装 MCP SDK
  python3 agent.py             # 启动 agent（自动启动 server.py 作为子进程）
"""
import os
import sys
import json
import asyncio

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

# 记录 server.py 的路径（和本文件在同一个目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(SCRIPT_DIR, "server.py")


# ── 第 1 步：连接 MCP 服务器，发现工具 ───────────────────────
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


# ── 第 2 步：Agentic Loop（用 MCP 工具）────────────────────
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


# ── 主程序 ──────────────────────────────────────────────────
async def main():
    # 启动 MCP 服务器子进程（就是旁边的 server.py）
    server_params = StdioServerParameters(
        command="python3",
        args=[SERVER_SCRIPT],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 发现工具
            mcp_tools, openai_tools = await discover_tools(session)

            print("=== MCP 工具发现 ===")
            print(f"从 MCP 服务器（server.py）发现 {len(mcp_tools)} 个工具：")
            for tool in mcp_tools:
                print(f"  - {tool.name}: {tool.description}")
            print()
            print("对比 File 1-3：工具是硬编码的（TOOLS = [EchoTool(), ...]）")
            print("MCP 方式：工具从外部服务器动态获取，agent 代码不用改")
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
