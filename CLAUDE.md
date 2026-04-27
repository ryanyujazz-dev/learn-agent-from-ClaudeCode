# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

A minimal Python implementation of claude-code for learning purposes. Reproduces the core agentic loop, tool system, and memory mechanisms from the original TypeScript codebase.

## Commands

```bash
# Install dependencies
pip install -e .

# Run from the project you want mini-claude to operate on
mini-claude

# Resume last session
mini-claude --resume

# Skip all permission prompts
mini-claude --auto

# Source-tree compatibility entry point
python main.py
```

## Architecture

The project mirrors the original claude-code architecture in Python:

- **`setup.py`** — Python package metadata and `mini-claude` console script.
- **`main.py`** — Thin compatibility wrapper for `python main.py`.
- **`mini_claude/main.py`** — REPL entry point (readline loop). Loads memory, manages session, calls `query()`.
- **`mini_claude/query.py`** — Core agentic loop (`while True`, max 20 turns): calls LLM API, dispatches tool calls, feeds results back. Corresponds to `src/query.ts`.
- **`mini_claude/tool.py`** — `Tool` ABC, `ToolUseContext` (dependency injection container), `ToolResult`. Three-step permission check. Corresponds to `src/Tool.ts`.
- **`mini_claude/tools/`** — Five built-in tools: `BashTool`, `FileReadTool`, `FileWriteTool`, `GlobTool`, `GrepTool`.
- **`mini_claude/memory/claudemd.py`** — Walks up directory tree collecting `CLAUDE.md` files, injects into system prompt. Corresponds to `src/memdir/`.
- **`mini_claude/memory/session.py`** — Writes `~/.mini-claude/sessions/latest.json` + timestamped archive. Supports `--resume`.
- **`mini_claude/security/command_check.py`** — Dangerous command pattern detection + intent classification. Corresponds to `src/tools/BashTool/bashSecurity.ts`.
- **`mini_claude/security/path_check.py`** — Path traversal detection (prevents escaping cwd).
- **`mini_claude/security/rules.py`** — Persistent allow/deny rules in `~/.mini-claude/permissions.json`. Corresponds to `src/tools/BashTool/bashPermissions.ts`.

## LLM Backend

Uses an OpenAI-compatible API configured by the first-run wizard:
- Config file: `~/.mini-claude/config.json`
- Default base URL: `https://open.bigmodel.cn/api/paas/v4/`
- Default model: `glm-5.1`

## Key Design Patterns

- `query()` is an async generator — yields stream chunks, stops at `end_turn` or `max_turns=20`
- Tools with `is_read_only() == True` run without confirmation; others go through 3-step permission check
- Permission check order: dangerous pattern block → persistent rules → interactive prompt (`y` once, `a` allow this tool for the session, default deny)
- `ToolUseContext` is passed through every tool call (dependency injection, not globals)
- `BashTool` appends `pwd` to every command to track cwd changes in `context.cwd`
- Session saves to `latest.json` (fast resume) + timestamped archive (history)
