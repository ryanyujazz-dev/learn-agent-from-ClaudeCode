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

## 状态机

```
开始
  ↓
[LLM 生成回复]
  ↓
有 tool_calls？
  ├── 否 → 输出回复，结束
  └── 是 → 执行工具 → 结果加入 messages → 回到 [LLM 生成回复]
```

这就是一个 while 循环——第 1 步用代码实现它。

---

## 文件 1：`01_agentic_loop.py` — 非流式 Agentic Loop

先搞懂循环逻辑，不涉及流式输出。本文件用一次工具调用的例子，重点理解"结果回喂"。

```bash
python3 01_agentic_loop.py
# 试试：「北京天气怎么样」
```

### 和第 5 课 File 3 的区别

第 5 课 File 3：LLM 调工具 → 我们执行 → 打印结果 → **结束**

本课：LLM 调工具 → 我们执行 → **结果回喂给 LLM** → LLM 继续回复

多了一步"回喂"，LLM 就能基于工具结果生成自然语言回复（比如"北京晴天25度，上海多云28度"）。用 while 循环包起来，LLM 可以连续调多个工具。

### 核心代码

```python
while turn < max_turns:
    # 1. 调 LLM
    response = await client.chat.completions.create(
        messages=messages,
        tools=[t.to_api_schema() for t in TOOLS],
    )
    message = response.choices[0].message

    # 2. 把 assistant 回复加入 messages（即使 content 为空也必须加）
    #    因为 API 要求：assistant（带 tool_calls）→ tool（带 tool_call_id）
    #    跳过 assistant 消息会导致 tool 消息接不上，API 报错
    messages.append({"role": "assistant", "content": message.content})

    # 3. 没有工具调用 → 结束
    if not message.tool_calls:
        return

    # 4. 执行工具，结果以 role="tool" 回喂
    for tc in message.tool_calls:
        result = await tool.call(json.loads(tc.function.arguments))
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,     # 匹配"哪个结果对应哪次调用"
            "content": result.data,
        })

    # 回到 while 开头，LLM 看到工具结果后继续
```

### 为什么 `message.content` 为空也要 append？

当 LLM 决定调用工具时，`content` 可能是 `None` 或空字符串——模型直接调工具，不说话。但这条 assistant 消息**仍然必须加入 messages**。

原因是 API 对消息顺序有严格要求：

```
assistant（带 tool_calls）  ←  触发工具调用
tool      （tool_call_id）  ←  对应的工具结果
```

`tool` 角色消息必须跟在带 `tool_calls` 的 `assistant` 消息后面。如果跳过 assistant 消息直接发 tool 消息，API 会报错：

```
messages with role 'tool' must be a response to a preceding message with 'tool_calls'
```

所以 `messages.append` 控制的是**记录对话历史**（必须），`if message.content: print()` 控制的是**给用户看**（只有有内容时才打印）。

### 为什么需要 `tool_call_id`？

一次 LLM 回复可能同时调用多个工具（比如同时查北京和上海的天气）。每个 tool_call 有唯一 id，回喂结果时用这个 id 匹配"哪个结果对应哪次调用"。

---

## 为什么需要循环？

File 1 问"北京天气怎么样"——LLM 调一次 `get_weather` 就结束了，while 循环只跑了一轮。

但问"北京今天适合做什么？"——LLM 需要：
1. **第 1 轮**：调用 `get_weather("北京")` → 拿到"晴天，25°C"
2. **第 2 轮**：看到天气结果，调用 `recommend_activity("晴天，25°C")` → 拿到"建议户外活动"
3. **第 3 轮**：综合结果，输出"北京今天晴天25度，适合爬山、逛公园或骑行"

第 2 步依赖第 1 步的结果。LLM 没法在不知道天气的情况下推荐活动。这就是**循环存在的原因**——有些任务需要多步完成，每一步依赖上一步的结果。File 2 加入了 `RecommendActivityTool` 来演示这种多轮循环。

