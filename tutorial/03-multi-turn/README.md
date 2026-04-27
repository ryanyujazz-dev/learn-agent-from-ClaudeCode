# Lesson 3 — 多轮对话

## 本节新概念

**messages 列表**：LLM 本身没有记忆，每次调用都要把完整的对话历史传给它。

## 关键理解

LLM 是"无状态"的——它不记得上一次你问了什么。
我们用一个 Python 列表 `messages` 来保存所有对话，每次都把整个列表发给 LLM。

```
messages = [
    {"role": "user",      "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮你？"},
    {"role": "user",      "content": "我叫小明"},   # ← 新消息追加到末尾
]
```

## 核心代码解读

```python
messages = []  # 对话历史，程序运行期间一直保留

while True:
    user_input = input("你: ")
    messages.append({"role": "user", "content": user_input})

    # 把完整历史发给 LLM
    stream = client.chat.completions.create(model=..., messages=messages, stream=True)

    reply = ""
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            print(text, end="", flush=True)
            reply += text  # 收集完整回复
    print()

    messages.append({"role": "assistant", "content": reply})  # 保存 LLM 的回复
```

## 运行

```bash
python3 main.py
# 输入 /quit 退出
```

## 作业

加一个 `/clear` 命令：当用户输入 `/clear` 时，清空 `messages` 列表，打印"对话已清空"。
