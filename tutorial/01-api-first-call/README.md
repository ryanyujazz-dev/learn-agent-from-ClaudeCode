# Lesson 1 — 第一次调用 LLM API

## 本节新概念

**openai SDK 同步调用**：用 Python 向 LLM 发一条消息，拿到回复。

## 前置准备

```bash
pip install openai
# 支持任何 OpenAI 兼容接口：ZhipuAI、OpenAI、DeepSeek、Ollama 等
export LLM_API_KEY="你的key"
export LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"  # 可选，默认 ZhipuAI
export LLM_MODEL="glm-5.1"                                    # 可选，默认 glm-5.1
```

## 核心代码解读

```python
client = OpenAI(api_key=..., base_url=...)
```
`OpenAI` 是一个"客户端"对象，负责帮你发 HTTP 请求。`base_url` 告诉它去哪个服务器。

```python
response = client.chat.completions.create(
    model="glm-5.1",
    messages=[{"role": "user", "content": "你好"}]
)
```
`messages` 是一个列表，每条消息有 `role`（谁说的）和 `content`（说了什么）。

```python
print(response.choices[0].message.content)
```
LLM 可能返回多个候选回复（`choices`），我们取第一个。

## 运行

```bash
python3 main.py
```

## 作业

修改 `main.py` 第 14 行的 `content`，换一个问题，观察 LLM 的回复。
