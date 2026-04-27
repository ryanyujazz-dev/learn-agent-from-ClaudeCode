try:
    from mini_claude.main import cli
except ModuleNotFoundError as exc:
    missing = exc.name or "a dependency"
    raise SystemExit(
        f"Missing Python package: {missing}\n"
        "Install mini-claude first:\n"
        "  cd /Users/letitbery/PycharmProjects/claude_code_ran\n"
        "  pip install -e ."
    ) from exc


if __name__ == "__main__":
    cli()
