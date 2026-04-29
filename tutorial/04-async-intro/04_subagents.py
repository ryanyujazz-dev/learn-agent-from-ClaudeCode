"""
Lesson 4 — 第 4 步：Subagent 调度（核心架构）

新概念: 主 Agent 和用户真实对话，决定派 Subagent，汇总结果后回复用户。

Claude Code 的 Agent Tool 流程：
  1. 用户发消息给主 Agent（真实 LLM 对话）
  2. 主 Agent 思考后，决定调用 Agent 工具（tool_call）
  3. 程序启动 Subagent，给它独立的 system prompt + 任务描述
  4. Subagent 执行任务，结果回传给主 Agent
  5. 主 Agent 综合结果，继续回复用户

本课简化版（还没学 tool_call，所以手动模拟第 2-3 步）：
  - Step 1: 用户发消息 → 主 Agent（真实 LLM 调用）
  - Step 2: 模拟主 Agent 决定派 Subagent（还没学 tool_call，先硬编码）
  - Step 3: 三个 Subagent 并发执行（真实 LLM 调用）
  - Step 4: Subagent 结果回传 → 主 Agent 汇总输出（真实 LLM 调用）

对比 03_multi_agent.py：
  - 03：多个 Agent 并发，直接打印结果，没有"主 Agent"概念
  - 04：主 Agent 真正和用户对话，调度 Subagent，汇总后回复——Claude Code 的架构
"""
import os
import time
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)

# 主 Agent 的 system prompt
# Claude Code 中，主 Agent 有很长的系统提示词，定义了它的身份和工具使用方式
MAIN_AGENT_PROMPT = "你是一个 AI 编程助手。你会分析用户的请求，决定需要做什么。用中文回复。"

# 待审查的代码
CODE = """
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("users.db")
    query = f"SELECT * FROM users WHERE id={user_id}"
    return conn.execute(query).fetchall()

def get_all_users():
    conn = sqlite3.connect("users.db")
    results = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return results
"""


async def subagent(name: str, system_prompt: str, task: str) -> str:
    """
    Subagent: 独立的 Agent，有自己的 system prompt，从零开始（fresh context）。

    Claude Code 中的对应：
      - Agent Tool 启动 Subagent，给它独立的 system prompt
      - Subagent 不继承主 Agent 的对话历史
      - 主 Agent 通过 prompt 参数传递任务
    """
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-4.7"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ],
    )
    return response.choices[0].message.content


async def main():
    user_request = "帮我全面审查这段代码"

    # ── Step 1: 用户 → 主 Agent（真实 LLM 调用）──────────────────
    # 这是真实的对话：主 Agent 收到用户请求，思考后回复
    print(f"用户: {user_request}\n")

    main_response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=[
            {"role": "system", "content": MAIN_AGENT_PROMPT},
            {"role": "user", "content": f"{user_request}\n\n代码如下:\n{CODE}"},
        ],
    )
    main_reply = main_response.choices[0].message.content
    print(f"主 Agent: {main_reply}\n")

    # ── Step 2: 模拟主 Agent 决定派 Subagent ──────────────────────
    # Claude Code 中，主 Agent 会通过 tool_call 调用 Agent 工具
    # 我们还没学 tool_call，所以这里手动模拟调度
    # （第 6 课学完 tool_call 后，这一步由 LLM 自己决定）
    print("── 主 Agent 决定派出 Subagent ──\n")

    subagents = [
        {
            "name": "代码质量审查员",
            "system_prompt": "你是代码质量专家。从可读性、命名、代码结构角度审查。用中文，简洁列出问题。",
        },
        {
            "name": "安全审查员",
            "system_prompt": "你是安全专家。从 SQL 注入、数据泄露、输入验证角度审查。用中文，简洁列出问题。",
        },
        {
            "name": "性能审查员",
            "system_prompt": "你是性能优化专家。从数据库连接、查询效率、资源管理角度审查。用中文，简洁列出问题。",
        },
    ]

    # ── Step 3: Subagent 并发执行（真实 LLM 调用）─────────────────
    # Claude Code 中，Subagent 结果以 tool_result 形式回传给主 Agent
    print("派出 3 个 Subagent 并发审查...\n")
    start = time.time()
    results = await asyncio.gather(*[
        subagent(s["name"], s["system_prompt"], f"请审查以下代码:\n\n{CODE}")
        for s in subagents
    ])
    elapsed = time.time() - start

    for s, r in zip(subagents, results):
        print(f"【{s['name']}】: {r}\n")
    print(f"三个 Subagent 并发完成，耗时: {elapsed:.1f} 秒\n")

    # ── Step 4: Subagent 结果 → 主 Agent 汇总（真实 LLM 调用）─────
    # Claude Code 中，Subagent 的结果作为 tool_result 回传
    # 主 Agent 看到所有结果后，继续生成回复（同一个对话的下一轮）
    print("── Subagent 结果回传给主 Agent ──\n")

    summary = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=[
            {"role": "system", "content": MAIN_AGENT_PROMPT},
            {"role": "user", "content": f"{user_request}\n\n代码如下:\n{CODE}"},
            {"role": "assistant", "content": main_reply},
            {
                "role": "user",
                "content": (
                    "以下是三个 Subagent 的审查结果，请综合给出最终报告:\n\n"
                    f"【代码质量审查员】:\n{results[0]}\n\n"
                    f"【安全审查员】:\n{results[1]}\n\n"
                    f"【性能审查员】:\n{results[2]}"
                ),
            },
        ],
    )
    print("=" * 50)
    print("主 Agent 最终回复:")
    print(summary.choices[0].message.content)


asyncio.run(main())
