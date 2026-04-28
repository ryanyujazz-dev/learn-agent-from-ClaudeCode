# Lesson 2 — 流式输出

## 本节新概念

**stream=True**：不等 LLM 生成完再返回，而是边生成边接收，逐字打印。

## 为什么需要流式？

非流式：等待 5 秒 → 一次性打印全部文字（用户体验差）
流式：立刻开始打印 → 字一个个出现（像真正的 AI 对话）

## 核心代码解读

```python
stream = client.chat.completions.create(..., stream=True)
for chunk in stream:
    text = chunk.choices[0].delta.content
    if text:
        print(text, end="", flush=True)
```

- `stream=True` 让 API 返回一个"流"对象
- `for chunk in stream` 每次拿到一小块文字
- `delta.content` 是这一块新增的文字（可能为 None，要判断）
- `end=""` 不换行，`flush=True` 立刻输出到屏幕

## 前置准备

### 安装依赖

```bash
pip install openai
# 或使用 uv
uv pip install openai
```

### 配置全局环境变量

第 1 课用 `export` 设置环境变量，但每次开新终端都要重新输入。一劳永逸的方法是写进 shell 配置文件：

```bash
# 查看你的 shell 类型
echo $SHELL
# /bin/zsh → 用 ~/.zshrc
# /bin/bash → 用 ~/.bashrc
```

**zsh 用户（macOS 默认）：**

```bash
echo 'export LLM_API_KEY="你的key"' >> ~/.zshrc
echo 'export LLM_BASE_URL="你的base_url"' >> ~/.zshrc
source ~/.zshrc    # 立即生效
```

**bash 用户：**

```bash
echo 'export LLM_API_KEY="你的key"' >> ~/.bashrc
echo 'export LLM_BASE_URL="你的base_url"' >> ~/.bashrc
source ~/.bashrc
```

配置完后，**所有新终端和 PyCharm 都会自动读取**，后续课程不用再 export。

验证是否生效：

```bash
echo $LLM_API_KEY
# 应打印你的 key
```

> **PyCharm 用户**：配置全局环境变量后，需要**重启 PyCharm** 才能生效。

### 激活虚拟环境

项目使用了虚拟环境（`.venv`），不同运行方式有不同的处理：

**PyCharm**：自动使用项目的虚拟环境，无需额外操作。

**苹果终端**：需要先激活虚拟环境，否则会找不到 `openai` 模块：

```bash
cd /Users/letitbery/PycharmProjects/claude_code_ran
source .venv/bin/activate    # 激活后命令行前会出现 (.venv)
cd tutorial/02-streaming
python streaming.py
```

**Windows 终端**：

```cmd
cd C:\你的路径\claude_code_ran
.venv\Scripts\activate       :: 激活后命令行前会出现 (.venv)
cd tutorial\02-streaming
python streaming.py
```

退出虚拟环境：`deactivate`

> 激活一次后，该终端窗口内后续课程都可以直接运行对应的 `.py` 文件，无需重复激活。

## 运行

```bash
python3 streaming.py
```

## 作业

在循环结束后，打印一行 `\n共收到 X 个 chunk`，统计 chunk 数量。
