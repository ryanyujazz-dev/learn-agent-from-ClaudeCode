import os


def load_claudemd(start_dir: str = None) -> str:
    """
    Walk up from start_dir collecting CLAUDE.md files.
    Mirrors src/memdir/memdir.ts — injects project memory into system prompt.
    """
    parts = []
    current = os.path.abspath(start_dir or os.getcwd())
    visited = set()

    while True:
        if current in visited:
            break
        visited.add(current)

        path = os.path.join(current, "CLAUDE.md")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    parts.append(f"# Memory from {path}\n{content}")
            except Exception:
                pass

        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return "\n\n".join(reversed(parts))  # root-first, like original
