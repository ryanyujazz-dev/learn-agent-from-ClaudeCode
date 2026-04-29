"""
Lesson 10 File 3：简易 Pipeline RAG
新概念: 知识库检索, 检索结果注入上下文

前两个文件讲了 CLAUDE.md（静态知识注入）和滑动窗口（上下文裁剪）。
本文件演示 RAG 的核心流程：用户提问 → 检索相关知识 → 注入上下文 → LLM 回复。

这里用关键词匹配做检索（简化版，不需要向量数据库）。
生产环境的 RAG 通常用向量数据库（如 Chroma、FAISS）做语义检索，
原理一样，只是"怎么找到相关内容"这步更精确。
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI


# ── 知识库 ──────────────────────────────────────────────────
# 实际项目中，知识库可能是：
#   - 向量数据库（Chroma, FAISS, Pinecone）
#   - 全文搜索引擎（Elasticsearch）
#   - 或者像这里，一个简单的字典
# 这里用关键词匹配做检索，是为了不引入额外依赖，聚焦 RAG 流程。

KNOWLEDGE_BASE: list[dict] = [
    {
        "title": "Agentic Loop 工作原理",
        "content": "Agentic Loop 的核心是一个 while 循环。每轮：1) 调 LLM；2) 如果 LLM "
                   "返回 tool_calls，执行工具并把结果回喂；3) 如果没有 tool_calls，输出文字，循环结束。"
                   "max_turns 参数防止无限循环。",
        "keywords": ["agentic", "loop", "while", "循环", "工具", "回喂"],
    },
    {
        "title": "Tool Calling 协议",
        "content": "OpenAI 兼容 API 的 tool calling 流程：1) 用 tools 参数注册工具（名字 + JSON Schema）；"
                   "2) LLM 返回 tool_calls（包含工具名和参数）；3) 程序执行工具，结果以 role='tool' "
                   "消息回喂；4) LLM 基于结果继续回复。tool_call_id 用来匹配调用和结果。",
        "keywords": ["tool", "calling", "工具", "tool_call_id", "schema"],
    },
    {
        "title": "CLAUDE.md 记忆机制",
        "content": "CLAUDE.md 是项目级的静态记忆。Agent 启动时向上遍历目录，收集所有 CLAUDE.md 文件，"
                   "注入到 system prompt。这样无论在哪个子目录运行，agent 都能读到项目说明。"
                   "它和会话记忆（latest.json）不同：CLAUDE.md 每次启动都一样，会话记忆是动态的对话历史。",
        "keywords": ["CLAUDE.md", "记忆", "memory", "system prompt", "目录", "遍历"],
    },
    {
        "title": "流式输出与 tool_calls 拼接",
        "content": "流式输出时，一个工具调用的参数分多个 chunk 到达。用字典收集：name 用 =（只来一次），"
                   "arguments 用 +=（分块拼接）。流结束后用 json.loads() 解析完整的 arguments。"
                   "文字内容直接逐 chunk 打印，工具参数需要先拼接再解析。",
        "keywords": ["stream", "流式", "chunk", "拼接", "delta", "tool_calls"],
    },
]


def search_knowledge_base(query: str, top_k: int = 2) -> list[dict]:
    """
    简易检索：用关键词匹配找到最相关的文档。

    生产环境会用向量数据库做语义检索：
      query → embedding → 在向量空间中找最近邻 → 返回最相关的文档
    这里用关键词匹配，效果差一些，但不需要额外依赖。
    """
    query_lower = query.lower()
    scored: list[tuple[int, dict]] = []
    for doc in KNOWLEDGE_BASE:
        # 统计 query 命中了多少个关键词
        hits = sum(1 for kw in doc["keywords"] if kw.lower() in query_lower)
        if hits > 0:
            scored.append((hits, doc))

    # 按命中数排序，取 top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


# ── 工具基类（复用自 01）───────────────────────────────────
@dataclass
class ToolResult:
    data: str
    error: bool = False


class Tool(ABC):
    name: str = ""
    description_text: str = ""
    input_schema: dict = {}

    @abstractmethod
    async def call(self, args: dict, cwd: str) -> ToolResult: ...

    def to_api_schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description_text,
            "parameters": self.input_schema,
        }}


class BashTool(Tool):
    name = "bash"
    description_text = "执行 shell 命令"
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    async def call(self, args: dict, cwd: str) -> ToolResult:
        proc = await asyncio.create_subprocess_shell(
            args["command"], cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return ToolResult(data=(stdout.decode() + stderr.decode()).strip())


# ── Agentic Loop ──────────────────────────────────────────────
client = AsyncOpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
)
TOOLS = [BashTool()]


async def query(messages: list, system_prompt: str, cwd: str, max_turns: int = 10):
    api_messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + messages
    turn = 0
    while turn < max_turns:
        stream = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "glm-5.1"), messages=api_messages,
            tools=[t.to_api_schema() for t in TOOLS], stream=True,
        )
        full_text = ""
        tool_calls_raw: dict[int, dict] = {}
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue
            if delta.content:
                full_text += delta.content
                yield delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_raw:
                        tool_calls_raw[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_raw[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_raw[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_raw[idx]["arguments"] += tc.function.arguments

        assistant_msg = {"role": "assistant", "content": full_text or None}
        if tool_calls_raw:
            assistant_msg["tool_calls"] = [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                for tc in tool_calls_raw.values()
            ]
        messages.append(assistant_msg)
        api_messages.append(assistant_msg)
        if not tool_calls_raw:
            return
        turn += 1
        for tc in tool_calls_raw.values():
            args = json.loads(tc["arguments"] or "{}")
            tool = next((t for t in TOOLS if t.name == tc["name"]), None)
            result = await tool.call(args, cwd) if tool else ToolResult(data="未知工具", error=True)
            yield f"\n[{tc['name']}]: {result.data[:300]}\n"
            tool_msg = {"role": "tool", "tool_call_id": tc["id"], "content": result.data}
            messages.append(tool_msg)
            api_messages.append(tool_msg)

    yield f"\n[已达到最大轮数 {max_turns}]\n"


async def main():
    cwd = os.getcwd()

    print("简易 Pipeline RAG 演示")
    print("提问时，系统会自动检索知识库，把相关内容注入上下文。")
    print("试试：「agentic loop 是怎么工作的？」或「流式输出的参数怎么拼？」\n")

    messages: list[dict] = []

    while True:
        user_input = input("你: ").strip()
        if user_input == "/quit":
            break
        if not user_input:
            continue

        # ── RAG 核心：检索 + 注入 ──────────────────────────
        # 1. 检索：根据用户问题，从知识库找到相关文档
        results = search_knowledge_base(user_input, top_k=2)

        if results:
            # 2. 拼接：把检索到的文档格式化成文本
            context_parts = []
            for i, doc in enumerate(results, 1):
                context_parts.append(f"【参考文档 {i}】{doc['title']}\n{doc['content']}")
            context_text = "\n\n".join(context_parts)

            # 3. 注入：把检索结果放到 system prompt 里
            #    这就是 Pipeline RAG 的核心——用户无感知，系统自动完成
            system_prompt = (
                f"以下是知识库中与用户问题相关的参考文档：\n\n"
                f"{context_text}\n\n"
                f"请基于以上参考文档回答用户的问题。如果参考文档中没有相关信息，请如实说明。"
            )
            print(f"  [检索到 {len(results)} 篇相关文档: {', '.join(d['title'] for d in results)}]")
        else:
            system_prompt = "知识库中没有找到与用户问题相关的文档。请根据你的知识回答。"
            print("  [未检索到相关文档]")

        # 4. 把用户问题加入 messages，调 LLM
        messages.append({"role": "user", "content": user_input})
        print("AI: ", end="")
        async for text in query(messages, system_prompt, cwd):
            print(text, end="", flush=True)
        print("\n")


asyncio.run(main())
