import os


def check_path(path: str, cwd: str) -> tuple[bool, str]:
    """
    Ensure path stays within cwd — mirrors pathValidation.ts.
    Returns (safe, reason).
    """
    resolved = os.path.realpath(os.path.join(cwd, path))
    base = os.path.realpath(cwd)
    if not resolved.startswith(base + os.sep) and resolved != base:
        return False, f"path escapes working directory: {resolved}"
    return True, ""
