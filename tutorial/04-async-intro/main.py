"""
Lesson 4: async/await 入门
新概念: async def, await, asyncio.run(), async for
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
    print("多轮对话（输入 /quit 退出）")
    while True:
        user_input = input("你: ").strip()
        if user_input == "/quit":
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        stream = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "glm-5.1"),
            messages=messages,
            stream=True,
        )

        print("AI: ", end="")
        reply = ""
        async for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                print(text, end="", flush=True)
                reply += text
        print()

        messages.append({"role": "assistant", "content": reply})


asyncio.run(chat())
