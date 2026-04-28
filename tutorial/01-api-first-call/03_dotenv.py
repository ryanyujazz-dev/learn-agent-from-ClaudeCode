"""
Lesson 1 — 方式 3：.env 文件读取 API Key
适合团队协作，.env 文件不提交到 git。

使用前：
  1. pip install python-dotenv
  2. 复制 .env.example 为 .env，填入你的 key
  3. 运行本文件
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 从 .env 文件加载环境变量

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
    messages=[
        {"role": "system", "content": "你是一个老练python程序员，经常为大伙儿解答python问题。"}, # 加入系统提示词
        {"role": "user", "content": user_input}
    ],
)

# print(response) # 打印完整的回复，可以试着去查看返回的结构化内容
print(response.choices[0].message.content) # 打印 LLM 的回复
