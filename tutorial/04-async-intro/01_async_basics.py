"""
Lesson 4 — 第 1 步：async/await 基础语法
新概念: async def, await, asyncio.sleep(), asyncio.run(), asyncio.gather()

不需要 API Key，纯本地运行。
目标：搞懂"同步串行"和"异步并发"的区别。
"""
import asyncio
import time


# ── 同步版本：一件事做完再做下一件 ────────────────────────────
def sync_cook():
    print("开始煮饭...")
    time.sleep(2)       # 同步等待，程序卡住 2 秒
    print("饭好了！")


def sync_soup():
    print("开始煲汤...")
    time.sleep(3)       # 同步等待，程序卡住 3 秒
    print("汤好了！")


print("=== 同步（串行）===")
start = time.time()
sync_cook()             # 先煮饭，2 秒
sync_soup()             # 再煲汤，3 秒
print(f"总耗时: {time.time() - start:.1f} 秒")
# 结果：2 + 3 = 5 秒


# ── 异步版本：两件事同时推进 ──────────────────────────────────
# async def — 声明这个函数里有需要等待的地方
# await — 标记等待的地点，切换去执行其他函数（不是傻等，是去干别的）
async def async_cook():
    print("开始煮饭...")
    await asyncio.sleep(2)  # 等待 2 秒，但程序会切换去执行 async_soup
    print("饭好了！")


async def async_soup():
    print("开始煲汤...")
    await asyncio.sleep(3)  # 等待 3 秒，程序会切换回来继续煮饭的逻辑
    print("汤好了！")


async def main():
    # asyncio.gather — 同时推进多个异步任务，在它们之间来回切换
    await asyncio.gather(async_cook(), async_soup())


print("\n=== 异步（并发）===")
start = time.time()

# asyncio.run — 启动异步函数的入口
asyncio.run(main())

print(f"总耗时: {time.time() - start:.1f} 秒")
# 结果：max(2, 3) = 3 秒（同时进行，取最长的）

print("\n--- 语法对照 ---")
print("普通函数:  def foo():       → 调用: foo()")
print("异步函数:  async def foo(): → 调用: await foo()")
print("普通等待:  time.sleep(2)    → 站着等，什么都干不了")
print("异步等待:  await asyncio.sleep(2) → 切换去干别的，到了再回来")
print("启动入口:  asyncio.run(main())   → 运行异步函数")
