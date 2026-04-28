"""
Lesson 3 对比：没有记忆的多轮对话
每次只发当前这一条消息，不保留历史。
试试连续问：「我叫张三」→「我叫什么名字？」→ AI 答不上来。
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)

SYSTEM_PROMPT = """
你是一个python学习助手，你需要帮助用户解决各种问题。
"""

print("没有记忆的多轮对话（输入 /quit 退出）")
print("试试连续问：「我叫张三」→「我叫什么名字？」\n")

while True:
    user_input = input(">>> ").strip()
    if user_input == "/quit":
        break
    if not user_input:
        continue

    # 每次只发 system + 当前这条消息，不保留历史
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    stream = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=messages,
        stream=True,
    )

    print("AI: ", end="")
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            print(text, end="", flush=True)
    print()
