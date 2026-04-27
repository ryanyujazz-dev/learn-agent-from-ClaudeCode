import json
import os
import asyncio
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI, APIError
from tool import Tool, ToolUseContext, ToolResult
from config import load_config

_client: Optional[AsyncOpenAI] = None
_model: Optional[str] = None

def _get_client() -> AsyncOpenAI:
    global _client, _model
    if _client is None:
        cfg = load_config()
        _model = cfg["model"]
        _client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    return _client


def get_model() -> str:
    if _model is None:
        _get_client()
    return _model


async def _create_stream_with_retry(client, **kwargs):
    """Retry API calls on transient errors — mirrors withRetry.ts."""
    for attempt in range(3):
        try:
            return await client.chat.completions.create(**kwargs)
        except APIError as e:
            if attempt == 2 or e.status_code in (400, 401, 403):
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _tools_to_schema(tools: list) -> list:
    return [t.to_api_schema() for t in tools]


def _tool_summary(name: str, args: dict, result: "ToolResult") -> str:
    """Generate a human-readable one-line summary for a tool call."""
    if name == "bash":
        cmd = args.get("command", "").split("\n")[0][:40]
        return f"bash({cmd})"
    if name == "file_write":
        lines = args.get("content", "").count("\n") + 1
        return f"file_write({args.get('path', '')}) [{lines} lines]"
    if name == "file_read":
        return f"file_read({args.get('path', '')})"
    if name == "glob":
        return f"glob({args.get('pattern', '')})"
    if name == "grep":
        return f"grep({args.get('pattern', '')!r})"
    return name


async def _dispatch_tool(name: str, args: dict, context: ToolUseContext) -> ToolResult:
    for tool in context.tools:
        if tool.name == name:
            return await tool.call(args, context)
    return ToolResult(data=f"Unknown tool: {name}", error=True)


async def query(
    messages: list[dict],
    system_prompt: str,
    context: ToolUseContext,
    max_turns: int = 20,
) -> AsyncGenerator[str, None]:
    """
    Core agentic loop — mirrors src/query.ts queryLoop.

    Yields text chunks as they stream. Mutates `messages` in place
    (appends assistant turns and tool results), so the caller's list
    stays up-to-date for session persistence.
    """
    client = _get_client()
    api_messages = [{"role": "system", "content": system_prompt}] + messages if system_prompt else list(messages)
    turn = 0

    while turn < max_turns:
        # 1. Stream from LLM (with retry)
        stream = await _create_stream_with_retry(
            client,
            model=get_model(),
            messages=api_messages,
            tools=_tools_to_schema(context.tools) or None,
            stream=True,
        )

        # Accumulate the full response
        full_text = ""
        tool_calls_raw: dict[int, dict] = {}  # index → {id, name, arguments}

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # Text content
            if delta.content:
                full_text += delta.content
                yield delta.content  # stream to caller

            # Tool call deltas
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_raw:
                        tool_calls_raw[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_raw[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            # Use assignment not +=: name arrives complete in first chunk
                            tool_calls_raw[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_raw[idx]["arguments"] += tc.function.arguments

            finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

        # 2. Build assistant message and append to history
        assistant_msg: dict = {"role": "assistant", "content": full_text or None}
        if tool_calls_raw:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls_raw.values()
            ]
        messages.append(assistant_msg)
        api_messages.append(assistant_msg)

        # 3. Stop if no tool calls
        if not tool_calls_raw:
            return

        turn += 1

        # 4. Dispatch tools and collect results
        for tc in tool_calls_raw.values():
            try:
                args = json.loads(tc["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}

            yield f"\x00TOOL:{tc['name']}:{json.dumps(args, ensure_ascii=False)}"
            result = await _dispatch_tool(tc["name"], args, context)
            summary = _tool_summary(tc["name"], args, result)
            yield f"\x00DONE:{'ERR' if result.error else 'OK'}:{summary}"

            tool_msg = {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result.data),
                # is_error signals the model that the tool failed — mirrors original
                **({"is_error": True} if result.error else {}),
            }
            messages.append(tool_msg)
            api_messages.append(tool_msg)

        # 5. Continue loop with tool results fed back

    yield f"\n[max_turns={max_turns} reached, stopping]\n"
