# Lesson 2 — 流式输出

## 本节新概念

**stream=True**：不等 LLM 生成完再返回，而是边生成边接收，逐字打印。

## 为什么需要流式？

非流式：等待 5 秒 → 一次性打印全部文字（用户体验差）
流式：立刻开始打印 → 字一个个出现（像真正的 AI 对话）

## 核心代码解读

```python
stream = client.chat.completions.create(..., stream=True)
for chunk in stream:
    text = chunk.choices[0].delta.content
    if text:
        print(text, end="", flush=True)
```

- `stream=True` 让 API 返回一个"流"对象
- `for chunk in stream` 每次拿到一小块文字
- `delta.content` 是这一块新增的文字（可能为 None，要判断）
- `end=""` 不换行，`flush=True` 立刻输出到屏幕

## 运行

```bash
python3 main.py
```

## 作业

在循环结束后，打印一行 `\n共收到 X 个 chunk`，统计 chunk 数量。
