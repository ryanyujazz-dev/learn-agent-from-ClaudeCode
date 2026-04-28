"""
Lesson 3: 多轮对话
新概念: messages 列表, role(user/assistant), 对话历史追加
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

# 对话容器，缓存聊天记录
messages = []

print("多轮对话（输入 /quit 退出）")
while True:
    user_input = input(">>> ").strip()
    if user_input == "/quit":
        break
    if not user_input:
        continue

    messages.append({"role": "user", "content": user_input})
    system_message = {"role": "system", "content": SYSTEM_PROMPT}
    api_messages = [system_message] + messages

    stream = client.chat.completions.create(
        model = os.environ.get("LLM_MODEL", "glm-5.1"),
        messages = api_messages,
        stream = True,
    )

    print("AI: ", end="")
    reply = ""
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            print(text, end="", flush=True)
            reply += text
    print()

    messages.append({"role": "assistant", "content": reply})
