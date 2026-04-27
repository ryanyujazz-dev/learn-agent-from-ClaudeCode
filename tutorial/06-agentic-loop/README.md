# Lesson 6 — Agentic Loop（核心）

## 本节新概念

**Agentic Loop**：LLM 调用工具 → 工具返回结果 → LLM 继续 → 直到不再需要工具。

## 状态机图

```
开始
  ↓
[LLM 生成回复]
  ↓
有 tool_calls？
  ├── 否 → 打印回复，结束
  └── 是 → 执行工具 → 把结果加入 messages → 回到 [LLM 生成回复]
```

## 核心代码解读

```python
while turn < max_turns:
    # 1. 调用 LLM
    response = await client.chat.completions.create(...)

    # 2. 有工具调用吗？
    if not response.choices[0].message.tool_calls:
        break  # 没有，结束循环

    # 3. 执行每个工具
    for tc in response.choices[0].message.tool_calls:
        result = await dispatch(tc.function.name, tc.function.arguments)
        # 4. 把结果加回 messages
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    turn += 1
```

## async generator

`query()` 函数用 `yield` 边执行边输出文字，调用方用 `async for` 接收：

```python
async def query(...):
    yield "一些文字"   # 立刻发给调用方

async for text in query(...):
    print(text, end="")
```

## 运行

```bash
python3 main.py
# 试着问："帮我 echo 一下 hello world"
```

## 作业

把 `max_turns=5` 改成 `max_turns=2`，观察超出限制时的提示。
