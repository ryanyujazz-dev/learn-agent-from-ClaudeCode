"""
Lesson 3: 多轮对话
新概念: messages 列表, role(user/assistant), 对话历史追加
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["ZHIPUAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

messages = []

print("多轮对话（输入 /quit 退出）")
while True:
    user_input = input("你: ").strip()
    if user_input == "/quit":
        break
    if not user_input:
        continue

    messages.append({"role": "user", "content": user_input})

    stream = client.chat.completions.create(
        model="glm-5.1",
        messages=messages,
        stream=True,
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
