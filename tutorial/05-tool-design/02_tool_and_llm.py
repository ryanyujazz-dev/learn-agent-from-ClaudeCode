"""
Lesson 5 — 第 2 步：怎么让 LLM 知道我们的工具？

第 1 步的工具能用了，但有个问题：LLM 不知道它的存在。

你问 LLM "帮我 echo 一下 hello"，它只会用文字回答，不会调用工具。
因为它不知道有 echo 工具可以用。

怎么办？——把工具的"说明书"告诉 LLM。这份说明书就是 JSON Schema。
"""
import os
import json
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)


# ── JSON Schema：工具的"说明书" ───────────────────────────────
#
# 就像餐厅菜单告诉顾客有什么菜、每道菜有什么配料可选，
# JSON Schema 告诉 LLM 有什么工具、每个工具接受什么参数。

echo_schema = {
    "type": "function",
    "function": {
        "name": "echo",                       # 工具名
        "description": "原样返回输入的消息",   # 告诉 LLM 这个工具干嘛的
        "parameters": {                        # 告诉 LLM 要传什么参数
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "要回显的内容"},
            },
            "required": ["message"],
        },
    },
}

print("告诉 LLM 的工具说明书（JSON Schema）:")
print(json.dumps(echo_schema, ensure_ascii=False, indent=2))
print()

# ── 把说明书传给 LLM ─────────────────────────────────────────
#
# API 调用里加一个 `tools` 参数，LLM 就知道有哪些工具可用。
# 这是第 1-4 课唯一的新东西：messages 参数旁边多了一个 tools 参数。


async def main():
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=[
            {"role": "user", "content": "我需要你的帮助，你能帮我 echo 一下 hello world吗？"},
        ],
        tools=[echo_schema],  # ← 新参数！把工具说明书传给 LLM
    )

    message = response.choices[0].message

    # ── LLM 的回复有两种可能 ─────────────────────────────────
    # 1. 普通文字回复（content 不为空）→ LLM 觉得不需要工具
    # 2. 工具调用（tool_calls 不为空）→ LLM 决定调用工具

    if message.content:
        print(f"LLM 文字回复: {message.content}")

    if message.tool_calls:
        tc = message.tool_calls[0]
        #print(tc) # ChatCompletionMessageFunctionToolCall(id='call_-7667511578303921228', function=Function(arguments='{"message":"hello world"}', name='echo'), type='function', index=0)
        print(f"LLM 决定调用工具: {tc.function.name}")
        print(f"参数: {tc.function.arguments}")

        # 这就是 LLM 返回的 tool_call：
        #   - function.name = "echo"
        #   - function.arguments = '{"message": "hello world"}'
        #
        # LLM 自己决定了调用哪个工具、传什么参数！
        # 第 6 课会做：解析这些参数 → 执行工具 → 结果回喂给 LLM


asyncio.run(main())
