# Lesson 5 — 工具系统设计

## 行业术语：Tool Calling

本课涉及的概念在行业里有标准叫法：

| 术语 | 含义 | 本课对应 |
|------|------|---------|
| **Tool Schema** | 用 JSON Schema 定义工具接受什么参数（告诉 LLM 怎么用） | `input_schema` / `to_api_schema()` |
| **Tool Calling / Function Calling** | LLM 决定调用哪个函数、传什么参数 | 第 2 步演示，第 6 课完整实现 |
| **Tool Dispatch** | 程序根据 LLM 返回的工具名，路由到对应的处理函数 | 第 3 步的 `next((t for t in TOOLS ...))` |
| **Tool Result** | 工具执行完的结果，回喂给 LLM | `call()` 的返回值 |

## 不用装饰器行不行？

**行。** 1-2 个工具完全不需要 ABC、@abstractmethod。直接写类就行。

那什么时候需要？——当你有多个工具，需要一个 agentic loop 统一处理它们的时候。本课分 3 步，一步步告诉你为什么需要。

---

## 文件 1：`01_simple_tool.py` — 工具就是"名字 + 函数"

不需要 API Key，纯本地运行。

```bash
python3 01_simple_tool.py
```

不用装饰器，不用抽象类。一个工具就是：

```python
class EchoTool:
    name = "echo"

    async def call(self, args: dict) -> str:
        return args["message"]
```

就这么简单。名字 + 接受字典的函数。能用吗？完全能用。

---

## 文件 2：`02_tool_and_llm.py` — 怎么让 LLM 知道我们的工具？

第 1 步的工具能用了，但 LLM 不知道它的存在。我们需要告诉 LLM："你有这些工具可以用"。

### JSON Schema：工具的"菜单"

就像餐厅菜单告诉顾客有什么菜，JSON Schema 告诉 LLM 有什么工具、每个工具接受什么参数：

```python
echo_schema = {
    "type": "function",
    "function": {
        "name": "echo",          # 工具名
        "description": "原样返回输入的消息",  # 告诉 LLM 这个工具干嘛的
        "parameters": {           # 告诉 LLM 要传什么参数
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "要回显的内容"},
            },
            "required": ["message"],
        },
    },
}
```

### 传给 LLM

API 调用只多了一个参数：

```python
response = await client.chat.completions.create(
    model="glm-5.1",
    messages=[...],
    tools=[echo_schema],          # ← 唯一新东西：告诉 LLM 有什么工具
)
```

LLM 收到后，回复里可能出现 `tool_calls`：

```python
message.tool_calls[0].function.name       # "echo"
message.tool_calls[0].function.arguments  # '{"message": "hello world"}'
```

LLM 决定了调用哪个工具、传什么参数。但还没有执行——第 6 课会把这一切串起来。

### Function Calling 完整规范

上面的代码展示了 Function Calling 的前两步。完整协议其实就三步：

**第 1 步：请求——告诉 LLM 有什么工具**

```python
response = await client.chat.completions.create(
    model="glm-5.1",
    messages=[...],
    tools=[{
        "type": "function",
        "function": {
            "name": "工具名",
            "description": "工具描述",
            "parameters": { ... }       # JSON Schema
        }
    }],
)
```

**第 2 步：响应——LLM 决定调用哪个工具**

```python
message = response.choices[0].message

message.tool_calls[0].id              # "call_abc123" — 这次调用的唯一 ID
message.tool_calls[0].function.name   # "echo" — 要调的工具名
message.tool_calls[0].function.arguments  # '{"message":"hello"}' — 参数（JSON 字符串）
```

为什么需要 `id`？因为一次回复可能同时调用多个工具，回喂结果时需要用 id 匹配"哪个结果对应哪次调用"。

**第 3 步：结果回喂——把工具执行结果告诉 LLM**（第 6 课实现）

```python
messages.append({
    "role": "tool",                     # 固定值，标识这是工具结果
    "tool_call_id": "call_abc123",     # 对应第 2 步的 id
    "content": "hello",                # 工具执行的结果
})
```

LLM 看到 tool 消息后，继续生成回复（可能再次调用工具，也可能直接输出文字）。

```
┌─────────┐     tools=[...]      ┌─────────┐
│  你的程序  │ ──────────────────→ │   LLM    │
│          │ ←────────────────── │          │
│          │   tool_calls[name,  │          │
│          │   args, id]         │          │
│          │                      │          │
│  执行工具  │     tool_result     │          │
│          │ ──────────────────→ │          │
│          │ ←────────────────── │          │
│          │   最终文字回复        │          │
└─────────┘                      └─────────┘
```

这就是整个 Function Calling 协议。第 6 课的 agentic loop 就是把这三步放进一个 while 循环。

```bash
python3 02_tool_and_llm.py
```

---

## 你可能注意到了

File 1 定义了 `EchoTool`（`name = "echo"`）。
File 2 手写了 `echo_schema`（`name: "echo"`）。

同一个工具，信息写了两遍。如果有 10 个工具，就要手写 10 份 JSON Schema。

能不能让工具自己生成这份 JSON？——这就是 File 3 要解决的问题。

---

## 文件 3：`03_why_abc.py` — 工具多了怎么办？为什么需要 ABC？

### 解决"信息写两遍"的问题

File 3 把 File 1 的工具定义和 File 2 的 JSON Schema 合并到一个类里：

```python
class EchoTool(Tool):
    name = "echo"
    description_text = "原样返回输入的消息"
    input_schema = {...}

    async def call(self, args: dict) -> ToolResult:
        return ToolResult(data=args["message"])
```

