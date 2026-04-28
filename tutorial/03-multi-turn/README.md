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

## messages 完整格式

多轮对话只用到了 `user` 和 `assistant` 两种 role。加入工具后还有第三种：

| role | 什么时候出现 | content 的值 |
|------|------------|-------------|
| `user` | 用户发消息 | 用户输入的文字 |
| `assistant` | LLM 回复 | LLM 生成的文字；有工具调用时可以是 `null` |
| `tool` | 工具执行结果 | 工具返回的内容（Lesson 6 引入） |
| `system` | 程序启动时注入 | 项目说明、行为规则（Lesson 10 引入） |

`assistant` 消息有工具调用时，结构变成：

```python
{
    "role": "assistant",
    "content": null,          # 没有文字输出时是 null，不是空字符串
    "tool_calls": [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": "{\"command\": \"ls\"}"  # JSON 字符串，不是 dict
            }
        }
    ]
}
```

`tool` 消息（工具结果）：

```python
{
    "role": "tool",
    "tool_call_id": "call_abc123",  # 对应上面的 id
    "content": "file1.txt\nfile2.txt"
}
```

**为什么 `content` 是 `null` 不是 `""`？** OpenAI API 规定：有 `tool_calls` 时 `content` 必须是 `null`，传空字符串会报错。

## 运行

本课有两个文件，先运行对比版感受区别，再运行正式版。

### 对比实验：没有记忆的多轮对话

```bash
python3 01_no_memory.py
```

试试连续输入：
```
>>> 我叫张三
>>> 我叫什么名字？
```

AI 答不上来——因为每次只发了当前这条消息，没有历史。

### 正式版：有记忆的多轮对话

```bash
python3 02_multi_turn.py
```

再试同样的对话：
```
>>> 我叫张三
>>> 我叫什么名字？
```

这次 AI 能答上来——因为 `messages` 列表保留了所有历史，每次都把完整对话发给 LLM。

### 对比结论

| | `01_no_memory.py` | `02_multi_turn.py` |
|---|----------------|-----------------|
| messages | 每轮重建，只有当前消息 | 累积追加，包含完整历史 |
| AI 能记住吗 | 不能 | 能 |
| 核心差异 | `api_messages` 只有 2 条 | `messages` 不断追加 |

### 进阶：跨会话记忆

```bash
python3 03_persistent.py
```

对话几轮后输入 `/quit` 退出，然后重新运行——AI 还记得你之前说过什么。

原理：用 `json.dump` 把 `messages` 保存到 `session.json`，下次启动用 `json.load` 恢复。

只加了 5 行核心代码，但解决了"退出即遗忘"的问题。

> 这只是最简单的持久化。第10课会讲更完整的记忆系统（CLAUDE.md 项目知识 + 会话归档 + system prompt 分离）。

## 作业

加一个 `/clear` 命令：当用户输入 `/clear` 时，清空 `messages` 列表，打印"对话已清空"。
