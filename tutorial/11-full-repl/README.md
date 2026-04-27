# Lesson 11 — 完整 REPL

## 本节新概念

**ToolUseContext 依赖注入 + is_error 信号**：对齐原版 claude-code 的架构。

## readline

```python
import readline  # 只需 import，自动启用上下键翻历史、左右键移动光标
```

## ToolUseContext — 依赖注入容器

之前每个工具的 `call()` 都接受 `cwd`、`auto` 等散乱参数。原版用一个 dataclass 打包：

```python
@dataclass
class ToolUseContext:
    tools: list
    cwd: str = ""
    permission_mode: str = "default"  # default | auto
```

好处：工具签名统一为 `call(args, context)`，新增参数不需要改所有工具。

## is_error — 告诉 LLM 工具失败了

```python
tool_msg = {
    "role": "tool",
    "tool_call_id": tc["id"],
    "content": result.data,
    **({"is_error": True} if result.error else {}),  # 失败时加标记
}
```

LLM 看到 `is_error: True` 会知道工具执行失败，可以调整策略（比如换一种命令）。
如果只把错误信息放在 `content` 里，LLM 需要自己解析文字才能判断是否出错。

## 完整功能清单

| 功能 | 来自 |
|------|------|
| 流式输出 | Lesson 2 |
| 多轮对话 | Lesson 3 |
| async/await | Lesson 4 |
| 工具系统 | Lesson 5 |
| Agentic Loop | Lesson 6 |
| BashTool + FileReadTool + FileWriteTool | Lesson 7 |
| 超时 + 重试 + cwd 追踪 | Lesson 8 |
| 权限检查 | Lesson 9 |
| CLAUDE.md + 会话持久化 | Lesson 10 |
| ToolUseContext + is_error + readline | Lesson 11 |

## 运行

```bash
python3 main.py           # 新会话
python3 main.py --resume  # 恢复上次会话
python3 main.py --auto    # 自动允许所有工具
```

## 架构思考：ToolUseContext 解决了什么问题

**没有它时**，每次给工具加一个新参数，所有工具签名都要改：

```python
# Lesson 7：call(args, cwd)
# Lesson 8：call(args, cwd)  ← 超时在 BashTool 内部硬编码
# 如果要让调用方控制超时：call(args, cwd, timeout)  ← 所有工具都要改
# 再加权限模式：call(args, cwd, timeout, auto)  ← 再改一遍
```

**有了它**，context 是一个容器，随时可以加字段，工具签名永远不变：

```python
call(args, context)  # 永远是这个签名

# 加 timeout：context.timeout = 30
# 加权限模式：context.permission_mode = "auto"
# 加任何东西：context.xxx = ...
```

这是**依赖注入**模式的核心价值：把"变化的部分"封装进容器，稳定接口。

## 作业

对比本文件与项目根目录的 `main.py`，找出它们的相同点和不同点。

