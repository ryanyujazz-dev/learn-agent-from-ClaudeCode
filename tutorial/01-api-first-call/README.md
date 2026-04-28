# Lesson 1 — 第一次调用 LLM API

## 本节新概念

- **openai SDK 同步调用**：用 Python 向 LLM 发一条消息，拿到回复。
- **API Key 配置**：三种方式由浅入深，从硬编码到 .env 文件。
- **messages 结构**：`user` 和 `system` 两种角色的消息。

## 前置准备

```bash
pip install openai
pip install python-dotenv    # 仅方式 3 需要
```

## 三个文件，逐步深入

本课有三个 py 文件，**按顺序运行和学习**。每个文件都在前一个基础上多一个新概念。

---

### 文件 1：`01_hardcode.py` — 最快跑通

把 `"YOUR_API_KEY"` 替换成你的真实 key，直接运行：

```bash
python3 01_hardcode.py
```

**新概念**：
- `OpenAI` 客户端对象——负责发 HTTP 请求
- `client.chat.completions.create()`——发消息给 LLM
- `response.choices[0].message.content`——取 LLM 的回复

> key 写在代码里，可以快速验证。但**绝对不要把含有 key 的代码提交到 git 或发给别人**。

---

### 文件 2：`02_env_var.py` — 用户输入 + 环境变量

在文件 1 的基础上新增两个概念：

**新概念 1：`input()` 用户输入**

```python
user_input = input(">>> ")
```

现在你可以在终端里输入自己的问题了，不再是硬编码的提问。

**新概念 2：环境变量读取 key**

```python
api_key=os.environ["LLM_API_KEY"]
```

key 不再写在代码里，而是从系统环境变量读取。设置方法：

```bash
# 终端
export LLM_API_KEY="你的key"
export LLM_BASE_URL="你的base_url"

# PyCharm
# Run Configuration（编辑） → Environment variables（环境变量）中添加
```

运行：

```bash
export LLM_API_KEY="你的key"
python3 02_env_var.py
```

---

### 文件 3：`03_dotenv.py` — system 角色 + .env 文件

在文件 2 的基础上新增两个概念：

**新概念 1：`system` 角色消息**

```python
messages=[
    {"role": "system", "content": "你是一个老练的 Python 程序员..."},
    {"role": "user", "content": user_input},
]
```

`messages` 列表可以包含多条消息，每条有 `role`（角色）：
- `system`：设定 AI 的行为和身份（你是谁、怎么回答）
- `user`：用户的提问

`system` 消息放在最前面，它会影响 AI 回答的风格和方向。

**新概念 2：`.env` 文件**

```python
from dotenv import load_dotenv
load_dotenv()  # 从 .env 文件加载环境变量
```

把 key 写在 `.env` 文件里，程序启动时自动读取。这样每个开发者有自己的 `.env`，不会互相覆盖。

使用方法：

```bash
cp .env.example .env          # 复制模板
# 编辑 .env，填入你的 key
python3 03_dotenv.py
```

**探索提示**：代码里有一行被注释的 `# print(response)`。取消注释运行一次，看看 LLM 返回的完整结构化内容长什么样。

---

## 三种配置方式对比

| | 硬编码 | 环境变量 | .env 文件 |
|---|-------|---------|----------|
| 配置难度 | 最简单 | 中等 | 中等 |
| 代码安全性 | 不安全 | 安全 | 安全 |
| 适合场景 | 试玩 | 个人开发 | 团队协作 |
| 对应文件 | `01_hardcode.py` | `02_env_var.py` | `03_dotenv.py` |

> **后续课程统一使用方式 2（环境变量）**。第 1 课讲透三种方式后，从第 2 课起默认用环境变量。

## 支持的平台

默认使用智谱 AI (ZhipuAI) GLM-5.1。如果要换成其他平台，修改 `base_url` 和 `model` 即可：

| 平台 | base_url | model |
|------|----------|-------|
| 智谱 AI（默认） | `https://open.bigmodel.cn/api/paas/v4/` | `glm-5.1` |
| DeepSeek | `https://api.deepseek.com/` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1/` | `gpt-4o` |
| Ollama 本地 | `http://localhost:11434/v1/` | 你的模型名 |

## 作业

1. 三个文件按顺序跑通，确认理解每个文件新增了什么。
2. 修改 `03_dotenv.py` 的 `system` 消息，把 AI 设定成不同角色（比如英语老师、代码审查员），观察回答风格的变化。
3. （进阶）取消注释 `print(response)`，看看完整返回结构里还有哪些有用的字段。
