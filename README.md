# mini-claude

**12 节课，用 Python 从零构建一个 AI Coding Agent。**

复刻 claude-code 的核心架构：Agentic Loop、Tool Calling、MCP、权限安全、记忆系统、Skills——每一层都用最少的代码讲清楚。

---

## 这个项目是什么

它有两个部分：

- **一套 12 节课的教程**（`tutorial/`）——从 10 行代码的 API 调用，一步步构建到完整的 AI Agent
- **一个可以运行的 mini-claude**（`mini_claude/`）——教程学完后，你能读懂这里的每一行

不需要 async 经验、不需要 AI Agent 知识、不需要 TypeScript。只要会 Python 基础语法（变量、函数、类、for 循环），就能学。

---

## 课程大纲

```
基础篇（1-4课）         核心篇（5-8课）           工程篇（9-12课）
┌──────────────┐    ┌──────────────┐     ┌──────────────┐
│ 1. API 调用   │    │ 5. 工具设计   │     │  9. 权限安全  │
│ 2. 流式输出   │───→│ 6. Agentic   │───→ │ 10. 上下文工程│
│ 3. 多轮对话   │    │    Loop      │     │ 11. 完整 REPL │
│ 4. async     │    │ 7. 真实工具   │     │ 12. 状态展示  │
└──────────────┘    │ 8. 健壮性     │     └──────────────┘
                    └──────────────┘
```

| # | 主题 | 你会学到 |
|---|------|---------|
| 1 | API 第一次调用 | openai SDK、环境变量 |
| 2 | 流式输出 | stream=True、逐字打印 |
| 3 | 多轮对话 | messages 列表、对话记忆 |
| 4 | 异步编程 | async/await、并发请求 |
| 5 | 工具设计 | Tool ABC、JSON Schema、**MCP 实战** |
| 6 | Agentic Loop | while 循环、工具分发、结果回喂 |
| 7 | 真实工具 | subprocess、文件读写 |
| 8 | 健壮性 | 超时、重试、cwd 追踪 |
| 9 | 权限安全 | 危险命令拦截、持久化规则 |
| 10 | 上下文工程 | CLAUDE.md、**RAG**、**Skills**、滑动窗口 |
| 11 | 完整 REPL | 依赖注入、is_error 信号、全功能合体 |
| 12 | 状态展示 | 事件协议、rich spinner、展示层分离 |

每节课都是独立可运行的单文件，只引入一个新概念。严格按顺序学习。

---

## 快速开始

### 学习教程

```bash
git clone https://github.com/ryanyujazz-dev/learn-agent-from-ClaudeCode.git
cd learn-agent-from-ClaudeCode

# 配置 API Key（支持任何 OpenAI 兼容接口）
export LLM_API_KEY="你的key"
# export LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"  # 可选
# export LLM_MODEL="glm-5.1"                                    # 可选

# 从第 1 课开始
cd tutorial/01-api-first-call
python3 01_hardcode.py
```

详细的环境配置和学习指南见 [tutorial/GUIDE.md](./tutorial/GUIDE.md)。

### 运行 mini-claude

```bash
# 安装
pip install -e .

# 在你想操作的项目目录里运行
cd /path/to/your-project
mini-claude

# 恢复上次会话
mini-claude --resume
```

首次运行时会引导你配置 API。

---

## 课程里你会遇到哪些行业概念

本课不只是写 Python 代码，还会遇到 AI Agent 领域的通用概念：

| 概念 | 在哪一课 | 一句话解释 |
|------|---------|-----------|
| Tool Calling | 第 5-6 课 | LLM 决定调哪个函数、传什么参数 |
| Agentic Loop | 第 6 课 | while 循环：调工具 → 结果回喂 → 继续 |
| MCP | 第 5 课 File 4 | 标准协议，让 agent 动态发现外部工具服务器 |
| RAG | 第 10 课 | 先检索知识，再注入上下文让 LLM 回答 |
| Skills | 第 10 课 | 操作手册，告诉模型按什么步骤完成任务 |
| 依赖注入 | 第 11 课 | 把变化的部分封装进容器，稳定接口 |

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

完成 12 节课后，阅读 [tutorial/architecture.md](./tutorial/architecture.md) ——它解释了每个架构决策背后的"为什么"。

---

## LLM 后端

默认使用 [ZhipuAI](https://open.bigmodel.cn/) GLM-5.1。支持任何 OpenAI 兼容接口：

| 平台 | 申请地址 | 备注 |
|------|---------|------|
| 智谱 AI | https://open.bigmodel.cn/ | 默认配置 |
| DeepSeek | https://platform.deepseek.com/ | 改 `LLM_BASE_URL` 和 `LLM_MODEL` |
| OpenAI | https://platform.openai.com/ | 改 `LLM_BASE_URL` 和 `LLM_MODEL` |
| Ollama 本地 | http://localhost:11434/v1/ | 免费，无需 API Key |

---

## 这个项目不是什么

- 不是 claude-code 的完整复刻（原版有更多工具和更复杂的权限模型）
- 不是生产可用的工具（没有并发工具调用、context window 管理）
- 不是教你使用 claude-code（那直接看官方文档）

它是一个**学习用的参考实现**——读完之后你能理解 AI Agent 的核心机制，然后自己动手写一个。

## License

MIT
