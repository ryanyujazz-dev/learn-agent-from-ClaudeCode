"""
Lesson 4 — 第 2 步：用 async 调用 LLM
新概念: AsyncOpenAI, await 等待 LLM 回复

在 01 的基础上，把 async 用到 LLM 调用上。
和 Lesson 1 的同步版对比：
  同步: OpenAI       → response = client.chat.completions.create(...)
  异步: AsyncOpenAI  → response = await client.chat.completions.create(...)
就这两处不同，其余完全一样。
"""
import os
import asyncio
from openai import AsyncOpenAI  # 注意：是 AsyncOpenAI，不是 OpenAI

client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)


async def main():
    user_input = input(">>> ")

    # 和同步版唯一的区别：前面加了 await
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=[{"role": "user", "content": user_input}],
    )

    print(response.choices[0].message.content)


# 和 01 一样，用 asyncio.run 启动
asyncio.run(main())
