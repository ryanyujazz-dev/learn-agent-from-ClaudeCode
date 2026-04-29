"""
Lesson 4 — 第 2 步：async 在 LLM 场景下的真实价值
新概念: AsyncOpenAI, asyncio.gather() 并发请求

串行问 LLM 两个问题 vs 并发同时问——看看耗时差多少。
"""
import os
import time
import asyncio
from openai import AsyncOpenAI  # 注意：是 AsyncOpenAI，不是 OpenAI

client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)


async def ask_llm(question: str) -> str:
    """发一个问题给 LLM，返回回复。"""
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content


async def main():
    question_1 = "用一句话解释什么是Python"
    question_2 = "用一句话解释什么是JavaScript"

    # ── 串行：一个问完再问下一个 ─────────────────────────────
    print("=== 串行（一个一个问）===")
    start = time.time()
    answer_1 = await ask_llm(question_1)
    print(f"Q: {question_1}\nA: {answer_1}\n")

    answer_2 = await ask_llm(question_2)
    print(f"Q: {question_2}\nA: {answer_2}\n")
    print(f"串行耗时: {time.time() - start:.1f} 秒\n")

    # ── 并发：两个问题同时发 ─────────────────────────────────
    print("=== 并发（同时问）===")
    start = time.time()
    # asyncio.gather 让两个请求同时发出，谁先回来就先处理谁
    answer_1, answer_2 = await asyncio.gather(
        ask_llm(question_1),
        ask_llm(question_2),
    )
    print(f"Q: {question_1}\nA: {answer_1}\n")
    print(f"Q: {question_2}\nA: {answer_2}\n")
    print(f"并发耗时: {time.time() - start:.1f} 秒")

    # ── 总结 ─────────────────────────────────────────────────
    print("\n--- 语法对照 ---")
    print("同步 LLM: from openai import OpenAI")
    print("异步 LLM: from openai import AsyncOpenAI")
    print("同步调用: response = client.chat.completions.create(...)")
    print("异步调用: response = await client.chat.completions.create(...)")
    print("串行等待: answer_1 = await ask(); answer_2 = await ask()")
    print("并发等待: answer_1, answer_2 = await asyncio.gather(ask(), ask())")


asyncio.run(main())