---

## 文件 2：`02_streaming_loop.py` — 流式 Agentic Loop + 多轮循环

File 1 搞懂了循环逻辑。File 2 加上流式输出 + `RecommendActivityTool`，展示真正的多轮循环。

```bash
python3 02_streaming_loop.py
# 试试：「北京今天适合做什么？」（观察多轮循环的流式输出）
```

### 和第 1 步的区别

只改了"怎么从 LLM 拿数据"：

```python
# 第 1 步：一次性拿到完整回复
response = await client.chat.completions.create(messages=..., tools=...)
message = response.choices[0].message

# 第 2 步：逐 chunk 拿（stream=True）
stream = await client.chat.completions.create(messages=..., tools=..., stream=True)
async for chunk in stream:
    ...
```

### async generator：用 yield 实时输出

```python
async def query(messages):
    ...
    if delta.content:
        yield delta.content  # 立刻发给调用方，用户逐字看到
    ...

# 调用方用 async for 接收
async for text in query(messages):
    print(text, end="", flush=True)
```

### 流式 tool_calls 拼接（最复杂的部分）

流式输出时，一个工具调用的参数**分多个 chunk 到达**：

```
chunk 1: {id: "call_1", name: "echo", arguments: "{\"mes"}
chunk 2: {arguments: "sage\": \"hello\"}"}
chunk 3: {arguments: ""}   ← 结束
```

用一个字典收集，`name` 用 `=`（只来一次），`arguments` 用 `+=`（分块拼接）：

```python
tool_calls_raw: dict[int, dict] = {}  # index → {id, name, arguments}

for tc in delta.tool_calls:
    idx = tc.index
    if idx not in tool_calls_raw:
        tool_calls_raw[idx] = {"id": "", "name": "", "arguments": ""}
    if tc.function.name:
        tool_calls_raw[idx]["name"] = tc.function.name        # = 只赋一次
    if tc.function.arguments:
        tool_calls_raw[idx]["arguments"] += tc.function.arguments  # += 拼接！

# 流结束后，json.loads() 解析完整的 arguments
args = json.loads(tool_calls_raw[0]["arguments"])
```

### 作业：观察分块过程

在 `async for chunk in stream` 循环里加几行：

```python
if delta.tool_calls:
    for tc in delta.tool_calls:
        print(f"  chunk: index={tc.index}, name={tc.function.name!r}, args_fragment={tc.function.arguments!r}")
```

问 "帮我 echo hello"，观察 name 只在第一个 chunk 出现、arguments 分多个 chunk 到达。

---

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

**文字和工具调用在同一次回复里。** "让我看看"是模型自己生成的过渡句，不是系统提示词写死的。模型学会了先告诉用户自己的意图，再执行动作。

---

## 两文件递进总结

| 文件 | 新增概念 | 和上一文件的区别 |
|------|---------|----------------|
| `01_agentic_loop.py` | while 循环、tool result 回喂、max_turns | 第 5 课 + 结果回喂 + while 循环 |
| `02_streaming_loop.py` | stream=True、yield、tool_calls 分块拼接、多轮循环（RecommendActivityTool） | 第 1 步 + 流式 + 多轮依赖 |

File 1 用一次工具调用理解"结果回喂"。File 2 加上流式输出和多轮循环，才是完整的 agentic loop。

> **工具从哪来？** 本课的工具是硬编码的（`TOOLS = [WeatherTool(), EchoTool()]`）。第 5 课 File 4 展示了 MCP 动态发现工具的方式——agentic loop 本身不需要改，只是工具来源不同。对 LLM 来说，tools 格式完全一样。

## 下一课预告

本课的 agent 已经能调工具了，但只有 WeatherTool、EchoTool、RecommendActivityTool。
第 7 课加入真正的工具——BashTool（执行命令）、FileReadTool（读文件）等。
有了这些，agent 就能真正操作你的电脑了。
