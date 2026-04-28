"""
Lesson 1 — 方式 1：硬编码 API Key
最快跑通，适合自己试玩。
"""
from openai import OpenAI

# 把下面的 "你的key" 替换成你的真实 API Key
# 创建 OpenAI 客户端
client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

# 创建会话，接收LLM的回复
response = client.chat.completions.create(
    model="glm-5.1",
    messages=[{"role": "user", "content": "用一句话解释什么是人工智能"}],
)

print(response.choices[0].message.content)
