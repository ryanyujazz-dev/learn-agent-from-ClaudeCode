# Lesson 4 — async/await 入门

## 本节新概念

**async/await**：让多个函数同时推进，而不是一个做完再做下一个。

本课分 3 个文件，每个只多一个新概念，按顺序学。

---

## 为什么需要 async？

从第 6 课开始，agent 需要**执行 bash 命令、读写文件**——这些操作都要等待。如果用同步写法，执行一条命令时整个程序会卡住。async 是后续所有课程的基础，现在切换是为了后面不再分心。

## 核心理解：不是暂停，是切换

很多人说 `await` 是"暂停"，但这个说法容易误导。

想象一个厨师，按下电饭煲后不会站着等，而是转身去洗菜切菜。厨师一直在工作，只是**在不同任务之间切换**。

```
厨师的时间线：
按电饭煲 → 洗菜 → 切菜 → 汤下锅 → 电饭煲响了 → 盛饭
         ────────────────────────
         这段时间在干别的活，没有闲着
```

`await` 就是这个"转身去干别的"的动作：

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

## 文件 2：`02_async_llm.py` — 用 async 调用 LLM

把 async 用到 LLM 调用上。和第 1 课的同步版对比：

```python
# 第 1 课（同步）
from openai import OpenAI
response = client.chat.completions.create(...)

# 本文件（异步）—— 只有两处不同
from openai import AsyncOpenAI          # ① OpenAI → AsyncOpenAI
response = await client.chat.completions.create(...)  # ② 前面加 await
```

就这两处改动，其余完全一样。没有流式、没有多轮，先把单次调用搞懂。

```bash
python3 02_async_llm.py
```

---

## 文件 3：`03_async_streaming.py` — async for 流式多轮

在文件 2 基础上加流式输出和多轮对话。和第 2/3 课的同步版对比：

```python
# 第 2 课（同步）
for chunk in stream:
    ...

# 本文件（异步）—— 只有一个关键字不同
async for chunk in stream:
    ...
```

`async for` 就是"异步版 for 循环"——每次迭代可能会暂停等待下一个 chunk，但暂停期间程序可以去干别的。

```bash
python3 03_async_streaming.py
```

---

## 三文件递进总结

| 文件 | 新增概念 | 需要 API Key |
|------|---------|-------------|
| `01_async_basics.py` | `async def`、`await`、`asyncio.run()`、`asyncio.gather()` | 不需要 |
| `02_async_llm.py` | `AsyncOpenAI`、`await` 等待 LLM | 需要 |
| `03_async_streaming.py` | `async for` 流式输出 | 需要 |

每个文件和前一文件的区别都只有一两行。

## 作业

1. 修改 `01_async_basics.py`，再加一个"炒菜"任务（等待 1.5 秒），观察三个并发任务的总耗时。
2. 修改 `02_async_llm.py`，用 `asyncio.gather()` 同时发两个不同问题，打印两个回复，观察总耗时。
