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
python3 01_memory_agent.py           # 新会话
python3 01_memory_agent.py --resume  # 恢复上次会话
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
python3 01_memory_agent.py

# 3. 退出后恢复会话
python3 01_memory_agent.py --resume
```

## 本课相对上一课的变更

| 新增内容 | 位置 |
|---------|------|
| `load_claude_md()` 向上遍历目录收集 CLAUDE.md | 新增函数 |
| `save_session()` / `load_session()` JSON 持久化 | 新增函数 |
| `query()` 新增 `system_prompt` 参数，分离 `api_messages` | `query()` 签名 |
| `--resume` 命令行参数支持 | `main()` |
| 每轮结束后自动 `save_session()` | `main()` while 循环 |

> **注意**：为聚焦记忆概念，本课仅保留 `BashTool`，未包含第 8-9 课的超时、重试、cwd 追踪和权限系统。所有功能会在第 11-12 课合齐。

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

## 行业概念：RAG（检索增强生成）

本课的 CLAUDE.md 注入，其实就是一种简化版的 **RAG**（Retrieval-Augmented Generation，检索增强生成）。

LLM 的知识来自训练数据，它不知道你的项目文档、公司内部知识库、最新的新闻。RAG 的思路是：**先检索相关信息，再塞进上下文，让 LLM 基于这些信息生成回复**。

### 两种主流模式

**1. Pipeline RAG（管道式）** — 每次提问前自动检索

不走工具调用，系统自动检索相关内容注入上下文，模型不知道这步的存在：

```
用户提问 → 系统自动检索知识库 → [检索结果] + [用户问题] 一起发给 LLM → LLM 生成回复
```

CLAUDE.md 就是这种模式：启动时自动收集文件，注入 system prompt，LLM 不需要主动去"查"。

**2. Agentic RAG（工具式）** — 模型自己决定什么时候查

把检索注册为工具，由模型判断是否需要调用：

```
用户提问 → LLM 判断需要查资料 → 调用 search_knowledge_base 工具 → 拿到结果 → 基于结果生成回复
```

这跟第 6 课学的 tool calling 完全一样，只是工具从"查天气"变成了"查知识库"。

### 对比

| | Pipeline RAG | Agentic RAG |
|---|---|---|
| 谁决定检索 | 系统（每次都检） | 模型自己（按需检索） |
| 对应本课概念 | CLAUDE.md 自动注入 | 第 6 课 tool calling |
| 优点 | 简单可靠，不遗漏 | 按需检索，省 token |
| 缺点 | 每次都检索，浪费 token | 模型可能忘记查 |

两者经常结合使用：系统层面自动注入基础信息（Pipeline），同时提供检索工具让模型按需深入查询（Agentic）。

---

## 进阶思考：记忆压缩

### 问题：messages 会无限增长

`messages` 列表每轮都在追加，对话越长，发给 API 的数据越大。超过模型的 **context window**（token 上限），API 就会报错。

三种压缩策略：

| 策略 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **截断** | 只保留最近 N 条 | 最简单 | 直接丢失早期记忆 |
| **摘要压缩** | 用 LLM 总结历史，用摘要替代原文 | 保留关键信息 | 需要额外 API 调用 |
| **滑动窗口** | 保留 system + 最近 K 轮 | 平衡简单与效果 | 早期细节会丢失 |

### 运行滑动窗口示例

```bash
python3 02_sliding_window.py
```

与 `01_memory_agent.py` 的区别：

```python
# 滑动窗口：超过阈值时，保留 system prompt + 最近 20 条消息
if len(api_messages) > MAX_MESSAGES + 1:
    system = [api_messages[0]]
    return system + api_messages[-MAX_MESSAGES:]
```

试着连续对话 10 轮以上，观察：
- `messages` 列表持续增长（完整历史被保存）
- 发给 API 的消息数被控制在 20 条以内（滑动窗口裁剪）
- AI 仍然能正常对话，但记不住 10 轮之前的细节

| | `01_memory_agent.py` | `02_sliding_window.py` |
|---|---------------------|----------------------|
| messages 增长 | 无限增长 | 完整保存，但发送时裁剪 |
| 超长对话 | 会报错（超 context window） | 安全（窗口保护） |
| 早期记忆 | 完整保留 | 被裁剪丢弃 |

