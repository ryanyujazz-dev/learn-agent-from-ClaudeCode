"""
Lesson 1: 第一次调用 LLM API
新概念: openai SDK 同步调用
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)

response = client.chat.completions.create(
    model=os.environ.get("LLM_MODEL", "glm-5.1"),
    messages=[{"role": "user", "content": "用一句话解释什么是人工智能"}],
)

print(response.choices[0].message.content)
