# Lesson 6 — Agentic Loop（核心）

## 行业术语：Tool Calling 流程

第 5 课定义了工具长什么样，本课实现完整的 Tool Calling 流程：

```
用户提问
  ↓
LLM 返回 tool_call（包含工具名 + 参数）   ← Tool Calling
  ↓
程序解析参数，找到对应工具并执行           ← Tool Dispatch
  ↓
工具结果回喂给 LLM                        ← Tool Result
  ↓
LLM 继续生成回复（可能再次调用工具）
  ↓
没有更多工具调用时，输出最终回复
```

| 术语 | 含义 | 本课对应 |
|------|------|---------|
| **Tool Calling** | LLM 返回 `tool_calls`，包含要调用的函数名和参数 | `delta.tool_calls` 解析 |
| **Tool Dispatch** | 根据工具名找到对应的工具对象并执行 | `next((t for t in TOOLS if t.name == ...))` |
| **Tool Result** | 工具执行结果，以 `role: "tool"` 消息回喂给 LLM | `messages.append({"role": "tool", ...})` |

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

## 一次 LLM 回复里有什么？

你可能注意过 Claude Code 的输出：

```
⏺ 让我看看第5、6课现在怎么讲的。
  Read 2 files (ctrl+o to expand)
⏺ 第5、6课讲了工具设计和 agentic loop...
```

第一句话"让我看看"和后面的工具调用，来自**同一次 LLM 回复**。

API 返回的 message 有两个字段：

```python
response.choices[0].message.content      # "让我看看第5、6课现在怎么讲的。"
response.choices[0].message.tool_calls    # [Read(file="05..."), Read(file="06...")]
```

**文字和工具调用在同一次回复里。** 流式输出时，文字先到，工具调用紧跟其后：

```
chunk: content="让我"         ← 文字先出来
chunk: content="看看"
chunk: content="第5、6课..."
chunk: content=None           ← 文字结束
chunk: tool_calls=[Read(...)] ← 工具调用开始
```

所以用户看到的效果是：模型先说"让我查一下"，然后工具开始执行。这不是两步，而是一次回复里的两个部分。

"让我看看"不是系统提示词写死的模板，而是模型自己生成的过渡句——就像一个人说"等我翻一下资料"然后去翻书。模型学会了先告诉用户自己的意图，再执行动作。

这就是 agentic loop 的核心体验：用户能看到模型在"思考和行动"，而不是黑盒等待。

## 运行

```bash
python3 agentic_loop.py
# 试着问："帮我 echo 一下 hello world"
```

## 架构思考：为什么 query() 是 async generator？

普通函数必须等所有工具执行完才能返回，用户看到的是"等待 → 一次性输出"。

async generator 用 `yield` 边执行边输出，实现：
- 流式文字实时打印（用户看到逐字输出）
- 工具调用结果立即显示（不用等后续工具）
- 用户感知到 agent 在"思考和行动"，而不是黑盒等待

这是 agent 体验和批处理脚本的本质区别。

## 本课相对上一课的变更

| 新增内容 | 位置 |
|---------|------|
| `query()` async generator，含 while 循环 | `query()` 函数 |
| 流式 tool_calls 拼接逻辑 | `async for chunk in stream` 块 |
| 工具执行 + tool 消息回喂 | `for tc in tool_calls_raw.values()` 块 |
| `EchoTool` 演示工具 | 文件顶部 |

第 1-5 课的代码（`Tool` ABC、`ToolResult`、`AsyncOpenAI` 客户端）原样保留，无改动。

## 作业

在 `async for chunk in stream` 循环里，加几行打印：

```python
if delta.tool_calls:
    for tc in delta.tool_calls:
        print(f"  chunk: index={tc.index}, name={tc.function.name!r}, args_fragment={tc.function.arguments!r}")
```

然后问 agent "帮我 echo hello"，观察：
- `name` 只在第一个 chunk 出现，后续是 `None`
- `arguments` 分多个 chunk 到达，每次是 JSON 的一个片段
- 理解为什么 `name` 用 `=`，`arguments` 用 `+=`
