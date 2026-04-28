"""
Lesson 3 进阶：会话持久化
新概念: json.dump/json.load, 退出保存, 启动恢复

在 02_multi_turn.py 基础上加 5 行代码，让 AI 跨会话记住你。
退出后再运行，AI 还记得之前的对话。
"""
import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)

SYSTEM_PROMPT = """
你是一个python学习助手，你需要帮助用户解决各种问题。
"""

# ── 会话文件路径 ──────────────────────────────────────────────
# __file__ 是当前 .py 文件的路径，比如 "03_persistent.py"
# os.path.abspath(__file__) → 绝对路径，如 "/Users/xxx/03-multi-turn/03_persistent.py"
# os.path.dirname(...)      → 取目录部分，如 "/Users/xxx/03-multi-turn/"
# os.path.join(...)          → 拼接路径，目录 + 子目录 + 文件名
#
# 为什么要构建绝对路径？
# 因为 os.path.exists("session.json") 检查的是"你从哪个目录运行脚本"（cwd），
# 而不是"脚本在哪个目录"。比如你从 /Users/xxx/ 运行脚本，
# 它会检查 /Users/xxx/session.json，而不是脚本旁边的 session.json。
# 用绝对路径就不会有这个问题。
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
SESSION_FILE = os.path.join(DATA_DIR, "session.json")



# 加载上次的对话历史（如果有）
def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# 保存对话历史到文件
def save_session(messages):
    os.makedirs(DATA_DIR, exist_ok=True)  # 目录不存在则创建，已存在则忽略
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


# 启动时恢复历史
messages = load_session()
if messages:
    print(f"[已恢复上次的对话，共 {len(messages)} 条消息]")
else:
    print("[新会话]")

print("持久化多轮对话（输入 /quit 退出保存）\n")

while True:
    user_input = input(">>> ").strip()
    if user_input == "/quit":
        save_session(messages)
        print("[对话已保存，下次运行会自动恢复]")
        break
    if not user_input:
        continue

    print("AI: ", end="")
    messages.append({"role": "user", "content": user_input})
    system_message = {"role": "system", "content": SYSTEM_PROMPT}
    api_messages = [system_message] + messages

    stream = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "glm-5.1"),
        messages=api_messages,
        stream=True,
    )

    reply = ""
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            print(text, end="", flush=True)
            reply += text
    print()

    messages.append({"role": "assistant", "content": reply})
    save_session(messages)  # 每轮自动保存，防止意外退出丢失
