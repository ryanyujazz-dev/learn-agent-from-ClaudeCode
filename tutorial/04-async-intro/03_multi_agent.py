"""
Lesson 4 — 第 3 步：多 Agent 协作
新概念: 不同角色的 Agent 并发工作，汇总结果

一个代码片段，同时交给两个 Agent 审查：
  Agent A：代码质量审查员 —— 检查代码风格、可读性、最佳实践
  Agent B：安全审查员 —— 检查潜在安全漏洞、敏感信息泄露

两个审查同时进行，耗时取最慢的那个，而不是累加。
"""
import os
import time
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)

# 待审查的代码
CODE = """
import os

def login(username, password):
    # 连接数据库验证用户
    conn = sqlite3.connect("users.db")
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = conn.execute(query).fetchone()
    if result:
        print(f"欢迎, {username}!")
        return True
    return False
"""


async def agent_review(agent_name: str, system_prompt: str, code: str) -> str:
    """让一个 Agent 审查代码，返回审查意见。"""
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请审查以下代码，指出问题并给出修改建议：\n\n{code}"},
        ],
    )
    return response.choices[0].message.content


async def main():
    print("=== 多 Agent 协作审查代码 ===")
    print(f"待审查代码:\n{CODE}")
    print("启动两个 Agent 同时审查...\n")

    # 定义两个 Agent 的角色
    code_reviewer_prompt = "你是一个资深 Python 开发者，专注于代码质量。请从可读性、性能、最佳实践角度审查代码。用中文回复，简洁列出问题。"
    security_reviewer_prompt = "你是一个安全工程师，专注于代码安全。请从 SQL 注入、XSS、敏感信息泄露、权限控制角度审查代码。用中文回复，简洁列出问题。"

    # 并发：两个 Agent 同时工作
    start = time.time()
    code_review, security_review = await asyncio.gather(
        agent_review("代码审查员", code_reviewer_prompt, CODE),
        agent_review("安全审查员", security_reviewer_prompt, CODE),
    )
    elapsed = time.time() - start

    # 汇总结果
    print("=" * 50)
    print("【代码审查员】的意见：")
    print(code_review)
    print()
    print("=" * 50)
    print("【安全审查员】的意见：")
    print(security_review)
    print()
    print("=" * 50)
    print(f"两个 Agent 并发审查完成，耗时: {elapsed:.1f} 秒")
    print("(如果串行执行，耗时约为现在的 2 倍)")


asyncio.run(main())
