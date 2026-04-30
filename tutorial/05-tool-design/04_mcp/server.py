"""
Lesson 5 File 4 — MCP 服务器

这是一个独立的 MCP 服务器程序，提供三个工具：echo、add、get_weather。

和 File 1-3 的 Tool 类做的事一样：定义名字、描述、参数 → 等待调用 → 返回结果。
区别是这些工具通过 MCP 协议暴露给外部，而不是写在 agent 代码里。

你可以把本文件想象成"别人写的服务"——agent 的开发者不需要看这个文件的代码，
只需要知道：启动这个服务器，它就提供了这些工具。

运行方式：
  python3 server.py          # 手动启动服务器（通常由 agent 自动启动）
  python3 server.py &        # 后台运行
"""
import logging

from mcp.server.fastmcp import FastMCP

# 抑制日志，避免 INFO 级别输出污染终端
logging.getLogger("mcp").setLevel(logging.WARNING)

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


# 启动服务器，通过 stdin/stdout 通信（MCP 的 stdio 传输模式）
mcp.run(transport="stdio")
