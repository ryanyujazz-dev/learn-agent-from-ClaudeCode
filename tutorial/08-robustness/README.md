# Lesson 8 — 健壮性工程

## 本节新概念

三个让 agent 在真实环境中稳定运行的工程技巧。

## 1. 命令超时（asyncio.wait_for）

如果 agent 执行 `sleep 9999`，程序会永远卡住。用超时保护：

```python
try:
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(), timeout=30
    )
except asyncio.TimeoutError:
    proc.kill()
    return ToolResult(data="命令超时（30秒）", error=True)
```

## 2. API 重试（指数退避）

网络抖动会导致 API 偶发失败。重试策略：

```python
for attempt in range(3):
    try:
        return await client.chat.completions.create(...)
    except APIError as e:
        if attempt == 2 or e.status_code in (400, 401, 403):
            raise  # 不可恢复的错误，直接抛出
        await asyncio.sleep(2 ** attempt)  # 1s, 2s 后重试
```

- 400/401/403 是客户端错误，重试没有意义
- 500/503 是服务端临时错误，等待后重试

## 3. cd 命令的 cwd 追踪

问题：`cd /tmp` 执行后，下一条命令仍在原目录执行。

原因：每次 `create_subprocess_shell` 都是新进程，不继承上一次的目录。

解决：在命令末尾追加 `\npwd`，从输出最后一行读取新目录：

```python
full_cmd = command + "\npwd"
# 执行后，输出最后一行就是当前目录
lines = output.strip().splitlines()
new_cwd = lines[-1] if lines[-1].startswith("/") else cwd
```

## 运行

```bash
python3 main.py
# 试试：「cd /tmp 然后列出文件」→ 应在 /tmp 下列出
# 试试：「执行 sleep 60」→ 30秒后超时
```

## 架构思考：健壮性是生产级的门槛

这三个问题在开发环境几乎不会出现，但在真实使用中必然遇到：

- **没有超时**：用户让 agent 执行一条卡死的命令，整个程序永久挂起，只能强制杀进程
- **没有重试**：网络抖动（尤其是国内访问海外 API）导致对话中断，用户体验断裂
- **没有 cwd 追踪**：`cd /tmp` 执行成功，但下一条命令仍在原目录，agent 无法导航文件系统

这三个问题的共同特点：**功能测试通过，但生产环境必然暴露**。健壮性工程就是提前堵住这些洞。

## 作业

把超时时间改成 5 秒，执行 `sleep 3`（应成功）和 `sleep 10`（应超时），观察区别。
