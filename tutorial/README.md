# Mini-Claude 从零到一：12节课构建你自己的 AI Agent

> **新手入门？** 先读 [GUIDE.md](./GUIDE.md) — 环境配置、学习路线、常见问题一网打尽。

## 目标学员

只懂 Python 基础语法（变量、函数、类、for 循环），没有 async/await、API 调用、agent 经验。

## 学完之后你能做什么

构建一个与本项目根目录完全等价的 mini-claude：能调用真实 LLM、执行 bash 命令、读写文件、记住上下文。

## 课程大纲

| # | 文件夹 | 新概念 | 一句话描述 |
|---|--------|--------|-----------|
| 1 | `01-api-first-call` | openai SDK | 10行代码问 GLM 一个问题 |
| 2 | `02-streaming` | stream=True | 逐字打印，像真正的 AI |
| 3 | `03-multi-turn` | messages 列表 | 多轮对话，LLM 记住上下文 |
| 4 | `04-async-intro` | async/await | 异步版多轮对话 + 并发演示 |
| 5 | `05-tool-design` | ABC 抽象类 | 定义统一的工具接口 |
| 6 | `06-agentic-loop` | while + tool dispatch | 完整 agentic loop |
| 7 | `07-real-tools` | subprocess + 文件读写 | 让 agent 真正执行命令 |
| 8 | `08-robustness` | 超时+重试+cwd追踪 | 生产级健壮性工程 |
| 9 | `09-permission` | 正则 + 持久化规则 | 危险命令被拦截 |
| 10 | `10-memory` | CLAUDE.md + RAG + Skills | 上下文工程：记忆、检索、行为指令 |
| 11 | `11-full-repl` | ToolUseContext + is_error | 完整 mini-claude REPL |
| 12 | `12-rich-status` | 事件协议 + rich spinner | 实时展示 agent 状态 |

## 运行方式

```bash
# 配置 API Key（只需一次）
# 支持任何 OpenAI 兼容接口：ZhipuAI、OpenAI、DeepSeek、Ollama 等
export LLM_API_KEY="你的key"
export LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"  # 可选，默认 ZhipuAI
export LLM_MODEL="glm-5.1"                                    # 可选，默认 glm-5.1

# 每节课独立运行
cd tutorial/01-api-first-call
python3 main.py
```

## 进阶阅读

完成12节课后，阅读 [architecture.md](./architecture.md) — 系统讲解每个架构决策背后的"为什么"。

## 学习建议

1. 按顺序学，每节课都跑通再进入下一节
2. 完成每节课末尾的作业
3. 遇到不懂的地方，先跑代码看效果，再读解释
