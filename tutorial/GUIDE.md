# Mini-Claude 课程使用指南

> 本文档帮助你高效地完成这 12 节课。如果你是第一次打开这个项目，从这里开始。

---

## 一、你需要什么基础

- **Python 语法**：变量、函数、类、for 循环、字典操作
- **命令行**：能运行 `python3 xxx.py` 和 `export`
- **不需要**：async/await 经验、API 调用经验、AI Agent 知识（课程会教你）

---

## 二、环境准备（5 分钟）

### 1. 安装依赖

```bash
pip install openai
pip install rich    # 仅第 12 课需要
```

### 2. 配置 API Key

第 1 课提供了三种配置方式（硬编码、环境变量、.env 文件），由浅入深讲解。详见第 1 课 README。

**最快跑通**：运行第 1 课的 `01_hardcode.py`，把 `"你的key"` 改成你的真实 key 即可。

**如果你没有 API Key**，可以去以下平台申请（都提供免费额度）：

| 平台 | 申请地址 | 备注 |
|------|---------|------|
| 智谱 AI | https://open.bigmodel.cn/ | 默认配置 |
| DeepSeek | https://platform.deepseek.com/ | 改 `LLM_BASE_URL` 和 `LLM_MODEL` |
| OpenAI | https://platform.openai.com/ | 改 `LLM_BASE_URL` 和 `LLM_MODEL` |
| Ollama 本地 | http://localhost:11434/v1/ | 免费，无需 API Key |

### 3. PyCharm 用户注意

- **第 1 课方式 1（硬编码）**：直接运行 `01_hardcode.py`，不需要任何配置。
- **第 1 课方式 2（环境变量）及后续课程**：PyCharm 不会读取终端 `export` 的环境变量，需要在运行配置里单独设置：
  1. 点击右上角运行按钮旁的下拉菜单 → **Edit Configurations...**
  2. 左侧选中你要运行的 `.py` 文件
  3. 找到 **Environment variables**，点击右边的图标
  4. 点 **+** 添加：

  | Name | Value |
  |------|-------|
  | `LLM_API_KEY` | 你的 key |

  5. 点 **OK** 保存，重新运行

### 4. 验证环境

```bash
cd tutorial/01-api-first-call
python3 main.py
```

看到 LLM 的回复就说明环境就绪。

---

## 三、课程结构

### 学习路线

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

**严格按顺序学习。** 每节课依赖前一课的知识，不能跳过。

### 概念依赖图

```
Lesson 1 (API)
  └─ Lesson 2 (stream)
       └─ Lesson 3 (multi-turn)
            └─ Lesson 4 (async)
                 └─ Lesson 5 (Tool ABC)
                      └─ Lesson 6 (Agentic Loop)
                           └─ Lesson 7 (Real Tools)
                                ├─ Lesson 8 (Robustness)
                                ├─ Lesson 9 (Permission)
                                └─ Lesson 10 (Memory)
                                     └─ Lesson 11 (Full REPL)
                                          └─ Lesson 12 (Rich Status)
```

### 每课时间参考

| 阶段 | 课程 | 预计时间 |
|------|------|---------|
| 基础篇 | 1-4 课 | 各 15-20 分钟 |
| 核心篇 | 5-6 课 | 各 30-45 分钟 |
| 核心篇 | 7-8 课 | 各 20-30 分钟 |
| 工程篇 | 9-10 课 | 各 20-30 分钟 |
| 工程篇 | 11-12 课 | 各 30-45 分钟 |

总计约 **4-5 小时**，建议分 2-3 次学完。

---

## 四、如何学每一课

### 每课标准流程

```
1. 读 README.md → 理解新概念
2. 运行本课 .py 文件 → 看效果
3. 读代码 → 对照 README 理解
4. 做作业 → 动手实践
5. 进入下一课
```

### 三个实用建议

1. **先跑代码，再看解释** — 运行效果比文字描述更直观
2. **必须做作业** — 每课作业都刻意设计为 5-15 分钟的小练习，不做作业等于没学
3. **对照变更摘要** — 第 6 课起每课 README 有"本课相对上一课的变更"表格，帮你快速定位新增代码

### 重要提示：功能积累方式

从第 8 课开始，每课为了聚焦新概念，会**暂时不包含前几课的部分功能**（如超时、权限等）。这不影响学习——所有功能会在第 11-12 课完整合齐。每课 README 的变更摘要会如实标注。

---

## 五、课程速查表

