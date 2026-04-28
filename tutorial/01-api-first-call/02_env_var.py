"""
Lesson 1 — 方式 2：环境变量读取 API Key
代码里不包含 key，更安全，适合日常开发。

使用前先设置环境变量：
    终端: export LLM_API_KEY="你的key"
         export LLM_BASE_URL="你的base_url""
    PyCharm：Run Configuration(编辑） → Environment variables(环境变量) 中添加 LLM_API_KEY和LLM_BASE_URL

"""
import os
from openai import OpenAI

# 获取用户输入
user_input = input(">>> ")

# 创建 OpenAI 客户端
client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)


# 创建会话，接收LLM的回复
response = client.chat.completions.create(
    model=os.environ.get("LLM_MODEL", "glm-5.1"),
    messages=[{"role": "user", "content": user_input}],
)

print(response.choices[0].message.content)
