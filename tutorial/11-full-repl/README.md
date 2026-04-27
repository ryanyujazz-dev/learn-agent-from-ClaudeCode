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

## 作业

对比本文件与项目根目录的 `main.py`，找出它们的相同点和不同点。