| # | 文件夹 | 新概念 | 作业 | 运行提示 |
|---|--------|--------|------|---------|
| 1 | `01-api-first-call` | openai SDK 同步调用 | 换一个问题问 LLM | 直接运行 |
| 2 | `02-streaming` | stream=True 流式输出 | 统计 chunk 数量 | 观察逐字打印 |
| 3 | `03-multi-turn` | messages 列表多轮对话 | 加 `/clear` 命令 | 输入 `/quit` 退出 |
| 4 | `04-async-intro` | async/await + AsyncOpenAI | 用 gather 并发两个请求 | 行为与第 3 课一样，只是写法变了 |
| 5 | `05-tool-design` | ABC 抽象类 + JSON Schema + MCP | 实现 AddTool | File 4 需安装 mcp 包 |
| 6 | `06-agentic-loop` | while 循环 + tool dispatch | 观察 tool_calls 分 chunk 到达 | 说"帮我 echo hello" |
| 7 | `07-real-tools` | subprocess + 文件读写 | 实现 FileWriteTool | 说"列出当前目录的文件" |
| 8 | `08-robustness` | 超时 + 重试 + cwd 追踪 | 改超时为 5 秒测试 | 试"cd /tmp"和"sleep 60" |
| 9 | `09-permission` | 正则拦截 + 持久化规则 | 加 shutdown 拦截规则 | 试"rm -rf /"被拦截 |
| 10 | `10-context_engineering` | CLAUDE.md + RAG + Skills | 写自定义 skill 文件 | File 3-4 需思考检索和指令注入 |
| 11 | `11-full-repl` | ToolUseContext + is_error | 对比根目录 main.py | 用 `--auto` 跳过权限 |
| 12 | `12-rich-status` | 事件协议 + rich spinner | 改 `_tool_summary()` | 需安装 rich |

---

## 六、常见问题

### 运行报错：`KeyError: 'LLM_API_KEY'`

环境变量未设置。回到[环境准备](#二环境准备5-分钟)设置 `LLM_API_KEY`。

### 运行报错：`ImportError: attempted relative import with no known parent package`

不能直接运行 `mini_claude/main.py`。应该运行每节课目录下的对应文件：

```bash
cd tutorial/02-streaming
python3 streaming.py
```

### API 调用报错：`ConnectionError` / `TimeoutError`

检查网络连接和 `LLM_BASE_URL` 是否正确。如果用智谱，确保地址是 `https://open.bigmodel.cn/api/paas/v4/`（注意末尾斜杠）。

### 模型说"我是 Claude"或答非所问

这是 LLM 的正常行为——模型会根据训练数据自我介绍。这不影响课程学习。

### 第 5 课没有调用 LLM？

是的。第 5 课纯讲工具系统设计（ABC + JSON Schema），不调用 API。第 6 课才把工具接入 LLM。

### 第 10 课以后功能变少了？

每课为聚焦新概念做了精简，所有功能在第 11-12 课完整合齐。详见每课 README 的变更摘要。

---

## 七、学完之后

完成 12 节课后，你有两条路：

### 路线 A：阅读完整项目

阅读项目根目录的代码，你会认出每一行的来源：

```
mini_claude/
├── main.py       ← Lesson 11-12 的完整版
├── query.py      ← Lesson 6 + 12 的完整版
├── tool.py       ← Lesson 5 + 11 的完整版
├── tools/        ← Lesson 7 + glob/grep
├── memory/       ← Lesson 10 的完整版
└── security/     ← Lesson 9 的完整版
```

同时阅读 [architecture.md](./architecture.md)，理解每个架构决策背后的"为什么"。

### 路线 B：进阶练习

| 练习 | 难度 | 提示 |
|------|------|------|
| 实现并发工具调用 | 中 | LLM 可一次返回多个 tool_calls，用 `asyncio.gather()` |
| 添加 GlobTool | 低 | 参考 `mini_claude/tools/glob_tool.py` |
| 添加 GrepTool | 中 | 参考 `mini_claude/tools/grep_tool.py` |
| 实现 context window 管理 | 高 | 超过 token 限制时截断或压缩 messages |
| 支持 Esc 中断 | 高 | 参考根目录 `main.py` 的线程监听方案 |

---

## 八、课程文件说明

```
tutorial/
├── GUIDE.md            ← 你正在读的这个文件
├── README.md           ← 课程大纲概览
├── architecture.md     ← 学完后读的架构专题
├── 01-api-first-call/
│   ├── README.md       ← 概念讲解
│   └── main.py         ← 可运行的代码
├── 02-streaming/
│   ├── README.md
│   └── streaming.py
├── 03-multi-turn/
│   ├── README.md
│   └── multi_turn.py
├── 04-async-intro/
│   ├── README.md
│   └── async_chat.py
├── 05-tool-design/
│   ├── README.md
│   └── tool_design.py
├── 06-agentic-loop/
│   ├── README.md
│   └── agentic_loop.py
├── 07-real-tools/
│   ├── README.md
│   └── real_tools.py
├── 08-robustness/
│   ├── README.md
│   └── robust_agent.py
├── 09-permission/
│   ├── README.md
│   └── permission_agent.py
├── 10-context_engineering/
│   ├── README.md
│   ├── 01_memory_agent.py
│   ├── 02_sliding_window.py
│   ├── 03_simple_rag.py
│   ├── 04_skills.py
│   └── skills/
│       ├── code_review.md
│       └── explain_code.md
├── 11-full-repl/
│   ├── README.md
│   └── full_repl.py
└── 12-rich-status/
    ├── README.md
    └── rich_agent.py
```

每节课都是**独立可运行的单文件**，不需要导入其他课的代码。
