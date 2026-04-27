# mini-claude

一个用 Python 从零开始学习搭建 AI Coding Agent的教程，复刻了 claude-code 的核心架构。

这个项目有两个部分：一个**可以真正运行的 mini-claude**，以及一套**12节课的教程**，带你一步步理解它是怎么做出来的。

---

## 为什么做这个？

claude-code 是目前最好用的 AI 编程助手之一，但它是 TypeScript 写的，源码对很多人来说有门槛。

这个项目的目标很简单：**用最少的 Python 代码，把 claude-code 的核心思想讲清楚**。

不是玩具，是真的能用的东西——能执行 bash 命令、读写文件、记住上下文、拦截危险操作。代码量控制在可以一口气读完的范围内。

---

## 快速开始

推荐把 mini-claude 安装成一个命令，然后在你想操作的项目目录里运行它。

### 从 GitHub 安装

```bash
# 推荐：作为独立 CLI 安装
pipx install git+https://github.com/ryanyujazz-dev/learn-agent-from-ClaudeCode.git

# 进入你真正想让 mini-claude 操作的项目
cd /path/to/your-project
mini-claude
```

### 本地开发安装

```bash
# 1. 克隆并进入 mini-claude 仓库
git clone https://github.com/ryanyujazz-dev/learn-agent-from-ClaudeCode.git
cd claude_code_ran

# 2. 安装为本地可编辑命令
pip install -e .

# 3. 去你想操作的项目里运行
cd /path/to/your-project
mini-claude

# 恢复上次会话
mini-claude --resume

# 跳过所有权限确认
mini-claude --auto
```

首次运行时，程序会自动引导你输入 API 配置：

```
欢迎使用 mini-claude！首次运行需要配置 LLM 接口。
API Base URL（回车使用默认 https://open.bigmodel.cn/api/paas/v4/）:
API Key: sk-xxx
模型名称（回车使用默认 glm-5.1）:
配置已保存到 ~/.mini-claude/config.json
```

配置保存在 `~/.mini-claude/config.json`，不在项目目录内，不会被提交到 git。支持任何 OpenAI 兼容接口（ZhipuAI、OpenAI、DeepSeek、Ollama 等）。

如果只是临时从源码目录运行，也可以继续使用：

```bash
python main.py
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
| `main.py` | 兼容入口，转发到 `mini_claude.main:cli` | `src/cli.ts` |
| `setup.py` | Python 包配置，生成 `mini-claude` 命令 | - |
| `mini_claude/main.py` | REPL 入口，rich spinner 状态展示 | `src/cli.ts` |
| `mini_claude/query.py` | Agentic loop，流式输出，工具分发，重试 | `src/query.ts` |
| `mini_claude/tool.py` | Tool ABC，ToolUseContext，权限检查 | `src/Tool.ts` |
| `mini_claude/tools/` | BashTool, FileReadTool, FileWriteTool, GlobTool, GrepTool | `src/tools/` |
| `mini_claude/memory/` | CLAUDE.md 注入，会话持久化 + 归档 | `src/memdir/` |
| `mini_claude/security/` | 危险命令拦截，路径越界检测，持久化规则 | `src/tools/BashTool/bash*.ts` |

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

默认使用 [ZhipuAI](https://open.bigmodel.cn/) GLM-5.1，通过 OpenAI 兼容接口调用。

申请 API Key：https://open.bigmodel.cn/

如果你想换成 OpenAI、DeepSeek、Ollama 或其他兼容接口，首次运行时填写对应的 `base_url`、`api_key` 和 `model` 即可。配置会保存到 `~/.mini-claude/config.json`。

---

## 这个项目不是什么

- 不是 claude-code 的完整复刻（原版有更多工具、更复杂的权限模型、更完善的错误处理）
- 不是生产可用的工具（没有并发工具调用、没有 context window 管理）
- 不是教你怎么用 claude-code（那个直接看官方文档）

它是一个**学习用的参考实现**，目标是让你读完之后能理解 AI Agent 的核心机制，然后自己动手写一个。
