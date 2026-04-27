# Lesson 10 — 完整 REPL

## 本节新概念

**readline + sys.argv + 模块整合**：把前9课的所有模块组合成完整的 mini-claude。

## readline

```python
import readline  # 只需 import，自动启用上下键翻历史、左右键移动光标
```

## sys.argv

```python
import sys
# python3 main.py --resume --auto
# sys.argv = ["main.py", "--resume", "--auto"]
resume = "--resume" in sys.argv
auto = "--auto" in sys.argv
```

## 完整功能清单

本节 `main.py` 集成了所有前9课的内容：

| 功能 | 来自 |
|------|------|
| 流式输出 | Lesson 2 |
| 多轮对话 | Lesson 3 |
| async/await | Lesson 4 |
| 工具系统 | Lesson 5 |
| Agentic Loop | Lesson 6 |
| BashTool + FileReadTool + FileWriteTool | Lesson 7 |
| 权限检查 | Lesson 8 |
| CLAUDE.md + 会话持久化 | Lesson 9 |
| readline REPL | Lesson 10 |

## 运行

```bash
python3 main.py           # 新会话
python3 main.py --resume  # 恢复上次会话
python3 main.py --auto    # 自动允许所有工具（bypass 模式）
```

## 作业

对比本文件与项目根目录的 `main.py`，找出它们的相同点和不同点。
