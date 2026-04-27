# Lesson 4 — async/await 入门

## 本节新概念

**async/await**：让程序在"等待"时可以去做别的事，而不是傻等。

## 类比理解

**同步**（之前的写法）：你去餐厅点餐，站在柜台前等厨师做完，才能去找座位。

**异步**（本节的写法）：你点完餐，拿到号码牌，先去找座位。号码叫到了再去取餐。

对 agent 来说：执行一个 bash 命令可能要等 3 秒，异步让我们在等待期间可以处理其他事情。

## 核心语法

```python
# 定义异步函数
async def chat():
    ...

# 在异步函数里"等待"一个耗时操作
reply = await some_async_function()

# 异步 for 循环（用于流式输出）
async for chunk in stream:
    ...

# 程序入口：运行异步函数
import asyncio
asyncio.run(chat())
```

## 本节代码

把 Lesson 3 改成异步版，**行为完全一样**，只是写法变了。

## 运行

```bash
python3 main.py
```

## asyncio.gather() — 并发的威力

异步真正的价值在于**同时做多件事**：

```python
import asyncio, time

async def slow_task(name, seconds):
    await asyncio.sleep(seconds)  # 模拟耗时操作
    return f"{name} 完成"

async def main():
    start = time.time()

    # 串行：总耗时 = 2 + 2 = 4 秒
    r1 = await slow_task("任务A", 2)
    r2 = await slow_task("任务B", 2)

    # 并发：总耗时 ≈ 2 秒（同时进行）
    r1, r2 = await asyncio.gather(
        slow_task("任务A", 2),
        slow_task("任务B", 2),
    )
    print(f"耗时: {time.time() - start:.1f}s")
```

## 作业

修改 `main.py`，在对话开始前用 `asyncio.gather()` 同时发两个不同问题给 LLM，打印两个回复，观察总耗时是否比串行快。
