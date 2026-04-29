"""
Lesson 5 — 第 1 步：工具就是"名字 + 函数"

为什么需要工具？因为 LLM 只能生成文字，不能真正"做事"。

  用户: "帮我算 3+5"  → LLM 只能回答 "3+5=8"，这是文字，不是真正的计算
  用户: "帮我读文件"  → LLM 做不到，它没有文件系统

工具 = 给 LLM 装上"手脚"。有了工具，LLM 可以真正执行操作：
  - 读文件（FileReadTool）
  - 运行命令（BashTool）
  - 搜索代码（GrepTool）

本课不用装饰器，不用抽象类(后面讲)。一个工具就是：名字 + 函数。
"""
import asyncio


class EchoTool:
    """最简单的工具：把输入原样返回。"""

    name = "echo"

    async def call(self, args: dict) -> str:
        return args["message"]


class AddTool:
    """另一个工具：计算两个数的和。"""

    name = "add"

    async def call(self, args: dict) -> str:
        return str(args["a"] + args["b"])


async def main():
    # 直接用，不需要装饰器
    echo = EchoTool()
    print(f"工具名: {echo.name}")
    result = await echo.call({"message": "hello world"})
    print(f"调用结果: {result}")

    add = AddTool()
    print(f"\n工具名: {add.name}")
    result = await add.call({"a": 3, "b": 5})
    print(f"3 + 5 = {result}")

    # 能用吗？完全能用。不需要装饰器。
    # 但有个问题：LLM 不知道这些工具的存在。
    # 第 2 步解决这个问题。


asyncio.run(main())
