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

## 作业

思考：为什么 agent 需要异步？（提示：agent 调用工具时，工具执行需要时间）
