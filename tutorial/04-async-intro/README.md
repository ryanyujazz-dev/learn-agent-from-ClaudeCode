# Lesson 4 — async/await 入门

## 本节新概念

**async/await**：让多个函数同时推进，而不是一个做完再做下一个。

本课分 2 个文件，按顺序学。

---

## 为什么需要 async？

从第 6 课开始，agent 需要**执行 bash 命令、读写文件**——这些操作都要等待。如果用同步写法，执行一条命令时整个程序会卡住，无法同时处理流式输出和工具调用。async 是后续所有课程的基础。

## 核心理解：不是暂停，是切换

`await` 不是"停下来等"，而是"切换去干别的"。

想象一个厨师，按下电饭煲后不会站着等，而是转身去洗菜切菜。厨师一直在工作，只是**在不同任务之间切换**。

```
厨师的时间线：
按电饭煲 → 洗菜 → 切菜 → 汤下锅 → 电饭煲响了 → 盛饭
         ────────────────────────
         这段时间在干别的活，没有闲着
```

| 关键字 | 作用 | 厨师类比 |
|--------|------|---------|
| `async def` | 声明这个函数里有需要等待的地方 | 这道菜有需要等锅开的步骤 |
| `await` | 标记等待的地点，切换去执行其他函数 | 按下电饭煲，转身去切菜 |
| `asyncio.gather()` | 注册多个函数，在它们之间来回切换 | 同时管理好几道菜 |

**同步 vs 异步的区别**：

- 同步：`time.sleep(2)` — 厨师站着等 2 秒，什么都不干
- 异步：`await asyncio.sleep(2)` — 厨师去干别的，2 秒后回来继续

---

## 文件 1：`01_async_basics.py` — async 基础语法

不需要 API Key，纯本地运行。

```bash
python3 01_async_basics.py
```

你会看到两种做饭方式：

**同步（串行）**：先煮饭 2 秒，再煲汤 3 秒，总共 5 秒。
**异步（并发）**：煮饭和煲汤同时推进，总共 3 秒。

### 语法对照

| 同步 | 异步 | 说明 |
|------|------|------|
| `def foo():` | `async def foo():` | 定义函数，加个 `async` |
| `foo()` | `await foo()` | 调用函数，加个 `await` |
| `time.sleep(2)` | `await asyncio.sleep(2)` | 等待，异步版本在等待时去干别的 |
| 直接调用 | `asyncio.run(main())` | 异步函数的启动入口 |
| — | `asyncio.gather(a, b)` | 同时推进多个异步任务 |

---

## 文件 2：`02_async_llm.py` — async 在 LLM 场景下的真实价值

把 async 用到实际的 LLM 调用上，串行和并发对比：

- 串行：问 LLM 两个问题，一个问完再问下一个
- 并发：用 `asyncio.gather()` 同时发两个请求

```bash
python3 02_async_llm.py
```

你会看到耗时差距——并发版本接近减半。

### 同步 LLM vs 异步 LLM

```python
# 同步（Lesson 1-3 用的）
from openai import OpenAI
response = client.chat.completions.create(...)

# 异步（本课起的写法，只有两处不同）
from openai import AsyncOpenAI          # ① OpenAI → AsyncOpenAI
response = await client.chat.completions.create(...)  # ② 前面加 await
```

就这两处改动。后续课程（第 5 课起）统一使用 `AsyncOpenAI`。

---

## 两文件递进总结

| 文件 | 新增概念 | 需要 API Key |
|------|---------|-------------|
| `01_async_basics.py` | `async def`、`await`、`asyncio.run()`、`asyncio.gather()` | 不需要 |
| `02_async_llm.py` | `AsyncOpenAI`、并发 LLM 请求 | 需要 |

---

## 文件 3：`03_multi_agent.py` — 多 Agent 协作

这是并发 LLM 的**真实落地场景**：一段代码同时交给两个不同角色的 Agent 审查。

```bash
python3 03_multi_agent.py
```

- **代码审查员**：检查可读性、性能、最佳实践
- **安全审查员**：检查 SQL 注入、敏感信息泄露

两个审查同时进行，耗时接近单次审查，而不是累加。

### 核心代码

```python
# 同一个 agent_review 函数，不同的 system_prompt = 不同的 Agent 角色
code_review, security_review = await asyncio.gather(
    agent_review("代码审查员", code_reviewer_prompt, CODE),
    agent_review("安全审查员", security_reviewer_prompt, CODE),
)
```

关键发现：**一个 Agent = 一个 system prompt + 一次 LLM 调用**。多 Agent 协作的本质就是多个 LLM 调用并发执行。

### 这个模式可以扩展到

| 场景 | Agent A | Agent B |
|------|---------|---------|
| 代码审查 | 质量审查员 | 安全审查员 |
| 文档处理 | 中文翻译 | 摘要生成 |
| 学习辅助 | 概念解释员 | 出题测验员 |
| 产品设计 | 用户体验评审 | 技术可行性评审 |

---

## 三文件递进总结

| 文件 | 新增概念 | 需要 API Key |
|------|---------|-------------|
| `01_async_basics.py` | `async def`、`await`、`asyncio.gather()` | 不需要 |
| `02_async_llm.py` | `AsyncOpenAI`、并发 LLM 请求 | 需要 |
| `03_multi_agent.py` | 多 Agent 角色、system prompt 定义角色 | 需要 |

## 作业

1. 修改 `01_async_basics.py`，再加一个"炒菜"任务（等待 1.5 秒），观察三个并发任务的总耗时。
2. 修改 `03_multi_agent.py`，新增第三个 Agent（比如"性能优化建议员"），三个 Agent 同时审查。
