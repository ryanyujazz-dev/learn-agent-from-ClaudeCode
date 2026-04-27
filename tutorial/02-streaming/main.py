"""
Lesson 2: 流式输出
新概念: stream=True, for chunk in stream, delta.content
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["ZHIPUAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

stream = client.chat.completions.create(
    model="glm-5.1",
    messages=[{"role": "user", "content": "用三句话介绍一下Python语言"}],
    stream=True,
)

for chunk in stream:
    text = chunk.choices[0].delta.content
    if text:
        print(text, end="", flush=True)

print()  # 最后换行