`to_api_schema()` 方法把 `name` + `description_text` + `input_schema` 组装成 File 2 手写的那份 JSON——**自动生成，不用手写**。

### ToolResult：统一的返回格式

```python
@dataclass
class ToolResult:
    data: str
    error: bool = False
```

为什么需要？agentic loop 需要知道工具是否执行成功。`error=True` 时，loop 把错误回喂给 LLM，让它换个思路。

`@dataclass` 就是自动生成 `__init__` 的语法糖，不用手写构造函数。

### 有了统一接口，loop 就好写了

```python
# 找工具
tool = next((t for t in TOOLS if t.name == tool_name), None)
# 调工具
result: ToolResult = await tool.call(tool_args)
```

不管有几个工具，这两行代码不用改。

```bash
python3 03_why_abc.py
```

---

## 上一课的连接

第 4 课得出公式：**Agent = system prompt + query() 循环 + 工具池**。

本课搞定了"工具池"里工具长什么样：
- 工具的本质：名字 + 函数（第 1 步）
- 怎么告诉 LLM：JSON Schema（第 2 步）
- 怎么统一管理：ABC 抽象基类（第 3 步）

下一课（第 6 课）把工具接到 agentic loop 里，实现完整的 query() 循环。

## 你知道吗？MCP（Model Context Protocol）

本课学的 Tool Schema（用 JSON 描述工具的参数），在业界有一个标准化的协议：**MCP**。

它做的事情和我们第 2 步一样——描述工具、传递参数、返回结果——但做了两件我们没做的事：

| | 本课的做法 | MCP 的做法 |
|--|----------|-----------|
| 工具从哪来？ | 硬编码在代码里 | 外部服务器动态提供 |
| 工具怎么描述？ | 我们手写 JSON Schema | 服务器自动返回 Schema |
| 工具怎么执行？ | 本地 `call()` | 通过网络调用服务器 |

好处：**不用改 agent 代码就能添加新工具**。只要启动一个 MCP 服务器，agent 的工具池就自动多出新的工具。

Claude Code 支持通过 MCP 连接外部工具服务器（数据库查询、GitHub 操作、文件搜索等）。File 4 让你亲手操作这个流程。

---

## 文件 4：`04_mcp/` — MCP 实战：动态工具发现 + LLM 调用

前面三个文件的工具都是硬编码的（`TOOLS = [EchoTool(), ...]`）。File 4 演示另一种方式：**工具从外部 MCP 服务器动态获取**。

```bash
pip install "mcp[cli]"         # 先安装 MCP SDK（新增依赖）
cd 04_mcp
python3 agent.py               # 启动 agent（自动启动 server.py 作为子进程）
# 试试：「帮我 echo hello」或「3加5等于多少」或「北京天气怎么样」
```

### 为什么拆成两个文件？

MCP 的核心是**agent 和工具服务器分离**。拆成两个独立程序才能真正体现这一点：

```
server.py（工具服务器）          agent.py（AI agent）
┌──────────────────┐            ┌──────────────────┐
│  别人写的代码       │  MCP 协议  │  你写的代码         │
│  提供 echo、add、   │ ←───────→ │  不知道有哪些工具    │
│  get_weather      │            │  启动时自动发现      │
└──────────────────┘            └──────────────────┘
```

- `server.py` — MCP 服务器，定义工具。你可以把它想象成"别人维护的独立服务"
- `agent.py` — Agent，连接服务器发现工具，接入 LLM

要加新工具？只改 `server.py`，`agent.py` 完全不用动。

### 核心代码：MCP Schema → OpenAI Schema 转换

从 MCP 服务器获取的工具描述，需要转成 OpenAI 的 `tools` 格式才能传给 LLM。两者的 JSON Schema 格式几乎一样，只是外层包装不同：

```python
# MCP 服务器返回的格式
mcp_tool = {"name": "echo", "description": "原样返回", "inputSchema": {...}}

# OpenAI 需要的格式
openai_tool = {
    "type": "function",
    "function": {"name": "echo", "description": "原样返回", "parameters": {...}}
}
```

### 对比：硬编码 vs MCP

| | File 1-3 | File 4 (MCP) |
|---|---|---|
| 工具定义在哪？ | agent 代码里 | 外部服务器 |
| 加新工具？ | 改 agent 代码 | 只改服务器 |
| 工具列表何时确定？ | 编译时（写死的） | 运行时（动态发现） |
| 工具怎么调用？ | `tool.call(args)` | `session.call_tool(name, args)` |
| LLM 端有区别吗？ | **没有** — LLM 看到的 tools 格式完全一样 |

关键发现：对 LLM 来说，工具是硬编码还是 MCP 提供的，完全透明。LLM 只看到 `tools=[{name, schema}]`。

---

## 四文件递进总结

| 文件 | 新增概念 | 需要 API Key |
|------|---------|-------------|
| `01_simple_tool.py` | 工具的本质：名字 + 函数 | 不需要 |
| `02_tool_and_llm.py` | JSON Schema、`tools` 参数、`tool_calls` 响应 | 需要 |
| `03_why_abc.py` | ABC、`@abstractmethod`、统一接口 | 不需要 |
| `04_mcp/` (server.py + agent.py) | MCP 协议、动态工具发现、Schema 转换 | 需要（+ `pip install "mcp[cli]"`）|

## 作业

1. 在 `01_simple_tool.py` 里加一个 `MultiplyTool`（乘法工具），不用装饰器，直接用。
2. 在 `02_tool_and_llm.py` 里，问 LLM 一个不需要工具的问题（比如"什么是 Python"），观察 `tool_calls` 是否为空——LLM 会自己判断要不要用工具。
