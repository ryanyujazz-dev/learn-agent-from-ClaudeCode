# Lesson 10 — 记忆系统

## 本节新概念

**CLAUDE.md 注入 + JSON 会话持久化**：让 agent 跨会话记住项目信息。

## 记忆的本质

LLM 是无状态的——每次 API 调用都是全新的，它不记得上一次对话。

所有"记忆"都是我们在调用前塞进 `messages` 的内容。记忆有两个维度：

| 维度 | 问题 | 解决方案 |
|------|------|---------|
| 会话内记忆 | LLM 记得这次对话说了什么 | `messages` 列表（Lesson 3 已解决） |
| 跨会话记忆 | 下次启动还记得项目背景 | CLAUDE.md + latest.json（本节） |

两种记忆的本质区别：
- **项目记忆（CLAUDE.md）**：静态知识，每次启动都注入，内容不变
- **会话记忆（latest.json）**：动态历史，可选恢复，内容随对话增长

还有一个隐性限制：context window。`messages` 列表不能无限增长，超过模型的 context window 就会报错。生产级 agent 需要截断或压缩历史（mini-claude 暂不处理）。

## 两种记忆

### 1. 项目记忆（CLAUDE.md）

agent 启动时，向上遍历目录，找到 `CLAUDE.md` 文件，注入到 system prompt：

```
当前目录 → 父目录 → 父父目录 → ... → 根目录
```

这样无论你在哪个子目录运行 agent，它都能读到项目说明。

### 2. 会话记忆（latest.json）

把 `messages` 列表序列化成 JSON，下次启动时用 `--resume` 恢复：

```bash
python3 main.py           # 新会话
python3 main.py --resume  # 恢复上次会话
```

## 核心代码

```python
def load_claude_md(start_dir: str) -> str:
    """向上遍历目录，收集所有 CLAUDE.md 内容"""
    parts = []
    path = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(path, "CLAUDE.md")
        if os.path.exists(candidate):
            parts.append(open(candidate).read())
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return "\n\n".join(parts)
```

## 运行

```bash
# 1. 在当前目录创建 CLAUDE.md
echo "这是一个教程项目，用于学习 mini-claude。" > CLAUDE.md

# 2. 运行 agent，它会读到 CLAUDE.md
python3 main.py

# 3. 退出后恢复会话
python3 main.py --resume
```

## 本课相对上一课的变更

| 新增内容 | 位置 |
|---------|------|
| `load_claude_md()` 向上遍历目录收集 CLAUDE.md | 新增函数 |
| `save_session()` / `load_session()` JSON 持久化 | 新增函数 |
| `query()` 新增 `system_prompt` 参数，分离 `api_messages` | `query()` 签名 |
| `--resume` 命令行参数支持 | `main()` |
| 每轮结束后自动 `save_session()` | `main()` while 循环 |

第 9 课的权限系统**原样保留，无改动**。

## 作业

在 `CLAUDE.md` 里写上你的项目说明，观察 agent 的回答是否有变化。

## 重要设计：为什么要分 messages 和 api_messages？

```python
# messages：持久化存储（不含 system prompt）
messages = []

# api_messages：发给 API 的完整列表（含 system prompt）
api_messages = [{"role": "system", "content": claude_md}] + messages
```

**原因**：`system` 消息不应该存入 `latest.json`。
如果存了，`--resume` 时会重复注入 system prompt，导致 LLM 收到两份相同的项目说明。

## 重要设计：每轮自动保存

```python
async for text in query(...):
    print(text, end="", flush=True)
print()
save_session(messages)  # 每轮结束后立即保存
```

只在 `/quit` 时保存的问题：用户按 Ctrl+C 时，整轮对话丢失。
每轮保存确保任何退出方式都不丢数据。
