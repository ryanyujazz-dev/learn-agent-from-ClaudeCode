# mini-claude

一个用 Python 从零手写的 AI Agent，复刻了 claude-code 的核心架构。

这个项目有两个部分：一个**可以真正运行的 mini-claude**，以及一套**12节课的教程**，带你一步步理解它是怎么做出来的。

---

## 为什么做这个？

claude-code 是目前最好用的 AI 编程助手之一，但它是 TypeScript 写的，源码对很多人来说有门槛。

这个项目的目标很简单：**用最少的 Python 代码，把 claude-code 的核心思想讲清楚**。

不是玩具，是真的能用的东西——能执行 bash 命令、读写文件、记住上下文、拦截危险操作。代码量控制在可以一口气读完的范围内。

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key（使用 ZhipuAI GLM-5.1）
export ZHIPUAI_API_KEY="你的key"

# 3. 运行
python main.py

# 恢复上次会话
python main.py --resume

# 跳过所有权限确认
python main.py --auto
```

运行后你会看到：

```
mini-claude (glm-5.1) — type 'exit' to quit

>>> 帮我列出当前目录的文件
⠋ bash(ls -la)
✓ bash(ls -la)
当前目录包含以下文件：...
```

---

## 架构

```
┌─────────────────────────────────────┐
│  REPL (main.py)                     │  用户交互层
├─────────────────────────────────────┤
│  Agentic Loop (query.py)            │  核心循环层
├─────────────────────────────────────┤
│  Tool System (tool.py + tools/)     │  工具层
├─────────────────────────────────────┤
│  Memory (memory/)                   │  记忆层
├─────────────────────────────────────┤
│  Security (security/)               │  安全层
└─────────────────────────────────────┘
```

| 文件/目录 | 职责 | 对应原版 |
|-----------|------|---------|
| `main.py` | REPL 入口，rich spinner 状态展示 | `src/cli.ts` |
| `query.py` | Agentic loop，流式输出，工具分发，重试 | `src/query.ts` |
| `tool.py` | Tool ABC，ToolUseContext，权限检查 | `src/Tool.ts` |
| `tools/` | BashTool, FileReadTool, FileWriteTool, GlobTool, GrepTool | `src/tools/` |
| `memory/` | CLAUDE.md 注入，会话持久化 + 归档 | `src/memdir/` |
| `security/` | 危险命令拦截，路径越界检测，持久化规则 | `src/tools/BashTool/bash*.ts` |

---

## 内置工具

| 工具 | 功能 |
|------|------|
| `bash` | 执行 shell 命令，追踪 cd 后的目录变化 |
| `file_read` | 读取文件，路径越界检测 |
| `file_write` | 写入文件，权限确认 |
| `glob` | 文件模式匹配 |
| `grep` | 内容搜索 |

---

## 12节课教程

如果你想理解这一切是怎么做出来的，`tutorial/` 目录有一套从零开始的课程：

| # | 主题 | 新概念 |
|---|------|--------|
| 1 | API 第一次调用 | openai SDK |
| 2 | 流式输出 | stream=True |
| 3 | 多轮对话 | messages 列表 + 完整格式 |
| 4 | 异步 | async/await + asyncio.gather |
| 5 | 工具设计 | ABC 抽象类 |
| 6 | Agentic Loop | while + tool dispatch |
| 7 | 真实工具 | subprocess + 文件读写 |
| 8 | 健壮性 | 超时 + 重试 + cwd 追踪 |
| 9 | 权限安全 | 正则拦截 + 持久化规则 |
| 10 | 记忆系统 | CLAUDE.md + 会话持久化 |
| 11 | 完整 REPL | ToolUseContext + is_error |
| 12 | 状态展示 | 事件协议 + rich spinner |

每节课都是独立可运行的单文件，只引入一个新概念。

完成12节课后，读 [`tutorial/architecture.md`](./tutorial/architecture.md)——它解释了每个架构决策背后的"为什么"，以及教程与根目录代码的差异对照表。

```bash
cd tutorial/01-api-first-call
python3 main.py
```

---

## LLM 后端

使用 [ZhipuAI](https://open.bigmodel.cn/) GLM-5.1，通过 OpenAI 兼容接口调用。

申请 API Key：https://open.bigmodel.cn/

如果你想换成 OpenAI 或其他兼容接口，修改 `query.py` 里的 `base_url` 和 `model` 即可。

---

## 这个项目不是什么

- 不是 claude-code 的完整复刻（原版有更多工具、更复杂的权限模型、更完善的错误处理）
- 不是生产可用的工具（没有并发工具调用、没有 context window 管理）
- 不是教你怎么用 claude-code（那个直接看官方文档）

它是一个**学习用的参考实现**，目标是让你读完之后能理解 AI Agent 的核心机制，然后自己动手写一个。
