"""
Lesson 2: 流式输出
新概念: stream=True, for chunk in stream, delta.content
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)

user_input = input(">>> ")

stream = client.chat.completions.create(
    model=os.environ.get("LLM_MODEL", "glm-5.1"),
    messages=[
        {"role": "system", "content": "你是一个老练python程序员，经常为大伙儿解答python问题。"},  # 加入系统提示词
        {"role": "user", "content": user_input}
    ],
    stream=True,
)

for chunk in stream:
    text = chunk.choices[0].delta.content
    if text:
        print(text, end="", flush=True)

print()  # 最后换行
