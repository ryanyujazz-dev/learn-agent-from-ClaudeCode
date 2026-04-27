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

## 流式 tool_calls 拼接（重要细节）

LLM 流式输出时，一个工具调用的参数可能**分多个 chunk 到达**：

```
chunk 1: {id: "call_1", name: "echo", arguments: "{\"mes"}
chunk 2: {arguments: "sage\": \"hello\"}"}
chunk 3: {arguments: ""}   ← 结束
```

所以我们用一个字典收集，用 `+=` 拼接 arguments：

```python
tool_calls_raw: dict[int, dict] = {}  # index → {id, name, arguments}

for tc in delta.tool_calls:
    idx = tc.index
    if idx not in tool_calls_raw:
        tool_calls_raw[idx] = {"id": "", "name": "", "arguments": ""}
    if tc.function.name:
        tool_calls_raw[idx]["name"] = tc.function.name   # 用 =，名字只来一次
    if tc.function.arguments:
        tool_calls_raw[idx]["arguments"] += tc.function.arguments  # 用 +=，拼接！

# 流结束后，从收集字典里取完整参数，再 json.loads() 解析
for collected in tool_calls_raw.values():
    args = json.loads(collected["arguments"])
```

## 运行

```bash
python3 main.py
# 试着问："帮我 echo 一下 hello world"
```

## 架构思考：为什么 query() 是 async generator？

普通函数必须等所有工具执行完才能返回，用户看到的是"等待 → 一次性输出"。

async generator 用 `yield` 边执行边输出，实现：
- 流式文字实时打印（用户看到逐字输出）
- 工具调用结果立即显示（不用等后续工具）
- 用户感知到 agent 在"思考和行动"，而不是黑盒等待

这是 agent 体验和批处理脚本的本质区别。

## 作业

把 `max_turns=5` 改成 `max_turns=2`，观察超出限制时的提示。
