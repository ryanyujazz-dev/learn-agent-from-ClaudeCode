# Lesson 12 — 状态展示

## 本节新概念

**事件协议 + rich spinner**：让用户实时看到 agent 在做什么。

---

## 问题：query() 内部发生的事，rich_agent.py 看不见

`query()` 是 async generator，它 yield 文字给 `rich_agent.py` 打印。
但工具执行发生在 `query()` 内部——`rich_agent.py` 不知道"现在在执行哪个工具"。

工具执行期间，用户看到的是空白等待：

```
>>> 帮我列出当前目录的文件
AI: （等待3秒...）
file1.py
file2.py
```

---

## 解决方案：事件协议

让 `query()` yield 两种东西：

```
普通文字:  "我来帮你列出文件..."
工具事件:  "\x00TOOL:bash:ls -la"
结果事件:  "\x00DONE:OK:bash(ls -la)"
```

用 `\x00`（null byte，不可见字符）作为前缀标记事件。
`rich_agent.py` 收到 chunk 时，检查前缀决定如何处理：

```python
async for chunk in query(...):
    if chunk.startswith("\x00TOOL:"):
        # 显示 spinner
    elif chunk.startswith("\x00DONE:"):
        # 停止 spinner，打印结果行
    else:
        # 普通文字，直接打印
```

**为什么用 `\x00` 而不是普通字符串（如 `[TOOL]`）？**
LLM 的回复可能包含 `[TOOL]` 这样的文字，会误判。`\x00` 不会出现在正常文字里。

---

## query.py 改动

工具调用前后，yield 事件而不是纯文字：

```python
# 改前：
yield f"\n[tool: {tc['name']}({args})]\n"
result = await _dispatch_tool(...)
yield f"[result: OK] ...\n"

# 改后：
yield f"\x00TOOL:{tc['name']}:{json.dumps(args)}"
result = await _dispatch_tool(...)
summary = _tool_summary(tc["name"], args, result)
yield f"\x00DONE:{'ERR' if result.error else 'OK'}:{summary}"
```

`_tool_summary()` 根据工具类型生成有意义的摘要：

```python
def _tool_summary(name, args, result):
    if name == "bash":
        return f"bash({args.get('command', '')[:40]})"
    if name == "file_write":
        lines = args.get("content", "").count("\n") + 1
        return f"file_write({args.get('path', '')}) [{lines} lines]"
    if name == "file_read":
        return f"file_read({args.get('path', '')})"
    return name
```

---

## rich Status：手动 start/stop

`rich.status.Status` 在终端显示旋转 spinner。

**不能用 `with` 块**，因为 `async for` 是流式的，进入和退出 spinner 发生在循环中间：

```python
# 错误：with 块包住整个循环，spinner 永远不停
with Status("") as status:
    async for chunk in query(...):
        ...

# 正确：手动控制
status = Status("", console=console)
spinner_running = False

async for chunk in query(...):
    if chunk.startswith("\x00TOOL:"):
        status.update("[cyan]bash[/] ls -la")
        if not spinner_running:
            status.start()
            spinner_running = True
    elif chunk.startswith("\x00DONE:"):
        if spinner_running:
            status.stop()
            spinner_running = False
        console.print("[green]✓[/] bash(ls -la)")
```

用 `spinner_running` 布尔变量追踪状态，避免重复 start/stop。

---

## 架构思考：展示层与逻辑层分离

`query()` 只负责产生事件，不关心如何展示。
`rich_agent.py` 决定如何展示（spinner、颜色、格式）。

好处：未来可以换成 Web UI、写入日志文件，`query()` 完全不需要改：

```python
# 终端展示（本节）
async for chunk in query(...):
    if chunk.startswith("\x00TOOL:"):
        status.start()

# Web UI（未来）
async for chunk in query(...):
    if chunk.startswith("\x00TOOL:"):
        await websocket.send({"type": "tool_start", ...})

# 日志文件（未来）
async for chunk in query(...):
    if chunk.startswith("\x00TOOL:"):
        logger.info("tool_start: %s", ...)
```

---

## 本课相对上一课的变更

| 新增内容 | 位置 |
|---------|------|
| `\x00TOOL:` / `\x00DONE:` 事件协议 yield | `query()` 工具调用前后 |
| `_tool_summary()` 生成工具摘要 | 新增函数 |
| `rich.Status` spinner 手动 start/stop | `main()` async for 循环 |
| `console = Console()` 替换 `print()` | 全局 |

第 11 课的 `ToolUseContext`、`is_error`、权限系统**原样保留，无改动**。

## 运行

```bash
pip install rich
python3 rich_agent.py
# 输入「列出当前目录的文件」
# 应看到：⠋ bash(ls) → ✓ bash(ls)
```

## 作业

修改 `_tool_summary()`，让 `file_write` 显示写入的前20个字符内容预览，例如：
`file_write(hello.py) [3 lines] "print('hello world')..."`
