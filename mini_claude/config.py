import json
from pathlib import Path

CONFIG_FILE = Path.home() / ".mini-claude" / "config.json"

_DEFAULTS = {
    "base_url": "https://open.bigmodel.cn/api/paas/v4/",
    "model": "glm-5.1",
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return _setup_wizard()


def _setup_wizard() -> dict:
    print("\n欢迎使用 mini-claude！首次运行需要配置 LLM 接口。")
    print("支持任何 OpenAI 兼容接口（ZhipuAI、OpenAI、DeepSeek、Ollama 等）\n")

    base_url = input(f"API Base URL（回车使用默认 {_DEFAULTS['base_url']}）: ").strip()
    if not base_url:
        base_url = _DEFAULTS["base_url"]

    api_key = input("API Key: ").strip()
    while not api_key:
        print("API Key 不能为空")
        api_key = input("API Key: ").strip()

    model = input(f"模型名称（回车使用默认 {_DEFAULTS['model']}）: ").strip()
    if not model:
        model = _DEFAULTS["model"]

    config = {"base_url": base_url, "api_key": api_key, "model": model}
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    print(f"\n配置已保存到 {CONFIG_FILE}\n")
    return config
