# Lesson 7 — 真实工具

## 本节新概念

**主概念：asyncio.create_subprocess_shell** — 异步执行 shell 命令，不阻塞事件循环。

**附带概念：is_read_only()** — 工具的只读标记，为 Lesson 9 的权限系统做铺垫。现在只是定义，还不生效。

## 为什么用异步 subprocess？

```python
# 同步（会阻塞）
import subprocess
result = subprocess.run("sleep 3", shell=True)  # 卡住 3 秒，期间什么都做不了

# 异步（不阻塞）
proc = await asyncio.create_subprocess_shell("sleep 3", ...)
await proc.communicate()  # 等待时可以处理其他任务
```

## BashTool 核心逻辑

```python
proc = await asyncio.create_subprocess_shell(
    command,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
stdout, stderr = await proc.communicate()
```

- `PIPE` 表示捕获输出（不打印到屏幕）
- `proc.communicate()` 等待命令结束，返回 stdout 和 stderr

## FileReadTool

```python
with open(path, "r", encoding="utf-8") as f:
    return ToolResult(data=f.read())
```

简单的文件读取，但要注意路径安全（Lesson 9 讲）。

## is_read_only() 是什么？

代码里有一个 `is_read_only()` 方法：

```python
def is_read_only(self, args: dict) -> bool:
    return True  # FileReadTool 只读，不需要权限确认
```

**作用**：告诉权限系统"这个工具只读，不需要询问用户"。
- `FileReadTool.is_read_only()` 返回 `True` → 直接执行，不弹权限提示
- `BashTool.is_read_only()` 返回 `False` → 需要权限检查（Lesson 9 实现）

现在这个方法还没有被调用，Lesson 9 会把它接入权限系统。

## 运行

```bash
python3 main.py
# 试着说：「列出当前目录的文件」或「读取 /etc/hostname」
```

## 本课相对上一课的变更

| 新增内容 | 位置 |
|---------|------|
| `BashTool`：用 `asyncio.create_subprocess_shell` 执行真实命令 | `BashTool.call()` |
| `FileReadTool`：读取文件，`is_read_only()` 返回 `True` | `FileReadTool` 类 |
| `EchoTool` 替换为真实工具 | `TOOLS` 列表 |

第 6 课的 `query()` agentic loop 逻辑**原样保留，无改动**。

## 作业

实现 `FileWriteTool`：接受 `path` 和 `content`，把内容写入文件。
