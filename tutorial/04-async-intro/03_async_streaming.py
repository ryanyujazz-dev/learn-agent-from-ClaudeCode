"""
Lesson 4 — 第 3 步：async for 流式输出 + 多轮对话
新概念: async for

在 02 的基础上，加上流式输出和多轮对话。
和 Lesson 2/3 的同步版对比：
  同步流式: for chunk in stream:
  异步流式: async for chunk in stream:
就这一个关键字不同。
"""
import os
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)

messages = []


async def chat():
    print("异步多轮对话（输入 /quit 退出）")
    while True:
        user_input = input(">>> ").strip()
        if user_input == "/quit":
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # 和同步版唯一的区别：await
        stream = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "glm-5.1"),
            messages=messages,
            stream=True,
        )

        print("AI: ", end="")
        reply = ""
        # 和同步版唯一的区别：async for（不是 for）
        # async for 意味着：每个 chunk 到来前，程序可以切换去干别的
        async for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                print(text, end="", flush=True)
                reply += text
        print()

        messages.append({"role": "assistant", "content": reply})


asyncio.run(chat())
