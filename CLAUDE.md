# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

A minimal Python implementation of claude-code for learning purposes. Reproduces the core agentic loop, tool system, and memory mechanisms from the original TypeScript codebase.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the REPL
python main.py

# Resume last session
python main.py --resume

# Skip all permission prompts
python main.py --auto
```

## Architecture

The project mirrors the original claude-code architecture in Python:

- **`main.py`** — REPL entry point (readline loop). Loads memory, manages session, calls `query()`.
- **`query.py`** — Core agentic loop (`while True`, max 20 turns): calls LLM API, dispatches tool calls, feeds results back. Corresponds to `src/query.ts`.
- **`tool.py`** — `Tool` ABC, `ToolUseContext` (dependency injection container), `ToolResult`. Three-step permission check. Corresponds to `src/Tool.ts`.
- **`tools/`** — Five built-in tools: `BashTool`, `FileReadTool`, `FileWriteTool`, `GlobTool`, `GrepTool`.
- **`memory/claudemd.py`** — Walks up directory tree collecting `CLAUDE.md` files, injects into system prompt. Corresponds to `src/memdir/`.
- **`memory/session.py`** — Writes `~/.mini-claude/sessions/latest.json` + timestamped archive. Supports `--resume`.
- **`security/command_check.py`** — Dangerous command pattern detection + intent classification. Corresponds to `src/tools/BashTool/bashSecurity.ts`.
- **`security/path_check.py`** — Path traversal detection (prevents escaping cwd).
- **`security/rules.py`** — Persistent allow/deny rules in `~/.mini-claude/permissions.json`. Corresponds to `src/tools/BashTool/bashPermissions.ts`.

## LLM Backend

Uses ZhipuAI GLM-5.1 via OpenAI-compatible API:
- Base URL: `https://open.bigmodel.cn/api/paas/v4/`
- Model: `glm-5.1`
- API key env var: `ZHIPUAI_API_KEY`

## Key Design Patterns

- `query()` is an async generator — yields stream chunks, stops at `end_turn` or `max_turns=20`
- Tools with `is_read_only() == True` run without confirmation; others go through 3-step permission check
- Permission check order: dangerous pattern block → persistent rules → interactive prompt (`y/N/a/d`)
- `ToolUseContext` is passed through every tool call (dependency injection, not globals)
- `BashTool` appends `pwd` to every command to track cwd changes in `context.cwd`
- Session saves to `latest.json` (fast resume) + timestamped archive (history)
