# Lesson 10 — 上下文工程

## 本节新概念

**CLAUDE.md 注入 + JSON 会话持久化 + RAG + Skills**：所有"往上下文里塞什么"的问题。

## 上下文的本质

LLM 是无状态的——每次 API 调用都是全新的，它不记得上一次对话。

所有"记忆"都是我们在调用前塞进 `messages` 的内容。本课从四个维度解决这个问题：

| 维度 | 解决的问题 | 本课对应 |
|------|------|---------|
| 会话内记忆 | LLM 记得这次对话说了什么 | `messages` 列表（Lesson 3 已解决） |
| 项目记忆 | 每次启动都知道项目背景 | CLAUDE.md 注入（File 1） |
| 会话持久化 | 下次启动还记得上次对话 | latest.json（File 1） |
| 外部知识 | LLM 不知道的额外信息 | RAG（File 3） |
| 行为规范 | LLM 怎么完成某个任务 | Skills（File 4） |

还有一个隐性限制：context window。`messages` 列表不能无限增长，超过模型的 context window 就会报错。File 2 用滑动窗口解决这个问题。

---

## 文件 1：`01_memory_agent.py` — 项目记忆 + 会话持久化

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

### 核心代码

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

### 运行

```bash
# 1. 在当前目录创建 CLAUDE.md
echo "这是一个教程项目，用于学习 mini-claude。" > CLAUDE.md

# 2. 运行 agent，它会读到 CLAUDE.md
python3 01_memory_agent.py

# 3. 退出后恢复会话
python3 01_memory_agent.py --resume
```

### 重要设计：为什么要分 messages 和 api_messages？

```python
# messages：持久化存储（不含 system prompt）
messages = []

# api_messages：发给 API 的完整列表（含 system prompt）
api_messages = [{"role": "system", "content": claude_md}] + messages
```

**原因**：`system` 消息不应该存入 `latest.json`。
如果存了，`--resume` 时会重复注入 system prompt，导致 LLM 收到两份相同的项目说明。

### 重要设计：每轮自动保存

```python
async for text in query(...):
    print(text, end="", flush=True)
print()
save_session(messages)  # 每轮结束后立即保存
```

只在 `/quit` 时保存的问题：用户按 Ctrl+C 时，整轮对话丢失。
每轮保存确保任何退出方式都不丢数据。

---

## 文件 2：`02_sliding_window.py` — 滑动窗口

```bash
python3 02_sliding_window.py
```

当 messages 过长时，只保留 system prompt + 最近 K 轮对话，丢弃更早的消息。

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

| | File 1 | File 2 |
|---|--------|--------|
| messages 增长 | 无限增长 | 完整保存，但发送时裁剪 |
| 超长对话 | 会报错（超 context window） | 安全（窗口保护） |
| 早期记忆 | 完整保留 | 被裁剪丢弃 |

---

## 文件 3：`03_simple_rag.py` — 简易 Pipeline RAG

```bash
python3 03_simple_rag.py
# 试试：「agentic loop 是怎么工作的？」或「流式输出的参数怎么拼？」
```

CLAUDE.md 是静态知识——内容固定，每次启动都一样。但有时候你需要动态知识——根据用户的问题，实时检索相关信息。

这就是 **RAG**（Retrieval-Augmented Generation，检索增强生成）：**先检索相关信息，再塞进上下文，让 LLM 基于这些信息生成回复**。

### 两种主流 RAG 模式

**1. Pipeline RAG（管道式）** — 每次提问前自动检索

系统自动检索相关内容注入上下文，模型不知道这步的存在：

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

### File 3 的核心代码

```python
# 1. 检索：根据用户问题，从知识库找到相关文档
results = search_knowledge_base(user_input, top_k=2)

# 2. 拼接：把检索到的文档格式化成文本
context_text = "\n\n".join(f"【参考文档 {i}】{doc['title']}\n{doc['content']}" for i, doc in enumerate(results, 1))

# 3. 注入：把检索结果放到 system prompt 里
system_prompt = f"以下是知识库中与用户问题相关的参考文档：\n\n{context_text}\n\n请基于以上参考文档回答。"
```

这里用关键词匹配做检索（简化版，不需要向量数据库）。
生产环境的 RAG 通常用向量数据库（如 Chroma、FAISS）做语义检索，原理一样，只是"怎么找到相关内容"更精确。

---

## 文件 4：`04_skills.py` — Skills（操作手册）

```bash
python3 04_skills.py
# 先输入 /skill code_review 加载 skill，然后给一段代码让它审查
```

前面学了 Tools 和 RAG，它们解决不同的问题：

