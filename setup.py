from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent


setup(
    name="mini-claude",
    version="0.1.0",
    description="A minimal Python coding agent tutorial.",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["mini_claude", "mini_claude.*"]),
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.0.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mini-claude=mini_claude.main:cli",
        ],
    },
)
