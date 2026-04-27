# 架构专题：从脚本到生产级 Agent

> 本文面向完成11节课的学习者。你已经能构建完整的 mini-claude，现在来理解**为什么这样设计**。

---

## 一、演进路径：11节课做了什么

```
Lesson 1-3   单文件脚本      10行代码 → 多轮对话
Lesson 4-5   引入异步+工具   async/await → 统一工具接口
Lesson 6-7   核心循环        agentic loop → 真实工具执行
Lesson 8     健壮性          超时 + 重试 + cwd追踪
Lesson 9     安全层          危险命令拦截 + 路径越界检测
Lesson 10    记忆层          CLAUDE.md + 会话持久化
Lesson 11    依赖注入        ToolUseContext → 稳定接口
```

每一步都在解决一个真实问题，不是为了复杂而复杂。

---

## 二、分层架构

```
┌─────────────────────────────────────┐
│  REPL (main.py)                     │  用户交互层
│  readline, /quit, /clear, --resume  │
├─────────────────────────────────────┤
│  Agentic Loop (query.py)            │  核心循环层
│  LLM调用, 工具分发, 流式输出         │
├─────────────────────────────────────┤
│  Tool System (tool.py + tools/)     │  工具层
│  统一接口, 权限检查, 路径安全        │
├─────────────────────────────────────┤
│  Memory (memory/)                   │  记忆层
│  CLAUDE.md注入, 会话持久化           │
├─────────────────────────────────────┤
│  Security (security/)               │  安全层
│  危险命令拦截, 路径越界检测          │
└─────────────────────────────────────┘
```

每层只做一件事，层与层之间通过明确的接口通信。

---

## 三、核心架构决策

每个决策都有一个"如果不这样做"的反例。

### 1. `query()` 是 async generator

**为什么**：流式输出 + 工具调用可以交织。

**如果不这样做**：必须等所有工具执行完才能返回，用户看到的是黑盒等待，然后一次性输出。

```python
# 普通函数：等待 → 一次性返回
result = await query(messages)
print(result)

# async generator：边执行边输出
async for chunk in query(messages):
    print(chunk, end="", flush=True)  # 实时打印
```

### 2. `ToolUseContext` 依赖注入

**为什么**：工具签名稳定，新增参数不需要改所有工具。

**如果不这样做**：

```python
# 没有 ToolUseContext 时，每次加参数所有工具都要改：
call(args, cwd)
call(args, cwd, auto)
call(args, cwd, auto, timeout)   # 加了超时
call(args, cwd, auto, timeout, max_output)  # 再加输出限制

# 有了 ToolUseContext：
call(args, context)  # 永远不变，新参数加到 context 里
```

### 3. `messages` vs `api_messages` 分离

**为什么**：system prompt 不应该持久化到 `latest.json`。

**如果不这样做**：`--resume` 时重复注入 system prompt，LLM 收到两份相同的项目说明，行为混乱。

```python
messages = []                          # 持久化：不含 system prompt
api_messages = [system_msg] + messages # 发给 API：含 system prompt
```

### 4. `is_read_only()` 区分工具

**为什么**：只读操作不需要打扰用户确认。

**如果不这样做**：读一个文件也要弹权限提示，用户体验极差，agent 无法流畅工作。

```python
class FileReadTool(Tool):
    def is_read_only(self) -> bool:
        return True   # 直接执行，不询问

class BashTool(Tool):
    def is_read_only(self) -> bool:
        return False  # 需要权限检查
```

### 5. `is_error` 信号

**为什么**：LLM 能感知工具失败，主动调整策略。

**如果不这样做**：LLM 需要解析 `content` 文字才能判断是否出错，容易误判，无法可靠地重试或换方案。

```python
tool_msg = {
    "role": "tool",
    "content": result.data,
    **({"is_error": True} if result.error else {}),
}
```

### 6. 命令末尾追加 `\npwd`

**为什么**：每次 `create_subprocess_shell` 都是新进程，不继承上一次的目录。

**如果不这样做**：`cd /tmp` 执行成功，但下一条命令仍在原目录，agent 无法导航文件系统。

```python
full_cmd = command + "\npwd"
lines = output.strip().splitlines()
if lines and lines[-1].startswith("/"):
    context.cwd = lines[-1]   # 更新 cwd
```

### 7. 指数退避重试

**为什么**：网络抖动是暂时的，等待后重试通常成功；但 400/401/403 是客户端错误，重试没有意义。

**如果不这样做**：要么遇到网络抖动直接失败，要么无限重试客户端错误浪费资源。

```python
for attempt in range(3):
    try:
        return await client.chat.completions.create(...)
    except APIError as e:
        if e.status_code in (400, 401, 403):
            raise   # 客户端错误，不重试
        await asyncio.sleep(2 ** attempt)  # 1s, 2s
```

### 8. 向上遍历收集 CLAUDE.md

**为什么**：无论在哪个子目录运行 agent，都能读到项目说明。

**如果不这样做**：只能在项目根目录运行，子目录运行时 agent 不知道项目背景。

---

## 四、mini-claude 与生产级 agent 的差距

诚实地说，mini-claude 还缺少：

| 缺失 | 影响 | 生产级做法 |
|------|------|-----------|
| 并发工具调用 | 多个工具串行执行，速度慢 | `asyncio.gather()` 并发执行 |
| 工具输出结构化校验 | LLM 返回的 JSON 可能格式错误 | JSON Schema 校验 |
| 细粒度权限模型 | 只能 allow/deny 整条命令 | per-file, per-directory 规则 |
| 可观测性 | 出错时难以排查 | 结构化日志 + 追踪 ID |
| 多 LLM 后端 | 绑定 ZhipuAI | 抽象 LLM 接口，支持切换 |
| 会话完整性校验 | 恢复损坏的 JSON 会崩溃 | 校验 messages 结构再加载 |

这些不是 mini-claude 的缺陷，而是**有意简化**——每个都可以作为进阶练习。

---

## 五、下一步

如果你想继续深入：

1. **实现并发工具调用**：当 LLM 返回多个 tool_calls 时，用 `asyncio.gather()` 并发执行
2. **添加结构化日志**：用 `logging` 模块记录每次工具调用的输入输出
3. **支持更多工具**：参考 `tools/` 目录，实现 `GlobTool`、`GrepTool`
4. **对比原版**：阅读 `src/query.ts`、`src/Tool.ts`，找出 Python 版与 TypeScript 版的设计差异