| 层 | 解决的问题 | 对应课程 |
|---|---|---|
| Tools | LLM 能**做什么**（执行动作） | 第 5-7 课 |
| 记忆 / RAG | LLM **知道什么**（知识注入） | 第 10 课 |
| Skills | LLM **怎么做**（行为规范） | 本文件 |

如果 Tools 是锤子、螺丝刀这样的**单一工具**，那 Skills 就是一份**操作手册**——告诉模型完成某类任务时按什么步骤、用什么工具、遵循什么标准。

### Skills 和 Tools 的区别

**Tools** 有标准协议（OpenAI Tool Calling）：

```
注册：tools=[{name: "bash", schema: {...}}, ...]    ← 列表给模型
调用：模型输出 tool_calls: [{name: "bash", args}]   ← 结构化响应
执行：代码执行工具，结果回喂给模型
```

**Skills** 没有标准协议，靠 prompt 注入：

```
注册：系统提示里列出可用的 skill 名字（如 "/code_review, /explain_code"）
调用：用户输入 /skill code_review → 程序匹配 → 把完整 md 内容注入上下文
执行：模型读到了完整操作手册，自然地按步骤执行
```

核心区别：

| | Tools | Skills |
|---|---|---|
| 注册方式 | API 参数 `tools=[...]` | 系统提示里列名字 |
| 调用方式 | 模型输出 `tool_calls`（结构化） | 用户输入 `/xxx` 或程序自动触发 |
| 模型看到什么 | 名字 + 参数 Schema | 完整的操作手册全文 |
| 有无协议 | OpenAI Tool Calling 标准 | 没有标准，各家自己实现 |

模型并不是像调用工具那样"调用"一个 skill，而是被"塞了一份操作手册"，然后自然地照着做。

### File 4 的核心代码

```python
# 1. 启动时扫描 skills 目录，发现所有可用的 skill
skills = list_skills()  # {"code_review": "skills/code_review.md", ...}

# 2. 用户选择一个 skill
active_skill = "code_review"

# 3. 加载 skill 的完整内容（操作手册全文）
skill_content = load_skill(active_skill, skills)

# 4. 注入到 system prompt——这就是 Skills 的本质
system_prompt = f"请严格按照以下操作手册执行任务：\n\n{skill_content}"
```

### 三者关系

```
Skill（操作手册）："做 code review 要分这 4 步"
  ├── 第 1 步用了 GrepTool（工具）
  ├── 第 2 步用了 FileReadTool（工具）
  ├── 第 3 步依赖项目代码规范（记忆 / CLAUDE.md）
  └── 第 4 步用了 EditTool（工具）
```

Skill 把 Tools、记忆、行为规范组合在一起，完成一个完整任务。这也是为什么成熟的 Agent 产品（如 Claude Code）会同时具备这三个层面。

### 自定义 Skill

在 `skills/` 目录下创建新的 `.md` 文件，重启程序就能用。比如创建 `skills/translate.md`：

```markdown
# Translation Skill
1. 读取用户给的文本
2. 翻译成目标语言（用户指定）
3. 保持原文格式
```

然后运行 `python3 04_skills.py`，输入 `/skill translate` 即可使用。

---

## 本课相对上一课的变更

| 新增内容 | 文件 |
|---------|------|
| `load_claude_md()` 向上遍历目录收集 CLAUDE.md | File 1 |
| `save_session()` / `load_session()` JSON 持久化 | File 1 |
| `query()` 新增 `system_prompt` 参数，分离 `api_messages` | File 1 |
| `--resume` 命令行参数支持 | File 1 |
| 每轮结束后自动 `save_session()` | File 1 |
| `apply_sliding_window()` 滑动窗口裁剪 | File 2 |
| `search_knowledge_base()` 关键词检索 | File 3 |
| 检索结果注入 system_prompt | File 3 |
| `list_skills()` / `load_skill()` skill 加载 | File 4 |
| skill 内容注入 system_prompt | File 4 |
| `skills/` 目录 + 两个示例 skill 文件 | File 4 |

> **注意**：为聚焦上下文工程概念，本课仅保留 `BashTool`，未包含第 8-9 课的超时、重试、cwd 追踪和权限系统。所有功能会在第 11-12 课合齐。

## 作业

1. 在 `CLAUDE.md` 里写上你的项目说明，运行 File 1，观察 agent 的回答是否有变化。
2. 在 `skills/` 目录下创建一个新的 skill（比如"代码翻译"），运行 File 4 试试效果。

## 下一课预告

本课的 agent 已经有了记忆、RAG、Skills，但它还缺少一个统一的依赖注入容器（`ToolUseContext`）来把 cwd、权限模式等参数传给工具。第 11 课引入 `ToolUseContext`，把所有功能组装成完整的 REPL。
